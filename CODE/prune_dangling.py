"""Remove only track/via objects explicitly reported dangling by KiCad DRC."""
from pathlib import Path
import json,re,subprocess
root=Path(__file__).resolve().parents[1];target=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2.kicad_pcb';report=root/'DOCUMENTATION/board_review/drc.json'
for iteration in range(10):
    subprocess.run(['C:/Program Files/KiCad/9.0/bin/kicad-cli.exe','pcb','drc',str(target),'--format','json','--schematic-parity','-o',str(report)],check=True)
    d=json.loads(report.read_text());ids={i['uuid'] for v in d['violations'] if v['type'] in ['track_dangling','via_dangling'] for i in v['items']}
    if not ids:break
    text=target.read_text();target.write_text(re.sub(r'\n\t\((?:segment|via)\n.*?\n\t\)',lambda m:'' if any(u in m[0] for u in ids) else m[0],text,flags=re.S))
else:raise RuntimeError('Dangling cleanup did not converge')
assert not d['violations'] and not d['unconnected_items'] and not d['schematic_parity'], 'Board needs further routing review'
