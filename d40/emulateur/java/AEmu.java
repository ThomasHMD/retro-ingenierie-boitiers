package com.nikonhacker.emu;

import com.nikonhacker.disassembly.OutputOption;
import com.nikonhacker.disassembly.fr.FrCPUState;
import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.peripherials.interruptController.fr.FrInterruptController;

import java.io.*;
import java.util.*;

/**
 * Émulateur du processeur A du Nikon D40 (firmware AD400111, exposition), sans interface.
 * Même cœur FR que D40Emu (nikon-firmware-tools) ; carte mémoire du A :
 *  - 0x00000-0x00FFF : registres internes du microcontrôleur (AIo) ;
 *  - 0x3C000-0x3FFFF : RAM interne (16 Ko, variables, piles) ;
 *  - 0xC0000-0xFFFFF : flash interne (le fichier AD400111.bin, vecteurs à 0xFFC00, reset 0xC0042).
 * Étude de faisabilité (octobre 2026), copie de travail : rien ici n'est dans le dépôt.
 */
public class AEmu {
    public static final int BASE = 0xC0000, FIN_ROM = 0x100000;
    public static final int RAM0 = 0x3C000, RAM1 = 0x40000;

    public final DebuggableMemory memory = new DebuggableMemory(false);
    public final FrCPUState cpu;
    public final Platform platform;
    public final FrInterruptController intc;
    public final FrEmulator emu;
    public final AIo io;
    public long steps = 0;
    public interface HookA { /** @return true pour sauter l'instruction (le crochet a déplacé le PC) */ boolean run(AEmu e); }
    public final Map<Integer, HookA> hooks = new HashMap<>();
    public final PrintStream log;
    public boolean traceSyscalls = false;
    public final Map<String, Integer> syscallCounts = new TreeMap<>();
    /** sta_tsk vus : {n° de tâche, code de départ, instruction, PC}. */
    public final List<long[]> staTsk = new ArrayList<>();
    /** Premier passage dans chaque appel bloquant (wai_flg, slp_tsk…) : nom -> instruction. */
    public final Map<String, Long> premiersBloquants = new LinkedHashMap<>();
    public java.util.function.Consumer<AEmu> onSyscall = null;
    public boolean gardes = true;
    public final Set<Integer> horsRomSignale = new HashSet<>();

    public AEmu(File firmware, PrintStream log) throws IOException {
        this.log = log;
        memory.loadFile(firmware, BASE, false);
        int reset = memory.load32(0xFFFFC, null);   // vecteur 0 (TBR par défaut 0xFFC00)
        cpu = new FrCPUState(reset);
        MasterClock clock = new MasterClock();
        platform = new Platform(clock);
        platform.setCpuState(cpu);
        platform.setMemory(memory);
        intc = new FrInterruptController(platform);
        platform.setInterruptController(intc);
        emu = new FrEmulator(platform);
        emu.setContext(memory, cpu, intc);
        emu.setOutputOptions(EnumSet.noneOf(OutputOption.class));
        io = new AIo(this);
        memory.addActivityListener(io);
        memory.addActivityListener(new GardeFlash());
        // Piles des 12 tâches : mot 5 de la table 0xFEB0C = emplacement du contexte initial (0x50 octets dépilés
        // au premier lancement), donc haut réel = mot 5 + 0x50 (vu : R15 = mot 5 + 0x50 à l'entrée de chaque
        // tâche ; la tâche 12 finit en 0x3FFFC, fin de la RAM). Hypothèse : piles contiguës, la tâche n
        // descend jusqu'au haut de la tâche n − 1, la tâche 1 jusqu'à celui de la tâche de repos (0x3F2CC).
        for (int n = 1; n <= 12; n++) {
            pileHaut[n] = rd32(0xFEB10 + 28 * (n - 1) + 20) + 0x50;
            pileBas[n] = n == 1 ? 0x3F2CC : pileHaut[n - 1];
            pileMin[n] = pileHaut[n];
        }
    }

