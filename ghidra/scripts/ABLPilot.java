// ABL Ghidra pilot post-script (Java GhidraScript, runs under analyzeHeadless).
// 1. Imports re_symbols.sym as Ghidra labels/functions (the .sym file stays authoritative).
// 2. Decompiles a small sample of known functions and writes C to the out dir for cross-check.
// Args: <sym_file> <out_dir> <comma-separated sample hex addrs>
// @category ABL
import java.io.*;
import java.util.*;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.SourceType;
import ghidra.util.task.ConsoleTaskMonitor;

public class ABLPilot extends GhidraScript {
    static final long TEXT_LO = 0x80010000L;
    static final long TEXT_HI = 0x80082800L; // resident text end (docs/EXECUTABLE_AND_OVERLAYS.md)

    boolean looksLikeFunc(String name, long a) {
        if (a < TEXT_LO || a >= TEXT_HI) return false;
        String n = name.toLowerCase();
        if (n.startsWith("provisional_") || n.contains("table") || n.contains("scratch")) return false;
        if (name.startsWith("FUNC_")) return true;
        for (String k : new String[]{"state_machine","dispatch","entry","walker","parser","alloc","handler","store","clear"})
            if (n.contains(k)) return true;
        return false;
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String symPath = args[0], outDir = args[1];
        String[] sample = args[2].split(",");

        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        FunctionManager fm = currentProgram.getFunctionManager();
        Listing listing = currentProgram.getListing();

        int labels = 0, created = 0, renamed = 0;
        BufferedReader br = new BufferedReader(new FileReader(symPath));
        String line;
        while ((line = br.readLine()) != null) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] p = line.split("\\s+", 2);
            if (p.length != 2) continue;
            long ai;
            try { ai = Long.parseLong(p[0], 16); } catch (Exception e) { continue; }
            String name = p[1];
            Address addr = sp.getAddress(ai);
            try { createLabel(addr, name, true, SourceType.IMPORTED); labels++; } catch (Exception e) {}
            if (looksLikeFunc(name, ai)) {
                Function fn = fm.getFunctionAt(addr);
                if (fn == null) {
                    if (listing.getInstructionAt(addr) == null) disassemble(addr);
                    try { fn = createFunction(addr, name); if (fn != null) created++; } catch (Exception e) {}
                }
                if (fn != null) { try { fn.setName(name, SourceType.IMPORTED); renamed++; } catch (Exception e) {} }
            }
        }
        br.close();
        println("[ABLPilot] labels=" + labels + " created_funcs=" + created + " renamed=" + renamed);

        new File(outDir).mkdirs();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        for (String h : sample) {
            h = h.trim();
            Address addr = sp.getAddress(Long.parseLong(h, 16));
            Function fn = fm.getFunctionAt(addr);
            if (fn == null) {
                if (listing.getInstructionAt(addr) == null) disassemble(addr);
                fn = createFunction(addr, "FUNC_" + h.toUpperCase());
            }
            File outp = new File(outDir, "ghidra_" + h.toLowerCase() + ".c");
            PrintWriter o = new PrintWriter(new FileWriter(outp));
            if (fn == null) { o.println("// no function at " + h); }
            else {
                DecompileResults res = ifc.decompileFunction(fn, 120, mon);
                if (res != null && res.decompileCompleted()) o.print(res.getDecompiledFunction().getC());
                else o.println("// decompile failed at " + h + ": " + (res != null ? res.getErrorMessage() : "no result"));
            }
            o.close();
            println("[ABLPilot] wrote " + outp.getPath());
        }
    }
}
