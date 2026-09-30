package com.nikonhacker.emu;

import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.memory.listener.MemoryActivityListener;

import java.util.*;

/**
 * Périphériques du processeur B du D40, au strict nécessaire pour démarrer.
 *
 * - 0x0000-0x0FFF : registres internes du FR (minuteries à recharge 0x48.., DICR 0x44, ICR 0x440..).
 * - 0x40000000-0x5FFFFFFF : registres de l'ASIC d'image et ports (comportement de RAM par défaut,
 *   valeurs forcées dans {@link #overrides} quand le code attend un bit d'état).
 *
 * Chaque registre touché est journalisé (premières lectures et écritures, avec le PC).
 */
public class D40Io implements MemoryActivityListener {

    final D40Emu e;
    public boolean logAccess = true;
    public int logPerAddress = 3;
    final Map<Integer, int[]> counts = new TreeMap<>();   // adresse -> {lectures, écritures}
    /** Valeur forcée à la lecture (registres d'état). Clé = adresse, valeur = fonction de la valeur en mémoire. */
    public final Map<Integer, java.util.function.IntUnaryOperator> overrides = new HashMap<>();

    // Minuteries à recharge 16 bits (3 canaux)
    final int[] tmrlr = new int[3], tmr = new int[3], tmcsr = new int[3];
    final long[] acc = new long[3];
    public int timerScale = 1; // nombre de comptes par instruction et par diviseur (réglage de vitesse)

    D40Io(D40Emu e) {
        this.e = e; this.fakeA = new FakeA(e);
        // Codec JPEG 0x40030000 : après écriture de 0x4000 en 0x400, le code attend 0xC000 (prêt).
        overrides.put(0x40030400, v -> (v & 0x4000) != 0 ? (v | 0x8000) : v);
    }

    // ---- Liaison série 0 vers le processeur A (mode synchrone) ----
    // Registres (disposition des anciens FR) : 0x60 SSR0, 0x61 SIDR0/SODR0, 0x62 SCR0, 0x63 SMR0.
    // Poignée de main : 0x50000106 bit 4 = le B est prêt pour l'octet suivant (« strobe »).
    // Interruption de réception : 0x1B ; ligne de requête du A : interruption externe canal 1 (0x1F),
    // registres EIRR 0x38, ENIR 0x39, ELVR 0x3A.
    public final FakeA fakeA;
    /** Touches lues directement par le B sur le port 0x5000010C (bit à 1 = enfoncée). */
    public int portCKeys = 0;
    int sioRx = 0; boolean sioRxFull = false; int sioTx = 0; long sioCountdown = -1;
    public int sioDelay = 400; // instructions entre la poignée de main et l'octet reçu
    public long sioBytes = 0;

    @Override public boolean matches(int a) {
        return (a >= 0 && a < 0x1000) || (a >= 0x40000000 && a < 0x60000000);
    }
    @Override public boolean isReadOnly() { return false; }

    void note(boolean write, int a, int v, int size) {
        int[] c = counts.computeIfAbsent(a, k -> new int[2]);
        int n = c[write ? 1 : 0]++;
        if (logAccess && n < logPerAddress) {
            e.log.printf("IO %s%d %08X %s %0" + (size * 2) + "X @%08X%n", write ? "W" : "R", size * 8, a,
                    write ? "<-" : "->", v, e.cpu.pc);
        }
    }

    Integer readReg(int a, int v, int size) {
        java.util.function.IntUnaryOperator o = overrides.get(a);
        if (o != null) return o.applyAsInt(v);
        // minuteries
        for (int ch = 0; ch < 3; ch++) {
            int base = 0x48 + 8 * ch;
            if (a == base + 2 && size == 2) return tmr[ch];
            if (a == base + 6 && size == 2) return tmcsr[ch];
        }
        if (a == 0x44) return 0xFE; // DICR : bits hauts à 1
        if (a == 0x40060032 && size == 2) return g2dStatus;
        if (a == 0x40021FFE && size == 2) return rszStatus;
        if (a == 0x50000102 && size == 1) return (v & ~8) | (field << 3); // parité de trame vidéo
        if (a == 0x5000010C && size == 1) return 0x3F & ~portCKeys;          // touches du B, actives à 0
        if (a == 0x60 && size == 1) return 0x08 | (sioRxFull ? 0x10 : 0); // SSR0 : TDRE, RDRF, pas d'erreur
        if (a == 0x61 && size == 1) { sioRxFull = false; e.intc.removeRequest(0x1B); return sioRx; }
        return null;
    }

