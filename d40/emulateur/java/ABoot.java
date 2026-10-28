package com.nikonhacker.emu;

import com.nikonhacker.disassembly.fr.FrCPUState;

import java.io.*;
import java.util.*;

/**
 * Lanceur de l'émulateur du processeur A (étude de faisabilité).
 *
 *   ABoot <AD400111.bin> [--script f.txt] [--max N] [--io] [--sys]
 *   ABoot <AD400111.bin> --disasm <adresse> <n>
 *
 * Codes de sortie : 0 bon, 1 attente non tenue, 2 garde, 3 autre exception.
 *
 * Scénarios : mêmes commandes que Boot quand elles ont un sens pour le A :
 *   run <n> | jusqua <adr> <max> (exécuter jusqu'au passage du PC en adr)
 *   peek <adr> [n] | peek16s <adr> | poke8|poke16|poke32 <adr> <val> | expect8|expect16 <adr> <val>
 *   watch <adr>... | sys on|off | io on|off | regs | dis <adr> <n> | bilan
 *   appel <adr> [r4..r7]     comme Boot : interruptions masquées, pile à part (0x3FF00), retour vérifié
 *   retour <adr> <val>       la fonction en adr rend aussitôt val dans R4
 *   b <cmd> [octets]         (palier 2) le faux B envoie une commande au A — voir FakeB
 */
public class ABoot {
    static long parseN(String s) {
        s = s.toUpperCase();
        if (s.endsWith("M")) return (long) (Double.parseDouble(s.substring(0, s.length() - 1)) * 1e6);
        if (s.endsWith("K")) return (long) (Double.parseDouble(s.substring(0, s.length() - 1)) * 1e3);
        return Long.parseLong(s);
    }
    static int adr(String s) {
        boolean neg = s.startsWith("-"); if (neg) s = s.substring(1);
        int v = s.toLowerCase().startsWith("0x") ? (int) Long.parseLong(s.substring(2), 16) : (int) Long.parseLong(s);
        return neg ? -v : v;
    }

    static final Map<Integer, Integer> hist = new HashMap<>();

    static void runFor(AEmu e, long n) throws EmulationException {
        long end = e.steps + n;
        while (e.steps < end) {
            if ((e.steps & 63) == 0) hist.merge(e.cpu.pc, 1, Integer::sum);
            e.step();
        }
    }

    public static FakeB fakeB = null;

