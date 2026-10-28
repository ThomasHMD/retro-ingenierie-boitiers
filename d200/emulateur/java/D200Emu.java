package com.nikonhacker.emu;

import com.nikonhacker.disassembly.OutputOption;
import com.nikonhacker.disassembly.fr.FrCPUState;
import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.memory.listener.MemoryActivityListener;
import com.nikonhacker.emu.peripherials.interruptController.fr.FrInterruptController;

import java.io.*;
import java.util.*;

/**
 * Émulateur du processeur B du Nikon D200 (firmware B 2.01), réduit à l'appel de fonctions (octobre 2026).
 * Même cœur FR que l'émulateur du D40 (nikon-firmware-tools de Simeon Pilgrim : FrEmulator, FrCPUState,
 * DebuggableMemory, FrInterruptController) ; ni démarrage, ni noyau, ni périphériques : on prépare la mémoire,
 * on appelle les fonctions, on lit ce qu'elles ont écrit.
 *
 * Carte mémoire (d200/recherche/d200-firmware-image.md) :
 *  - 0x50000-0x40FFFF : le fichier B2000201.bin (offset = adresse - 0x50000), vecteurs à 0xEFC00 ;
 *  - tout le reste (RAM 0x9xxxxxxx, RAM interne 0x4xxxx, registres de la puce d'image 0x5001xxxx…) :
 *    de la mémoire simple, allouée à la première lecture ou écriture et mise à zéro.
 *
 * Gardes (exception D200Emu.Garde, code de sortie 2 du lanceur) :
 *  - instruction non définie ou 0xFFFF ;
 *  - saut, appel, retour, interruption ou instruction de plusieurs mots dans un créneau de délai ;
 *  - PC hors de la ROM et de la RAM, ou dans une plage jamais écrite par la mise à jour (0xF0000-0x11FFFF,
 *    0x1D0000-0x1FFFFF) : son contenu dans le boîtier est inconnu ;
 *  - écriture du code dans la ROM (0x50000-0x40FFFF) ;
 *  - INT (appel au noyau µITRON ou autre) : le noyau n'est pas émulé ; « noyau ok » dans un scénario le
 *    remplace par un retour immédiat E_OK (R4 = 0), journalisé.
 */
public class D200Emu {
    public static final int BASE = 0x50000, FIN_ROM = 0x410000;

    public final DebuggableMemory memory = new DebuggableMemory(false);
    public final FrCPUState cpu;
    public final Platform platform;
    public final FrInterruptController intc;
    public final FrEmulator emu;
    public long steps = 0;
    public final PrintStream log;

    public interface Crochet { /** @return true pour sauter l'instruction (le crochet a déplacé le PC) */ boolean run(D200Emu e); }
    public final Map<Integer, Crochet> hooks = new HashMap<>();

    /** Erreur de garde : ce qu'un vrai FR ferait planter, ou ce que l'émulateur ne sait pas reproduire. */
    public static class Garde extends RuntimeException { public Garde(String m) { super(m); } }

    /** Noms des appels µITRON (numéro négatif dans R12, INT #0x40), liste reprise de D40Emu (module ghidra-fr60). */
    public static final Map<Integer, String> SYSCALL = new HashMap<>();
    static { Map<Integer,String> N = SYSCALL; N.put(-23,"sta_tsk"); N.put(-21,"ext_tsk"); N.put(-25,"ter_tsk"); N.put(-30,"dis_dsp"); N.put(-29,"ena_dsp"); N.put(-27,"chg_pri"); N.put(-28,"rot_rdq"); N.put(-31,"rel_wai"); N.put(-24,"get_tid"); N.put(-20,"ref_tsk"); N.put(-33,"sus_tsk"); N.put(-35,"rsm_tsk"); N.put(-36,"frsm_tsk"); N.put(-38,"slp_tsk"); N.put(-37,"tslp_tsk"); N.put(-39,"wup_tsk"); N.put(-40,"can_wup"); N.put(-55,"sig_sem"); N.put(-53,"wai_sem"); N.put(-107,"preq_sem"); N.put(-171,"twai_sem"); N.put(-52,"ref_sem"); N.put(-48,"set_flg"); N.put(-47,"clr_flg"); N.put(-46,"wai_flg"); N.put(-106,"pol_flg"); N.put(-170,"twai_flg"); N.put(-44,"ref_flg"); N.put(-63,"snd_msg"); N.put(-61,"rcv_msg"); N.put(-108,"prcv_msg"); N.put(-172,"trcv_msg"); N.put(-60,"ref_mbx"); N.put(-141,"get_blk"); N.put(-104,"pget_blk"); N.put(-143,"rel_blk"); N.put(-140,"ref_mpl"); N.put(-77,"get_blf"); N.put(-103,"pget_blf"); N.put(-167,"tget_blf"); N.put(-79,"ref_blf"); N.put(-76,"ref_mpf"); N.put(-69,"ret_int"); N.put(-8,"loc_cpu"); N.put(-7,"unl_cpu"); N.put(-67,"chg_ilm"); N.put(-68,"ref_ilm"); N.put(-83,"set_tim"); N.put(-84,"get_tim"); N.put(-85,"dly_Tsk"); N.put(-90,"def_cyc"); N.put(-94,"act_cyc"); N.put(-92,"ref_cyc"); N.put(-89,"def_alm"); N.put(-91,"ref_alm"); N.put(-93,"ret_tmr"); N.put(-16,"get_ver"); N.put(-12,"ref_sys"); }

