package com.nikonhacker.emu;

import com.nikonhacker.disassembly.fr.FrCPUState;
import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.memory.listener.MemoryActivityListener;

import java.io.*;
import java.util.*;

/**
 * Lanceur de l'émulateur du processeur B du D200 (appel de fonctions, pas de démarrage).
 *
 *   D200Boot <B2000201.bin> --script f.txt
 *   D200Boot <B2000201.bin> --disasm <adresse> <n>
 *
 * Codes de sortie : 0 tout est conforme, 1 un contrôle (expect…) n'est pas tenu, 2 garde (instruction non
 * définie, créneau de délai, exécution hors code, écriture en ROM, appel au noyau, pile non rendue),
 * 3 autre exception.
 *
 * Nombres : 0x… en hexadécimal, sinon décimal, signe « - » accepté (-223, -0xDF). Les adresses s'écrivent en 0x….
 *
 * Langage des scénarios (une commande par ligne, « # » commente) :
 *   titre <texte>                     afficher un intertitre
 *   peek|peek16|peek32 <adr> [n]      afficher n octets, demi-mots, mots (avec leur valeur signée)
 *   poke8|poke16|poke32 <adr> <v>…    écrire une ou plusieurs valeurs consécutives
 *   remplir <adr> <n> <octet>         écrire n fois l'octet
 *   copier <src> <dst> <n>            recopier n octets
 *   charger <fichier> <adr>           recopier un fichier en mémoire (chemin relatif : au dossier du scénario)
 *   expect8|expect16|expect32 <adr> <v>…   vérifier une ou plusieurs valeurs consécutives (code 1 sinon)
 *   expectegal <a> <b> <n>            n octets identiques en a et b
 *   expectdemi <demi> <octets> <n>    n demi-mots en <demi> égaux aux n octets en <octets> (courbe 8 bits recopiée
 *                                     en demi-mots dans les registres de la puce)
 *   expectcourbe <demi> <seuils>      les 4096 demi-mots en <demi> sont la courbe développée des 256 seuils 16 bits
 *                                     en <seuils> (sortie k pour les entrées jusqu'au seuil k, comme FUN_0005df82,
 *                                     réécrit ici indépendamment)
 *   expectconv <reg> <src> <n> <taille> <bit>   les n demi-mots en <reg> sont les n valeurs signées de <taille>
 *                                     octets (2 ou 4) en <src>, converties en signe et module : v si v >= 0,
 *                                     <bit> | -v sinon ; échec aussi si |v| >= <bit> (le format ne peut pas la porter)
 *   appel <adr> [r4 r5 r6 r7]         exécuter une fonction jusqu'à son retour, comme un CALL : interruptions
 *                                     masquées, pile à part (0x9FFF0000), registres, PS et PC rendus ; garde si la
 *                                     pile n'est pas rendue
 *   retour <adr> <valeur>             la fonction en adr rend aussitôt valeur dans R4
 *   noyau ok|garde                    INT #0x40 : retour immédiat E_OK journalisé, ou garde (défaut)
 *   watch <adr>…                      journaliser chaque passage du PC
 *   watchw <adr> <n> [max]            journaliser les écritures du code dans une plage
 *   lectures <nom> <adr> <n>          noter ce que le code lit dans la plage avant de l'avoir écrit
 *   bilanlectures                     afficher, pour chaque plage suivie, les octets lus avant écriture
 *   dis <adr> <n> | regs              désassembler, registres
 *   macro <nom> … fin                 retenir une suite de commandes ; jouer <nom> la rejoue
 *   balayage <macro> <ldi8> <de> <à> <reg> <bit> brut|signe
 *                                     pour chaque v de <de> à <à> : poser LDI:8 #v en <ldi8> (même registre de
 *                                     destination), jouer la macro sans rien afficher, puis comparer le demi-mot en
 *                                     <reg> à la conversion signe et module de v lu tel quel (brut, 0 à 255) ou
 *                                     étendu en signe (signe, −128 à 127, comme avec EXTSB) ; l'instruction
 *                                     d'origine est remise à la fin
 */
