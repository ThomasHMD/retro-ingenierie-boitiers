// Nomme les fonctions du noyau REALOS : le gestionnaire de INT #0x40 (0xC1586) saute à
// 0xC157E + table[R12] (demi-mots signés, R12 = numéro d'appel négatif). Chaque cible
// devient une fonction « krn_<appel> » (noms : data/fr60_utron_syscall_numbers de ghidra-fr60).
// @category D40
import generic.jar.ResourceFile;
import ghidra.app.script.GhidraScript;
import ghidra.framework.Application;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

import java.nio.file.Files;
import java.util.HashMap;
import java.util.Map;

public class D40Noyau extends GhidraScript {

    private static final long BASE = 0xC157EL;
    private static final long ERREUR_1 = 0xC157EL, ERREUR_2 = 0xC1582L;

    @Override
    protected void run() throws Exception {
        Map<Integer, String> noms = new HashMap<>();
        ResourceFile f = Application.findDataFileInAnyModule("fr60_utron_syscall_numbers");
        for (String l : Files.readAllLines(f.getFile(false).toPath())) {
            if (!l.startsWith("#") && !l.isBlank()) {
                String[] p = l.trim().split(" ");
                noms.put(Integer.parseInt(p[0]), p[1]);
            }
        }
        createLabel(toAddr(0xC1586L), "krn_int40", true);
        int n = 0;
        for (int num = -1; num >= -176; num--) {
            long cible = BASE + getShort(toAddr(BASE + 2L * num));
            if (cible == ERREUR_1 || cible == ERREUR_2 || !noms.containsKey(num)) {
                continue;
            }
            Address a = toAddr(cible);
            disassemble(a);
            Function fn = getFunctionAt(a);
            String nom = "krn_" + noms.get(num);
            if (fn == null) {
                fn = createFunction(a, nom);
            } else {
                fn.setName(nom, SourceType.USER_DEFINED);
            }
            n++;
        }
        println("D40Noyau : " + n + " appels du noyau nommés");

        // Tâches : table de configuration 0xEA868 {u16 nombre, u16 taille} puis, par tâche,
        // +6 priorité (u16), +16 adresse d'entrée, +20 haut de pile.
        Address cfg = toAddr(CFG_TACHES);
        int nb = getShort(cfg) & 0xFFFF, taille = getShort(cfg.add(2)) & 0xFFFF;
        for (int i = 0; i < nb; i++) {
            Address e = cfg.add(4 + (long) i * taille);
            int prio = getShort(e.add(6)) & 0xFFFF;
            Address entree = toAddr(getInt(e.add(16)) & 0xFFFFFFFFL);
            String nom = String.format("tsk%02d_prio%02d", i + 1, prio);
            disassemble(entree);
            addEntryPoint(entree);
            Function fn = getFunctionAt(entree);
            if (fn == null) {
                createFunction(entree, nom);
            } else if (!fn.getName().startsWith("tsk")) {
                fn.setName(nom, SourceType.USER_DEFINED);
            }
        }
        println("D40Noyau : " + nb + " tâches nommées");
    }

    private static final long CFG_TACHES = 0xEA868L;
}
