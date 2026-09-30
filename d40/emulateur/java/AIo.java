package com.nikonhacker.emu;

import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.memory.listener.MemoryActivityListener;

import java.util.*;

/**
 * Registres internes du processeur A (0x0000-0x0FFF), au strict nécessaire pour l'étude.
 * Par défaut tout se comporte comme de la RAM ; chaque accès est compté (adresse, lectures,
 * écritures, premiers PC) pour savoir ce que le A touche.
 * Émulé : minuteries à recharge 0x48/0x50/0x58 (comme le B), DICR 0x44 (interruption 0x3F).
 */
public class AIo implements MemoryActivityListener {
    final AEmu e;
    public boolean logAccess = false;
    public int logPerAddress = 3;
    /** adresse -> {lectures, écritures} */
    public final Map<Integer, int[]> counts = new TreeMap<>();
    /** adresse -> PC des premiers accès */
    public final Map<Integer, Set<Integer>> pcs = new TreeMap<>();
    public final Map<Integer, java.util.function.IntUnaryOperator> overrides = new HashMap<>();
    public final Map<Integer, java.util.function.IntConsumer> onWrite = new HashMap<>();

    final int[] tmrlr = new int[3], tmr = new int[3], tmcsr = new int[3];
    final long[] acc = new long[3];
    public final long[] timerUnderflows = new long[3];
    public int timerScale = 1;

    AIo(AEmu e) {
        this.e = e;
        // 0x482 (TBCR) bit 7 : fin de l'attente de stabilisation de l'horloge (boucle 0xC00B4 du reset)
        overrides.put(0x482, v -> v | 0x80);
    }

    @Override public boolean matches(int a) { return (a >= 0 && a < 0x1100) || (a >= 0x7000 && a < 0x7100); }
    @Override public boolean isReadOnly() { return false; }

    void note(boolean write, int a, int v, int size) {
        if (muet) return;
        int[] c = counts.computeIfAbsent(a, k -> new int[2]);
        int n = c[write ? 1 : 0]++;
        Set<Integer> s = pcs.computeIfAbsent(a, k -> new TreeSet<>());
        if (s.size() < 6) s.add(e.cpu.pc);
        if (logAccess && n < logPerAddress)
            e.log.printf("IO %s%d %04X %s %0" + (size * 2) + "X @%05X n=%d%n", write ? "W" : "R", size * 8, a,
                    write ? "<-" : "->", v, e.cpu.pc, e.steps);
    }

    Integer readReg(int a, int v, int size) {
        java.util.function.IntUnaryOperator o = overrides.get(a);
        if (o != null) return o.applyAsInt(v);
        for (int ch = 0; ch < 3; ch++) {
            int base = 0x48 + 8 * ch;
            if (a == base + 2 && size == 2) return tmr[ch];
            if (a == base + 6 && size == 2) return tmcsr[ch];
            if (a == base + 7 && size == 1) return tmcsr[ch] & 0xFF;
            if (a == base + 6 && size == 1) return (tmcsr[ch] >> 8) & 0xFF;
        }
        if (a == 0x44 && size == 1) return v | 0xFE;
        if (a == 0x60 && size == 1) return (v & ~0x58) | (sioTxEnCours ? 0 : 0x08) | (sioRxPlein ? 0x10 : 0);
        if (a == 0x61 && size == 1 && fakeB != null) { sioRxPlein = false; e.intc.removeRequest(0x1B); return sioRx; }
        if (size == 4 && a == 0x3FC) return bsrr;          // BSRR : résultat de la dernière recherche
        if (size == 4 && (a == 0x3F0 || a == 0x3F4 || a == 0x3F8)) return bsd;
        return null;
    }

