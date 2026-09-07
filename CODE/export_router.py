"""Export with project rules loaded and preserve manually routed copper."""
from pathlib import Path
import pcbnew as p
root=Path(__file__).resolve().parents[1]
base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')))
b=p.LoadBoard(str(base.with_suffix('.kicad_pcb')))
for t in b.GetDrawings():
    if isinstance(t,p.PCB_TEXT) and t.GetText() in ['PWR   IN   GND','OUT   GND']:
        v=t.GetPosition();v.y=p.FromMM(129.1);t.SetPosition(v)
p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(base.with_suffix('.kicad_pcb')),b)
target=root/'DOCUMENTATION/board_review/remaining.dsn'
assert p.ExportSpecctraDSN(b,str(target))
mgr.UnloadProject(b.GetProject(),False)
source=target.read_text().replace('(type route)','(type protect)')
target.write_text(source)
print('Exported protected routing seed with project net classes')
