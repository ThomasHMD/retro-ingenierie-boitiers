package com.nikonhacker.emu;

import java.util.*;

/**
 * Faux processeur A : répond octet par octet au protocole de la tâche 14 du B (0xA9280), en lisant
 * l'état de l'automate de réception du B (0x83CEE964) au moment où l'octet arrive. Variantes (étude du A, octobre 2026) :
 *
 * Ajouts, pilotés par des variables d'environnement :
 *  - D40_FAUXA=normal|muet|silencieux
 *      muet       : le A ne répond plus du tout (aucun octet reçu par le B : délai de garde à chaque échange) ;
 *      silencieux : le A répond au protocole (accusés corrects) mais n'envoie jamais rien de lui-même.
 *  - D40_FAUXA_SANS=03,14,19 : commandes retirées de la séquence de démarrage ;
 *  - D40_FAUXA_SEUL=14,19    : séquence de démarrage réduite à ces commandes ;
 *  - D40_FAUXA_MAJ=1         : le faux A joue le côté A de la mise à jour (lu dans le firmware A,
 *      0xCEDF4, 0xCEE4C, 0xF8000, flasheur 0xF3000) : accusé 0x0E {0x40,0,0} à la commande 0x0D bit 6,
 *      puis demande des blocs de 128 octets par la commande 0x0F (n = 2, numéro de bloc), vérifie ce que
 *      le B renvoie contre D40_FAUXA_FICHIER, puis envoie 0x0E {D40_FAUXA_STATUT (défaut 0x42), 0, 0}.
 *      D40_FAUXA_BLOCS = liste de blocs en hexadécimal (défaut 0,1,2,400,600,680,700,7FF) ou « tous ».
 */
public class FakeA {
    final D40Emu e;
    public final Deque<Integer> requests = new ArrayDeque<>();
    public final Map<Integer, byte[]> data = new HashMap<>();
    public boolean log = true;
    public final Map<Integer, int[]> replies = new HashMap<>();
    public final Map<Integer, Integer> echo = new HashMap<>();

    final String mode = System.getenv().getOrDefault("D40_FAUXA", "normal");
    public final boolean muet = mode.equals("muet");
    final boolean silencieux = mode.equals("silencieux");
    final boolean maj = "1".equals(System.getenv("D40_FAUXA_MAJ"));

    {
        if (!silencieux) {
            replies.put(0x2C, new int[]{0x2D});
            replies.put(0x07, new int[]{0x08}); echo.put(0x08, 0x07);
            replies.put(0x05, new int[]{0x06}); echo.put(0x06, 0x05);
            replies.put(0x09, new int[]{0x0A}); echo.put(0x0A, 0x09);
        }
    }

    int tblBuf(int cmd) { return e.rd32(0xE482C + 16 * cmd); }
    public final Map<Integer, Integer> done = new TreeMap<>();
    int cur = 0;
    long holdoff = 0;

    FakeA(D40Emu e) { this.e = e; }

    static Set<Integer> liste(String s) {
        Set<Integer> r = new LinkedHashSet<>();
        if (s == null || s.isEmpty()) return r;
        for (String x : s.split(",")) r.add(Integer.parseInt(x.trim(), 16));
        return r;
    }

    public void bootSequence() {
        if (muet || silencieux) {
            System.out.println("  faux A : mode " + mode + ", aucune commande envoyée au démarrage");
            return;
        }
        byte[] c11 = new byte[9]; c11[1] = 0x08;
        data.put(0x11, c11);
        List<Integer> seq = new ArrayList<>();
        for (int c : new int[]{0x11, 0x08, 0x03, 0x02, 0x04, 0x06, 0x0A, 0x0C, 0x0E, 0x15, 0x16, 0x1A,
                0x1C, 0x23, 0x24, 0x25, 0x26, 0x28, 0x29, 0x14, 0x19}) seq.add(c);
        Set<Integer> seul = liste(System.getenv("D40_FAUXA_SEUL"));
        Set<Integer> sans = liste(System.getenv("D40_FAUXA_SANS"));
        if (!seul.isEmpty()) seq.retainAll(seul);
        seq.removeAll(sans);
        requests.addAll(seq);
        System.out.printf("  faux A : séquence de démarrage %s%n", hex(seq));
    }

