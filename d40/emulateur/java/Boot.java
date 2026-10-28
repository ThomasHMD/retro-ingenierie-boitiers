package com.nikonhacker.emu;

import java.io.*;
import java.util.*;

/**
 * Lanceur en ligne de commande de l'émulateur du processeur B du D40.
 *
 *   Boot <firmware.bin> [--script f.txt] [--sortie dossier] [--max N] [--style octet] [--verbeux] [--sys] [--io]
 *   Boot <firmware.bin> --disasm <adresse> <n>
 *
 * Codes de sortie : 0 tout va bien, 1 une attente (expect) n'est pas tenue,
 * 2 garde déclenchée (instruction non définie, créneau de délai interdit, exécution hors code),
 * 3 autre exception de l'émulateur.
 *
 * --style : octet écrit en 0x83CED0FF (réglages Style écran infos) dès 1 M instructions, avant tout
 * dessin. 0x01 Classique, 0x51 Graphique (valeur de départ de l'émulateur), 0xA1 Fond d'écran. Les
 * menus prennent le jeu de couleurs 0 en Classique, 1 sinon (recherche/ecran-reel-composition.md).
 *
 * Langage des scénarios (une commande par ligne, « # » commente) :
 *   run <n>                  exécuter n instructions (suffixes K et M acceptés)
 *   press <touche> [t] [p]   appuyer t instructions (4M par défaut) puis relâcher et attendre p (4M)
 *   down|up <touche>         enfoncer / relâcher sans attendre
 *   png <fichier>            capture du tampon d'interface (relatif au dossier --sortie)
 *   ybrut <fichier>          plan Y brut du tampon d'interface (640 × 480 octets) : avec une palette
 *                            de sonde (entrée i en gris de luminance connue), dit quelle entrée peint chaque point
 *   a <cmd> [octets hexa]    le faux A envoie la commande cmd (données facultatives)
 *   peek <adr> [n]           afficher n octets
 *   poke8 <adr> <val>        écrire un octet
 *   expect8 <adr> <val>      vérifier un octet (code 1 sinon)
 *   expect32min <adr> <val>  vérifier qu'un mot de 32 bits vaut au moins val
 *   watch <adr>...           journaliser chaque passage du PC à ces adresses
 *   sys on|off               tracer les appels au noyau
 *   pages <début> <fin>      pages de 64 Ko de RAM touchées dans une plage
 *   poke32 <adr> <val>       écrire un mot de 32 bits
 *   remplir <adr> <n> <oct>  écrire n fois l'octet oct (hexa) à partir de adr
 *   expect16 <adr> <val>     vérifier un demi-mot (code 1 sinon)
 *   expectegal <a> <b> <n>   vérifier que n octets (décimal, ou 0x…) en a et en b sont identiques (registres de la
 *                            puce contre une table de la ROM, par exemple ; code 1 sinon)
 *   copier <src> <dst> <n>   recopier n octets (décimal, ou 0x…) : garder une référence pour un
 *                            expectegal plus loin (ce que la puce a reçu dans un cas de comparaison)
 *   expecta <cmd> <i> <oct>  octet i de la dernière trame de la commande reçue du B par le faux A
 *   raza / expectcomptea <cmd> <min> <max>   compter les envois d'une commande par le B
 *   etata <cmd> <octets…>    bloc de la commande que le faux A a déjà reçu (gardé d'avant l'extinction) : il le
 *                            renvoie en écho (0x06 pour 0x05) tant que le B n'a rien envoyé d'autre
 *   entree <adr> <ou> [<et>] broches d'entrée d'un port : valeur lue = (mémoire & et) | ou ; « entree 0x50000105
 *                            0x02 » fait prendre au démarrage la branche où le B relit ses réglages perso en flash
 *                            et les renvoie au A (FUN_0004044c, hypothèse : celle du boîtier)
 *   onglet <n>               aller à l'onglet n (octet 0x83CE3FE8) depuis la ligne des onglets : ▶ si la
 *                            navigation du bandeau est présente (entrée 0x131F8A détournée), ▼ sinon
 *   appel <adr> [r4..r7]     appeler une fonction du firmware comme le ferait le code (R4 à R7 =
 *                            arguments), interruptions masquées, sur une pile à part ; l'état du
 *                            processeur est rendu tel quel au retour, la mémoire garde ses effets
 */