public class D200Boot {
    static long val(String s) {
        boolean neg = s.startsWith("-");
        if (neg || s.startsWith("+")) s = s.substring(1);
        long v = s.toLowerCase().startsWith("0x") ? Long.parseLong(s.substring(2), 16) : Long.parseLong(s);
        return neg ? -v : v;
    }
    static int adr(String s) { return (int) val(s); }

    static PrintStream out = System.out;
    static boolean muet = false;
    static void dire(String f, Object... a) { if (!muet) out.printf(f + "%n", a); }

    static int controles = 0, echecs = 0;
    static void controle(boolean ok, String f, Object... a) {
        controles++;
        if (!ok) echecs++;
        if (!muet || !ok) out.printf("  " + (ok ? "OK" : "ÉCHEC") + " : " + f + "%n", a);
    }

    static final Map<String, List<String>> macros = new LinkedHashMap<>();
    static File dossierScenario = new File(".");

    public static void main(String[] args) throws Exception {
        File fw = new File(args[0]);
        String scriptFile = null;
        D200Emu e = new D200Emu(fw, System.out);
        for (int i = 1; i < args.length; i++) {
            if (args[i].equals("--disasm")) { System.out.print(e.disasm(adr(args[i + 1]), Integer.parseInt(args[i + 2]))); return; }
            if (args[i].equals("--script")) scriptFile = args[++i];
        }
        if (scriptFile == null) { System.out.println("--script manquant"); System.exit(3); }
        dossierScenario = new File(scriptFile).getAbsoluteFile().getParentFile();
        List<String> script = new ArrayList<>();
        for (String l : java.nio.file.Files.readAllLines(new File(scriptFile).toPath())) {
            l = l.replaceAll("#.*", "").trim();
            if (!l.isEmpty()) script.add(l);
        }
        System.out.printf("firmware : %s%n", fw.getAbsolutePath());
        int code = 0;
        long t0 = System.currentTimeMillis();
        try {
            executer(e, script);
            if (echecs > 0) code = 1;
        } catch (D200Emu.Garde g) {
            System.out.println("ARRÊT, GARDE : " + g.getMessage());
            System.out.println(e.regs());
            System.out.println("64 derniers PC :" + e.derniersPc());
            code = 2;
        } catch (Throwable t) {
            System.out.println("ARRÊT sur exception : " + t);
            t.printStackTrace(System.out);
            System.out.println(e.regs());
            code = 3;
        }
        long dt = System.currentTimeMillis() - t0;
        System.out.printf("== bilan : %d contrôles, %d échec(s) ; %.3f M instructions en %.1f s%n", controles, echecs, e.steps / 1e6, dt / 1000.0);
        if (!e.appelsNoyau.isEmpty()) System.out.println("appels au noyau remplacés par E_OK : " + e.appelsNoyau);
        System.out.println(code == 0 ? "RÉSULTAT : OK" : "RÉSULTAT : ÉCHEC (code " + code + ")");
        System.exit(code);
    }

    static void executer(D200Emu e, List<String> script) throws Exception {
        for (int i = 0; i < script.size(); i++) {
            String cmd = script.get(i);
            String[] w = cmd.split("\\s+");
            if (w[0].equals("macro")) {
                List<String> corps = new ArrayList<>();
                while (!script.get(++i).equals("fin")) corps.add(script.get(i));
                macros.put(w[1], corps);
                continue;
            }
            if (w[0].equals("titre")) { dire("%n===== %s", cmd.substring(6)); continue; }
            dire("> %s", cmd);
            commande(e, w, cmd);
        }
    }

