/* Export PsyQ signature matches from a ghidra_psx_ldr-loaded program to CSV.
 *
 * Run as a headless postScript on the ABLPsx project (PsxLoader import). The
 * PsyQ Signatures analyzer names matched library functions (SourceType
 * IMPORTED / ANALYSIS); everything else stays FUN_/LAB_ default. We export
 * every function whose name is non-default, plus the detected "PsyQ Version"
 * program-info option, so tools/merge_psyq_symbols.py can merge into
 * symbols/re_symbols.sym (the authoritative map — Ghidra never writes back).
 *
 * args: <output-dir>   (writes psyq_matches.csv + psyq_version.txt)
 */
import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.listing.Program;
import ghidra.program.model.symbol.SourceType;

public class ExportPsyqMatches extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File outDir = new File(args.length > 0 ? args[0] : ".");
        outDir.mkdirs();

        String psyqVer = currentProgram.getOptions(Program.PROGRAM_INFO)
                .getString("PsyQ Version", "");
        try (PrintWriter pw = new PrintWriter(new File(outDir, "psyq_version.txt"))) {
            pw.println(psyqVer);
        }

        int total = 0, exported = 0;
        try (PrintWriter pw = new PrintWriter(new File(outDir, "psyq_matches.csv"))) {
            pw.println("address,name,source");
            FunctionIterator it = currentProgram.getFunctionManager().getFunctions(true);
            while (it.hasNext()) {
                Function f = it.next();
                total++;
                SourceType st = f.getSymbol().getSource();
                if (st == SourceType.DEFAULT || f.getName().startsWith("FUN_")) {
                    continue;
                }
                pw.printf("0x%08x,%s,%s%n",
                        f.getEntryPoint().getOffset(), f.getName(), st.toString());
                exported++;
            }
        }
        println(String.format("ExportPsyqMatches: psyq_version=%s functions_total=%d named_exported=%d -> %s",
                psyqVer, total, exported, outDir.getAbsolutePath()));
    }
}
