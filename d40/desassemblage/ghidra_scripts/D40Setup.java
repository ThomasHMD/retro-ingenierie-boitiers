// Prépare le firmware B du D40 : table des interruptions, reset, puis tous les symboles de
// desassemblage/symboles.tsv (adresse, nom, type, confiance, preuve). Chaque symbole reçoit un
// commentaire « [confiance] preuve ». Se lance avant l'analyse (preScript) et peut être relancé
// après (postScript) : il est idempotent.
// @category D40
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public class D40Setup extends GhidraScript {

    private static final long VECTEURS = 0xEFC00L;
    private static final long RESET = 0xC0F90L;

    @Override
    protected void run() throws Exception {
        Address vect = toAddr(VECTEURS);
        createLabel(vect, "tblVecteurs", true);
        for (int i = 0; i < 256; i++) {
            Address slot = vect.add(i * 4L);
            if (getDataAt(slot) == null) {
                createData(slot, new PointerDataType());
            }
            long cible = getInt(slot) & 0xFFFFFFFFL;
            if (cible >= 0x40000L && cible < 0x410000L && (cible & 1) == 0) {
                Address a = toAddr(cible);
                addEntryPoint(a);
                if (getFunctionAt(a) == null) {
                    createFunction(a, null);
                }
            }
        }
        addEntryPoint(toAddr(RESET));

        File tsv = new File(getSourceFile().getParentFile().getParentFile().getFile(false), "symboles.tsv");
        int n = 0;
        for (String l : Files.readAllLines(tsv.toPath(), StandardCharsets.UTF_8)) {
            String[] c = l.split("\t");
            if (c.length < 5 || !c[0].startsWith("0x")) {
                continue;
            }
            Address a = toAddr(Long.parseLong(c[0].substring(2), 16));
            String nom = c[1], type = c[2];
            if (type.equals("fonction")) {
                disassemble(a);
                addEntryPoint(a);
                Function f = getFunctionAt(a);
                if (f == null) {
                    f = createFunction(a, nom);
                }
                if (f != null) {
                    f.setName(nom, SourceType.USER_DEFINED);
                } else {
                    printf("D40Setup : fonction impossible à créer à %s (%s)%n", a, nom);
                }
            } else {
                createLabel(a, nom, true, SourceType.USER_DEFINED);
            }
            setPlateComment(a, "[" + c[3] + "] " + c[4]);
            n++;
        }
        println("D40Setup : " + n + " symboles appliqués depuis " + tsv);
    }
}
