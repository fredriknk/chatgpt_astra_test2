"""Verify exported package contents and checked CAD reports with stdlib Python."""
from pathlib import Path
import csv,json,zipfile,hashlib,subprocess
root=Path(__file__).resolve().parents[1]
docs=root/'DOCUMENTATION';project=root/'CAD/chatgpt_astra_test2'
runs=sorted(p for p in (root/'PRODUCTION').glob('*_chatgpt_astra_test2') if (p/'chatgpt_astra_test2_gerbers.zip').is_file())
assert runs,'No completed production package';run=runs[-1]
pcb=json.loads((docs/'board_review/drc.json').read_text())
erc=json.loads((docs/'schematic_review/erc.json').read_text())
conn=json.loads((docs/'schematic_review/verification.json').read_text())
assert not pcb['violations'] and not pcb['unconnected_items'] and not pcb['schematic_parity']
assert not [v for s in erc['sheets'] for v in s['violations']]
assert not conn['connectivity_or_pad_errors']
with zipfile.ZipFile(run/'chatgpt_astra_test2_gerbers.zip') as archive:
    assert archive.testzip() is None
    names=archive.namelist()
    for suffix in ['-F_Cu.gtl','-In1_Cu.g1','-In2_Cu.g2','-B_Cu.gbl','-Edge_Cuts.gm1','-F_Mask.gts','-B_Mask.gbs']:
        assert any(n.endswith(suffix) for n in names),suffix
    assert any('PTH' in n and n.endswith('.drl') for n in names)
    assert any('NPTH' in n and n.endswith('.drl') for n in names)
with (run/'chatgpt_astra_test2_bom.csv').open(newline='',encoding='utf-8-sig') as f:
    bom=list(csv.DictReader(f));qty=sum(int(r['Qty']) for r in bom)
assert qty==93,qty
for name in ['chatgpt_astra_test2_schematic.pdf','chatgpt_astra_test2_board_prints.pdf']:
    f=docs/name;assert f.is_file() and f.read_bytes().startswith(b'%PDF-'),name
for view in ['top','bottom','side','iso']:
    f=root/'PICTURES'/f'chatgpt_astra_test2_{view}.png';assert f.stat().st_size>1000
assert (root/'3D_MODEL/chatgpt_astra_test2.step').stat().st_size>1000
usb=json.loads((docs/'board_review/usb_audit.json').read_text());assert max(usb['orientation_skew_mm'].values())<.25
result={'status':'PASS','erc_violations':0,'drc_violations':0,'unconnected_items':0,'schematic_parity_errors':0,'components':qty,'pins_checked':conn['connected_pins_checked'],'production_run':str(run.relative_to(root)),'zip_members':len(names),'usb_skew_mm':usb['orientation_skew_mm'],'source_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(project.glob('*.kicad_*')) if f.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro']}}
(docs/'ci_summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
