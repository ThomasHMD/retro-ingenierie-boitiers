// Prépare le firmware A du D40 (AD400111.bin, chargé à 0xC0000) : table des 256 vecteurs à
// 0xFFC00 (TBR par défaut du FR), reset = dernier vecteur. Puis applique symboles-A.tsv.
// @category D40
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

public class D40ASetup extends GhidraScript {

    @Override
    protected void run() throws Exception {
        Address vect = toAddr(0xFFC00L);
        createLabel(vect, "tblVecteurs", true);
        for (int i = 0; i < 256; i++) {
            Address slot = vect.add(i * 4L);
            if (getDataAt(slot) == null) {
                createData(slot, new PointerDataType());
            }
            long cible = getInt(slot) & 0xFFFFFFFFL;
            if (cible >= 0xC0000L && cible < 0x100000L && (cible & 1) == 0) {
                Address a = toAddr(cible);
                addEntryPoint(a);
                if (getFunctionAt(a) == null) {
                    createFunction(a, i == 0 ? "reset" : null);
                }
            }
        }
        File tsv = new File(getSourceFile().getParentFile().getParentFile().getFile(false), "symboles-A.tsv");
        if (!tsv.exists()) {
            return;
        }
        for (String l : Files.readAllLines(tsv.toPath(), StandardCharsets.UTF_8)) {
            String[] c = l.split("\t");
            if (c.length < 5 || !c[0].startsWith("0x")) {
                continue;
            }
            Address a = toAddr(Long.parseLong(c[0].substring(2), 16));
            if (c[2].equals("fonction")) {
                disassemble(a);
                Function f = getFunctionAt(a);
                if (f == null) {
                    f = createFunction(a, c[1]);
                }
                if (f != null) {
                    f.setName(c[1], SourceType.USER_DEFINED);
                }
            } else {
                createLabel(a, c[1], true, SourceType.USER_DEFINED);
            }
            setPlateComment(a, "[" + c[3] + "] " + c[4]);
        }
    }
}