    // ---- Gardes propres au A (en plus des trois de D40Emu) ----
    /** Garde 4 : pile de chaque tâche (16 Ko de RAM, piles de 176 à 368 octets). */
    public final int[] pileHaut = new int[13], pileBas = new int[13], pileMin = new int[13], pileMax = new int[13], pileMaxPc = new int[13];
    public boolean gardePile = true;
    int tacheDeTcb(int t) { for (int n = 1; n <= 12; n++) if (tcb(n) == t) return n; return 0; }
    void verifierPile() {
        if (cpu.getS() != 1) return;                     // pile système (interruptions) : non suivie
        if (cpu.pc >= 0xFEB00 && cpu.pc < 0xFFC00) return; // noyau (changement de tâche en cours)
        int n = tacheDeTcb(rd32(0x3EB60));
        if (n == 0) return;
        int sp = r(15);
        if (sp < pileMin[n] && sp >= pileBas[n] - 0x400) pileMin[n] = sp;
        if (sp > pileMax[n] && sp < RAM1) { pileMax[n] = sp; pileMaxPc[n] = cpu.pc; }
        if (gardePile && sp < pileBas[n] && sp >= RAM0)
            throw new D40Emu.Garde(String.format("débordement de pile, tâche %d : R15 = %05X sous le bas %05X (haut %05X) à %05X",
                    n, sp, pileBas[n], pileHaut[n], cpu.pc));
    }
    public String marges() {
        StringBuilder sb = new StringBuilder("  pile des tâches (utilisé / taille, octets) :");
        for (int n = 1; n <= 12; n++)
            if (pileMax[n] != 0) sb.append(String.format(" t%d %d/%d%s", n, pileHaut[n] - pileMin[n], pileHaut[n] - pileBas[n],
                    pileMax[n] > pileHaut[n] ? String.format(" (R15 jusqu'à %05X, au-dessus du haut, à %05X)", pileMax[n], pileMaxPc[n]) : ""));
        return sb.toString();
    }

    /** Garde 5 : le code n'écrit jamais dans sa flash (0xC0000-0xFFFFF) ; les « poke » des scénarios, si. */
    class GardeFlash implements com.nikonhacker.emu.memory.listener.MemoryActivityListener {
        public boolean matches(int a) { return a >= BASE && a < FIN_ROM; }
        public boolean isReadOnly() { return false; }
        public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { return null; }
        public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
        public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
        public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
        void w(int a) { if (gardes) throw new D40Emu.Garde(String.format("écriture dans la flash du A en %05X depuis %05X", a, cpu.pc)); }
        public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { w(a); }
        public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { w(a); }
        public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { w(a); }
    }

    // ---- EEPROM série du A, simulée au niveau des fonctions de la tâche 5 (HLE) ----
    // La tâche 5 (0xD452C) reçoit par rcv_msg {adresse EEPROM (bit 15 = lecture), adresse RAM, longueur} en
    // 0x3D4F8/FA/FC, puis lit (0xD4894) ou écrit (0xD461E) par la liaison synchrone 0xB8-0xBF et le DMA, non
    // émulés : on remplace ces deux fonctions par une copie depuis/vers cette image (32 Ko, adresses sur 15 bits).
    public final byte[] eeprom = new byte[0x8000];
    public long eepromLectures = 0, eepromEcritures = 0;
    public void eepromHle() {
        hooks.put(0xD4894, em -> { eepromCopie(true); cpu.pc = r(FrCPUState.RP); return true; });
        hooks.put(0xD461E, em -> { eepromCopie(false); cpu.pc = r(FrCPUState.RP); return true; });
    }
    void eepromCopie(boolean lecture) {
        int ad = rd16(0x3D4F8) & 0x7FFF, ram = 0x30000 | rd16(0x3D4FA), n = rd16(0x3D4FC);
        for (int k = 0; k < n; k++) {
            if (lecture) wr8(ram + k, eeprom[(ad + k) & 0x7FFF]); else eeprom[(ad + k) & 0x7FFF] = (byte) rd8(ram + k);
        }
        if (lecture) eepromLectures++; else eepromEcritures++;
        log.printf("  EEPROM %s : %d octets, EEPROM %04X %s RAM %05X (instruction %d)%n", lecture ? "lecture" : "écriture", n, ad,
                lecture ? "->" : "<-", ram, steps);
    }

    public boolean inDelaySlot() { return emu.context.nextPc != null; }

    final com.nikonhacker.disassembly.fr.FrStatement probe = new com.nikonhacker.disassembly.fr.FrStatement();

    /** Les trois gardes de D40Emu.verifier(), avec la carte mémoire du A. */
    void verifier() {
        int pc = cpu.pc;
        int op = memory.loadUnsigned16(pc, null);
        com.nikonhacker.disassembly.fr.FrInstruction ins = com.nikonhacker.disassembly.fr.FrInstructionSet.instructionMap[op];
        if (ins == null || ins == com.nikonhacker.disassembly.fr.FrInstructionSet.defaultInstruction || op == 0xFFFF)
            throw new D40Emu.Garde(String.format("instruction non définie %04X à %08X", op, pc));
        if (inDelaySlot()) {
            probe.reset();
            probe.getNextStatement(memory, pc);
            probe.setInstruction(ins);
            probe.decodeOperands(pc, memory);
            boolean multi = probe.getNumBytes() > 2;
            boolean flux = ins.getFlowType() != com.nikonhacker.disassembly.Instruction.FlowType.NONE
                    || ins.getDelaySlotType() != com.nikonhacker.disassembly.Instruction.DelaySlotType.NONE;
            if (multi || flux)
                throw new D40Emu.Garde(String.format("instruction interdite dans un créneau de délai à %08X : %04X (%s)", pc, op, ins.getName()));
        }
        boolean rom = pc >= BASE && pc < 0xFFC00;           // la table des vecteurs n'est pas du code
        boolean ram = pc >= RAM0 && pc < RAM1;
        if (!rom && !ram) throw new D40Emu.Garde(String.format("exécution hors de la flash et de la RAM du A à %08X", pc));
        if (ram && horsRomSignale.add(pc & ~0xFF)) log.printf("note : exécution en RAM à %08X%n", pc);
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
        if (gardes) { verifier(); verifierPile(); }
        if (!inDelaySlot()) {
            HookA h = hooks.get(cpu.pc);
            if (h != null && h.run(this)) { steps++; return; }
            if (memory.loadUnsigned16(cpu.pc, null) == 0x1F40) syscall();
        }
        emu.context.cycleIncrement = 1;
        emu.onClockTick();
        steps++;
        io.tick();
    }

