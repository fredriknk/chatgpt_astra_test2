"""Apply pass two once to the 73e48d3 routing checkpoint with KiCad Python."""
from pathlib import Path
import pcbnew as p

base=Path(__file__).resolve().parents[1]/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
assert len(list(b.GetTracks()))==48, 'Expected first-pass routing; preserve subsequent edits'
fps={f.GetReference():f for f in b.GetFootprints()}
def xy(x,y):return p.VECTOR2I(p.FromMM(x+50),p.FromMM(y+50))
def pad(ref,num):return next(a for a in fps[ref].Pads() if a.GetNumber()==str(num))
def path(net,points,layer=p.F_Cu,width=.25):
    points=[xy(*a) if isinstance(a,tuple) else a for a in points]
    for a,z in zip(points,points[1:]):
        t=p.PCB_TRACK(b);t.SetStart(a);t.SetEnd(z);t.SetLayer(layer);t.SetWidth(p.FromMM(width));t.SetNetCode(net);b.Add(t)
def via(net,point):
    v=p.PCB_VIA(b);v.SetPosition(xy(*point));v.SetWidth(p.FromMM(.6));v.SetDrill(p.FromMM(.3));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNetCode(net);b.Add(v)
def ground(ref,num,point,width=.25):
    a=pad(ref,num);assert a.GetNetname()=='GND'
    path(a.GetNetCode(),[a.GetPosition(),point],width=width);via(a.GetNetCode(),point)
def route(a,z,points=(),width=.25):
    a=pad(*a);z=pad(*z);assert a.GetNetCode()==z.GetNetCode()
    path(a.GetNetCode(),[a.GetPosition(),*points,z.GetPosition()],width=width)
def backroute(a,z,first,last,middle=(),escape=(),entry=()):
    a=pad(*a);z=pad(*z);assert a.GetNetCode()==z.GetNetCode();net=a.GetNetCode()
    path(net,[a.GetPosition(),*escape,first]);via(net,first)
    path(net,[first,*middle,last],p.B_Cu);via(net,last)
    path(net,[last,*entry,z.GetPosition()])

# Buck feedback travels on the bottom, away from the switch/inductor region.
backroute(('U2',5),('R6',2),(21,37.1),(26.5,40.7),[(22,38.1),(22,40),(22.7,40.7)])
route(('R6',1),('C10',1),[(23.088,39.5),(26.5,39.5),(27.475,40.475)],.3)
for ref,num,point in [
    ('C4',2,(7,30.525)),('C5',2,(11.5,32)),('C7',2,(20.9,40)),
    ('C8',2,(34.3,27.525)),('C9',2,(34.3,32.525)),('C10',2,(34.3,37.525)),
    ('R7',2,(26,44)),('U2',1,(14,31.9)),
    ('C15',2,(45.5,38.05)),('C16',2,(58.4,39.05)),
    ('C17',2,(52.6,31.05)),('C18',2,(52.6,27.05)),
    ('C19',2,(64.2,37.05)),('C20',2,(64.2,41.05)),
    ('C21',2,(77.3,38.05)),('C22',2,(74,49.8)),
    ('C23',2,(78,55)),('C24',2,(71.6,58.05)),
    ('R22',2,(52.4,51.537)),('U8',2,(58.062,48.2)),('D7',2,(64.5,44.35)),
    ('U12',10,(81.5,50)),('R26',2,(73,50.1)),
]:ground(ref,num,point)

# Dedicated sense takeoff from the shunt terminal; load current uses a
# separate future top-layer connection to the same resistor pad.
backroute(('R22',1),('R23',1),(55.8,54.463),(51.7,47),[(55.8,49),(53.8,47)])
route(('R22',1),('TP1',1),[(55.463,55.926),(56.926,55.926)],.25)
route(('R23',2),('U8',1),[(56.1,47),(58.05,45.05)],.25)
route(('U8',1),('D7',1),[(60.7,45.05),(61.7,46.05),(61.7,47.65)],.25)
backroute(('R26',1),('U12',7),(74,54),(82,53),[(76,56),(79,56),(82,53)],entry=[(82,52.1),(81.4,51.5)])

b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b)
print('Pass two saved:',len(list(b.GetTracks())),'tracks/vias total')
mgr.UnloadProject(b.GetProject(),False)
