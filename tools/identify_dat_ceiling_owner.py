#!/usr/bin/env python3
"""Name what occupies RAM 0x801bf39c..0x801c1aac -- the region that caps LEVEL.DAT growth.

The size bisect put the ceiling in a 10 KB window (docs/G3_NATIVE_DAT_GROWTH_RESULT.md):
388,388 B passes, 398,388 B fails. Something live sits between those two end addresses. The
earlier ladder missed it by sampling 6.25%; this covers the window CONTIGUOUSLY -- 10 KB at
256 B per watch is 40 watches, inside the budget -- and reports the writer PCs, which name
the owner.
"""
from __future__ import annotations
import json, os, struct, subprocess, sys, time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUCK=os.path.expanduser("~/duckstation"); sys.path.insert(0,os.path.join(DUCK,"scripts","debugger-client"))
CFG,PORT,TOKEN="/tmp/dsowner",23470,"debugger-owner"
MOVIE=os.path.join(ROOT,"flik_to_level01_stall.mv.movie.json")
FORK=os.path.join(DUCK,"scripts/debugger-client/launch_debugger_instance.sh")
REPRO=os.path.join(ROOT,"tools/launch_repro_playback.sh")
FLIK_X,XMIN=0x800A6500,50000
LO,HI=0x801bf39c,0x801c1aac      # exactly the bisect window

def syms():
    d={}
    p=os.path.join(ROOT,"symbols/re_symbols.sym")
    for line in open(p):
        q=line.split(None,1)
        if len(q)==2:
            try: d[int(q[0],16)]=q[1].strip()
            except ValueError: pass
    return d

def main():
    S=syms()
    subprocess.run([FORK,"stop","--config-dir",CFG],capture_output=True)
    r=subprocess.run([REPRO,"--config-dir",CFG,"--port",str(PORT),"--token",TOKEN,
                      "--disc",os.path.join(ROOT,"Disney-Pixar A Bug's Life (v1.0).cue")],
                     capture_output=True,text=True)
    if r.returncode: sys.exit(r.stdout+r.stderr)
    time.sleep(2); res={"window":[hex(LO),hex(HI)]}
    try:
        from duckstation_debug_client import DebuggerClient
        c=DebuggerClient("127.0.0.1",PORT,"ws"); c.authenticate(TOKEN); c.transport.sock.settimeout(300)
        rd=lambda a,n: bytes.fromhex(c.call("debugger.readMemory",{"address":"0x%08x"%a,"length":n})["hex"])
        c.call("emulator.setTurbo",{"enabled":True}); c.call("debugger.reset",{})
        c.call("movie.load",{"path":MOVIE}); c.call("movie.startPlayback",{})
        for _ in range(75):
            if struct.unpack("<i",rd(FLIK_X,4))[0]>XMIN: break
            c.call("emulator.advanceFrames",{"frames":300})
        c.call("emulator.advanceFrames",{"frames":8})
        try: c.call("movie.stopPlayback",{})
        except Exception: pass
        c.call("emulator.setTurbo",{"enabled":False})
        x0=struct.unpack("<i",rd(FLIK_X,4))[0]
        c.call("accessLog.clear",{})
        ws=[]
        a=LO
        while a<HI:
            n=min(256,HI-a)
            try:
                w=c.call("accessLog.addWatch",{"address":"0x%08x"%a,"length":n,"type":"write",
                         "label":"w%05x"%(a-LO),"max_events":3000,"filter":{"max_per_frame":64}})
                ws.append((a,w.get("watch_id")))
            except Exception as e:
                res["budget_stop"]=hex(a); print("budget stop at",hex(a),e); break
            a+=n
        print(f"armed {len(ws)} contiguous 256B write-watches over "
              f"{LO:#x}..{(ws[-1][0]+256) if ws else LO:#x}")
        for btn,fr in (("Up",240),("Left",160),("Up",240),("Right",240),("Down",160),("Up",240)):
            for _ in range(fr//8):
                c.call("emulator.pressButton",{"button":btn,"frames":8,"port":0,"release_after":False})
                c.call("emulator.advanceFrames",{"frames":8})
            c.call("emulator.clearControllerState",{"port":0})
        moved=abs(struct.unpack("<i",rd(FLIK_X,4))[0]-x0)
        res["flik_moved"]=moved; res["stimulus_valid"]=moved>10000
        print(f"Flik moved {moved} -> stimulus_valid={res['stimulus_valid']}")
        pcs={}; hits=[]
        for base,wid in ws:
            off=0;cnt=0;lowest=None
            while True:
                pg=c.call("accessLog.get",{"watch_id":wid,"offset":off,"limit":3000})
                ev=pg.get("events") or []
                for e in ev:
                    cnt+=1
                    av=e.get("address"); av=int(av,16) if isinstance(av,str) else av
                    if av is not None and (lowest is None or av<lowest): lowest=av
                    pc=e.get("pc"); pc=int(pc,16) if isinstance(pc,str) else pc
                    if pc is not None:
                        k=pcs.setdefault(pc,{"pc":hex(pc),"count":0,"insn":e.get("instruction")})
                        k["count"]+=1
                off+=len(ev)
                if len(ev)<3000: break
            if cnt: hits.append({"base":hex(base),"writes":cnt,"lowest":hex(lowest) if lowest else None})
        res["blocks_written"]=len(hits); res["blocks_total"]=len(ws); res["hits"]=hits
        def nm(p):
            best=None
            for a2,n2 in S.items():
                if a2<=p and (best is None or a2>best[0]): best=(a2,n2)
            return f"{best[1]}+0x{p-best[0]:x}" if best else "?"
        top=sorted(pcs.values(),key=lambda v:-v["count"])[:10]
        for t in top: t["symbol"]=nm(int(t["pc"],16))
        res["writer_pcs"]=top
        print(f"{len(hits)}/{len(ws)} 256B blocks written")
        if hits: print(f"  lowest written address: {min(h['lowest'] for h in hits if h['lowest'])}")
        for t in top: print(f"  PC {t['pc']} x{t['count']:<6} {t['symbol']}  {t['insn']}")
    finally:
        subprocess.run([FORK,"stop","--config-dir",CFG],capture_output=True)
    o=os.path.join(ROOT,"analysis/dat_ceiling_owner.json"); json.dump(res,open(o,"w"),indent=1)
    print("wrote",o)
if __name__=="__main__": main()