    public static void main(String[] args) throws Exception {
        File fw = new File(args[0]);
        long max = 20_000_000L;
        boolean io = false, sys = false;
        String scriptFile = null;
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--max": max = parseN(args[++i]); break;
                case "--io": io = true; break;
                case "--sys": sys = true; break;
                case "--script": scriptFile = args[++i]; break;
            }
        }
        AEmu e = new AEmu(fw, System.out);
        for (int i = 1; i < args.length; i++)
            if (args[i].equals("--disasm")) { System.out.print(e.disasm(adr(args[i + 1]), Integer.parseInt(args[i + 2]))); return; }
        e.io.logAccess = io;
        e.traceSyscalls = sys;
        List<String> script = new ArrayList<>();
        if (scriptFile != null) {
            for (String l : java.nio.file.Files.readAllLines(new File(scriptFile).toPath())) {
                l = l.replaceAll("#.*", "").trim();
                if (!l.isEmpty()) script.add(l);
            }
        } else script.add("run " + max);

        int code = 0;
        long t0 = System.currentTimeMillis();
        try {
            for (String cmd : script) {
                String[] w = cmd.split("\\s+");
                System.out.printf("> %-40s (à %.3f M instructions)%n", cmd, e.steps / 1e6);
                switch (w[0]) {
                    case "run": runFor(e, parseN(w[1])); break;
                    case "jusqua": {
                        int a = adr(w[1]); long m = parseN(w[2]), end = e.steps + m;
                        while (e.steps < end && !(e.cpu.pc == a && !e.inDelaySlot())) e.step();
                        System.out.printf("  %s %05X à %d instructions%n", e.cpu.pc == a ? "atteint" : "PAS ATTEINT", a, e.steps);
                        if (e.cpu.pc != a) code = 1;
                        break;
                    }
                    case "peek": {
                        int a = adr(w[1]), n = w.length > 2 ? Integer.parseInt(w[2]) : 1;
                        StringBuilder sb = new StringBuilder(String.format("  %05X :", a));
                        for (int k = 0; k < n; k++) sb.append(String.format(" %02X", e.rd8(a + k)));
                        System.out.println(sb);
                        break;
                    }
                    case "peek16s": System.out.printf("  %05X = %d (0x%04X)%n", adr(w[1]), e.rds16(adr(w[1])), e.rd16(adr(w[1]))); break;
                    case "poke8": e.wr8(adr(w[1]), adr(w[2])); break;
                    case "poke16": e.wr16(adr(w[1]), adr(w[2])); break;
                    case "poke32": e.wr32(adr(w[1]), adr(w[2])); break;
                    case "expect8": case "expect16": {
                        boolean b16 = w[0].equals("expect16");
                        int v = b16 ? e.rd16(adr(w[1])) : e.rd8(adr(w[1])), att = adr(w[2]) & (b16 ? 0xFFFF : 0xFF);
                        boolean ok = v == att;
                        System.out.printf("  %s : %s = %X, attendu %X%n", ok ? "OK" : "ÉCHEC", w[1], v, att);
                        if (!ok) code = 1;
                        break;
                    }
                    case "sys": e.traceSyscalls = w[1].equals("on"); break;
                    case "io": e.io.logAccess = w[1].equals("on"); break;
                    case "regs": System.out.println("  " + e.regs()); break;
                    case "dis": System.out.print(e.disasm(adr(w[1]), Integer.parseInt(w[2]))); break;
                    case "watch":
                        for (int k = 1; k < w.length; k++) {
                            final int a = adr(w[k]);
                            e.hooks.put(a, em -> {
                                em.log.printf("  passage %05X RP=%08X R4=%08X R5=%08X (%d)%n", a, em.r(FrCPUState.RP), em.r(4), em.r(5), em.steps);
                                return false;
                            });
                        }
                        break;
                    case "retour": {
                        final int a = adr(w[1]), v = adr(w[2]);
                        e.hooks.put(a, em -> { em.setR(4, v); em.cpu.pc = em.r(FrCPUState.RP); return true; });
                        break;
                    }
                    case "appel": appel(e, w); break;
                    case "balayage": balayage(e, w); break;
                    case "bilan": bilan(e, false); break;
                    case "zones": { // blocs de 256 octets non nuls de la RAM du A
                        StringBuilder sb = new StringBuilder("  RAM non nulle (blocs de 256 o) :");
                        boolean io0 = e.io.logAccess; e.io.logAccess = false;
                        int debut = -1;
                        for (int a = AEmu.RAM0; a <= AEmu.RAM1; a += 256) {
                            boolean nz = false;
                            if (a < AEmu.RAM1) for (int k = 0; k < 256 && !nz; k++) nz = e.rd8(a + k) != 0;
                            if (nz && debut < 0) debut = a;
                            if (!nz && debut >= 0) { sb.append(String.format(" %05X-%05X", debut, a - 1)); debut = -1; }
                        }
                        e.io.logAccess = io0;
                        System.out.println(sb);
                        break;
                    }
                    case "b": {
                        if (fakeB == null) fakeB = new FakeB(e);
                        int c = Integer.parseInt(w[1].replace("0x", ""), 16);
                        byte[] d = new byte[w.length - 2];
                        for (int k = 2; k < w.length; k++) d[k - 2] = (byte) Integer.parseInt(w[k], 16);
                        fakeB.envoyer(c, d);
                        break;
                    }
                    case "eeprom": { // eeprom ff|zero|valide|<fichier> : image de l'EEPROM et simulation HLE
                        java.util.Arrays.fill(e.eeprom, (byte) (w[1].equals("ff") ? 0xFF : 0));
                        if (w[1].equals("valide")) { e.eeprom[0] = 1; e.eeprom[0x37F] = (byte) 0xFF; } // somme 0x000-0x37F nulle, ni tout 0 ni tout FF
                        else if (!w[1].equals("ff") && !w[1].equals("zero")) {
                            byte[] f = java.nio.file.Files.readAllBytes(new File(w[1]).toPath());
                            System.arraycopy(f, 0, e.eeprom, 0, Math.min(f.length, e.eeprom.length));
                        }
                        e.eepromHle();
                        break;
                    }
                    case "taches": System.out.print(e.taches()); break;
                    case "entree": { // entree <adr> <ou> [<et>] : valeur lue = (mémoire & et) | ou (broches d'entrée d'un port)
                        final int a = adr(w[1]), ou = adr(w[2]), et = w.length > 3 ? adr(w[3]) : 0xFF;
                        e.io.overrides.put(a, v -> (v & et) | ou);
                        break;
                    }
                    case "fakeb": { // fakeb [inverser 0|1] [controle 0|1|2] [delai N]
                        if (fakeB == null) fakeB = new FakeB(e);
                        for (int k = 1; k + 1 < w.length; k += 2) {
                            if (w[k].equals("inverser")) fakeB.inverser = w[k + 1].equals("1");
                            if (w[k].equals("controle")) fakeB.modeControle = Integer.parseInt(w[k + 1]);
                            if (w[k].equals("delai")) fakeB.delaiPret = Integer.parseInt(w[k + 1]);
                        }
                        break;
                    }
                    case "finb": if (fakeB != null) { fakeB.fin(); for (String j : fakeB.journal) System.out.println("  " + j); fakeB.journal.clear(); } break;
                    default: System.out.println("  commande inconnue : " + cmd); code = 1;
                }
            }
        } catch (D40Emu.Garde g) {
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
        System.out.printf("== bilan : %.3f M instructions en %.1f s (%.1f M/s)%n", e.steps / 1e6, dt / 1000.0, e.steps / 1000.0 / Math.max(1, dt));
        bilan(e, true);
        System.out.println(code == 0 ? "RÉSULTAT : OK" : "RÉSULTAT : ÉCHEC (code " + code + ")");
        System.exit(code);
    }

    static String vitesse(int tv48) {
        double t = Math.pow(2, -tv48 / 48.0);
        return t < 0.95 ? String.format("1/%d", Math.round(1 / t)) : String.format("%.1f s", t);
    }
    static String ouverture(int av48) { return String.format("f/%.1f", Math.pow(2, av48 / 96.0)); }

    /**
     * balayage p|chaine <ev0> <ev1> <pas> : Ev (IL entiers ou décimaux) de ev0 à ev1 ; « p » pose ccc2 et appelle
     * la fonction de P (0xC60E2) ; « chaine » pose la mesure cf68 (Ev = cf68 + 8·e1ee − correction de
     * 0xC4064) et appelle expo_programme (0xC3F84), ISO auto compris. Imprime Tv, Av (et l'ISO) calculés.
     */
    static void balayage(AEmu e, String[] w) throws EmulationException {
        boolean chaine = w[1].equals("chaine");
        double ev0 = Double.parseDouble(w[2]), ev1 = Double.parseDouble(w[3]), pas = Double.parseDouble(w[4]);
        System.out.println(chaine ? "    Ev  |  Tv            |  Av        | ISO  | Ev à l'ISO choisi" : "    Ev  |  Tv            |  Av");
        for (double ev = ev0; ev <= ev1 + 1e-9; ev += pas) {
            int ev48 = (int) Math.round(ev * 48);
            if (chaine) {
                int ccb9 = e.rd8(0x3D100) >> 1, corr = ccb9 < 7 ? 0 : ccb9 > 12 ? 8 : 4;
                e.wr16(0x3CF68, ev48 - 8 * e.rd8(0x3E1EE) + corr + 8 * (byte) e.rd8(0x3D0B2));
                appelMuet(e, 0xC3F84);
                int tv = 2 * e.rds16(0x3CCB2), av = 2 * e.rds16(0x3CCB4), sv = e.rd8(0x3CCBC);
                System.out.printf("  %5.1f | %4d %-9s | %4d %-5s | %4d | %5.1f%n", ev, tv, vitesse(tv), av, ouverture(av),
                        Math.round(3.125 * Math.pow(2, sv / 6.0)), (tv + av) / 48.0);
            } else {
                e.wr16(0x3CCC2, ev48);
                appelMuet(e, 0xC60E2);
                int tv = e.rds16(0x3CCC0), av = e.rds16(0x3CCBE);
                System.out.printf("  %5.1f | %4d %-9s | %4d %-5s%n", ev, tv, vitesse(tv), av, ouverture(av));
            }
        }
    }

    static void appelMuet(AEmu e, int adr) throws EmulationException {
        java.io.PrintStream o = System.out;
        System.setOut(new java.io.PrintStream(new java.io.ByteArrayOutputStream()));
        try { appel(e, new String[]{"appel", "0x" + Integer.toHexString(adr)}); } finally { System.setOut(o); }
    }

    static void bilan(AEmu e, boolean complet) {
        System.out.println("PC : " + e.regs());
        System.out.println("appels au noyau : " + e.syscallCounts);
        StringBuilder sb = new StringBuilder("sta_tsk (tâche/code de départ @instruction) :");
        for (long[] t : e.staTsk) sb.append(String.format(" %d/%X@%d", t[0], t[1] & 0xFFFFFFFFL, t[2]));
        System.out.println(sb);
        System.out.println("premiers appels bloquants : " + e.premiersBloquants);
        System.out.printf("débordements des minuteries 0/1/2 : %d %d %d ; tics de la base 1 ms (int 0x2C) : %d ; compteur 0x3CC00 = %d ; conversions A/N : %d ; blocs DMA : %d%n",
                e.io.timerUnderflows[0], e.io.timerUnderflows[1], e.io.timerUnderflows[2], e.io.tics, e.rd16(0x3CC00), e.io.adcConversions, e.io.dmaBlocs);
        System.out.print(e.taches());
        System.out.println(e.marges());
        System.out.printf("EEPROM : %d lectures, %d écritures ; drapeau d'erreur 0x3CC9B = %02X%n", e.eepromLectures, e.eepromEcritures, e.rd8(0x3CC9B));
        if (complet) {
            System.out.println("PC les plus fréquents (1/64) :");
            hist.entrySet().stream().sorted((a, b) -> b.getValue() - a.getValue()).limit(10)
                    .forEach(en -> System.out.printf("  %05X %d%n", en.getKey(), en.getValue()));
            e.io.dumpCounts(System.out);
        }
    }

    /** Adresse de retour fictive (jamais exécutée) et pile privée de l'appel : hors des 16 Ko de RAM du A,
     *  entièrement occupés (piles des 12 tâches jusqu'à 0x3FFAC, table 0xFEB0C) ; l'émulateur accepte
     *  n'importe quelle adresse de données, le vrai A non : sans effet sur le code testé. */
    static final int RETOUR_APPEL = 0x50010;
    static final int PILE_APPEL = 0x50000;

    static void appel(AEmu e, String[] w) throws EmulationException {
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
            if (++n > 50_000_000L) throw new D40Emu.Garde("appel " + w[1] + " : pas de retour après 50 M instructions");
        }
        int r4 = e.r(4), spFin = e.r(15);
        c.setPS(ps, false);
        for (int k = 0; k < regs.length; k++) if (k != 15) c.setReg(k, regs[k]);
        c.setReg(15, sp);
        c.pc = pc;
        System.out.printf("  retour de %s après %d instructions : R4=%08X, pile %s, profondeur max %d octets%n", w[1], n, r4,
                spFin == PILE_APPEL ? "rendue" : String.format("DÉCALÉE (%08X)", spFin), PILE_APPEL - spMin);
        if (spFin != PILE_APPEL) throw new D40Emu.Garde("appel " + w[1] + " : la pile n'est pas rendue");
    }
}
