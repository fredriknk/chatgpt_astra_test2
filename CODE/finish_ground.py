"""Add clearance-checked local ground stitches, rejecting conflicting candidates."""
from pathlib import Path
import json,subprocess
import pcbnew as p
import wx
wx.Log.EnableLogging(False)
root=Path(__file__).resolve().parents[1];base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
target=base.with_suffix('.kicad_pcb');seed=target.read_bytes()
report=root/'DOCUMENTATION/board_review/drc.json'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
specs=[('C1','2',77.5,112.05),('C3','2',79.5,96.525),('C11','2',111,51.7),('C12','2',113,55.7),('C13','2',111.3,62),('C14','2',101.7,69.05),('R15','2',86.7,61.0875),('R16','2',100.8,65.0875),('U5','1',104.8,65.05),('U1','9',70.2,105.275),('U4','40',135.2,51.44),('U6','2',92.5,64),('U9','10',106.2,89.65),('U10','6',112.5,84),('U11','4',117.5,90.5),('R29','2',109.7,109.0875),('Q2','2',113,112.95),('D9','2',124.7,117.85),('C25','2',143.4,115),('SW1','2',80.85,59.2)]
rejected=[]
while True:
    target.write_bytes(seed);b=p.LoadBoard(str(target));fps={f.GetReference():f for f in b.GetFootprints()};ids={}
    for spec in specs:
        ref,num,x,y=spec;a=next(a for a in fps[ref].Pads() if a.GetNumber()==num);assert a.GetNetname()=='GND'
        v=p.PCB_VIA(b);v.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(a.GetNetCode());b.Add(v)
        t=p.PCB_TRACK(b);t.SetStart(a.GetPosition());t.SetEnd(v.GetPosition());t.SetWidth(p.FromMM(.2));t.SetLayer(p.F_Cu);t.SetNetCode(a.GetNetCode());b.Add(t)
        ids[t.m_Uuid.AsString()]=spec;ids[v.m_Uuid.AsString()]=spec
    b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(target),b)
    subprocess.run(['C:/Program Files/KiCad/9.0/bin/kicad-cli.exe','pcb','drc',str(target),'--format','json','--schematic-parity','-o',str(report)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
    d=json.loads(report.read_text());bad=set()
    for issue in d['violations']:
        for item in issue['items']:
            if item['uuid'] in ids:bad.add(ids[item['uuid']])
    print(len(specs),'candidates;',len(d['violations']),'violations;',len(d['unconnected_items']),'open',flush=True)
    if not d['violations']:break
    if not bad:target.write_bytes(seed);raise RuntimeError('Unexpected baseline violation')
    rejected.extend(bad);specs=[s for s in specs if s not in bad]
(root/'DOCUMENTATION/board_review/ground_stitching.json').write_text(json.dumps({'accepted':specs,'rejected':rejected},indent=2)+'\n')
mgr.UnloadProject(b.GetProject(),False)
