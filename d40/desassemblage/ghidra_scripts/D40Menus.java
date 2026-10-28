// Crée et nomme les fonctions des écrans de menu : tblEcrans (0x156644, 170 enregistrements de
// 12 octets {u16 attributs, u16, fonction d'entrée, fonction d'action}) est indexée par le numéro
// d'écran (+0x12 de l'en-tête d'un menu). Ghidra ne trouve pas seul ces fonctions (pointées
// seulement depuis la table). Les titres viennent de desassemblage/ecrans.tsv (outils/menus.py ecrans).
// Nom : ecranNNN_entree / ecranNNN_action pour un seul écran, menu_entree_XXXXXX / menu_action_XXXXXX
// pour une fonction partagée ; le commentaire liste les écrans. Ne renomme pas un symbole posé à la main.
// @category D40
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class D40Menus extends GhidraScript {

    private static final long TBL_ECRANS = 0x156644L;
    private static final int NB_ECRANS = 170;

    @Override
    protected void run() throws Exception {
        Map<Integer, String> titres = new HashMap<>();
        File tsv = new File(getSourceFile().getParentFile().getParentFile().getFile(false), "ecrans.tsv");
        if (tsv.exists()) {
            for (String l : Files.readAllLines(tsv.toPath(), StandardCharsets.UTF_8)) {
                String[] c = l.split("\t");
                if (c.length >= 5) {
                    titres.put(Integer.parseInt(c[0]), c[4]);
                }
            }
        }
        // fonction -> liste des écrans, pour l'entrée (0) et l'action (1)
        List<Map<Long, List<Integer>>> usages = List.of(new TreeMap<>(), new TreeMap<>());
        createLabel(toAddr(TBL_ECRANS), "tblEcrans", true, SourceType.USER_DEFINED);
        for (int n = 0; n < NB_ECRANS; n++) {
            Address e = toAddr(TBL_ECRANS + 12L * n);
            for (int k = 0; k < 2; k++) {
                long f = getInt(e.add(4 + 4L * k)) & 0xFFFFFFFFL;
                if (f != 0) {
                    usages.get(k).computeIfAbsent(f, x -> new ArrayList<>()).add(n);
                }
            }
        }
        int nb = 0;
        String[] role = {"entree", "action"};
        for (int k = 0; k < 2; k++) {
            for (Map.Entry<Long, List<Integer>> u : usages.get(k).entrySet()) {
                Address a = toAddr(u.getKey());
                List<Integer> ecrans = u.getValue();
                disassemble(a);
                addEntryPoint(a);
                Function fn = getFunctionAt(a);
                String nom = ecrans.size() == 1 ? String.format("ecran%03d_%s", ecrans.get(0), role[k])
                        : String.format("menu_%s_%06x", role[k], u.getKey());
                if (fn == null) {
                    fn = createFunction(a, nom);
                } else if (fn.getName().startsWith("FUN_")) {
                    fn.setName(nom, SourceType.USER_DEFINED);
                }
                StringBuilder c = new StringBuilder("[vérifié] fonction d'" + role[k] + " des écrans de menu (tblEcrans) :");
                for (int n : ecrans) {
                    c.append(String.format(" %d %s ;", n, titres.getOrDefault(n, "")));
                }
                setPlateComment(a, c.toString());
                nb++;
            }
        }
        println("D40Menus : " + nb + " fonctions d'écran nommées");
    }
}
