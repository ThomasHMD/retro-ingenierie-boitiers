// Désassemble, crée et décompile les fonctions demandées (projet importé sans analyse).
// Arguments : <sortie> <adresse hex> ...
// @category D200
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;

import java.io.PrintWriter;

public class D200Fonctions extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        DecompInterface deco = new DecompInterface();
        deco.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(args[0], "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                Address a = toAddr(Long.parseLong(args[i].replace("0x", ""), 16));
                disassemble(a);
                Function f = getFunctionAt(a);
                if (f == null) f = createFunction(a, null);
                if (f == null) { out.printf("// %s : pas de fonction%n%n", args[i]); continue; }
                out.printf("// ===== %s @ %s%n", f.getName(), f.getEntryPoint());
                for (Instruction ins = getInstructionAt(a); ins != null && f.getBody().contains(ins.getAddress()); ins = ins.getNext())
                    out.printf("//   %s  %s%n", ins.getAddress(), ins);
                DecompileResults res = deco.decompileFunction(f, 120, monitor);
                out.println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "// échec : " + res.getErrorMessage());
                out.println();
            }
        } finally {
            deco.dispose();
        }
    }
}
