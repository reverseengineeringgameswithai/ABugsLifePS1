// Export bounded high-p-code metadata for one ABL resident/overlay image.
// Raw output is external evidence and must never be committed.
// Args: <function-tsv> <output-json> <gp-hex> <range-lo-hex> <range-hi-hex> <image-id>
// TSV columns: start<TAB>end<TAB>range_type<TAB>name
// @category ABL
import java.io.*;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.*;
import ghidra.program.model.pcode.*;
import ghidra.program.model.symbol.SourceType;
import ghidra.util.task.ConsoleTaskMonitor;

public class ExportPhase4StaticFrontier extends GhidraScript {
    static class Spec {
        long start, end;
        String type, name;
        Spec(long s, long e, String t, String n) { start=s; end=e; type=t; name=n; }
    }

    static String esc(String s) {
        if (s == null) return "null";
        StringBuilder b = new StringBuilder("\"");
        for (int i=0; i<s.length(); i++) {
            char c=s.charAt(i);
            if (c=='\\' || c=='\"') b.append('\\').append(c);
            else if (c=='\n') b.append("\\n");
            else if (c=='\r') b.append("\\r");
            else if (c=='\t') b.append("\\t");
            else if (c < 0x20) b.append(String.format("\\u%04x", (int)c));
            else b.append(c);
        }
        return b.append('"').toString();
    }

    static String hx(long value) { return String.format("0x%08X", value); }

