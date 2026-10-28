// Décompile en pseudo-C les fonctions demandées et les écrit dans un fichier.
// Arguments : <fichier de sortie> <adresse ou nom> [<adresse ou nom> ...]
// Une adresse peut viser l'intérieur d'une fonction : c'est la fonction qui la contient qui sort.
// @category D40
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.io.PrintWriter;
import java.util.List;

public class D40Decompile extends GhidraScript {

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            printerr("usage : D40Decompile.java <sortie> <adresse|nom> ...");
            return;
        }
        DecompInterface deco = new DecompInterface();
        deco.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(args[0], "UTF-8")) {
            out.printf("// %d fonctions dans le programme%n%n", currentProgram.getFunctionManager().getFunctionCount());
            for (int i = 1; i < args.length; i++) {
                Function f = trouver(args[i]);
                if (f == null) {
                    out.printf("// %s : aucune fonction%n%n", args[i]);
                    continue;
                }
                out.printf("// ===== %s @ %s (appelée depuis :", f.getName(), f.getEntryPoint());
                for (Reference r : getReferencesTo(f.getEntryPoint())) {
                    Function appelant = getFunctionContaining(r.getFromAddress());
                    out.printf(" %s", appelant == null ? r.getFromAddress().toString() : appelant.getName());
                }
                out.println(")");
                DecompileResults res = deco.decompileFunction(f, 120, monitor);
                out.println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "// échec : " + res.getErrorMessage());
                out.println();
            }
        } finally {
            deco.dispose();
        }
    }

    private Function trouver(String cle) {
        if (cle.startsWith("0x")) {
            Address a = toAddr(Long.parseLong(cle.substring(2), 16));
            Function f = getFunctionAt(a);
            return f != null ? f : getFunctionContaining(a);
        }
        List<Function> fs = getGlobalFunctions(cle);
        return fs.isEmpty() ? null : fs.get(0);
    }
}
