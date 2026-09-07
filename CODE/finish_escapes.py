"""Local escape rework; apply to the saved fine-pitch routing candidate."""
from pathlib import Path
import re
import pcbnew as p
root=Path(__file__).resolve().parents[1];base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2';target=base.with_suffix('.kicad_pcb')
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
b=p.LoadBoard(str(target));remove=set()
for t in b.GetTracks():
    if t.GetNetname()=='AO_FAULT_N':remove.add(t.m_Uuid.AsString())
    if t.GetNetname().endswith('/DAC_FILTER') and (isinstance(t,p.PCB_VIA) or t.GetLayer()==p.In2_Cu):remove.add(t.m_Uuid.AsString())
    if t.GetNetname().endswith('/EF_RTN'):remove.add(t.m_Uuid.AsString())
    if t.GetNetname().endswith('/XTR_REG') and (isinstance(t,p.PCB_VIA) or abs(t.GetLength()-p.FromMM(.5))>10):remove.add(t.m_Uuid.AsString())
    if t.GetNetname()=='GND':
        if isinstance(t,p.PCB_VIA) and t.GetPosition()==p.VECTOR2I(p.FromMM(131.5),p.FromMM(100)):remove.add(t.m_Uuid.AsString())
        elif not isinstance(t,p.PCB_VIA) and ((t.GetStart()==p.VECTOR2I(p.FromMM(130.15),p.FromMM(100))) or t.m_Uuid.AsString()=='bcec3133-4f34-49ee-8cd4-06aa14e9041b'):remove.add(t.m_Uuid.AsString())
s=target.read_text();s=re.sub(r'\n\t\((?:segment|via)\n.*?\n\t\)',lambda m:'' if any(u in m[0] for u in remove) else m[0],s,flags=re.S);target.write_text(s)
b=p.LoadBoard(str(target));fps={f.GetReference():f for f in b.GetFootprints()}
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def pad(r,n):return next(a for a in fps[r].Pads() if a.GetNumber()==str(n))
def path(net,pts,layer=p.F_Cu,width=.15):
    pts=[xy(*a) if isinstance(a,tuple) else a for a in pts]
    for a,z in zip(pts,pts[1:]):
        t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(z);t.SetLayer(layer);t.SetWidth(p.FromMM(width));t.SetNetCode(net);b.Add(t)
def via(net,x,y):
    v=p.PCB_VIA(b);v.SetPosition(xy(x,y));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(net);b.Add(v)
def escape(r,n,x,y):
    a=pad(r,n);path(a.GetNetCode(),[a.GetPosition(),(x,y)]);via(a.GetNetCode(),x,y);return a.GetNetCode()
for spec in [('U1',9,70,105.275),('U6',2,94.8,64),('U9',10,103.5,89.65),('U12',10,131.5,99.3)]:escape(*spec)
n=escape('U1',11,70.5,103.975);escape('R5',1,70.0875,95.7);path(n,[(70.5,103.975),(71.5,102.975),(71.5,97.1125),(70.0875,95.7)],p.B_Cu)
escape('J4','A9',92.55,60.5)
escape('U12',2,124.6,100.4)
escape('U12',9,131.6,100.5)
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(target),b);mgr.UnloadProject(b.GetProject(),False)
