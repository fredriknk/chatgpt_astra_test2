"""Set explicit prototype routing rules and export a protected routing seed."""
from pathlib import Path
import json
root=Path(__file__).resolve().parents[1]
base=root/'CAD/chatgpt_astra_test2/chatgpt_astra_test2'
target=base.with_suffix('.kicad_pro')
pro=json.loads(target.read_text())
default=pro['net_settings']['classes'][0]
def nc(name,width,clearance=.2):
    d=dict(default);d.update(name=name,track_width=width,clearance=clearance,via_diameter=.6,via_drill=.3)
    return d
pro['net_settings']['classes']=[nc('Default',.25),nc('Power24V',.75),nc('Power3V3',.6),nc('Analog',.25),nc('USB',.2)]
pro['net_settings']['netclass_patterns']=[{'netclass':'Power24V','pattern':n} for n in ['VIN24','V24_PROT','SENSOR_PWR','*VIN_FUSED']]+[{'netclass':'Power3V3','pattern':'V3V3'}]+[{'netclass':'Analog','pattern':n} for n in ['AI_IN','AO_OUT','*AI_*','*DAC_*','*XTR_*']]+[{'netclass':'USB','pattern':'*USB_D*'}]
rules=pro['board']['design_settings']['rules']
rules.update(min_clearance=.15,min_track_width=.15,min_via_diameter=.6,min_through_hole_diameter=.3,min_hole_to_hole=.25,min_copper_edge_clearance=.3,min_silk_clearance=.15,min_silk_text_height=.8,min_silk_text_thickness=.12)
target.write_text(json.dumps(pro,indent=2)+'\n')
print('Configured five net classes and minimum fabrication rules')
