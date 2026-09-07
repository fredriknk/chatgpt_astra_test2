"""Add heat-spreading copper on the devices' actual thermal-pad nets."""
from pathlib import Path
import pcbnew as p
root=Path(__file__).resolve().parents[1];base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')));b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def zone(net,layer,rect):
    z=p.ZONE(b);z.SetNet(b.FindNet(net));z.SetLayer(layer);z.SetLocalClearance(p.FromMM(.25));z.SetMinThickness(p.FromMM(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
    poly=z.Outline();poly.NewOutline();x1,y1,x2,y2=rect
    for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:v=xy(x,y);poly.Append(v.x,v.y)
    b.Add(z)
for net,front,back,points in [
    ('/02 / POWER AND SENSOR SUPPLY/SENS_RAW',(84,104,90,111),(77,100,92,124),[(88.5,105.5),(88.5,104.5)]),
    ('/04 / PROTECTED CURRENT INPUT/AI_LIMIT_OUT',(97,103,103,109),(94,99,106,116),[(101.5,104.7),(101.5,103.7)]),
]:
    zone(net,p.F_Cu,front);zone(net,p.B_Cu,back)
    for x,y in points:
        v=p.PCB_VIA(b);v.SetPosition(xy(x,y));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(net));b.Add(v)
zone('/02 / POWER AND SENSOR SUPPLY/EF_RTN',p.B_Cu,(61,97,70,107))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b);mgr.UnloadProject(b.GetProject(),False)
