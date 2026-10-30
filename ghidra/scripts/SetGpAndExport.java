// ABL: set the MIPS $gp register context (runtime gp = 0x80081D98, matching r2
// anal.gp) over the resident text range, re-analyze so gp-relative loads/stores
// resolve to real globals, then:
//   1. export every text-range function to <csv_out>/ghidra_functions.csv
//      (address,name; Ghidra FUN_* auto-names exported as empty — the census
//      uses the address as a discovery signal, names stay .sym-authoritative)
//   2. re-decompile the sample functions to <out_dir>/ghidra_<addr>_gp.c for a
//      before/after unaff_gp comparison against the pre-gp ghidra_<addr>.c.
// Args: <csv_out_dir> <decomp_out_dir> <comma-separated sample hex addrs>
// @category ABL
import java.io.*;
import java.math.BigInteger;
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSpace;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.*;
import ghidra.util.task.ConsoleTaskMonitor;

public class SetGpAndExport extends GhidraScript {
    static final long TEXT_LO = 0x80010000L;
    static final long TEXT_HI = 0x80082800L;   // exclusive
    static final long GP = 0x80081D98L;        // runtime $gp (docs/EXECUTABLE_AND_OVERLAYS.md)

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String csvDir = args[0], outDir = args[1];
        String[] sample = args.length > 2 ? args[2].split(",") : new String[0];

        AddressSpace sp = currentProgram.getAddressFactory().getDefaultAddressSpace();
        Address lo = sp.getAddress(TEXT_LO), hi = sp.getAddress(TEXT_HI - 1);

        Register gp = currentProgram.getRegister("gp");
        if (gp == null) throw new IllegalStateException("no gp register in language");
        BigInteger prev = currentProgram.getProgramContext().getValue(gp, lo, false);
        currentProgram.getProgramContext().setValue(gp, lo, hi, BigInteger.valueOf(GP));
        println("[SetGp] gp context " + (prev == null ? "unset" : ("0x" + prev.toString(16)))
                + " -> 0x" + Long.toHexString(GP) + " over 0x" + Long.toHexString(TEXT_LO)
                + "..0x" + Long.toHexString(TEXT_HI));

        println("[SetGp] re-analyzing with gp context ...");
        analyzeAll(currentProgram);

        // ---- export function list ----
        new File(csvDir).mkdirs();
        File csv = new File(csvDir, "ghidra_functions.csv");
        PrintWriter w = new PrintWriter(new FileWriter(csv));
        w.println("address,name");
        int n = 0, named = 0;
        FunctionManager fm = currentProgram.getFunctionManager();
        for (Function fn : fm.getFunctions(true)) {
            long a = fn.getEntryPoint().getOffset();
            if (a < TEXT_LO || a >= TEXT_HI) continue;
            String name = fn.getName();
            if (name.startsWith("FUN_")) name = "";   // Ghidra auto-name, not a real name
            else named++;
            w.println("0x" + Long.toHexString(a) + "," + name);
            n++;
        }
        w.close();
        println("[SetGp] exported " + n + " text-range functions (" + named + " named) -> " + csv.getPath());

        // ---- re-decompile samples for the before/after comparison ----
        new File(outDir).mkdirs();
        DecompInterface ifc = new DecompInterface();
        ifc.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();
        Listing listing = currentProgram.getListing();
        for (String h : sample) {
            h = h.trim();
            if (h.isEmpty()) continue;
            Address addr = sp.getAddress(Long.parseLong(h, 16));
            Function fn = fm.getFunctionAt(addr);
            if (fn == null) {
                if (listing.getInstructionAt(addr) == null) disassemble(addr);
                fn = createFunction(addr, "FUNC_" + h.toUpperCase());
            }
            File outp = new File(outDir, "ghidra_" + h.toLowerCase() + "_gp.c");
            PrintWriter o = new PrintWriter(new FileWriter(outp));
            if (fn == null) o.println("// no function at " + h);
            else {
                DecompileResults res = ifc.decompileFunction(fn, 120, mon);
                if (res != null && res.decompileCompleted()) o.print(res.getDecompiledFunction().getC());
                else o.println("// decompile failed at " + h + ": "
                               + (res != null ? res.getErrorMessage() : "no result"));
            }
            o.close();
            println("[SetGp] wrote " + outp.getPath());
        }
    }
}