    static String digest(List<String> values) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        for (String value : values) {
            md.update(value.getBytes(StandardCharsets.UTF_8));
            md.update((byte)'\n');
        }
        StringBuilder b = new StringBuilder();
        for (byte value : md.digest()) b.append(String.format("%02x", value & 0xff));
        return b.toString();
    }

    static String varnode(Varnode v) {
        if (v == null) return "null";
        if (v.isConstant()) return "const:" + hx(v.getOffset()) + ":" + v.getSize();
        if (v.isAddress()) return "address:" + v.getAddress() + ":" + v.getSize();
        if (v.isRegister()) return "register:" + v.getAddress() + ":" + v.getSize();
        if (v.isUnique()) return "unique:" + Long.toHexString(v.getOffset()) + ":" + v.getSize();
        return v.getAddress().getAddressSpace().getName() + ":" +
            Long.toHexString(v.getOffset()) + ":" + v.getSize();
    }

    List<Spec> readSpecs(String path) throws Exception {
        List<Spec> specs = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            String line;
            while ((line=br.readLine()) != null) {
                if (line.isBlank() || line.startsWith("#")) continue;
                String[] p=line.split("\\t", -1);
                if (p.length < 4) throw new IllegalArgumentException("bad spec row: " + line);
                specs.add(new Spec(Long.decode(p[0]), Long.decode(p[1]), p[2], p[3]));
            }
        }
        specs.sort(Comparator.comparingLong(s -> s.start));
        return specs;
    }

    @Override public void run() throws Exception {
        String[] args=getScriptArgs();
        if (args.length != 6) throw new IllegalArgumentException("expected six args");
        String specPath=args[0], outputPath=args[1], imageId=args[5];
        long gpValue=Long.decode(args[2]), loValue=Long.decode(args[3]), hiValue=Long.decode(args[4]);
        List<Spec> specs=readSpecs(specPath);
        AddressSpace space=currentProgram.getAddressFactory().getDefaultAddressSpace();
        Address lo=space.getAddress(loValue), hi=space.getAddress(hiValue-1);
        Register gp=currentProgram.getRegister("gp");
        if (gp == null) throw new IllegalStateException("MIPS language has no gp register");
        currentProgram.getProgramContext().setValue(gp, lo, hi, BigInteger.valueOf(gpValue));

        FunctionManager fm=currentProgram.getFunctionManager();
        Listing listing=currentProgram.getListing();
        for (Spec spec : specs) {
            if (spec.type.equals("data")) continue;
            Address address=space.getAddress(spec.start);
            if (listing.getInstructionAt(address) == null) disassemble(address);
            Function fn=fm.getFunctionAt(address);
            if (fn == null) {
                try { fn=createFunction(address, spec.name.isBlank() ? "FUNC_" + Long.toHexString(spec.start) : spec.name); }
                catch (Exception ignored) {}
            }
            if (fn != null && !spec.name.isBlank()) {
                try { fn.setName(spec.name, SourceType.IMPORTED); } catch (Exception ignored) {}
            }
        }
        analyzeAll(currentProgram);

        DecompInterface decompiler=new DecompInterface();
        decompiler.toggleCCode(false);
        decompiler.toggleSyntaxTree(true);
        decompiler.openProgram(currentProgram);
        ConsoleTaskMonitor monitor=new ConsoleTaskMonitor();
        File output=new File(outputPath);
        output.getParentFile().mkdirs();
        try (PrintWriter out=new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(output), StandardCharsets.UTF_8))) {
            out.print("{\n  \"schema\":\"abl-phase4-ghidra-raw/1\",\n");
            out.print("  \"image_id\":" + esc(imageId) + ",\n");
            out.print("  \"gp\":" + esc(hx(gpValue)) + ",\n  \"functions\":[\n");
            boolean first=true;
            for (Spec spec : specs) {
                if (!first) out.print(",\n");
                first=false;
                out.print("    {\"entry\":" + esc(hx(spec.start)) +
                          ",\"end\":" + esc(hx(spec.end)) +
                          ",\"range_type\":" + esc(spec.type) +
                          ",\"name\":" + esc(spec.name));
                if (spec.type.equals("data")) {
                    out.print(",\"status\":\"not_applicable\",\"pcode_op_count\":0," +
                              "\"pcode_fingerprint\":null,\"pcode_ops\":[]," +
                              "\"calls\":[],\"memory_ops\":[]}");
                    continue;
                }
                Function fn=fm.getFunctionAt(space.getAddress(spec.start));
                if (fn == null) {
                    out.print(",\"status\":\"instruction_fallback_required\"," +
                              "\"error\":\"canonical function entry is absent after analysis\"," +
                              "\"pcode_op_count\":0,\"pcode_fingerprint\":null," +
                              "\"pcode_ops\":[],\"calls\":[],\"memory_ops\":[]}");
                    continue;
                }
                DecompileResults result=decompiler.decompileFunction(fn, 120, monitor);
                if (result == null || !result.decompileCompleted() || result.getHighFunction() == null) {
                    String error=result == null ? "no result" : result.getErrorMessage();
                    out.print(",\"status\":\"instruction_fallback_required\",\"error\":" + esc(error) +
                              ",\"pcode_op_count\":0,\"pcode_fingerprint\":null," +
                              "\"pcode_ops\":[],\"calls\":[],\"memory_ops\":[]}");
                    continue;
                }
                List<String> normalized=new ArrayList<>(), calls=new ArrayList<>(), memory=new ArrayList<>();
                Iterator<PcodeOpAST> iterator=result.getHighFunction().getPcodeOps();
                int count=0;
                while (iterator.hasNext()) {
                    PcodeOpAST op=iterator.next();
                    count++;
                    StringBuilder row=new StringBuilder(op.getMnemonic()).append('|').append(varnode(op.getOutput()));
                    for (int i=0; i<op.getNumInputs(); i++) row.append('|').append(varnode(op.getInput(i)));
                    normalized.add(row.toString());
                    if (op.getOpcode()==PcodeOp.CALL || op.getOpcode()==PcodeOp.CALLIND)
                        calls.add(row.toString());
                    if (op.getOpcode()==PcodeOp.LOAD || op.getOpcode()==PcodeOp.STORE)
                        memory.add(row.toString());
                }
                out.print(",\"status\":\"high_pcode\",\"pcode_op_count\":" + count +
                          ",\"pcode_fingerprint\":" + esc(digest(normalized)) + ",\"pcode_ops\":[");
                for (int i=0; i<normalized.size(); i++) {
                    if (i>0) out.print(','); out.print(esc(normalized.get(i)));
                }
                out.print("],\"calls\":[");
                for (int i=0; i<calls.size(); i++) { if (i>0) out.print(','); out.print(esc(calls.get(i))); }
                out.print("],\"memory_ops\":[");
                for (int i=0; i<memory.size(); i++) { if (i>0) out.print(','); out.print(esc(memory.get(i))); }
                out.print("]}");
            }
            out.print("\n  ]\n}\n");
        }
        println("[ExportPhase4StaticFrontier] wrote " + outputPath + " for " + specs.size() + " census rows");
    }
}