public class Boot {
    static long parseN(String s) {
        s = s.toUpperCase();
        if (s.endsWith("M")) return (long) (Double.parseDouble(s.substring(0, s.length() - 1)) * 1e6);
        if (s.endsWith("K")) return (long) (Double.parseDouble(s.substring(0, s.length() - 1)) * 1e3);
        return Long.parseLong(s);
    }

    /** Décimal, ou hexadécimal avec 0x. */
    static int nombre(String s) { return s.toLowerCase().startsWith("0x") ? adr(s) : Integer.parseInt(s); }

    static int adr(String s) { return (int) Long.parseLong(s.toLowerCase().replace("0x", ""), 16); }

    static final Map<Integer, Integer> hist = new HashMap<>();

    /** Style écran infos à poser à 1 M instructions (null : laisser la valeur de départ). */
    static Integer style = null;

    static void runFor(D40Emu e, long n) throws EmulationException {
        long end = e.steps + n;
        while (e.steps < end) {
            if (style != null && e.steps >= 1_000_000) {
                e.wr8(0x83CED0FF, style);
                System.out.printf("  style écran infos : 0x83CED0FF = 0x%02X%n", style);
                style = null;
            }
            if ((e.steps & 63) == 0) hist.merge(e.cpu.pc, 1, Integer::sum);
            e.step();
        }
    }

