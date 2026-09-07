"""Record the selected nominal fabrication stackup and prototype revision."""
from pathlib import Path
import json
import pcbnew as p
root=Path(__file__).resolve().parents[1];base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2';target=base.with_suffix('.kicad_pcb')
source=target.read_text()
stackup='''
        (stackup
            (layer "F.SilkS" (type "Top Silk Screen"))
            (layer "F.Paste" (type "Top Solder Paste"))
            (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01) (epsilon_r 3.8))
            (layer "F.Cu" (type "copper") (thickness 0.035))
            (layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4))
            (layer "In1.Cu" (type "copper") (thickness 0.0152))
            (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.6))
            (layer "In2.Cu" (type "copper") (thickness 0.0152))
            (layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "FR4 7628") (epsilon_r 4.4))
            (layer "B.Cu" (type "copper") (thickness 0.035))
            (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01) (epsilon_r 3.8))
            (layer "B.Paste" (type "Bottom Solder Paste"))
            (layer "B.SilkS" (type "Bottom Silk Screen"))
            (copper_finish "ENIG")
            (dielectric_constraints yes)
        )'''
assert '(stackup' not in source, 'Stackup already set; preserve reviewed settings'
target.write_text(source.replace('(setup','(setup'+stackup,1))
mgr=p.GetSettingsManager();mgr.LoadProject(str(base.with_suffix('.kicad_pro')));b=p.LoadBoard(str(target))
for t in b.GetDrawings():
    if isinstance(t,p.PCB_TEXT) and t.GetText()=='REV A - ROUTING DRAFT':t.SetText('REV A - PROTOTYPE')
b.BuildConnectivity();p.ZONE_FILLER(b).Fill(b.Zones());p.SaveBoard(str(target),b)
counts={}
for t in b.GetTracks():
    name='vias' if isinstance(t,p.PCB_VIA) else p.LayerName(t.GetLayer());counts[name]=counts.get(name,0)+1
(root/'DOCUMENTATION/board_review/routing_stats.json').write_text(json.dumps(counts,indent=2)+'\n')
mgr.UnloadProject(b.GetProject(),False)
