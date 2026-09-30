// Écrit le listing assembleur Ghidra d'une ou plusieurs plages (désassemble ce qui ne l'est pas).
// Arguments : <sortie> <début>-<fin> ...   (adresses hexadécimales)
// @category D40
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

import java.io.PrintWriter;

public class P645Listing extends GhidraScript {

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        try (PrintWriter out = new PrintWriter(args[0], "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                String[] p = args[i].split("-");
                Address a = toAddr(Long.parseLong(p[0].replace("0x", ""), 16));
                Address fin = toAddr(Long.parseLong(p[1].replace("0x", ""), 16));
                out.println("; ---- " + args[i]);
                while (a.compareTo(fin) < 0) {
                    if (getInstructionAt(a) == null && getDataAt(a) == null) {
                        disassemble(a);
                    }
                    Function f = getFunctionAt(a);
                    if (f != null) {
                        out.println(f.getName() + ":");
                    }
                    CodeUnit cu = currentProgram.getListing().getCodeUnitAt(a);
                    if (cu == null) {
                        a = a.add(2);
                        continue;
                    }
                    String lab = getSymbolAt(a) != null && f == null ? getSymbolAt(a).getName() + ": " : "";
                    out.printf("%s  %s%s%n", a, lab, cu instanceof Instruction ? cu.toString() : "  .data " + cu);
                    a = a.add(cu.getLength());
                }
            }
        }
    }
}
