"""Measure shortest copper paths through each USB-C contact orientation."""
from pathlib import Path
from collections import defaultdict
import heapq,json,math
import pcbnew as p
root=Path(__file__).resolve().parents[1];b=p.LoadBoard(str(root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2.kicad_pcb'))
fps={f.GetReference():f for f in b.GetFootprints()}
def coord(v):return (round(p.ToMM(v.x)*100),round(p.ToMM(v.y)*100))
def pad(r,n):return next(a for a in fps[r].Pads() if a.GetNumber()==str(n))
def distance(a,z):
    a=pad(*a);z=pad(*z);net=a.GetNetCode();assert net==z.GetNetCode()
    ts=[t for t in b.GetTracks() if t.GetNetCode()==net];graph=defaultdict(list)
    points=defaultdict(set)
    for t in ts:
        if isinstance(t,p.PCB_VIA):
            for layer in (p.F_Cu,p.B_Cu):points[layer].add(coord(t.GetPosition()))
        else:points[t.GetLayer()].update([coord(t.GetStart()),coord(t.GetEnd())])
    def edge(s,e,w):graph[s].append((e,w));graph[e].append((s,w))
    for t in ts:
        if isinstance(t,p.PCB_VIA):
            c=coord(t.GetPosition());edge((p.F_Cu,*c),(p.B_Cu,*c),1.6)
        else:
            layer=t.GetLayer();s=coord(t.GetStart());e=coord(t.GetEnd());dx=e[0]-s[0];dy=e[1]-s[1];den=dx*dx+dy*dy
            if not den:continue
            on=[]
            for pt in points[layer]:
                u=((pt[0]-s[0])*dx+(pt[1]-s[1])*dy)/den
                if -.001<=u<=1.001 and abs((pt[0]-s[0])*dy-(pt[1]-s[1])*dx)/math.sqrt(den)<1.5:on.append((u,pt))
            on.sort()
            for (_,v),(_,w) in zip(on,on[1:]):edge((layer,*v),(layer,*w),math.dist(v,w)/100)
    start=(p.F_Cu,*coord(a.GetPosition()));end=(p.F_Cu,*coord(z.GetPosition()))
    # Imports may shorten track ends to pad edges; join copper points inside pads.
    for endpoint,pa in [(start,a),(end,z)]:
        for node in list(graph):
            if node[0]==p.F_Cu and pa.HitTest(p.VECTOR2I(p.FromMM(node[1]/100),p.FromMM(node[2]/100))):edge(endpoint,node,math.dist(endpoint[1:],node[1:])/100)
    queue=[(0,start)];seen=set()
    while queue:
        dist,node=heapq.heappop(queue)
        if node==end:return dist
        if node in seen:continue
        seen.add(node)
        for other,w in graph[node]:
            if other not in seen:heapq.heappush(queue,(dist+w,other))
    raise RuntimeError('No measured path: '+a.GetNetname())
result={}
for polarity,r,esd_in,esd_out,module,contacts in [('DP','R17',3,4,14,['A6','B6']),('DM','R18',1,6,13,['A7','B7'])]:
    protected=distance(('U6',esd_out),(r,1));mcu=distance((r,2),('U4',module))
    inputs={c:distance(('J4',c),('U6',esd_in)) for c in contacts}
    result[polarity]={'connector_paths_mm':inputs,'protected_path_mm':protected,'resistor_to_module_mm':mcu,'total_paths_mm':{c:v+protected+mcu for c,v in inputs.items()}}
result['orientation_skew_mm']={'A':abs(result['DP']['total_paths_mm']['A6']-result['DM']['total_paths_mm']['A7']),'B':abs(result['DP']['total_paths_mm']['B6']-result['DM']['total_paths_mm']['B7'])}
result['measurement_note']='Geometric copper centreline paths, including 1.6 mm per through-board transition; excludes internal IC and resistor paths. Coordinates quantized to 0.01 mm.'
(root/'DOCUMENTATION/board_review/usb_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
