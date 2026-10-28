// Décompile des fonctions du firmware 645D (base 0x10000000, données initialisées copiées en 0x80000000).
// Arguments : <sortie> <adresse> [<adresse> ...]   (adresse hexadécimale ; peut viser l'intérieur d'une fonction)
// Le début de fonction est cherché en remontant jusqu'au RET (0x9720) ou RET:D (0x9F20 + créneau) précédent.
// @category P645
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

import java.io.PrintWriter;

public class P645Decomp extends GhidraScript {

    void preparer() throws Exception {
        Memory mem = currentProgram.getMemory();
        if (mem.getBlock(toAddr(0x80000000L)) == null) {
            int n = 0x14000 - 0x4fa4;
            byte[] buf = new byte[n];
            mem.getBytes(toAddr(0x10004fa4L), buf);
            MemoryBlock b = mem.createInitializedBlock("ram_data", toAddr(0x80000000L), n, (byte) 0, monitor, false);
            mem.setBytes(toAddr(0x80000000L), buf);
            b.setWrite(true);
            MemoryBlock z = mem.createUninitializedBlock("ram_bss", toAddr(0x80000000L + n), 0x100000 - n, false);
            z.setWrite(true);
        }
    }

    Address debut(Address a) throws Exception {
        long off = a.getOffset() & ~1L;
        for (long p = off - 2; p > off - 0x8000; p -= 2) {
            int h = getShort(toAddr(p)) & 0xffff;
            if (h == 0x9720) {
                return toAddr(p + 2);
            }
            if (h == 0x9f20) {
                return toAddr(p + 4);
            }
        }
        return toAddr(off);
    }

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        preparer();
        DecompInterface deco = new DecompInterface();
        deco.openProgram(currentProgram);
        try (PrintWriter out = new PrintWriter(args[0], "UTF-8")) {
            for (int i = 1; i < args.length; i++) {
                Address a = toAddr(Long.parseLong(args[i].replace("0x", ""), 16));
                Function f = getFunctionContaining(a);
                if (f == null) {
                    Address d = debut(a);
                    // sauter le remplissage éventuel (NOP 0x9fa0)
                    while ((getShort(d) & 0xffff) == 0x9fa0) d = d.add(2);
                    disassemble(d);
                    f = getFunctionAt(d);
                    if (f == null) f = createFunction(d, null);
                    if (f == null) f = getFunctionContaining(a);
                }
                if (f == null) {
                    out.printf("// %s : aucune fonction%n%n", args[i]);
                    continue;
                }
                out.printf("// ===== %s @ %s (demandé %s ; appelée depuis :", f.getName(), f.getEntryPoint(), args[i]);
                for (Reference r : getReferencesTo(f.getEntryPoint())) {
                    Function ap = getFunctionContaining(r.getFromAddress());
                    out.printf(" %s", ap == null ? r.getFromAddress().toString() : ap.getName());
                }
                out.println(")");
                DecompileResults res = deco.decompileFunction(f, 180, monitor);
                out.println(res.decompileCompleted() ? res.getDecompiledFunction().getC() : "// échec : " + res.getErrorMessage());
                out.println();
            }
        } finally {
            deco.dispose();
        }
    }
}
