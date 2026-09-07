"""Import generated session; always run full KiCad DRC after import."""
from pathlib import Path
import json
import pcbnew as p
root=Path(__file__).resolve().parents[1]
base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
assert p.ImportSpecctraSES(b,str(root/'DOCUMENTATION/board_review/remaining.ses'))
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones())
p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b)
counts={}
for t in b.GetTracks():
    key='vias' if isinstance(t,p.PCB_VIA) else p.LayerName(t.GetLayer())
    counts[key]=counts.get(key,0)+1
(root/'DOCUMENTATION/board_review/routing_stats.json').write_text(json.dumps(counts,indent=2)+'\n')
print(counts)
mgr.UnloadProject(b.GetProject(),False)