    public String syscallName() {
        String n = D40Emu.SYSCALL.get(r(12));
        return n == null ? "sys" + r(12) : n;
    }

    static final Set<String> BLOQUANTS = new HashSet<>(Arrays.asList("wai_flg", "twai_flg", "slp_tsk", "tslp_tsk",
            "wai_sem", "twai_sem", "rcv_msg", "trcv_msg", "dly_Tsk", "get_blf", "tget_blf"));

    /** Dernier appel au noyau de chaque tâche (bloc de contrôle courant en 0x3EB60). */
    public final Map<Integer, String> dernierAppel = new TreeMap<>();
    /** Tâche n -> bloc de contrôle (table statique 0xFEB0C : 12 tâches de 28 octets). */
    public int tcb(int n) { return rd32(0xFEB10 + 28 * (n - 1)); }
    public String taches() {
        StringBuilder sb = new StringBuilder();
        int cur = rd32(0x3EB60);
        for (int n = 1; n <= 12; n++) {
            int t = tcb(n), entree = rd32(0xFEB10 + 28 * (n - 1) + 16), prio = rd16(0xFEB10 + 28 * (n - 1) + 6);
            String d = dernierAppel.get(t);
            sb.append(String.format("  tâche %2d entrée %05X prio %d TCB %05X état+8=%08X %s%s%n", n, entree, prio, t, rd32(t + 8),
                    d == null ? "(aucun appel au noyau)" : "dernier appel " + d, t == cur ? "  <- courante" : ""));
        }
        return sb.toString();
    }

    void syscall() {
        String n = syscallName();
        dernierAppel.put(rd32(0x3EB60), String.format("%s@%05X (R4=%X R5=%X) n=%d", n, cpu.pc, r(4), r(5), steps));
        syscallCounts.merge(n, 1, Integer::sum);
        if (n.equals("sta_tsk")) staTsk.add(new long[]{r(4), r(5), steps, cpu.pc});
        if (BLOQUANTS.contains(n)) premiersBloquants.putIfAbsent(String.format("%s@%05X", n, cpu.pc), steps);
        if (traceSyscalls)
            log.printf("SYS %-9s R4=%08X R5=%08X R6=%08X R7=%08X @%08X n=%d%n", n, r(4), r(5), r(6), r(7), cpu.pc, steps);
        if (onSyscall != null) onSyscall.accept(this);
    }

    public int r(int n) { return cpu.getReg(n); }
    public void setR(int n, int v) { cpu.setReg(n, v); }
    public int rd32(int a) { return memory.load32(a, null); }
    public int rd16(int a) { return memory.loadUnsigned16(a, null); }
    public int rd8(int a) { return memory.loadUnsigned8(a, null); }
    public int rds16(int a) { return (short) memory.loadUnsigned16(a, null); }
    public void wr32(int a, int v) { memory.store32(a, v, null); }
    public void wr16(int a, int v) { memory.store16(a, v, null); }
    public void wr8(int a, int v) { memory.store8(a, v, null); }

    public String disasm(int addr, int n) {
        StringBuilder sb = new StringBuilder();
        com.nikonhacker.disassembly.StatementContext ctx = new com.nikonhacker.disassembly.StatementContext();
        ctx.cpuState = cpu.createCopy();
        ctx.memory = memory;
        boolean l = io.logAccess; io.logAccess = false;
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
        io.logAccess = l;
        return sb.toString();
    }

    public String regs() {
        StringBuilder sb = new StringBuilder();
        sb.append(String.format("PC=%08X", cpu.pc));
        for (int i = 0; i < 16; i++) sb.append(String.format(" R%d=%08X", i, r(i)));
        sb.append(String.format(" RP=%08X SSP=%08X USP=%08X TBR=%08X PS=%08X ILM=%d S=%d I=%d",
                r(FrCPUState.RP), r(FrCPUState.SSP), r(FrCPUState.USP), r(FrCPUState.TBR), cpu.getPS(), cpu.getILM(), cpu.getS(), cpu.I));
        return sb.toString();
    }
}