    static void commande(D200Emu e, String[] w, String cmd) throws Exception {
        switch (w[0]) {
            case "peek": case "peek16": case "peek32": {
                int a = adr(w[1]), n = w.length > 2 ? adr(w[2]) : 1;
                int t = w[0].equals("peek") ? 1 : w[0].equals("peek16") ? 2 : 4;
                StringBuilder sb = new StringBuilder(String.format("  %08X :", a));
                for (int k = 0; k < n; k++) {
                    int b = a + k * t;
                    if (t == 1) sb.append(String.format(" %02X", e.rd8(b)));
                    else if (t == 2) sb.append(String.format(" %04X(%d)", e.rd16(b), (short) e.rd16(b)));
                    else sb.append(String.format(" %08X(%d)", e.rd32(b), e.rd32(b)));
                }
                dire("%s", sb);
                break;
            }
            case "poke8": case "poke16": case "poke32": {
                int a = adr(w[1]), t = w[0].equals("poke8") ? 1 : w[0].equals("poke16") ? 2 : 4;
                for (int k = 2; k < w.length; k++, a += t) {
                    int v = (int) val(w[k]);
                    if (t == 1) e.wr8(a, v); else if (t == 2) e.wr16(a, v); else e.wr32(a, v);
                }
                break;
            }
            case "remplir": { int a = adr(w[1]), n = adr(w[2]), v = adr(w[3]); for (int k = 0; k < n; k++) e.wr8(a + k, v); break; }
            case "copier": { int a = adr(w[1]), d = adr(w[2]), n = adr(w[3]); for (int k = 0; k < n; k++) e.wr8(d + k, e.rd8(a + k)); break; }
            case "charger": {
                String chemin = w[1].startsWith("~/") ? System.getProperty("user.home") + w[1].substring(1) : w[1];
                File f = new File(chemin).isAbsolute() ? new File(chemin) : new File(dossierScenario, chemin);
                byte[] b = java.nio.file.Files.readAllBytes(f.toPath());
                int a = adr(w[2]);
                for (int k = 0; k < b.length; k++) e.wr8(a + k, b[k] & 0xFF);
                dire("  %d octets chargés en %08X", b.length, a);
                break;
            }
            case "expect8": case "expect16": case "expect32": {
                int a = adr(w[1]), t = w[0].equals("expect8") ? 1 : w[0].equals("expect16") ? 2 : 4;
                long masque = t == 1 ? 0xFF : t == 2 ? 0xFFFF : 0xFFFFFFFFL;
                for (int k = 2; k < w.length; k++, a += t) {
                    long att = val(w[k]) & masque;
                    long v = (t == 1 ? e.rd8(a) : t == 2 ? e.rd16(a) : e.rd32(a)) & masque;
                    long sv = t == 1 ? (byte) v : t == 2 ? (short) v : (int) v;
                    controle(v == att, "%s %08X = 0x%0" + (2 * t) + "X (%d), attendu %s", t == 1 ? "octet" : t == 2 ? "demi-mot" : "mot", a, v, sv, w[k]);
                }
                break;
            }
            case "expectegal": {
                int a = adr(w[1]), b = adr(w[2]), n = adr(w[3]), diff = -1;
                for (int k = 0; k < n && diff < 0; k++) if (e.rd8(a + k) != e.rd8(b + k)) diff = k;
                if (diff < 0) controle(true, "%d octets identiques en %s et %s", n, w[1], w[2]);
                else controle(false, "%s et %s diffèrent à +%d (%02X au lieu de %02X)", w[1], w[2], diff, e.rd8(a + diff), e.rd8(b + diff));
                break;
            }
            case "expectdemi": {
                int a = adr(w[1]), b = adr(w[2]), n = adr(w[3]), diff = -1;
                for (int k = 0; k < n && diff < 0; k++) if (e.rd16(a + 2 * k) != e.rd8(b + k)) diff = k;
                if (diff < 0) controle(true, "%d demi-mots en %s = les %d octets en %s (premier %04X, dernier %04X)", n, w[1], n, w[2],
                        e.rd16(a), e.rd16(a + 2 * (n - 1)));
                else controle(false, "demi-mot %d en %s = %04X, octet en %s = %02X", diff, w[1], e.rd16(a + 2 * diff), w[2], e.rd8(b + diff));
                break;
            }
            case "expectcourbe": { // expectcourbe <demi> <seuils> : 256 seuils 16 bits développés comme FUN_0005df82
                int a = adr(w[1]), s = adr(w[2]), i = 0, diff = -1;
                int[] lut = new int[4096];
                for (int k = 0; k < 256; k++) {
                    int seuil = Math.min(e.rd16(s + 2 * k), 0xFFF);
                    for (; i <= seuil; i++) lut[i] = k;
                }
                for (int k = 0; k < 4096 && diff < 0; k++) if (e.rd16(a + 2 * k) != lut[k]) diff = k;
                if (diff < 0) controle(true, "4096 demi-mots en %s = courbe développée des seuils en %s (entrée 2048 -> %d, 4095 -> %d)",
                        w[1], w[2], lut[2048], lut[4095]);
                else controle(false, "demi-mot %d en %s = %04X, courbe développée des seuils en %s : %d", diff, w[1], e.rd16(a + 2 * diff), w[2], lut[diff]);
                break;
            }
            case "expectconv": {
                int reg = adr(w[1]), src = adr(w[2]), n = adr(w[3]), t = adr(w[4]), bit = adr(w[5]);
                for (int k = 0; k < n; k++) {
                    int v = t == 2 ? (short) e.rd16(src + 2 * k) : e.rd32(src + 4 * k);
                    int att = v >= 0 ? v : (bit | -v), lu = e.rd16(reg + 2 * k);
                    boolean porte = Math.abs(v) < bit;
                    controle(porte && lu == att, "%08X = 0x%04X ; source %08X = %d -> 0x%04X%s", reg + 2 * k, lu, src + t * k, v, att & 0xFFFF,
                            porte ? "" : String.format(" (hors format : |v| >= 0x%X)", bit));
                }
                break;
            }
            case "appel": appel(e, w); break;
            case "retour": {
                final int a = adr(w[1]), v = adr(w[2]);
                e.hooks.put(a, em -> { em.setR(4, v); em.cpu.pc = em.r(FrCPUState.RP); return true; });
                break;
            }
            case "noyau": e.noyauOk = w[1].equals("ok"); break;
            case "watch":
                for (int k = 1; k < w.length; k++) {
                    final int a = adr(w[k]);
                    e.hooks.put(a, em -> {
                        dire("  passage %08X RP=%08X R4=%08X R5=%08X R6=%08X (%d)", a, em.r(FrCPUState.RP), em.r(4), em.r(5), em.r(6), em.steps);
                        return false;
                    });
                }
                break;
            case "watchw": e.memory.addActivityListener(new Surveillance200(e, adr(w[1]), adr(w[2]), w.length > 3 ? Integer.parseInt(w[3]) : 50)); break;
            case "lectures": e.tracer(w[1], adr(w[2]), adr(w[3])); break;
            case "bilanlectures":
                for (D200Emu.Lectures l : e.traceurs) dire("  %s (%08X, %d octets), lu avant écriture : %s", l.nom, l.a0, l.a1 - l.a0, l.plages());
                break;
            case "dis": dire("%s", e.disasm(adr(w[1]), Integer.parseInt(w[2]))); break;
            case "regs": dire("  %s", e.regs()); break;
            case "jouer": {
                List<String> corps = macros.get(w[1]);
                if (corps == null) throw new IllegalArgumentException("macro inconnue : " + w[1]);
                executer(e, corps);
                break;
            }
            case "balayage": balayage(e, w); break;
            default: throw new IllegalArgumentException("commande inconnue : " + cmd);
        }
    }

