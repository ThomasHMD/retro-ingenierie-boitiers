package com.nikonhacker.emu;

import java.util.*;

/**
 * Touches du boîtier, telles que la tâche 15 (0x4D896) les lit dans FUN_0004e2b6 :
 *  - port 0x5000010C du B (actif à 0), bits 0-5 -> bits 24-29 du mot de touches ;
 *  - commande 0x11 envoyée par le A (9 octets, copiés en 0x83CE98EC..) -> bits 4-15.
 * Les noms marqués « ? » sont des hypothèses à confirmer en regardant l'écran.
 */
public class Touches {
    /** nom -> {source (0 = port du B, 1..3 = octet 0..2 de la commande 0x11), masque} */
    public static final Map<String, int[]> K = new LinkedHashMap<>();
    static {
        K.put("menu", new int[]{0, 0x04});     // mot 0x04000000 -> FUN_0004c570 (ouvre le menu) : vérifié par le code
        K.put("play", new int[]{0, 0x02});     // 0x02000000 -> FUN_0004c4dc (visualisation) : vérifié par le code
        K.put("b08", new int[]{0, 0x08});      // 0x08000000 -> FUN_0004c5b0 / c456
        K.put("info", new int[]{0, 0x10});     // 0x10000000 -> FUN_0004c456(0) (écran d'infos) ?
        K.put("b01", new int[]{0, 0x01});
        K.put("ok", new int[]{0, 0x20});       // 0x20000000 : vérifié (valide le choix dans un sous-menu, 0x83CE957F change)
        K.put("left", new int[]{1, 0x40});     // 0x4000 : vérifié à l'écran (menu)
        K.put("right", new int[]{1, 0x80});    // 0x8000 : vérifié à l'écran (menu)
        K.put("up", new int[]{1, 0x20});       // 0x2000 : vérifié à l'écran (menu)
        K.put("down", new int[]{1, 0x10});     // 0x1000 : vérifié à l'écran (menu)
        K.put("a0_02", new int[]{1, 0x02});    // 0x0800
        K.put("a0_01", new int[]{1, 0x01});    // 0x0020 : quitte le menu vers l'écran d'infos (déclencheur à mi-course ?)
        K.put("a0_04", new int[]{1, 0x04});    // 0x0040
        K.put("a1_02", new int[]{2, 0x02});    // 0x0200
        K.put("a1_01", new int[]{2, 0x01});    // 0x0100
        K.put("a1_10", new int[]{2, 0x10});    // 0x0010
        K.put("a2_80", new int[]{3, 0x80});    // 0x0080
    }

    public static void set(D40Emu e, String name, boolean down) {
        int[] k = K.get(name);
        if (k == null) throw new IllegalArgumentException("touche inconnue : " + name + " (connues : " + K.keySet() + ")");
        if (k[0] == 0) {
            if (down) e.io.portCKeys |= k[1]; else e.io.portCKeys &= ~k[1];
        } else {
            byte[] d = e.io.fakeA.data.computeIfAbsent(0x11, c -> new byte[9]);
            d[1] |= 0x08; // bit attendu par la tâche 21
            int i = k[0] - 1;
            if (down) d[i] |= k[1]; else d[i] &= ~k[1];
            e.io.fakeA.requests.add(0x11);
        }
    }
}
