"""Manual USB pair routing; run once against the pre-USB refinement board.

Equivalent ESD channels are swapped in the matching schematic and intent.
The named fabrication stackup is documented separately; impedance needs fab control.
"""
from pathlib import Path
import json,re,sys
import pcbnew as p
import wx
wx.Log.EnableLogging(False)
root=Path(__file__).resolve().parents[1];base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2';target=base.with_suffix('.kicad_pcb')
pro=json.loads(base.with_suffix('.kicad_pro').read_text())
for nc in pro['net_settings']['classes']:
    if nc['name']=='USB':nc.update(clearance=.15,track_width=.25,diff_pair_width=.25,diff_pair_gap=.15,via_diameter=.5,via_drill=.25)
pro['board']['design_settings']['rules'].update(min_via_diameter=.5,min_through_hole_diameter=.25)
base.with_suffix('.kicad_pro').write_text(json.dumps(pro,indent=2)+'\n')
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')));b=p.LoadBoard(str(target))
remove=set()
copper_only='--copper-only' in sys.argv
for t in b.GetTracks():
    usb='USB_D' in t.GetNetname()
    points=[t.GetPosition()] if isinstance(t,p.PCB_VIA) else [t.GetStart(),t.GetEnd()]
    xs=[p.ToMM(a.x) for a in points];ys=[p.ToMM(a.y) for a in points]
    corridor=max(xs)>=92 and min(xs)<=116 and max(ys)>=60 and min(ys)<=78
    # Clear the local controller routing to accommodate relocated parts and pair.
    ground_return=t.GetNetname()=='GND' and ((isinstance(t,p.PCB_VIA) and (round(xs[0],2),round(ys[0],2)) in [(96.8,60.6),(90.8,63.8),(90.8,65.2),(94.8,64)]) or (not isinstance(t,p.PCB_VIA) and abs(xs[0]-93.8625)<.001 and abs(ys[0]-64)<.001))
    if usb or (corridor and not copper_only) or ground_return:remove.add(t.m_Uuid.AsString())
s=target.read_text();target.write_text(re.sub(r'\n\t\((?:segment|via)\n.*?\n\t\)',lambda m:'' if any(u in m[0] for u in remove) else m[0],s,flags=re.S))
b=p.LoadBoard(str(target));fps={f.GetReference():f for f in b.GetFootprints()}
def xy(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
def pad(r,n):return next(a for a in fps[r].Pads() if a.GetNumber()==str(n))
for ref,x,y in [('R18',112.5,65.8),('R17',112.5,68.8),('U5',107,75),('C14',103.8,73.4),('D3',109,71.8),('R10',137,75),('R16',99.5,70.5)]:
    f=fps[ref];f.SetPosition(xy(x,y))
    if ref=='R10':f.SetOrientationDegrees(0)
prefix='/03 / ESP32 AND USB/'
for pin,name in [('1','USB_DM'),('6','USB_DM_ESD'),('3','USB_DP'),('4','USB_DP_ESD')]:pad('U6',pin).SetNet(b.FindNet(prefix+name))
def path(net,pts,layer=p.F_Cu,width=.25):
    pts=[xy(*a) if isinstance(a,tuple) else a for a in pts]
    for a,z in zip(pts,pts[1:]):
        t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(z);t.SetLayer(layer);t.SetWidth(p.FromMM(width));t.SetNetCode(net);b.Add(t)
def via(net,x,y):
    v=p.PCB_VIA(b);v.SetPosition(xy(x,y));v.SetWidth(p.FromMM(.5));v.SetDrill(p.FromMM(.25));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(net);b.Add(v)
def route(a,z,pts=(),width=.25):
    a=pad(*a);z=pad(*z);assert a.GetNetCode()==z.GetNetCode();path(a.GetNetCode(),[a.GetPosition(),*pts,z.GetPosition()],width=width)
# Paired protected trunk, with series resistors near the module.
route(('U6',6),('R18',1),[(97.7,63.05),(99.65,65),(101,65),(101.5,64.5),(101.5,62.9945),(102.5,62.9945),(102.5,64.5),(103,65),(108.5,65),(109.3,65.8)])
route(('U6',4),('R17',1),[(97.7843,64.95),(98.2343,65.4),(107,65.4),(110.4,68.8)])
route(('R18',2),('U4',13),[(114.7,65.8),(115.58,66.68)])
route(('R17',2),('U4',14),[(114.7,68.8),(115.55,67.95)])
# USB-C duplicate data contacts join at symmetric midpoints on B.Cu.
for name,pins,xs,y in [('USB_DP',['B6','A6'],[94.25,95.25],60.3),('USB_DM',['A7','B7'],[94.75,95.75],61.1)]:
    net=b.FindNet(prefix+name).GetNetCode()
    for pin,x in zip(pins,xs):path(net,[pad('J4',pin).GetPosition(),(x,y)],width=.15);via(net,x,y)
    middle=(sum(xs)/2,y);path(net,[(xs[0],y),middle,(xs[1],y)],p.B_Cu,.15)
    if name=='USB_DP':
        path(net,[middle,(92.75,62.3),(91.6,62.3),(91.6,64.95)],p.B_Cu);via(net,91.6,64.95);path(net,[(91.6,64.95),pad('U6',3).GetPosition()])
    else:
        path(net,[middle,(94.65,61.7),(93.925,61.7),(92.4,63.225)],p.B_Cu);via(net,92.4,63.225);path(net,[(92.4,63.225),pad('U6',1).GetPosition()])
# Ground returns beside the crossover transitions and ESD reference pin.
g=b.FindNet('GND').GetNetCode()
for x,y in [(96.8,60.6),(90.8,63.8),(90.8,65.2),(94.8,64)]:via(g,x,y)
path(g,[pad('U6',2).GetPosition(),(94.8,64)])
z=p.ZONE(b);z.SetNet(b.FindNet('GND'));z.SetLayer(p.In2_Cu);z.SetLocalClearance(p.FromMM(.2));z.SetMinThickness(p.FromMM(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
poly=z.Outline();poly.NewOutline()
for x,y in [(90.5,59.8),(98,59.8),(98,66),(90.5,66)]:v=xy(x,y);poly.Append(v.x,v.y)
if not copper_only:b.Add(z)
from build_board import place_references
place_references(b,{r:f for r,f in fps.items() if not r.startswith('H')})
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(target),b);mgr.UnloadProject(b.GetProject(),False)