    @Override public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {
        Integer r = readReg(a, v & 0xFF, 1); note(false, a, r == null ? v & 0xFF : r, 1); return r == null ? null : (byte) (int) r;
    }
    @Override public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {
        Integer r = readReg(a, v & 0xFFFF, 2); note(false, a, r == null ? v & 0xFFFF : r, 2); return r;
    }
    @Override public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {
        Integer r = readReg(a, v, 4); note(false, a, r == null ? v : r, 4); return r;
    }
    @Override public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
    @Override public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
    @Override public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}

    @Override public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { note(true, a, v & 0xFF, 1); writeReg(a, v & 0xFF, 1); }
    @Override public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { note(true, a, v & 0xFFFF, 2); writeReg(a, v & 0xFFFF, 2); }
    @Override public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {
        note(true, a, v, 4);
        if (a == 0x3F0 || a == 0x3F4 || a == 0x3F8) { bsd = v; bsrr = bitSearch(a); return; }
        if (a >= 0x200 && a < 0x228) {           // DMACA/DMACB des 5 canaux
            final int ch = (a - 0x200) >> 3; final boolean ca = ((a - 0x200) & 4) == 0;
            if (ca && (v & 0x80000000) != 0) dmaEcheance[ch] = e.steps + dmaDelaiParElement * Math.max(1, v & 0xFFFF);
            if (!ca) e.intc.removeRequest(0x2A);
            return;
        }
        writeReg(a, (v >>> 16) & 0xFFFF, 2); writeReg(a + 2, v & 0xFFFF, 2);
    }

    // Module de recherche de bit du FR (écrire 0x3F0 BSD0 premier 0, 0x3F4 BSD1 premier 1, 0x3F8 BSDC changement ;
    // lire le résultat en 0x3FC BSRR, 32 si rien) :
    // le répartiteur du noyau (0xFF344) y cherche la plus haute priorité prête.
    int bsd = 0, bsrr = 32;
    public long bitSearches = 0;
    int bitSearch(int a) {
        bitSearches++;
        if (a == 0x3F0) return Integer.numberOfLeadingZeros(~bsd);
        if (a == 0x3F4) return Integer.numberOfLeadingZeros(bsd);
        int x = bsd < 0 ? ~bsd : bsd;  // 0x3F8 : premier bit différent du bit 31
        int n = Integer.numberOfLeadingZeros(x);
        return n == 32 ? 32 : n;
    }

    void writeReg(int a, int v, int size) {
        if (muet) return;
        java.util.function.IntConsumer w = onWrite.get(a);
        if (w != null) w.accept(v);
        if (a == 0x146 && size == 1 && (v & 1) == 0) e.intc.removeRequest(0x2C);
        // Liaison série 0 (vers le B) : écrire SODR0 fait tourner l'horloge (le A est maître) ; l'octet du B
        // arrive sioDelai instructions plus tard (RDRF, IRQ 0x1B si RIE = bit 1 de SSR0).
        if (a == 0x61 && size == 1 && fakeB != null) { sioTx = v & 0xFF; sioTxEnCours = true; sioEcheance = e.steps + sioDelai; }
        // Interruptions externes 0-7 : EIRR 0x40 (effacer un bit retire la demande), ENIR 0x41, IRQ 0x10 + canal
        if (a == 0x40 && size == 1) { for (int ch = 0; ch < 8; ch++) if ((v & (1 << ch)) == 0) e.intc.removeRequest(0x10 + ch); }
        if (a == 0x41 && size == 1) {
            final int en = v;
            apres.add(() -> { int p = rawRd8(0x40); for (int ch = 0; ch < 8; ch++) if ((en & p & (1 << ch)) != 0) e.intc.request(0x10 + ch); });
        }
        // Convertisseur A/N 0x150-0x15B (10 bits) : bit 1 de 0x154 = départ ; fin immédiate (bit 6), résultat
        // adcValeur en 0x156 ; interruption 0x2B si le bit 7 est mis (hypothèse). La mesure de lumière passe par
        // ce convertisseur et le DMA (0xDC458) : non émulée, on la remplace par la variable 0x3CF68.
        if (a == 0x154 && size == 1) {
            if ((v & 2) != 0) {
                adcConversions++;
                apres.add(() -> {   // après l'écriture elle-même (le mémoire écrit l'octet après l'écouteur)
                    rawWr8(0x154, (rawRd8(0x154) & ~2) | 0x40);
                    rawWr8(0x156, (adcValeur >> 8) & 3); rawWr8(0x157, adcValeur & 0xFF);
                    if ((rawRd8(0x154) & 0x80) != 0) e.intc.request(0x2B);
                });
            } else if ((v & 0x40) == 0) e.intc.removeRequest(0x2B);
        }
        if (a == 0x44 && size == 1) {
            if ((v & 1) != 0) e.intc.request(0x3F); else e.intc.removeRequest(0x3F);
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

    void writeTmcsr(int ch, int v) {
        int old = tmcsr[ch];
        int uf = (old & 4) & v;
        int nv = (v & ~4) | uf;
        if ((v & 1) != 0) tmr[ch] = tmrlr[ch];
        nv &= ~1;
        tmcsr[ch] = nv;
        updateTimerIrq(ch);
    }

    void updateTimerIrq(int ch) {
        int irq = 0x18 + ch;
        if ((tmcsr[ch] & 4) != 0 && (tmcsr[ch] & 8) != 0) e.intc.request(irq);
        else e.intc.removeRequest(irq);
    }

    /** Appelé après chaque instruction. */
    public java.util.function.Consumer<AEmu> onTick = null;

    // ---- Base de temps « 1 ms » : 0x146 bit 0 drapeau, bit 1 interruption permise ; 0x147 bit 0 marche ;
    // 0x14A (16 bits) = 999 (rechargement, 1000 comptes) ; interruption 0x2C (gestionnaire 0xC0444, qui efface
    // le bit 0 de 0x146 et compte en 0x3CC00). Cadence réelle inconnue : instrParCompte instructions par compte.
    public int instrParCompte = 16;      // hypothèse : 16 000 instructions par période (16 MIPS si 1 ms)
    long accBase = 0; int cptBase = 0; public long tics = 0;
    public int adcValeur = 0x200; public long adcConversions = 0;

    void tickBase() {
        if ((e.memory.loadUnsigned8(0x147, null) & 1) == 0) return;   // lecture directe, hors journal
        if (++accBase < instrParCompte) return;
        accBase = 0;
        if (cptBase > 0) { cptBase--; return; }
        cptBase = baseReload();
        tics++;
        int f = rawRd8(0x146) | 1;
        rawWr8(0x146, f);
        if ((f & 2) != 0) e.intc.request(0x2C);
    }
    int baseReload() { return (rawRd8(0x14A) << 8) | rawRd8(0x14B); }
    boolean muet = false;
    int rawRd8(int a) { boolean l = logAccess; muet = true; int v = e.memory.loadUnsigned8(a, null); muet = false; return v; }
    void rawWr8(int a, int v) { muet = true; e.memory.store8(a, v, null); muet = false; }

    // ---- Contrôleur DMA (DMACA 0x200+8n, DMACB 0x204+8n, DMASA 0x1000+8n, DMADA 0x1004+8n) ----
    // Simplifié : dès que DENB (bit 31 de DMACA) est mis, tout le bloc est transféré d'un coup (sans attendre
    // les demandes du périphérique), DSS = fin normale, interruption 0x2A si EDIE (bit 19 de DMACB).
    // Utilisé par la lecture des capteurs (convertisseur A/N 0x156 -> RAM, 0xE560C, 0xDC458).
    public long dmaBlocs = 0;
    /** Fin du bloc après dmaDelaiParElement instructions par élément (une conversion A/N : hypothèse). */
    public int dmaDelaiParElement = 40;
    final long[] dmaEcheance = {-1, -1, -1, -1, -1};
    void dmaTransfert(int ch) {
        int ca = e.rd32(0x200 + 8 * ch), cb = e.rd32(0x204 + 8 * ch);
        int sa = e.rd32(0x1000 + 8 * ch), da = e.rd32(0x1004 + 8 * ch);
        int n = ca & 0xFFFF; if (n == 0) n = 0x10000;
        int ws = (cb >>> 26) & 3, taille = ws == 0 ? 1 : ws == 1 ? 2 : 4;
        int sasz = (byte) (cb >> 8), dasz = (byte) cb;
        if (sa == 0x156 || sa == 0x157) { rawWr8(0x156, (adcValeur >> 8) & 3); rawWr8(0x157, adcValeur & 0xFF); }
        for (int k = 0; k < n; k++) {
            int v = taille == 1 ? e.rd8(sa) : taille == 2 ? e.rd16(sa) : e.rd32(sa);
            if (taille == 1) e.wr8(da, v); else if (taille == 2) e.wr16(da, v); else e.wr32(da, v);
            sa += sasz; da += dasz;
        }
        dmaBlocs++;
        e.wr32(0x200 + 8 * ch, ca & 0x7FFF0000);
        e.wr32(0x204 + 8 * ch, (cb & ~0x70000) | 0x40000);
        if ((cb & 0x80000) != 0) e.intc.request(0x2A);
    }

    public FakeB fakeB = null;
    int sioTx = 0, sioRx = 0; boolean sioRxPlein = false, sioTxEnCours = false; long sioEcheance = -1;
    public int sioDelai = 200;

    /** Front sur l'entrée d'interruption externe ch (EIRR mis, IRQ 0x10 + ch si ENIR le permet). */
    public void frontExterne(int ch) {
        rawWr8(0x40, rawRd8(0x40) | (1 << ch));
        if ((rawRd8(0x41) & (1 << ch)) != 0) e.intc.request(0x10 + ch);
    }

    /** Effets à appliquer après l'instruction qui a écrit le registre. */
    final List<Runnable> apres = new ArrayList<>();

    void tick() {
        if (!apres.isEmpty()) { for (Runnable r : apres) r.run(); apres.clear(); }
        for (int ch = 0; ch < 5; ch++)
            if (dmaEcheance[ch] >= 0 && e.steps >= dmaEcheance[ch]) { dmaEcheance[ch] = -1; dmaTransfert(ch); }
        tickBase();
        if (fakeB != null) {
            if (sioEcheance >= 0 && e.steps >= sioEcheance) {
                sioEcheance = -1; sioTxEnCours = false;
                sioRx = fakeB.octet(sioTx); sioRxPlein = true;
                if ((rawRd8(0x60) & 2) != 0) e.intc.request(0x1B);
            }
            fakeB.tick();
        }
        for (int ch = 0; ch < 3; ch++) {
            int c = tmcsr[ch];
            if ((c & 2) == 0) continue;
            int csl = (c >> 10) & 3;
            int div = 2 << (2 * csl);
            acc[ch] += timerScale;
            if (acc[ch] < div) continue;
            acc[ch] -= div;
            if (tmr[ch] == 0) {
                tmcsr[ch] |= 4;
                timerUnderflows[ch]++;
                if ((c & 0x10) != 0) tmr[ch] = tmrlr[ch]; else tmcsr[ch] &= ~2;
                updateTimerIrq(ch);
            } else tmr[ch]--;
        }
        if (onTick != null) onTick.accept(e);
    }

    public void dumpCounts(java.io.PrintStream out) {
        out.println("== registres touchés (adresse lectures écritures, premiers PC) ==");
        for (Map.Entry<Integer, int[]> en : counts.entrySet()) {
            StringBuilder sb = new StringBuilder();
            for (int pc : pcs.get(en.getKey())) sb.append(String.format(" %05X", pc));
            out.printf("%04X %9d %9d %s%n", en.getKey(), en.getValue()[0], en.getValue()[1], sb);
        }
    }
}
