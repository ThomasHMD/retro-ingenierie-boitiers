package com.nikonhacker.emu;

import java.util.*;

/**
 * Faux processeur B, branché sur la liaison du vrai A émulé (étude, palier 2).
 *
 * Côté A (lu dans le code, octobre 2026) : liaison série 0 du A (0x60 SSR0, 0x61 SIDR0/SODR0, 0x62 SCR0,
 * 0x63 SMR0 = 0xB2 : synchrone, horloge interne émise, donc le A est maître de l'horloge ; 0xDA868),
 * U-timer 0x64 = 0x0F. Tâche 8 du A (0xD9F90) : un échange par octet ; le A écrit SODR0 (0xDA8A8) quand le
 * B a signalé qu'il est prêt (front sur l'interruption externe 4 du A, IRQ 0x14, gestionnaire 0xD9F34 au
 * repos, 0xDA4C8 pendant l'échange, à condition que PDR0 bit 4 = 0) ; à la réception (IRQ 0x1B,
 * gestionnaire 0xDA544) il prend 0xFF − octet. Table des 48 commandes côté A : 0xFB528 (12 octets :
 * longueur A→B, longueur B→A, ?, ?, variable, tampon).
 *
 * Le faux B suit le format vu côté B (FakeA) : [commande][longueur][données…][contrôle], puis des zéros tant
 * que le A fait tourner l'horloge. Inversion sur le fil : réglable (inverser = true : le B émet ~octet).
 */
public class FakeB {
    final AEmu e;
    public boolean log = true;
    public boolean inverser = true;
    /** Contrôle : 0 = 0xFF − (cmd + n + Σ données), 1 = 0xFF − (n + Σ données), 2 = 0xFF − Σ données. */
    public int modeControle = 0;
    public final Deque<int[]> file = new ArrayDeque<>();
    public final List<String> journal = new ArrayList<>();
    int[] cur = null; int pos = 0, totalAB = 0;
    /** Octets émis par le A pendant l'échange en cours (le dernier bloc A→B complet est dans dernierBloc). */
    public final List<Integer> recuA = new ArrayList<>();
    public final Map<Integer, int[]> blocsRecus = new TreeMap<>();
    long pret = -1;               // échéance du prochain front « B prêt »
    public int delaiPret = 300;   // instructions entre la réception d'un octet et le front suivant (hypothèse)
    public long octets = 0;
    final StringBuilder recuDuA = new StringBuilder(), envoyeAuA = new StringBuilder();

    /** Ligne du B vers le A, lue en PDR0 bit 4 et reliée à l'interruption externe 4 du A (front descendant,
     *  ELVR = 11) : 1 au repos, 0 pendant un échange ; chaque front descendant = « le B est prêt ». */
    public int ligne = 1;
    long dernierOctet = -1;
    public int finSilence = 20000;   // instructions sans octet : échange terminé, la ligne remonte
    public boolean repondreAuA = true; // répondre à la ligne de requête du A (PDR E bit 3) par une commande 0

    FakeB(AEmu e) {
        this.e = e; e.io.fakeB = this;
        e.io.overrides.put(0x00, v -> (v & ~0x10) | (ligne << 4));
    }

    void pretB() { ligne = 1; ligne = 0; e.io.frontExterne(4); }

    public void envoyer(int cmd, byte[] d) {
        int n = d.length;
        int[] t = new int[n + 3];
        t[0] = cmd; t[1] = n;
        int s = modeControle == 0 ? cmd + n : modeControle == 1 ? n : 0;
        for (int k = 0; k < n; k++) { t[2 + k] = d[k] & 0xFF; s += d[k] & 0xFF; }
        t[n + 2] = (0xFF - s) & 0xFF;
        file.add(t);
    }

    /** Le A a fait tourner l'horloge pour un octet : il émet a, on rend l'octet du B (tel que sur le fil). */
    int octet(int a) {
        octets++;
        int b = 0;
        if (cur != null && pos < cur.length) b = cur[pos];
        // Sens A→B (le B n'a rien envoyé : commande 0) : le A émet requête, n, n octets, contrôle ; le B rend
        // des zéros puis, au dernier octet (position n + 4), son contrôle (somme de ses octets = 0xFF), comme
        // le A le fait dans l'autre sens (vu sur la commande 0x05).
        if (cur != null && cur.length == 1 && pos == 1) totalAB = a + 5;
        if (cur != null && cur.length == 1 && totalAB > 0 && pos == totalAB - 1) b = 0xFF;
        if (pos == 0) recuA.clear();
        recuA.add(a);
        pos++;
        dernierOctet = e.steps;
        recuDuA.append(String.format(" %02X", a));
        envoyeAuA.append(String.format(" %02X", b));
        if (log) e.log.printf("  liaison : octet %d, A émet %02X, B émet %02X (instruction %d)%n", pos - 1, a, b, e.steps);
        pret = e.steps + delaiPret;
        return inverser ? (~b) & 0xFF : b;
    }

    void tick() {
        if (cur == null && (e.rd8(0x41) & 0x10) != 0) {
            boolean requeteA = repondreAuA && (e.rd8(0x0E) & 0x08) != 0;
            if (!file.isEmpty() || requeteA) {
                cur = file.isEmpty() ? new int[]{0} : file.poll(); pos = 0; totalAB = 0;
                recuDuA.setLength(0); envoyeAuA.setLength(0);
                if (log) e.log.printf("  liaison : le B ouvre un échange, commande %02X%s (instruction %d)%n", cur[0],
                        requeteA ? " (ligne de requête du A levée)" : "", e.steps);
                dernierOctet = e.steps;
                pretB();
            }
        }
        if (pret >= 0 && e.steps >= pret) {
            pret = -1;
            pretB();   // mémorisé dans EIRR même si le A ne l'a pas encore permis (ENIR)
        }
        if (cur != null && pret < 0 && e.steps - dernierOctet > finSilence) {
            ligne = 1;
            fin();
        }
    }

    public void fin() {
        if (cur != null && cur.length == 1 && recuA.size() >= 2 && recuA.get(0) != 0) {
            int n = recuA.get(1), s = 0;
            int[] d = new int[n];
            for (int k = 0; k < n && k + 2 < recuA.size(); k++) d[k] = recuA.get(k + 2);
            for (int k = 0; k < Math.min(recuA.size(), n + 3); k++) s += recuA.get(k);
            blocsRecus.put(recuA.get(0), d);
            if (log) e.log.printf("  liaison : bloc A→B %02X de %d octets, somme de contrôle %s%n", recuA.get(0), n, (s & 0xFF) == 0xFF ? "bonne" : "FAUSSE");
        }
        totalAB = 0;
        if (cur != null) {
            String j = String.format("échange %02X : B ->%s | A ->%s", cur[0], envoyeAuA, recuDuA);
            journal.add(j);
            if (log) e.log.println("  liaison : fin, " + j + String.format(" (instruction %d)", e.steps));
        }
        cur = null;
    }
}
