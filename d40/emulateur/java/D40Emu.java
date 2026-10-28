package com.nikonhacker.emu;

import com.nikonhacker.disassembly.OutputOption;
import com.nikonhacker.disassembly.fr.FrCPUState;
import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.peripherials.interruptController.fr.FrInterruptController;

import java.io.*;
import java.util.*;

/**
 * Émulateur du processeur B du Nikon D40 (firmware BD400111), sans interface graphique.
 * S'appuie sur le cœur FR de nikon-firmware-tools (Simeon Pilgrim) : seul le jeu d'instructions
 * et le contrôleur d'interruptions sont repris ; la carte mémoire et les périphériques du D40
 * sont dans D40Io.
 *
 * Placé dans le paquet com.nikonhacker.emu pour accéder au contexte protégé de l'émulateur
 * (créneau de délai en cours).
 */
public class D40Emu {

    public final DebuggableMemory memory = new DebuggableMemory(false);
    public final FrCPUState cpu;
    public final Platform platform;
    public final FrInterruptController intc;
    public final FrEmulator emu;
    public final D40Io io;
    public long steps = 0;
    public final Map<Integer, PcHook> hooks = new HashMap<>();
    public final PrintStream log;
    /** Noms des appels µITRON (numéro négatif dans R12, INT #0x40), liste du module ghidra-fr60. */
    public static final Map<Integer, String> SYSCALL = new HashMap<>();
    static { Map<Integer,String> N = SYSCALL; N.put(-23,"sta_tsk"); N.put(-21,"ext_tsk"); N.put(-25,"ter_tsk"); N.put(-30,"dis_dsp"); N.put(-29,"ena_dsp"); N.put(-27,"chg_pri"); N.put(-28,"rot_rdq"); N.put(-31,"rel_wai"); N.put(-24,"get_tid"); N.put(-20,"ref_tsk"); N.put(-33,"sus_tsk"); N.put(-35,"rsm_tsk"); N.put(-36,"frsm_tsk"); N.put(-38,"slp_tsk"); N.put(-37,"tslp_tsk"); N.put(-39,"wup_tsk"); N.put(-40,"can_wup"); N.put(-55,"sig_sem"); N.put(-53,"wai_sem"); N.put(-107,"preq_sem"); N.put(-171,"twai_sem"); N.put(-52,"ref_sem"); N.put(-48,"set_flg"); N.put(-47,"clr_flg"); N.put(-46,"wai_flg"); N.put(-106,"pol_flg"); N.put(-170,"twai_flg"); N.put(-44,"ref_flg"); N.put(-63,"snd_msg"); N.put(-61,"rcv_msg"); N.put(-108,"prcv_msg"); N.put(-172,"trcv_msg"); N.put(-60,"ref_mbx"); N.put(-141,"get_blk"); N.put(-104,"pget_blk"); N.put(-143,"rel_blk"); N.put(-140,"ref_mpl"); N.put(-77,"get_blf"); N.put(-103,"pget_blf"); N.put(-167,"tget_blf"); N.put(-79,"ref_blf"); N.put(-76,"ref_mpf"); N.put(-69,"ret_int"); N.put(-8,"loc_cpu"); N.put(-7,"unl_cpu"); N.put(-67,"chg_ilm"); N.put(-68,"ref_ilm"); N.put(-83,"set_tim"); N.put(-84,"get_tim"); N.put(-85,"dly_Tsk"); N.put(-90,"def_cyc"); N.put(-94,"act_cyc"); N.put(-92,"ref_cyc"); N.put(-89,"def_alm"); N.put(-91,"ref_alm"); N.put(-93,"ret_tmr"); N.put(-16,"get_ver"); N.put(-12,"ref_sys"); }
    public boolean traceSyscalls = false;
    public final Map<String, Integer> syscallCounts = new TreeMap<>();
    /** Appelé à chaque INT #0x40, avant exécution. */
    public java.util.function.Consumer<D40Emu> onSyscall = null;

    public interface PcHook { /** @return true pour sauter l'exécution de l'instruction (le crochet a déplacé le PC) */
        boolean run(D40Emu e);
    }

    public D40Emu(File firmware, PrintStream log) throws IOException {
        this.log = log;
        memory.loadFile(firmware, 0x40000, false);
        cpu = new FrCPUState(0xC0F90);           // vecteur 0 de la table 0xEFC00
        MasterClock clock = new MasterClock();
        platform = new Platform(clock);
        platform.setCpuState(cpu);
        platform.setMemory(memory);
        intc = new FrInterruptController(platform);
        platform.setInterruptController(intc);
        emu = new FrEmulator(platform);
        emu.setContext(memory, cpu, intc);
        emu.setOutputOptions(EnumSet.noneOf(OutputOption.class));
        io = new D40Io(this);
        memory.addActivityListener(io);
    }

    public boolean inDelaySlot() {
        return emu.context.nextPc != null;
    }

    /** Erreur de garde : ce qu'un vrai FR ferait planter ou ce que le boîtier ne tolérerait pas. */
    public static class Garde extends RuntimeException {
        public Garde(String m) { super(m); }
    }

    final com.nikonhacker.disassembly.fr.FrStatement probe = new com.nikonhacker.disassembly.fr.FrStatement();
    public boolean gardes = true;
    public final Set<Integer> horsRomSignale = new HashSet<>();