    static String hex(Collection<Integer> c) {
        StringBuilder sb = new StringBuilder();
        for (int x : c) sb.append(String.format("%s%02X", sb.length() > 0 ? " " : "", x));
        return sb.toString();
    }

    int tblLen(int cmd) { return e.rd32(0xE482C + 16 * cmd + 4); }
    int tblDir(int cmd) { return e.rd32(0xE482C + 16 * cmd + 8); }

    // ---- mise à jour du A ----
    final Deque<byte[]> payload0E = new ArrayDeque<>();
    final Deque<Integer> blocs = new ArrayDeque<>();
    byte[] cur0E = null;
    int curBloc = -1, nbRecus = 0, octetN = -1;
    final byte[] blocBuf = new byte[128];
    /** Données reçues du B, sur le fil, par commande (dernière trame) : le vrai A renvoie en écho ce qu'il a
     *  reçu (0x06 pour 0x05…), pas la mémoire du B ; écart visible quand le B modifie la copie envoyée. */
    public final Map<Integer, byte[]> recu = new HashMap<>();
    int recvCmd = -1;
    java.io.ByteArrayOutputStream recvBuf = null;
    int blocPos = 0, sommeB = 0;
    public int blocsOk = 0, blocsFaux = 0;
    byte[] fichier = null;
    boolean majLancee = false;