    public boolean gardes = true;
    /** INT #0x40 (noyau) : false = garde, true = retour immédiat R4 = 0 (journalisé). */
    public boolean noyauOk = false;
    public final Map<String, Integer> appelsNoyau = new TreeMap<>();

    public D200Emu(File firmware, PrintStream log) throws IOException {
        this.log = log;
        memory.loadFile(firmware, BASE, false);
        int reset = memory.load32(0xEFFFC, null);   // vecteur INT #0 de la table 0xEFC00
        cpu = new FrCPUState(reset);
        cpu.setReg(FrCPUState.TBR, 0xEFC00);
        MasterClock clock = new MasterClock();
        platform = new Platform(clock);
        platform.setCpuState(cpu);
        platform.setMemory(memory);
        intc = new FrInterruptController(platform);
        platform.setInterruptController(intc);
        emu = new FrEmulator(platform);
        emu.setContext(memory, cpu, intc);
        emu.setOutputOptions(EnumSet.noneOf(OutputOption.class));
        memory.addActivityListener(new GardeRom());
    }

    public boolean inDelaySlot() { return emu.context.nextPc != null; }

    /** Écriture du code dans la ROM : le firmware ne le fait jamais hors du flasheur (copié en RAM). */
    class GardeRom implements MemoryActivityListener {
        public boolean matches(int a) { return a >= BASE && a < FIN_ROM; }
        public boolean isReadOnly() { return false; }
        public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { return null; }
        public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
        public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
        public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        void w(int a) { if (gardes) throw new Garde(String.format("écriture dans la ROM en %08X depuis %08X", a, cpu.pc)); }
        public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { w(a); }
        public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { w(a); }
        public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { w(a); }
    }

    /**
     * Lectures d'une plage par le code avant que le code ne l'ait lui-même écrite : ce que les fonctions prennent en
     * entrée (valeurs posées par le scénario comprises ; les écritures du scénario ne comptent pas).
     */
    public class Lectures implements MemoryActivityListener {
        public final String nom; public final int a0, a1;
        public final BitSet lu = new BitSet(), ecrit = new BitSet();
        Lectures(String nom, int a, int n) { this.nom = nom; a0 = a; a1 = a + n; }
        public boolean matches(int a) { return a + 3 >= a0 && a < a1; }
        public boolean isReadOnly() { return false; }
        void lire(int a, int n) { for (int k = 0; k < n; k++) { int o = a + k - a0; if (o >= 0 && a + k < a1 && !ecrit.get(o)) lu.set(o); } }
        public void ecrire(int a, int n) { for (int k = 0; k < n; k++) { int o = a + k - a0; if (o >= 0 && a + k < a1) ecrit.set(o); } }
        public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { lire(a, 1); return null; }
        public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { lire(a, 2); return null; }
        public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { lire(a, 4); return null; }
        public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { ecrire(a, 1); }
        public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { ecrire(a, 2); }
        public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { ecrire(a, 4); }
        /** Plages lues avant écriture, en décalages depuis le début (« +0x4D », « +0x5C0-0x5C3 »). */
        public String plages() {
            StringBuilder sb = new StringBuilder();
            for (int i = lu.nextSetBit(0); i >= 0; ) {
                int j = lu.nextClearBit(i);
                sb.append(sb.length() > 0 ? " " : "").append(j - i == 1 ? String.format("+0x%X", i) : String.format("+0x%X-0x%X", i, j - 1));
                i = lu.nextSetBit(j);
            }
            return sb.length() == 0 ? "(rien)" : sb.toString();
        }
    }
    public final List<Lectures> traceurs = new ArrayList<>();
    public Lectures tracer(String nom, int a, int n) {
        Lectures l = new Lectures(nom, a, n);
        traceurs.add(l);
        memory.addActivityListener(l);
        return l;
    }

