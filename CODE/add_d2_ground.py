"""Record of the accepted D2 ground stitch after bulk routing.

Apply once to the 7b6780f board. Further ground stitches need manual review.
"""
from pathlib import Path
import pcbnew as p
base=Path(__file__).resolve().parents[1]/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
assert len(list(b.GetTracks()))==690
net=b.FindNet('GND').GetNetCode()
v=p.PCB_VIA(b);v.SetPosition(p.VECTOR2I(p.FromMM(77.1),p.FromMM(106)));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(net);b.Add(v)
t=p.PCB_TRACK(b);t.SetStart(p.VECTOR2I(p.FromMM(76),p.FromMM(106)));t.SetEnd(v.GetPosition());t.SetWidth(p.FromMM(.2));t.SetLayer(p.F_Cu);t.SetNetCode(net);b.Add(t)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b)
mgr.UnloadProject(b.GetProject(),False)
