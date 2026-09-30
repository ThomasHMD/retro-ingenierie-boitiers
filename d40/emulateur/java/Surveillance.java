package com.nikonhacker.emu;

import com.nikonhacker.emu.memory.DebuggableMemory;
import com.nikonhacker.emu.memory.listener.MemoryActivityListener;

/** Commande de scénario « watchw <adresse> <longueur> [max] » : journalise les écritures dans une plage (PC, RP, valeur). */
public class Surveillance implements MemoryActivityListener {
    final D40Emu e; final int a0, a1; int reste;

    Surveillance(D40Emu e, int a, int n, int max) { this.e = e; a0 = a; a1 = a + n; reste = max; }

    @Override public boolean matches(int a) { return a + 3 >= a0 && a < a1; }
    @Override public boolean isReadOnly() { return false; }

    void note(int a, int v, int size) {
        if (a + size <= a0 || a >= a1 || reste <= 0) return;
        reste--;
        e.log.printf("  écriture %08X <- %0" + (size * 2) + "X (%d octet%s) PC=%08X RP=%08X (%d)%n", a, v, size, size > 1 ? "s" : "",
                e.cpu.pc, e.r(com.nikonhacker.disassembly.fr.FrCPUState.RP), e.steps);
    }

    @Override public Byte onLoadData8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { return null; }
    @Override public Integer onLoadData16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
    @Override public Integer onLoadData32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { return null; }
    @Override public void onLoadInstruction8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) {}
    @Override public void onLoadInstruction16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
    @Override public void onLoadInstruction32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) {}
    @Override public void onStore8(byte[] p, int a, byte v, DebuggableMemory.AccessSource s) { note(a, v & 0xFF, 1); }
    @Override public void onStore16(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { note(a, v & 0xFFFF, 2); }
    @Override public void onStore32(byte[] p, int a, int v, DebuggableMemory.AccessSource s) { note(a, v, 4); }
}