    public static void main(String[] args) throws Exception {
        File fw = new File(args[0]);
        long max = 80_000_000L;
        boolean io = false, sys = false, verbeux = false;
        File sortie = new File(".");
        String scriptFile = null;
        for (int i = 1; i < args.length; i++) {
            switch (args[i]) {
                case "--max": max = parseN(args[++i]); break;
                case "--io": io = true; break;
                case "--sys": sys = true; break;
                case "--verbeux": verbeux = true; break;
                case "--sortie": sortie = new File(args[++i]); break;
                case "--script": scriptFile = args[++i]; break;
                case "--style": style = nombre(args[++i]); break;
            }
        }
        D40Emu e = new D40Emu(fw, System.out);
        for (int i = 1; i < args.length; i++) {
            if (args[i].equals("--disasm")) {
                System.out.print(e.disasm(adr(args[i + 1]), Integer.parseInt(args[i + 2])));
                return;
            }
        }
        sortie.mkdirs();
        e.io.logAccess = io;
        e.io.logG2d = verbeux;
        e.io.fakeA.log = verbeux;
        e.traceSyscalls = sys;
        e.io.fakeA.bootSequence();

        List<String> script = new ArrayList<>();
        if (scriptFile != null) {
            for (String l : java.nio.file.Files.readAllLines(new File(scriptFile).toPath())) {
                l = l.replaceAll("#.*", "").trim();
                if (!l.isEmpty()) script.add(l);
            }
        } else {
            script.add("run " + max);
            script.add("png ecran.png");
        }

        int code = 0;
        long t0 = System.currentTimeMillis();
        try {
            for (String cmd : script) {
                String[] w = cmd.split("\\s+");
                System.out.printf("> %-40s (à %.1f M instructions)%n", cmd, e.steps / 1e6);
                if (w[0].equals("onglet")) {
                    // onglet <n> : aller à l'onglet n (0x83CE3FE8) depuis la ligne des onglets, avec la touche du
                    // firmware joué : ▶ si la navigation du bandeau (étape 7) détourne 0x131F8A, ▼ sinon (Nikon)
                    boolean bandeau = e.rd8(0x131F8A) == 0x9F && e.rd8(0x131F8B) == 0x8C;
                    w = new String[]{"jusqua8", "0x83CE3FE8", w[1], bandeau ? "right" : "down", "6"};
                }
                switch (w[0]) {
                    case "run": runFor(e, parseN(w[1])); break;
                    case "png": {
                        int fb = Ecran.base(e);
                        File f = new File(w[1]).isAbsolute() ? new File(w[1]) : new File(sortie, w[1]);
                        if (fb == 0) System.out.println("  pas encore de tampon d'écran");
                        else { Ecran.png(e, fb, f); System.out.println("  capture : " + f.getAbsolutePath()); }
                        break;
                    }
                    case "ybrut": {
                        int fb = Ecran.base(e);
                        File f = new File(w[1]).isAbsolute() ? new File(w[1]) : new File(sortie, w[1]);
                        byte[] y = new byte[640 * 480];
                        for (int k = 0; k < y.length; k++) y[k] = (byte) e.rd8(fb + k);
                        java.nio.file.Files.write(f.toPath(), y);
                        System.out.println("  plan Y : " + f.getAbsolutePath());
                        break;
                    }
                    case "down": Touches.set(e, w[1], true); break;
                    case "up": Touches.set(e, w[1], false); break;
                    case "press":
                        Touches.set(e, w[1], true); runFor(e, parseN(w.length > 2 ? w[2] : "4M"));
                        Touches.set(e, w[1], false); runFor(e, parseN(w.length > 3 ? w[3] : "4M"));
                        break;
                    case "a": {
                        int c = Integer.parseInt(w[1].replace("0x", ""), 16);
                        if (w.length > 2) {
                            byte[] d = new byte[w.length - 2];
                            for (int k = 2; k < w.length; k++) d[k - 2] = (byte) Integer.parseInt(w[k], 16);
                            e.io.fakeA.data.put(c, d);
                        }
                        e.io.fakeA.requests.add(c);
                        break;
                    }
                    case "peek": {
                        int a = adr(w[1]), n = w.length > 2 ? Integer.parseInt(w[2]) : 1;
                        StringBuilder sb = new StringBuilder(String.format("  %08X :", a));
                        for (int k = 0; k < n; k++) sb.append(String.format(" %02X", e.rd8(a + k)));
                        System.out.println(sb);
                        break;
                    }
                    case "poke8": e.wr8(adr(w[1]), adr(w[2])); break;
                    case "expect8": {
                        int v = e.rd8(adr(w[1])), att = adr(w[2]);
                        boolean ok = v == att;
                        System.out.printf("  %s : octet %s = %02X, attendu %02X%n", ok ? "OK" : "ÉCHEC", w[1], v, att);
                        if (!ok) code = 1;
                        break;
                    }
                    case "expect32min": {
                        long v = e.rd32(adr(w[1])) & 0xFFFFFFFFL, att = Long.parseLong(w[2]);
                        boolean ok = v >= att;
                        System.out.printf("  %s : mot %s = %d, attendu au moins %d%n", ok ? "OK" : "ÉCHEC", w[1], v, att);
                        if (!ok) code = 1;
                        break;
                    }
                    case "sys": e.traceSyscalls = w[1].equals("on"); break;
                    case "watch":
                        for (int k = 1; k < w.length; k++) {
                            final int a = adr(w[k]);
                            e.hooks.put(a, em -> {
                                em.log.printf("  passage %08X RP=%08X R4=%08X (%d)%n", a, em.r(com.nikonhacker.disassembly.fr.FrCPUState.RP), em.r(4), em.steps);
                                return false;
                            });
                        }
                        break;
                    case "watchw": // watchw <adresse> <longueur> [max] : journal des écritures dans la plage
                        e.memory.addActivityListener(new Surveillance(e, adr(w[1]), adr(w[2]), w.length > 3 ? Integer.parseInt(w[3]) : 50));
                        break;
                    case "pages": {
                        long a0 = adr(w[1]) & 0xFFFFFFFFL, a1 = adr(w[2]) & 0xFFFFFFFFL;
                        StringBuilder sb = new StringBuilder("  pages touchées :");
                        for (long a = a0; a < a1; a += 0x10000) if (e.memory.isMapped((int) a)) sb.append(String.format(" %08X", a));
                        System.out.println(sb);
                        break;
                    }
                    case "poke32": e.wr32(adr(w[1]), adr(w[2])); break;
                    case "remplir": { // remplir <adr> <n> <octet>
                        int a = adr(w[1]), n = nombre(w[2]), v = adr(w[3]);
                        for (int k = 0; k < n; k++) e.wr8(a + k, v);
                        break;
                    }
                    case "expect16": {
                        int v = e.rd16(adr(w[1])), att = adr(w[2]) & 0xFFFF;
                        boolean ok = v == att;
                        System.out.printf("  %s : demi-mot %s = %04X, attendu %04X%n", ok ? "OK" : "ÉCHEC", w[1], v, att);
                        if (!ok) code = 1;
                        break;
                    }
                    case "expectegal": {
                        int a = adr(w[1]), b = adr(w[2]), n = nombre(w[3]), diff = -1;
                        for (int k = 0; k < n && diff < 0; k++) if (e.rd8(a + k) != e.rd8(b + k)) diff = k;
                        if (diff < 0) System.out.printf("  OK : %d octets identiques en %s et %s%n", n, w[1], w[2]);
                        else {
                            System.out.printf("  ÉCHEC : %s et %s diffèrent à +%d (%02X au lieu de %02X)%n", w[1], w[2], diff,
                                    e.rd8(a + diff), e.rd8(b + diff));
                            code = 1;
                        }
                        break;
                    }
                    case "copier": { // copier <src> <dst> <n>
                        int a = adr(w[1]), d = adr(w[2]), n = nombre(w[3]);
                        for (int k = 0; k < n; k++) e.wr8(d + k, e.rd8(a + k));
                        break;
                    }
                    case "jusqua8": { // jusqua8 <adr> <octet> <touche> <max> : appuyer (4M + 16M) tant que l'octet n'a pas la valeur
                        int a = adr(w[1]), att = adr(w[2]), maxi = nombre(w[4]), n = 0;
                        while (e.rd8(a) != att && n < maxi) {
                            Touches.set(e, w[3], true); runFor(e, parseN("4M"));
                            Touches.set(e, w[3], false); runFor(e, parseN("16M"));
                            n++;
                        }
                        boolean ok = e.rd8(a) == att;
                        System.out.printf("  %s : octet %s = %02X après %d appui(s) sur %s, attendu %02X%n",
                                ok ? "OK" : "ÉCHEC", w[1], e.rd8(a), n, w[3], att);
                        if (!ok) code = 1;
                        break;
                    }
                    case "expecta": { // expecta <cmd> <index> <octet> : donnée reçue du B par le faux A (dernière trame)
                        byte[] d = e.io.fakeA.recu.get(adr(w[1]));
                        int i = nombre(w[2]), att = adr(w[3]), v = d == null || i >= d.length ? -1 : d[i] & 0xFF;
                        boolean ok = v == att;
                        System.out.printf("  %s : commande %s reçue par le faux A, octet %d = %s, attendu %02X%n",
                                ok ? "OK" : "ÉCHEC", w[1], i, v < 0 ? "rien" : String.format("%02X", v), att);
                        if (!ok) code = 1;
                        break;
                    }
                    case "raza": e.io.fakeA.done.clear(); break; // remet à zéro le compte des commandes envoyées par le B
                    case "expectcomptea": { // expectcomptea <cmd> <min> <max> : nombre d'envois de la commande par le B depuis raza
                        int c = e.io.fakeA.done.getOrDefault(adr(w[1]), 0), mn = nombre(w[2]), mx = nombre(w[3]);
                        boolean ok = c >= mn && c <= mx;
                        System.out.printf("  %s : commande %s envoyée %d fois par le B, attendu %d à %d%n", ok ? "OK" : "ÉCHEC", w[1], c, mn, mx);
                        if (!ok) code = 1;
                        break;
                    }
                    case "charger": { // charger <fichier> <adr> : recopie un fichier en mémoire (ex. un AD40….BIN en 0x81000000)
                        File cf = new File(w[1]).isAbsolute() ? new File(w[1]) : new File(scriptFile).getParentFile().toPath().resolve("../..").resolve(w[1]).normalize().toFile();
                        byte[] f = java.nio.file.Files.readAllBytes(cf.toPath());
                        int a = adr(w[2]);
                        for (int k = 0; k < f.length; k++) e.wr8(a + k, f[k] & 0xFF);
                        System.out.printf("  %d octets chargés en %08X%n", f.length, a);
                        break;
                    }
                    case "retour": { // retour <adr> <valeur> : la fonction en <adr> rend aussitôt <valeur> dans R4, à chaque appel
                        final int a = adr(w[1]), v = adr(w[2]);
                        final int RP = com.nikonhacker.disassembly.fr.FrCPUState.RP;
                        e.hooks.put(a, em -> {
                            em.log.printf("  retour forcé de %08X : R4=%08X, vers %08X%n", a, v, em.r(RP));
                            em.setR(4, v);
                            em.cpu.pc = em.r(RP);
                            return true;
                        });
                        break;
                    }
                    case "etata": { // etata <cmd> <octets…> : bloc que le faux A a déjà reçu (gardé avant l'extinction), renvoyé en écho
                        byte[] d = new byte[w.length - 2];
                        for (int k = 0; k < d.length; k++) d[k] = (byte) Integer.parseInt(w[k + 2], 16);
                        e.io.fakeA.recu.put(adr(w[1]), d);
                        break;
                    }
                    case "entree": { // entree <adr> <ou> [<et>] : valeur lue = (mémoire & et) | ou (broches d'entrée d'un port)
                        final int a = adr(w[1]), ou = adr(w[2]), et = w.length > 3 ? adr(w[3]) : 0xFF;
                        e.io.overrides.put(a, v -> (v & et) | ou);
                        break;
                    }
                    case "appel": appel(e, w); break;
                    default: System.out.println("  commande inconnue : " + cmd); code = 1;
                }
            }
        } catch (D40Emu.Garde g) {
            System.out.println("ARRÊT, GARDE : " + g.getMessage());
            System.out.println(e.regs());
            code = 2;
        } catch (Throwable t) {
            System.out.println("ARRÊT sur exception : " + t);
            System.out.println(e.regs());
            code = 3;
        }
        long dt = System.currentTimeMillis() - t0;
        System.out.printf("== bilan : %.1f M instructions en %.1f s (%.1f M/s)%n", e.steps / 1e6, dt / 1000.0, e.steps / 1000.0 / Math.max(1, dt));
        System.out.println("PC final : " + e.regs());
        System.out.println("appels au noyau : " + e.syscallCounts);
        System.out.println("commandes échangées avec le faux A (0x1nn = envoyée par le A) : " + hexKeys(e.io.fakeA.done));
        System.out.printf("octets sur la liaison : %d, synchros trame : %d, commandes du moteur 2D : %s, redimensionnements : %d%n",
                e.io.sioBytes, e.io.vsyncs, hexKeys(e.io.g2dCmds), e.io.rszCount);
        System.out.println("PC les plus fréquents (1/64) :");
        hist.entrySet().stream().sorted((a, b) -> b.getValue() - a.getValue()).limit(8)
                .forEach(en -> System.out.printf("  %08X %d%n", en.getKey(), en.getValue()));
        if (io) e.io.dumpCounts(System.out);
        System.out.println(code == 0 ? "RÉSULTAT : OK" : "RÉSULTAT : ÉCHEC (code " + code + ")");
        System.exit(code);
    }