    final com.nikonhacker.disassembly.fr.FrStatement probe = new com.nikonhacker.disassembly.fr.FrStatement();

    void verifier() {
        int pc = cpu.pc;
        boolean rom = pc >= BASE && pc < FIN_ROM;
        boolean ram = (pc >= 0x90000000 && pc < 0x98000000) || (pc >= 0x40000 && pc < BASE);
        if (!rom && !ram) throw new Garde(String.format("exécution hors de la ROM et de la RAM à %08X", pc));
        if (rom && ((pc >= 0xF0000 && pc < 0x120000) || (pc >= 0x1D0000 && pc < 0x200000)))
            throw new Garde(String.format("exécution dans une zone jamais écrite par la mise à jour (%08X) : son contenu réel est inconnu", pc));
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
    }

    /** Les 64 derniers PC exécutés (pour comprendre un arrêt). */
    public final int[] derniers = new int[64];
    public String derniersPc() {
        StringBuilder sb = new StringBuilder();
        for (int k = 0; k < 64; k++) { int i = (int) ((steps + k) & 63); sb.append(String.format(" %05X", derniers[i])); }
        return sb.toString();
    }

    public void step() throws EmulationException {
        derniers[(int) (steps & 63)] = cpu.pc;
        if (gardes) verifier();
        if (!inDelaySlot()) {
            Crochet h = hooks.get(cpu.pc);
            if (h != null && h.run(this)) { steps++; return; }
            int op = memory.loadUnsigned16(cpu.pc, null);
            if ((op & 0xFF00) == 0x1F00) { // INT #u8
                String n = (op & 0xFF) == 0x40 ? String.format("noyau %s (R12=%d)", SYSCALL.getOrDefault(r(12), "?"), r(12))
                        : String.format("INT #0x%02X", op & 0xFF);
                if (!noyauOk || (op & 0xFF) != 0x40)
                    throw new Garde(String.format("%s à %08X : le noyau n'est pas émulé (« noyau ok » pour le remplacer par E_OK)", n, cpu.pc));
                appelsNoyau.merge(n, 1, Integer::sum);
                log.printf("  %s à %08X remplacé par E_OK (R4 = 0)%n", n, cpu.pc);
                setR(4, 0);
                cpu.pc += 2;
                steps++;
                return;
            }
        }
        emu.context.cycleIncrement = 1;
        emu.onClockTick();
        steps++;
    }

    public int r(int n) { return cpu.getReg(n); }
    public void setR(int n, int v) { cpu.setReg(n, v); }
    public int rd32(int a) { return memory.load32(a, null); }
    public int rd16(int a) { return memory.loadUnsigned16(a, null); }
    public int rd8(int a) { return memory.loadUnsigned8(a, null); }
    /** Écritures du scénario : ni garde de ROM (on peut y poser une instruction), ni traceurs. */
    public void wr32(int a, int v) { memory.store32(a, v, null); }
    public void wr16(int a, int v) { memory.store16(a, v, null); }
    public void wr8(int a, int v) { memory.store8(a, v, null); }

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
        StringBuilder sb = new StringBuilder(String.format("PC=%08X", cpu.pc));
        for (int i = 0; i < 16; i++) sb.append(String.format(" R%d=%08X", i, r(i)));
        sb.append(String.format(" RP=%08X SSP=%08X USP=%08X TBR=%08X PS=%08X ILM=%d S=%d I=%d",
                r(FrCPUState.RP), r(FrCPUState.SSP), r(FrCPUState.USP), r(FrCPUState.TBR), cpu.getPS(), cpu.getILM(), cpu.getS(), cpu.I));
        return sb.toString();
    }
}
