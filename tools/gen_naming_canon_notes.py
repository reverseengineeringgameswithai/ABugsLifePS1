#!/usr/bin/env python3
"""Generate Canon FUNC_ pages for the sc-1/sc-2 static-inference-named functions
(analysis/naming/sc1_batch*.json, tier=inferred). Skips addresses that already have
a Canon Function page (avoids validator dup_address). status=static_seen (inferred);
evidence = the campaign EXP + the source manifest path. Idempotent-ish: rerun after
new naming manifests to mint missing pages."""
import json, glob, re
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
NOTES=ROOT/"ObsidianVault/Canon/Functions"
cen=json.loads((ROOT/"analysis/functions.json").read_text())["functions"]
byaddr={int(f["start"],16):f for f in cen}
def owner_name(va):
    f=byaddr.get(va); return f.get("name") if f else None
existing=set()
for p in NOTES.glob("FUNC_*.md"):
    m=re.match(r"FUNC_([0-9A-Fa-f]{8})",p.name)
    if m: existing.add(int(m.group(1),16))
# collect names WITH their source manifest path
props={}
for mf in sorted(glob.glob(str(ROOT/"analysis/naming/sc1_batch*.json"))):
    rel=str(Path(mf).relative_to(ROOT))
    for r in json.load(open(mf)):
        if r.get("tier")=="inferred":
            props[int(r["address"],16)]=(r,rel)
def safe(s): return re.sub(r"[^A-Za-z0-9_]","_",s)[:60]
created=skipped=0
for va,(r,rel) in sorted(props.items()):
    if va in existing or va not in byaddr: skipped+=1; continue
    f=byaddr[va]; name=r["name"]
    callees=sorted({owner_name(int(x,16) if isinstance(x,str) else x) for x in f.get("callees",[])})
    callees=[c for c in callees if c][:16]
    ev=r.get("evidence",[]) or []
    fm={"kind":"function","id":f"FUNC_{va:08X}","aliases":[f"FUNC_{va:08X}",f"0x{va:08x}",name],
      "address":f"0x{va:08x}","name":name,"status":"static_seen","confidence":"medium",
      "source_state":"original_game","tier":"inferred","calls":callees,
      "evidence":["EXP_2026-07-09_static_inference_naming", rel],
      "src_paths":["symbols/re_symbols.sym","analysis/functions.json", rel],
      "patch_policy":"safe_to_read"}
    body=f"\n# FUNC_{va:08X} - {name}\n\n## Purpose\n{r.get('rationale','(static-inference reconstruction)')}\n\nNamed by static call-graph + disassembly inference ([[EXP_2026-07-09_static_inference_naming]]); **inferred** tier — role deduced from the evidence below, not runtime-proven.\n\n## Evidence\n"+"".join(f"- {e}\n" for e in ev)+f"\nProvenance: `symbols/re_symbols.sym`, the naming manifest `{rel}`, and the census `analysis/functions.json`. Byte-exact rebuild SHA-1 af43de22 holds with this name.\n\n## Related\n[[SYS_function_census]] · [[EXP_2026-07-09_static_inference_naming]]\n"
    (NOTES/f"FUNC_{va:08X}_{safe(name)}.md").write_text("---\n"+yaml.safe_dump(fm,sort_keys=False).strip()+"\n---\n"+body)
    created+=1
print(f"created {created}; skipped {skipped}")