    /** Adresse de retour fictive : le PC y arrive quand la fonction appelée rend la main (jamais exécutée). */
    static final int RETOUR_APPEL = 0x83FFFFF0;
    /** Haut de la pile privée des appels (page jamais touchée par le firmware dans l'émulateur, vu par « pages »). */
    static final int PILE_APPEL = 0x83FF0000;

    /**
     * appel <adr> [r4] [r5] [r6] [r7] : exécute une fonction du firmware jusqu'à son retour, comme un
     * CALL du code, mais depuis le scénario. Interruptions masquées pendant l'appel (le noyau ne
     * change pas de tâche au milieu) ; tous les registres, PS et PC sont rendus à l'identique.
     */
    static void appel(D40Emu e, String[] w) throws EmulationException {
        while (e.inDelaySlot()) e.step();          // jamais au milieu d'un créneau de délai
        com.nikonhacker.disassembly.fr.FrCPUState c = e.cpu;
        int ps = c.getPS(), pc = c.pc;
        int[] regs = new int[com.nikonhacker.disassembly.fr.FrCPUState.NUM_STD_REGISTERS];
        for (int k = 0; k < regs.length; k++) regs[k] = c.getReg(k);
        int sp = c.getReg(15);
        c.I = 0;
        for (int k = 2; k < w.length && k < 6; k++) e.setR(4 + k - 2, adr(w[k]));
        e.setR(15, PILE_APPEL);
        e.setR(com.nikonhacker.disassembly.fr.FrCPUState.RP, RETOUR_APPEL);
        c.pc = adr(w[1]);
        long n = 0;
        while (c.pc != RETOUR_APPEL || e.inDelaySlot()) {
            e.step();
            if (++n > 200_000_000L) throw new D40Emu.Garde("appel " + w[1] + " : pas de retour après 200 M instructions");
        }
        int r4 = e.r(4), spFin = e.r(15);
        c.setPS(ps, false);
        for (int k = 0; k < regs.length; k++) if (k != 15) c.setReg(k, regs[k]);
        c.setReg(15, sp);
        c.pc = pc;
        System.out.printf("  retour de %s après %d instructions : R4=%08X, pile %s%n", w[1], n, r4,
                spFin == PILE_APPEL ? "rendue" : String.format("DÉCALÉE (%08X au lieu de %08X)", spFin, PILE_APPEL));
        if (spFin != PILE_APPEL) throw new D40Emu.Garde("appel " + w[1] + " : la pile n'est pas rendue");
    }

    static String hexKeys(Map<Integer, Integer> m) {
        StringBuilder sb = new StringBuilder("{");
        m.forEach((k, v) -> sb.append(String.format("%s%X=%d", sb.length() > 1 ? ", " : "", k, v)));
        return sb.append("}").toString();
    }
}