    void lancerMaj() {
        majLancee = true;
        try { fichier = java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(System.getenv("D40_FAUXA_FICHIER"))); }
        catch (Exception x) { System.out.println("  faux A : fichier de référence illisible : " + x); }
        String b = System.getenv().getOrDefault("D40_FAUXA_BLOCS", "0,1,2,400,600,680,700,7FF");
        if (b.equals("tous")) { for (int k = 0; k < 0x800; k++) if (k < 0x680 || k >= 0x700) blocs.add(k); }
        else blocs.addAll(liste(b));
        int statut = Integer.parseInt(System.getenv().getOrDefault("D40_FAUXA_STATUT", "42"), 16);
        payload0E.add(new byte[]{0x40, 0, 0});
        requests.add(0x0E);                                  // accusé : « mise à jour du A acceptée »
        for (int k = 0; k < blocs.size(); k++) requests.add(0x0F);
        payload0E.add(new byte[]{(byte) statut, 0, 0});
        requests.add(0x0E);                                  // compte rendu final du flasheur
        System.out.printf("  faux A : 0x0D bit 6 reçu (0x83CE950B = %02X) : mise à jour du A, %d blocs à demander, statut final %02X (à %d)%n",
                e.rd8(0x83CE950B), blocs.size(), statut, e.steps);
    }

    byte[] dataFor(int cmd) {
        if (cmd == 0x0E && cur0E != null) return cur0E;
        Integer src = echo.get(cmd);
        if (src != null && recu.containsKey(src) && recu.get(src).length == tblLen(cmd)) return recu.get(src).clone();
        if (src != null) {
            byte[] d = new byte[tblLen(cmd)];
            for (int k = 0; k < d.length; k++) d[k] = (byte) e.rd8(tblBuf(src) + k);
            return d;
        }
        byte[] d = data.get(cmd);
        if (d == null) d = new byte[tblLen(cmd)];
        return d;
    }

    int byteFor(int tx) {
        int st = e.rd8(0x83CEE964);
        int sum = e.rd8(0x83CEE95B);
        switch (st) {
            case 0x01: {
                int b = e.rd8(0x83CEE962);
                if (!requests.isEmpty()) { cur = requests.poll(); } else cur = 0;
                if (cur == 0x0E && !payload0E.isEmpty()) cur0E = payload0E.poll();
                if (cur == 0x0F) { curBloc = blocs.isEmpty() ? 0 : blocs.poll(); blocPos = 0; octetN = -1; }
                if (log) e.log.printf("A<->B commande B=%02X A=%02X n=%d%n", b, cur, e.steps);
                // collision (les deux envoient une commande) : celle du A passe, le B renvoie la sienne plus tard
                // (relevé d’octobre 2026, démarrage réel) ; ni compte ni réponse pour la tentative perdue
                if (b != 0 && cur == 0) {
                    done.merge(b, 1, Integer::sum);
                    if (maj && b == 0x0D && !majLancee && (e.rd8(0x83CE950B) & 0x40) != 0) lancerMaj();
                    int[] r = replies.get(b);
                    if (r != null) for (int x : r) requests.add(x);
                }
                if (cur != 0) done.merge(0x100 | cur, 1, Integer::sum);
                return cur;
            }
            case 0x02: return tblLen(cur) & 0xFF;
            case 0x03: { int n = tblLen(cur); int k = n - e.rd8(0x83CEE95C); return dataFor(cur)[k] & 0xFF; }
            case 0x04: return (0xFF - sum) & 0xFF;
            case 0x0B: return 0;
            case 0x0C: return 0;
            case 0x0D: return (0xFF - sum) & 0xFF;
            // commande 0x0F (sens variable) : le A envoie n = 2 et le numéro de bloc, puis le B renvoie 128 octets
            case 0x0E: return 2;
            case 0x0F: { int k = 2 - e.rd8(0x83CEE95C); return k == 0 ? (curBloc >> 8) & 0xFF : curBloc & 0xFF; }
            case 0x10: return (0xFF - sum) & 0xFF;
            case 0x05: if (cur == 0x0F) { octetN = tx; sommeB = 0x0F + tx; } return 0;   // le B vient d'envoyer n
            case 0x06: if (cur == 0x0F && blocPos < 128) { blocBuf[blocPos++] = (byte) tx; sommeB += tx; } return 0;
            case 0x07: if (cur == 0x0F) finBloc(tx); return 0;                          // le B vient d'envoyer le contrôle
            // commande du B (sens B→A), relevé d’octobre 2026 : état 08 = le B vient d'envoyer la longueur,
            // 09 = un octet de données, 0A = la somme ; le faux A garde la trame reçue (écho, expecta)
            case 0x08: recvCmd = e.rd8(0x83CEE960); recvBuf = new java.io.ByteArrayOutputStream(); return 0;
            case 0x09: if (recvBuf != null) recvBuf.write(tx); return 0;
            case 0x0A: if (recvBuf != null) { recu.put(recvCmd, recvBuf.toByteArray()); recvBuf = null; } return 0;
            default: return 0;
        }
    }

    void finBloc(int ctrl) {
        boolean ok = fichier != null && blocPos == 128 && octetN == 0x80;
        int off = curBloc * 128;
        if (ok) for (int k = 0; k < 128; k++) if (off + k >= fichier.length || fichier[off + k] != blocBuf[k]) { ok = false; break; }
        if (ok) blocsOk++; else blocsFaux++;
        nbRecus++;
        if (nbRecus <= 12 || !ok)
            System.out.printf("  faux A : bloc %03X reçu (n=%02X, %d octets, contrôle %02X) : %s (à %d)%n", curBloc, octetN, blocPos,
                    ctrl, ok ? "identique au fichier, adresse A " + String.format("0x%05X", 0xC0000 + off) : "DIFFÉRENT", e.steps);
        if (nbRecus == 13) System.out.println("  faux A : (blocs suivants : seulement les écarts)");
    }

    void tick() {
        if (muet) return;
        if (!requests.isEmpty() && holdoff-- <= 0 && e.rd8(0x83CEE964) == 0 && e.rd8(0x83CEE963) == 1) {
            e.io.raiseARequest();
            holdoff = 2000;
        }
    }
}