    @Override public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {
        Integer r = readReg(a, v & 0xFF, 1);
        note(false, a, r == null ? v & 0xFF : r, 1);
        return r == null ? null : (byte) (int) r;
    }
    @Override public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {
        Integer r = readReg(a, v & 0xFFFF, 2);
        note(false, a, r == null ? v & 0xFFFF : r, 2);
        return r;
    }
    @Override public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {
        Integer r = readReg(a, v, 4);
        note(false, a, r == null ? v : r, 4);
        return r;
    }
    @Override public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
    @Override public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
    @Override public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}

    // ---- Moteur 2D 0x40060000 (remplissage / copie de rectangles), interruption 0x24 ----
    // 0x80 commande, 0x8C pas source, 0x8E pas destination, 0x90 largeur (octets), 0x92 hauteur,
    // 0x94 source, 0x98 destination ; état en 0x32 (bit 0x20 = fin, écrire 1 efface).
    int g2dStatus = 0;
    public boolean logG2d = true;
    public final Map<Integer, Integer> g2dCmds = new TreeMap<>();

    void g2dCommand(int cmd) {
        if (cmd == 0) return;
        int B = 0x40060000;
        int sstride = e.rd16(B + 0x8C), dstride = e.rd16(B + 0x8E), w = e.rd16(B + 0x90), h = e.rd16(B + 0x92);
        int src = e.rd32(B + 0x94), dst = e.rd32(B + 0x98);
        g2dCmds.merge(cmd & 0xFF00, 1, Integer::sum);
        if (logG2d) e.log.printf("G2D cmd=%04X src=%08X/%d dst=%08X/%d %dx%d m84=%08X m88=%08X @%08X%n", cmd, src, sstride, dst, dstride, w, h,
                e.rd32(B + 0x84), e.rd32(B + 0x88), e.cpu.pc);
        if ((cmd & 0xFF00) == 0x4700) {
            int val = cmd & 0xFF;
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++) e.memory.store8(dst + y * dstride + x, val, null);
        } else if ((cmd & 0x2000) != 0 && (cmd & 0x4000) == 0) {
            for (int y = 0; y < h; y++) for (int x = 0; x < w; x++)
                e.memory.store8(dst + y * dstride + x, e.memory.loadUnsigned8(src + y * sstride + x, null), null);
        }
        g2dStatus |= 0x20;
        e.intc.request(0x24);
    }

    // ---- Moteur de redimensionnement 0x40020000 : fin immédiate, sans calcul (interruption 0x28) ----
    int rszStatus = 0; public long rszCount = 0;

    void writeReg(int a, int v, int size) {
        if (a == 0x40020000 && size == 2) {
            if ((v & 0x08) != 0) {
                rszCount++;
                rszStatus |= 0x8000;
                if ((e.rd16(0x40021FFC) & 0x8000) != 0) e.intc.request(0x28);
            }
            return;
        }
        if (a == 0x40021FFE && size == 2) { rszStatus &= ~v; if ((rszStatus & 0x8000) == 0) e.intc.removeRequest(0x28); return; }
        if (a == 0x40060080 && size == 2) { g2dCommand(v & 0xFFFF); return; }
        if (a == 0x40060032 && size == 2) { g2dStatus &= ~v; if ((g2dStatus & 0x2C) == 0) e.intc.removeRequest(0x24); return; }
        if (a == 0x61 && size == 1) { sioTx = v & 0xFF; return; }
        if (a == 0x62 && size == 1) {
            // reprise après erreur (état 0x11 : le B attend n'importe quel octet)
            if ((v & 0x03) == 0x03 && e.rd8(0x83CEE964) == 0x11) sioCountdown = sioDelay;
            return;
        }
        if (a == 0x50000106 && size == 1) {
            if ((v & 0x10) != 0) sioCountdown = sioDelay;
            return;
        }
        if (a == 0x38 && size == 1) { // EIRR1 : effacer un bit retire la requête du canal (0x1E + canal)
            for (int ch = 0; ch < 8; ch++) if ((v & (1 << ch)) == 0) e.intc.removeRequest(0x1E + ch);
            return;
        }
        if (a == 0x39 && size == 1) { // ENIR1 : activer un canal déjà en attente lève la requête
            int pend = e.rd8(0x38);
            for (int ch = 0; ch < 8; ch++) {
                if ((v & pend & (1 << ch)) != 0) e.intc.request(0x1E + ch);
                else if ((v & (1 << ch)) == 0) e.intc.removeRequest(0x1E + ch);
            }
            return;
        }
        if (a == 0x44) {
            if ((v & 1) != 0) e.intc.request(FrInterruptController_DELAY);
            else e.intc.removeRequest(FrInterruptController_DELAY);
            return;
        }
        for (int ch = 0; ch < 3; ch++) {
            int base = 0x48 + 8 * ch;
            if (a == base && size == 2) { tmrlr[ch] = v & 0xFFFF; return; }
            if (a == base + 6 && size == 2) { writeTmcsr(ch, v & 0xFFFF); return; }
            if (a == base + 7 && size == 1) { writeTmcsr(ch, (tmcsr[ch] & 0xFF00) | (v & 0xFF)); return; }
            if (a == base + 6 && size == 1) { writeTmcsr(ch, (tmcsr[ch] & 0x00FF) | ((v & 0xFF) << 8)); return; }
        }
    }

    static final int FrInterruptController_DELAY = 0x3F;

    void writeTmcsr(int ch, int v) {
        int old = tmcsr[ch];
        // bit 2 UF : écrire 0 l'efface, écrire 1 ne change rien
        int uf = (old & 4) & v;
        int nv = (v & ~4) | uf;
        if ((v & 1) != 0) { // TRG : recharge
            tmr[ch] = tmrlr[ch];
        }
        nv &= ~1;
        tmcsr[ch] = nv;
        updateTimerIrq(ch);
    }

    void updateTimerIrq(int ch) {
        int irq = 0x18 + ch;
        if ((tmcsr[ch] & 4) != 0 && (tmcsr[ch] & 8) != 0) e.intc.request(irq);
        else e.intc.removeRequest(irq);
    }

    @Override public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { note(true, a, v & 0xFF, 1); writeReg(a, v & 0xFF, 1); }
    @Override public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { note(true, a, v & 0xFFFF, 2); writeReg(a, v & 0xFFFF, 2); }
    @Override public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {
        note(true, a, v, 4);
        // un accès 32 bits sur TMRLR+TMR
        writeReg(a, (v >>> 16) & 0xFFFF, 2);
        writeReg(a + 2, v & 0xFFFF, 2);
    }

    // ---- Synchro verticale : canal 0 de l'unité d'interruptions externes 0x38 (vecteur 0x1E) ----
    public long vsyncPeriod = 1_000_000; // instructions (≈ 60 Hz si le FR tourne vers 60 MIPS : hypothèse)
    long vsyncCount = 0; int field = 0; public long vsyncs = 0;

    void extInt1(int ch) {
        e.wr8(0x38, e.rd8(0x38) | (1 << ch));
        if ((e.rd8(0x39) & (1 << ch)) != 0) e.intc.request(0x1E + ch);
    }

    /** Le A lève sa ligne de requête (front montant sur le canal 1). */
    public void raiseARequest() {
        e.wr8(0x38, e.rd8(0x38) | 2);
        if ((e.rd8(0x39) & 2) != 0) e.intc.request(0x1F);
    }

    /** Appelé après chaque instruction. */
    void tick() {
        if (sioCountdown >= 0 && --sioCountdown < 0 && !fakeA.muet) {   // A muet : aucun octet ne revient
            sioRx = fakeA.byteFor(sioTx);
            sioRxFull = true;
            sioBytes++;
            e.intc.request(0x1B);
        }
        fakeA.tick();
        if (++vsyncCount >= vsyncPeriod) { vsyncCount = 0; field ^= 1; vsyncs++; extInt1(0); }
        for (int ch = 0; ch < 3; ch++) {
            int c = tmcsr[ch];
            if ((c & 2) == 0) continue; // CNTE
            int csl = (c >> 10) & 3;
            int div = 2 << (2 * csl);  // φ/2, φ/8, φ/32, (φ/128)
            acc[ch] += timerScale;
            if (acc[ch] < div) continue;
            acc[ch] -= div;
            if (tmr[ch] == 0) {
                tmcsr[ch] |= 4; // UF
                if ((c & 0x10) != 0) tmr[ch] = tmrlr[ch]; // RELD
                else tmcsr[ch] &= ~2;
                updateTimerIrq(ch);
            } else {
                tmr[ch]--;
            }
        }
    }

    public void dumpCounts(java.io.PrintStream out) {
        out.println("== registres touchés (adresse lectures écritures) ==");
        for (Map.Entry<Integer, int[]> en : counts.entrySet())
            out.printf("%08X %8d %8d%n", en.getKey(), en.getValue()[0], en.getValue()[1]);
    }
}
