// Décompile toutes les fonctions du programme dans un seul fichier C, pour pouvoir y chercher
// (grep) constantes, adresses et motifs. Chaque fonction est précédée de son adresse et de
// ses appelants. Argument : <fichier de sortie>
// @category D40
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.io.PrintWriter;

public class D40ExportC extends GhidraScript {

    @Override
    protected void run() throws Exception {
        String sortie = getScriptArgs()[0];
        DecompInterface deco = new DecompInterface();
        deco.openProgram(currentProgram);
        int ok = 0, ko = 0;
        try (PrintWriter out = new PrintWriter(sortie, "UTF-8")) {
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                monitor.checkCancelled();
                StringBuilder appelants = new StringBuilder();
                for (Reference r : getReferencesTo(f.getEntryPoint())) {
                    Function a = getFunctionContaining(r.getFromAddress());
                    appelants.append(' ').append(a == null ? r.getFromAddress().toString() : a.getName());
                }
                out.printf("//@@ %s %s appelants:%s%n", f.getEntryPoint(), f.getName(), appelants);
                DecompileResults res = deco.decompileFunction(f, 60, monitor);
                if (res.decompileCompleted()) {
                    out.println(res.getDecompiledFunction().getC());
                    ok++;
                } else {
                    out.println("// échec : " + res.getErrorMessage());
                    ko++;
                }
            }
        } finally {
            deco.dispose();
        }
        println(String.format("D40ExportC : %d fonctions décompilées, %d échecs", ok, ko));
    }
}
