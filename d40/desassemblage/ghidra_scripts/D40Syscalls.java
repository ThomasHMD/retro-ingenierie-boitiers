// Liste les appels système µITRON résolus par ResolveUTronSyscallsScript : pour chaque appel
// (cre_tsk, sta_tsk, wai_flg…), le nombre de sites d'appel et les fonctions appelantes.
// Argument : <fichier de sortie TSV> (appel, site, fonction appelante)
// @category D40
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

import java.io.PrintWriter;

public class D40Syscalls extends GhidraScript {

    @Override
    protected void run() throws Exception {
        AddressSpace sys = currentProgram.getAddressFactory().getAddressSpace("syscall");
        if (sys == null) {
            println("D40Syscalls : pas d'espace syscall, lancer ResolveUTronSyscallsScript d'abord");
            return;
        }
        int n = 0;
        try (PrintWriter out = new PrintWriter(getScriptArgs()[0], "UTF-8")) {
            out.println("appel\tsite\tfonction");
            for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
                if (f.getEntryPoint().getAddressSpace() != sys) {
                    continue;
                }
                for (Reference r : getReferencesTo(f.getEntryPoint())) {
                    Function a = getFunctionContaining(r.getFromAddress());
                    out.printf("%s\t%s\t%s%n", f.getName(), r.getFromAddress(), a == null ? "?" : a.getName());
                    n++;
                }
            }
        }
        println("D40Syscalls : " + n + " sites d'appel");
    }
}