    /** Vérifie l'instruction au PC avant de l'exécuter. */
    void verifier() {
        int pc = cpu.pc;
        int op = memory.loadUnsigned16(pc, null);
        com.nikonhacker.disassembly.fr.FrInstruction ins = com.nikonhacker.disassembly.fr.FrInstructionSet.instructionMap[op];
        if (ins == null || ins == com.nikonhacker.disassembly.fr.FrInstructionSet.defaultInstruction || op == 0xFFFF)
            throw new Garde(String.format("instruction non définie %04X à %08X (le FR lèverait l'exception « undefined instruction »)", op, pc));
        if (inDelaySlot()) {
            probe.reset();
            probe.getNextStatement(memory, pc);
            probe.setInstruction(ins);
            probe.decodeOperands(pc, memory);
            boolean multi = probe.getNumBytes() > 2;
            boolean flux = ins.getFlowType() != com.nikonhacker.disassembly.Instruction.FlowType.NONE
                    || ins.getDelaySlotType() != com.nikonhacker.disassembly.Instruction.DelaySlotType.NONE;
            if (multi || flux)
                throw new Garde(String.format("instruction interdite dans un créneau de délai à %08X : %04X (%s)%s", pc, op, ins.getName(),
                        multi ? ", instruction de plusieurs mots" : ", saut, appel, retour ou interruption"));
        }
        boolean rom = (pc >= 0x40000 && pc < 0x410000);
        boolean ram = (pc >= 0x83000000 && pc < 0x84000000) || (pc >= 0x68000000 && pc < 0x68010000);
        if (!rom && !ram) throw new Garde(String.format("exécution hors de la ROM et de la RAM à %08X", pc));
        if (ram && horsRomSignale.add(pc & ~0xFFF)) log.printf("note : exécution en RAM à %08X (normal pour les routines flash)%n", pc);
        if (rom && ((pc >= 0xF0000 && pc < 0x120000) || (pc >= 0x170000 && pc < 0x1B0000)))
            throw new Garde(String.format("exécution dans une zone jamais écrite par la mise à jour (%08X) : le contenu réel du boîtier y est inconnu", pc));
    }

    /** Exécute une instruction (avec crochets). */
    public void step() throws EmulationException {
        if (gardes) verifier();
        if (!inDelaySlot()) {
            PcHook h = hooks.get(cpu.pc);
            if (h != null && h.run(this)) {
                steps++;
                return;
            }
            if (memory.loadUnsigned16(cpu.pc, null) == 0x1F40) syscall();
        }
        emu.context.cycleIncrement = 1;
        emu.onClockTick();
        steps++;
        io.tick();
    }

    public String syscallName() {
        String n = SYSCALL.get(r(12));
        return n == null ? "sys" + r(12) : n;
    }

    /** Tâche courante (pointeur de bloc de contrôle à 0x68000000). */
    public int curTcb() { return rd32(0x68000000); }

    void syscall() {
        String n = syscallName();
        syscallCounts.merge(n, 1, Integer::sum);
        if (traceSyscalls)
            log.printf("SYS %-9s R4=%08X R5=%08X R6=%08X R7=%08X @%08X tcb=%08X n=%d%n", n, r(4), r(5), r(6), r(7), cpu.pc, curTcb(), steps);
        if (onSyscall != null) onSyscall.accept(this);
    }

    /** Retour de fonction simulé : PC = RP. */
    public void ret() {
        cpu.pc = cpu.getReg(FrCPUState.RP);
    }

    public int r(int n) { return cpu.getReg(n); }
    public void setR(int n, int v) { cpu.setReg(n, v); }
    public int rd32(int a) { return memory.load32(a, null); }
    public int rd16(int a) { return memory.loadUnsigned16(a, null); }
    public int rd8(int a) { return memory.loadUnsigned8(a, null); }
    public void wr32(int a, int v) { memory.store32(a, v, null); }
    public void wr16(int a, int v) { memory.store16(a, v, null); }
    public void wr8(int a, int v) { memory.store8(a, v, null); }

    public static String hex(int v) { return String.format("0x%08X", v); }

    /** Désassemble n instructions à partir de addr (sans effet de bord sur l'émulation). */
    public String disasm(int addr, int n) {
        StringBuilder sb = new StringBuilder();
        com.nikonhacker.disassembly.StatementContext ctx = new com.nikonhacker.disassembly.StatementContext();
        ctx.cpuState = cpu.createCopy();
        ctx.memory = memory;
        for (int i = 0; i < n; i++) {
            ctx.cpuState.pc = addr;
            com.nikonhacker.disassembly.fr.FrStatement st = new com.nikonhacker.disassembly.fr.FrStatement();
            try {
                st.getNextStatement(memory, addr);
                st.setInstruction(com.nikonhacker.disassembly.fr.FrInstructionSet.instructionMap[st.data[0]]);
                st.decodeOperands(addr, memory);
                st.formatOperandsAndComment(ctx, false, EnumSet.noneOf(OutputOption.class));
                sb.append(String.format("%08X  %-16s %s%n", addr, st.getFormattedBinaryStatement(), st.toString(EnumSet.noneOf(OutputOption.class)).trim()));
                addr += st.getNumBytes();
            } catch (Exception ex) {
                sb.append(String.format("%08X  ?? %s%n", addr, ex));
                addr += 2;
            }
        }
        return sb.toString();
    }

    public String regs() {
        StringBuilder sb = new StringBuilder();
        sb.append("PC=").append(hex(cpu.pc));
        for (int i = 0; i < 16; i++) sb.append(String.format(" R%d=%08X", i, r(i)));
        sb.append(String.format(" RP=%08X SSP=%08X USP=%08X TBR=%08X PS=%08X ILM=%d S=%d",
                r(FrCPUState.RP), r(FrCPUState.SSP), r(FrCPUState.USP), r(FrCPUState.TBR), cpu.getPS(), cpu.getILM(), cpu.getS()));
        return sb.toString();
    }
}
