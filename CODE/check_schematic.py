"""Check KiCad-exported connectivity and physical footprint pad coverage."""
from pathlib import Path
import json, xml.etree.ElementTree as ET
from build_schematic import ROOT, PROJECT, parse, children, uq

out=ROOT/'DOCUMENTATION/schematic_review'
intent=json.loads((out/'connectivity_intent.json').read_text())
netlist=ET.parse(out/'netlist.xml').getroot()
actual={}
for net in netlist.findall('nets/net'):
    for node in net.findall('node'):
        actual[(node.attrib['ref'],node.attrib['pin'])]=net.attrib['name']
errors=[];checked=0
groups={}
global_names={'VIN24','GND','V24_PROT','V3V3','SENSOR_PWR','AI_IN','AO_OUT','I2C_SDA','I2C_SCL','AO_ENABLE','AO_FAULT_N','SYS_OK','ADC_RDY'}
for ref,d in intent.items():
    if ref.startswith('#'):continue
    for pin,net in d['pins'].items():
        if net is None:continue
        checked+=1
        found=actual.get((ref,pin))
        if found is None or found.split('/')[-1]!=net:errors.append(f'{ref}.{pin}: wanted {net}, got {found}')
        groups.setdefault(net if net in global_names else d['sheet']+'/'+net,set()).add(found)
    fp=d['footprint'].split(':')[-1]
    pads={uq(p[1]) for p in children(parse((PROJECT/'libraries/LoopIO.pretty'/(fp+'.kicad_mod')).read_text(encoding='utf8')),'pad') if uq(p[1])}
    if pads!=set(d['pins']):errors.append(f'{ref}: footprint pad mismatch {pads ^ set(d["pins"])}')
for net,names in groups.items():
    if len(names)!=1:errors.append(f'Split intended net {net}: {names}')
erc=json.loads((out/'erc.json').read_text())
violations=[v for s in erc['sheets'] for v in s['violations']]
if violations:errors.append(f'ERC: {len(violations)} violations')
report={'components':len(netlist.findall('components/comp')),'connected_pins_checked':checked,'nets':len(netlist.findall('nets/net')),'erc_violations':len(violations),'connectivity_or_pad_errors':errors}
(out/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
raise SystemExit(bool(errors))
