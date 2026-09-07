"""Reconnect the three capacitor ground islands after USB area rearrangement."""
from pathlib import Path
import pcbnew as p
base=Path(__file__).resolve().parents[1]/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')));b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
fps={f.GetReference():f for f in b.GetFootprints()}
for ref,x,y in [('C18',104,75.9),('C12',114.3,57.05),('C13',110.5,63.2)]:
    a=next(a for a in fps[ref].Pads() if a.GetNumber()=='2');assert a.GetNetname()=='GND'
    v=p.PCB_VIA(b);v.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(a.GetNetCode());b.Add(v)
    t=p.PCB_TRACK(b);t.SetStart(a.GetPosition());t.SetEnd(v.GetPosition());t.SetWidth(p.FromMM(.2));t.SetLayer(p.F_Cu);t.SetNetCode(a.GetNetCode());b.Add(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b);mgr.UnloadProject(b.GetProject(),False)