    /** balayage <macro> <ldi8> <de> <à> <reg> <bit> brut|signe */
    static void balayage(D200Emu e, String[] w) throws Exception {
        int ldi = adr(w[2]), de = adr(w[3]), a = adr(w[4]), reg = adr(w[5]), bit = adr(w[6]);
        boolean signe = w[7].equals("signe");
        int orig = e.rd16(ldi);
        if ((orig & 0xF000) != 0xC000) throw new IllegalArgumentException(String.format("%08X n'est pas un LDI:8 (%04X)", ldi, orig));
        int c0 = controles, f0 = echecs, premierEchec = -1;
        StringBuilder exemples = new StringBuilder();
        for (int v = de; v <= a; v++) {
            e.wr16(ldi, (orig & 0xF00F) | (v << 4));
            int f = echecs;
            boolean m = muet;
            muet = true;
            try { executer(e, macros.get(w[1])); } finally { muet = m; }
            int charge = signe ? (byte) v : v;
            int att = charge >= 0 ? charge : (bit | -charge), lu = e.rd16(reg);
            controles++;
            if (lu != att) { echecs++; if (premierEchec < 0) premierEchec = v; }
            if (echecs != f && premierEchec < 0) premierEchec = v;
            if (v == de || v == a || v == 127 || v == 128 || v == 255 || lu != att)
                if (exemples.length() < 400) exemples.append(String.format(" %d->%04X", v, lu));
        }
        e.wr16(ldi, orig);
        boolean ok = echecs == f0;
        out.printf("  %s : balayage de LDI:8 en %08X, v = %d à %d (%s), demi-mot %08X = %s : %d contrôles%s%n",
                ok ? "OK" : "ÉCHEC", ldi, de, a, signe ? "étendu en signe" : "brut", reg,
                signe ? "signe et module de v étendu en signe" : "v", controles - c0,
                ok ? "" : String.format(", %d échec(s), premier à v = %d", echecs - f0, premierEchec));
        out.printf("    relevés :%s%n", exemples);
    }

