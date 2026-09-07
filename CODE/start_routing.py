"""First manual routing pass; run once on the placement checkpoint with KiCad Python.

Does not autoroute. Coordinates are mm from board upper left.
"""
from pathlib import Path
import pcbnew as p

root=Path(__file__).resolve().parents[1]
base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager()
mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
assert not list(b.GetTracks()), 'Already routed: do not overwrite existing routing'
fps={f.GetReference():f for f in b.GetFootprints()}
def xy(x,y): return p.VECTOR2I(p.FromMM(x+50),p.FromMM(y+50))
def pad(ref,num): return next(a for a in fps[ref].Pads() if a.GetNumber()==str(num))
def route(a,z,points=(),width=.25):
    a=pad(*a);z=pad(*z)
    assert a.GetNetCode()==z.GetNetCode(), (a.GetNetname(),z.GetNetname())
    pts=[a.GetPosition()]+[xy(*v) for v in points]+[z.GetPosition()]
    for start,end in zip(pts,pts[1:]):
        t=p.PCB_TRACK(b);t.SetStart(start);t.SetEnd(end);t.SetWidth(p.FromMM(width));t.SetLayer(p.F_Cu);t.SetNetCode(a.GetNetCode());b.Add(t)

# Bring the ceramic input and bootstrap capacitors beside the buck pins.
for ref,x,y,angle in [('C5',11.5,34.36,90),('C4',8.5,32,90),('C6',22.5,33.73,90)]:
    f=fps[ref];f.SetPosition(xy(x,y));f.SetOrientationDegrees(angle)
    f.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
fps['C5'].Reference().SetPosition(xy(11.8,37.3))
fps['C4'].Reference().SetPosition(xy(5.8,32))
fps['C6'].Reference().SetPosition(xy(22.5,31.5))
fps['U2'].Reference().SetPosition(xy(17,30.5))
route(('U2',2),('C5',1),[(13.2,34.365),(12.295,35.27)],.45)
route(('U2',2),('U2',3),width=.45)
route(('C4',1),('C5',1),[(9,35.27)],.6)
route(('U2',1),('C5',2),width=.45)
route(('C4',2),('C5',2),[(10,30.525),(11.5,32.025)],.45)
route(('U2',7),('C6',1),[(22.185,34.365)],.3)
route(('U2',8),('C6',2),[(22.185,33.095)],.6)
route(('C6',2),('L1',1),[(23.705,32.78)],.6)
route(('U2',6),('C7',1),[(22,35.635),(22,37.6),(21.3,38.3),(18.05,38.3)],.25)
# Feedback pin escape remains for the next pass; keep it away from SW copper.
route(('R6',2),('R7',1),[(25.5,41),(25.5,42.5),(23.088,42.5)],.25)
route(('L1',2),('C9',1),[(31.425,34.95)],.8)
route(('C8',1),('C9',1),[(35.5,30.475),(35.5,35.475)],width=.8)
route(('C9',1),('C10',1),[(35.5,35.475),(35.5,40.475)],width=.8)

# Local DAC reference and output filter. Leave the precision return routing
# for a subsequent pass; ground plane connectivity needs explicit stitching.
route(('U11',10),('C21',1),[(74.7,39),(75.65,39.95)],.2)
route(('U11',2),('R25',1),[(67.55,39.5),(67.55,44),(69.8,46)],.2)
route(('R25',2),('C22',1),[(74,46),(74,47.5),(72.55,47.5)],.25)
route(('C22',1),('TP3',1),[(69,49),(68,50)],.25)
route(('U12',4),('U12',5),width=.2)
for d in b.GetDrawings():
    if isinstance(d,p.PCB_TEXT) and d.GetText()=='REV A - PLACEMENT':d.SetText('REV A - ROUTING DRAFT')
b.BuildConnectivity()
p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b)
mgr.UnloadProject(b.GetProject(),False)
print('Saved first routing pass:',len(list(b.GetTracks())),'segments')