    /** Adresse de retour fictive (jamais exécutée) et pile privée de l'appel : hors de la RAM réelle du D200
     *  (0x90000000-0x97FFFFFF, hypothèse), que l'émulateur accepte comme n'importe quelle adresse de données. */
    static final int RETOUR_APPEL = 0x9FFFFFF0, PILE_APPEL = 0x9FFF0000;

    static void appel(D200Emu e, String[] w) throws EmulationException {
        while (e.inDelaySlot()) e.step();
        FrCPUState c = e.cpu;
        int ps = c.getPS(), pc = c.pc;
        int[] regs = new int[FrCPUState.NUM_STD_REGISTERS];
        for (int k = 0; k < regs.length; k++) regs[k] = c.getReg(k);
        int sp = c.getReg(15);
        c.I = 0;
        for (int k = 2; k < w.length && k < 6; k++) e.setR(4 + k - 2, adr(w[k]));
        e.setR(15, PILE_APPEL);
        e.setR(FrCPUState.RP, RETOUR_APPEL);
        c.pc = adr(w[1]);
        long n = 0;
        int spMin = PILE_APPEL;
        while (c.pc != RETOUR_APPEL || e.inDelaySlot()) {
            e.step();
            if (e.r(15) < spMin) spMin = e.r(15);
            if (++n > 50_000_000L) throw new D200Emu.Garde("appel " + w[1] + " : pas de retour après 50 M instructions");
        }
        int r4 = e.r(4), spFin = e.r(15);
        c.setPS(ps, false);
        for (int k = 0; k < regs.length; k++) if (k != 15) c.setReg(k, regs[k]);
        c.setReg(15, sp);
        c.pc = pc;
        dire("  retour de %s après %d instructions : R4=%08X, pile %s, profondeur max %d octets", w[1], n, r4,
                spFin == PILE_APPEL ? "rendue" : String.format("DÉCALÉE (%08X)", spFin), PILE_APPEL - spMin);
        if (spFin != PILE_APPEL) throw new D200Emu.Garde("appel " + w[1] + " : la pile n'est pas rendue");
    }

    /** watchw : journal des écritures du code dans une plage (PC, RP, valeur). */
    static class Surveillance200 implements MemoryActivityListener {
        final D200Emu e; final int a0, a1; int reste;
        Surveillance200(D200Emu e, int a, int n, int max) { this.e = e; a0 = a; a1 = a + n; reste = max; }
        public boolean matches(int a) { return a + 3 >= a0 && a < a1; }
        public boolean isReadOnly() { return false; }
        void note(int a, int v, int size) {
            if (a + size <= a0 || a >= a1 || reste <= 0) return;
            reste--;
            dire("  écriture %08X <- %0" + (size * 2) + "X PC=%08X RP=%08X (%d)", a, v, e.cpu.pc, e.r(FrCPUState.RP), e.steps);
        }
        public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { return null; }
        public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
        public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
        public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { note(a, v & 0xFF, 1); }
        public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { note(a, v & 0xFFFF, 2); }
        public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { note(a, v, 4); }
    }
}
