"""Create the serviceable PCB placement draft using KiCad's native pcbnew API.

Run with KiCad 9's bundled Python. Regenerates the board: preserve manual edits.
Coordinates below are millimetres from the upper-left corner of the base PCB.
"""
from pathlib import Path
import json, uuid, shutil, xml.etree.ElementTree as ET
import pcbnew as p

ROOT=Path(__file__).resolve().parents[1]
PROJ=ROOT/'CAD/chatgpt_astra_test2'
OUT=ROOT/'DOCUMENTATION/board_review'
OUT.mkdir(exist_ok=True)
intent=json.loads((ROOT/'DOCUMENTATION/schematic_review/connectivity_intent.json').read_text())
parts={d['Reference']:d for d in json.loads((ROOT/'DOCUMENTATION/schematic_review/components.json').read_text())}
def uid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'esp32-loop-reva/'+s))
def mm(x):return p.FromMM(x)
def pos(x,y):return p.VECTOR2I(mm(x+50),mm(y+50))
ROOT_ID='a269929a-5104-4f3f-907a-1d34fef46421'
glob={'VIN24','GND','V24_PROT','V3V3','SENSOR_PWR','AI_IN','AO_OUT','I2C_SDA','I2C_SCL','AO_ENABLE','AO_FAULT_N','SYS_OK','ADC_RDY'}
titles={'power':'02 / POWER AND SENSOR SUPPLY','controller':'03 / ESP32 AND USB','analog_input':'04 / PROTECTED CURRENT INPUT','analog_output':'05 / PRECISION CURRENT OUTPUT'}
def netname(sheet,n):return n if n in glob else '/'+titles[sheet]+'/'+n

# Upper edge: user interface and antenna. Lower edge: field wiring.
PLACE={
 'J1':(13,73,0),'J2':(39,73,0),'J3':(80,73,0),'J4':(45,4.8,180),'J5':(91,25,0),
 'U4':(75,6.7,0),'SW1':(34,6,0),'SW2':(24,6,0),'D4':(14,6,0),'R14':(14,10,0),
 'U5':(57,16,0),'D3':(58,21,0),'R10':(62,18,90),'R11':(64,23,0),'C13':(59,12,0),
 'C11':(61,4,90),'C12':(63,8,90),'C14':(53,20,90),'R12':(66,28,0),'R13':(66,32,0),
 'U6':(45,14,0),'R15':(38,12,90),'R16':(49.5,16,90),'R17':(53,12,0),'R18':(53,15,0),
 'F1':(10,63,90),'D1':(20,64,0),'C1':(26,63,90),'U1':(16,53,0),'D2':(24,56,0),
 'R1':(9,48,90),'R2':(9,52,90),'R3':(9,56,90),'R4':(5,58,90),'R5':(21,47,0),'C2':(24,51,0),'C3':(28,48,90),
 'U2':(17,35,0),'L1':(28,35,0),'C4':(10,34,90),'C5':(12,30,0),'C6':(21,30,0),'C7':(19,40,0),
 'C8':(33,29,90),'C9':(33,34,90),'C10':(33,39,90),'R6':(24,41,0),'R7':(24,44,0),
 'U3':(33,57,0),'R8':(31,63,0),'R9':(39,60,90),
 'D5':(42,63,0),'R19':(47,63,0),'D6':(55,67,0),'U7':(46,56,0),'R20':(43,50,0),'R21':(49,50,0),'R22':(54,53,90),
 'R23':(54,47,0),'U8':(59,46,0),'D7':(63,46,90),'U9':(52,39,0),'C15':(47,39,90),'C16':(57,40,90),
 'U10':(59,33,0),'C17':(54,32,90),'C18':(54,28,90),'R24':(61,26,90),'TP1':(58,57,0),'TP2':(60,41,0),
 'U11':(71,40,0),'C19':(65.5,38,90),'C20':(65.5,42,90),'C21':(76,39,90),'R25':(72,46,0),'C22':(72,49,0),'TP3':(67,50,0),
 'U12':(78,51,0),'C23':(78,57,90),'C24':(73,59,90),'R26':(73,52,90),'R27':(83,47,0),'R28':(82,43,0),
 'Q1':(65,57,0),'Q2':(65,62,0),'R29':(61,60,90),
 'Q3':(87,60,0),'Q4':(84,53,0),'R30':(87,49,0),'R31':(85,65,0),'C25':(91,65,0),'D8':(80,64,0),'D9':(73,70,90),
}

def text(board,s,x,y,size=1,layer=p.F_SilkS,angle=0):
    size=max(size,.8)
    t=p.PCB_TEXT(board);t.SetText(s);t.SetPosition(pos(x,y));t.SetTextSize(p.VECTOR2I(mm(size),mm(size)))
    t.SetTextThickness(mm(0.15));t.SetLayer(layer);t.SetTextAngle(p.EDA_ANGLE(angle,p.DEGREES_T));board.Add(t);return t

def zone(board,net,layer,rect,clearance=0.25,priority=0):
    z=p.ZONE(board);z.SetLayer(layer);z.SetNet(net);z.SetLocalClearance(mm(clearance));z.SetThermalReliefGap(mm(.25));z.SetThermalReliefSpokeWidth(mm(.3));z.SetMinThickness(mm(.2));z.SetAssignedPriority(priority)
    poly=z.Outline();poly.NewOutline()
    x1,y1,x2,y2=rect
    for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:v=pos(x,y);poly.Append(v.x,v.y)
    board.Add(z);return z

def place_references(b,fps):
    """Place legible horizontal references clear of bodies, pads and other text."""
    def body(fp):
        if fp.GetReference()=='U4':return p.BOX2I(pos(65.5,-6.5),p.VECTOR2I(mm(19),mm(26.8)))
        return fp.GetBoundingBox(False,False)
    obstacles=[body(fp).GetInflated(mm(.15)) for fp in b.GetFootprints()]
    occupied=[d.GetBoundingBox().GetInflated(mm(.2)) for d in b.GetDrawings() if isinstance(d,p.PCB_TEXT) and d.GetLayer()==p.F_SilkS]
    for ref,fp in sorted(fps.items(),key=lambda kv:(not kv[0].startswith('U'),kv[0])):
        bb=body(fp)
        x=(bb.GetLeft()+bb.GetRight())/2;y=(bb.GetTop()+bb.GetBottom())/2
        field=fp.Reference();field.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
        done=False
        for gap in [.65,1.1,1.6,2.2,3,4,5,6,8]:
            for shift in [0,2,-2,4,-4,6,-6]:
                candidates=[(x+mm(shift),bb.GetTop()-mm(gap)),(x+mm(shift),bb.GetBottom()+mm(gap)),(bb.GetLeft()-mm(gap+len(ref)*.3),y+mm(shift)),(bb.GetRight()+mm(gap+len(ref)*.3),y+mm(shift))]
                for xx,yy in candidates:
                    field.SetPosition(p.VECTOR2I(int(xx),int(yy)));fb=field.GetBoundingBox().GetInflated(mm(.15))
                    if fb.GetLeft()<mm(50.5) or fb.GetRight()>mm(149.5) or fb.GetTop()<mm(50.5) or fb.GetBottom()>mm(129.5):continue
                    if any(fb.Intersects(ob) for ob in obstacles+occupied):continue
                    occupied.append(fb);done=True;break
                if done:break
            if done:break
        if not done:raise RuntimeError('No clear reference position for '+ref)

def build():
    b=p.BOARD();b.SetFileName(str(PROJ/'chatgpt_astra_test2.kicad_pcb'));b.SetCopperLayerCount(4)
    b.GetDesignSettings().SetBoardThickness(mm(1.6))
    b.GetDesignSettings().m_CopperEdgeClearance=mm(.3)
    b.SetLayerName(p.In1_Cu,'In1.Cu');b.SetLayerName(p.In2_Cu,'In2.Cu')
    nets={};padnets={}
    for n in ET.parse(ROOT/'DOCUMENTATION/schematic_review/netlist.xml').getroot().findall('nets/net'):
        name=n.attrib['name'];nets[name]=None
        for node in n.findall('node'):padnets[(node.attrib['ref'],node.attrib['pin'])]=name
    for name in sorted(nets):n=p.NETINFO_ITEM(b,name);b.Add(n);nets[name]=n
    fps={}
    assert set(PLACE)==set(parts),(set(parts)-set(PLACE),set(PLACE)-set(parts))
    for ref,d in parts.items():
        name=d['Footprint'].split(':')[1]
        fp=p.FootprintLoad(str(PROJ/'libraries/LoopIO.pretty'),name)
        # Standard 0.3 mm plated thermal holes with 0.6 mm copper lands.
        modified=False
        for pad in fp.Pads():
            if 0<pad.GetDrillSize().x<mm(.3):
                pad.SetDrillSize(p.VECTOR2I(mm(.3),mm(.3)));pad.SetSize(p.VECTOR2I(mm(.6),mm(.6)));modified=True
        for shape in fp.GraphicalItems():
            if shape.GetLayer()!=p.F_SilkS:continue
            if (ref=='U4' and shape.GetBoundingBox().GetTop()<mm(-6.5)) or (ref=='J4' and shape.GetBoundingBox().GetBottom()>mm(4.5)):
                shape.SetLayer(p.F_Fab);modified=True
        if modified:p.FootprintSave(str(PROJ/'libraries/LoopIO.pretty'),fp)
        fp.SetReference(ref);fp.SetValue(d['Value']);fp.SetFPID(p.LIB_ID('LoopIO',name))
        fp.SetAttributes(fp.GetAttributes() & ~p.FP_EXCLUDE_FROM_BOM)
        path='/'+ROOT_ID
        if intent[ref]['sheet']!='chatgpt_astra_test2':path+='/'+uid('sheet-'+intent[ref]['sheet'])
        fp.SetPath(p.KIID_PATH(path+'/'+uid(ref)))
        b.Add(fp);x,y,angle=PLACE[ref];fp.SetPosition(pos(x,y));fp.SetOrientationDegrees(angle)
        fp.Reference().SetTextSize(p.VECTOR2I(mm(.8),mm(.8)));fp.Reference().SetTextThickness(mm(.12));fp.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));fp.Reference().SetKeepUpright(True)
        fp.Value().SetVisible(False)
        for pad in fp.Pads():
            nn=padnets.get((ref,pad.GetNumber()))
            if nn is not None:pad.SetNet(nets[nn])
        fps[ref]=fp
    # Base board. The module antenna projects 6.2 mm beyond the upper edge.
    for a,c in [((0,0),(100,0)),((100,0),(100,80)),((100,80),(0,80)),((0,80),(0,0))]:
        e=p.PCB_SHAPE(b);e.SetShape(p.SHAPE_T_SEGMENT);e.SetStart(pos(*a));e.SetEnd(pos(*c));e.SetWidth(mm(.05));e.SetLayer(p.Edge_Cuts);b.Add(e)
    libbase=Path('C:/Users/fnk/Documents/KiCad/Kicad-Libraries/kicad_8_libs/kicad-footprints')
    hole='MountingHole_3.2mm_M3'
    shutil.copyfile(libbase/'MountingHole.pretty'/(hole+'.kicad_mod'),PROJ/'libraries/LoopIO.pretty'/(hole+'.kicad_mod'))
    for i,(x,y) in enumerate([(4,4),(96,4),(4,76),(96,76)],1):
        fp=p.FootprintLoad(str(PROJ/'libraries/LoopIO.pretty'),hole);fp.SetReference('H'+str(i));fp.SetValue('M3 / 3.2mm');fp.SetFPID(p.LIB_ID('LoopIO',hole));fp.SetAttributes(p.FP_EXCLUDE_FROM_BOM|p.FP_EXCLUDE_FROM_POS_FILES|p.FP_BOARD_ONLY);b.Add(fp);fp.SetPosition(pos(x,y));fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
    # Solid internal ground plane; no splits under the digital/analog signals.
    zone(b,nets['GND'],p.In1_Cu,(.5,.5,99.5,79.5))
    # A copper keepout reinforces the module's own antenna rule area.
    ko=p.ZONE(b);ko.SetIsRuleArea(True);ko.SetLayerSet(p.LSET.AllCuMask());ko.SetDoNotAllowTracks(True);ko.SetDoNotAllowVias(True);ko.SetDoNotAllowCopperPour(True)
    poly=ko.Outline();poly.NewOutline()
    for x,y in [(65.5,-7),(84.5,-7),(84.5,0),(65.5,0)]:v=pos(x,y);poly.Append(v.x,v.y)
    b.Add(ko)
    # Assembly/service legends remain useful with components fitted.
    text(b,'ESP32 LOOP I/O',23,17,1.5);text(b,'24 V  |  AI + AO',23,20,1)
    text(b,'REV A - PLACEMENT',24,24,.8)
    text(b,'RESET',34,10,1);text(b,'BOOT',24,10,1);text(b,'USB DATA',44,19,1)
    text(b,'+24V  GND',16,79, .85)
    text(b,'PWR   IN   GND',44,79,.85)
    text(b,'OUT   GND',83,79,.85)
    text(b,'UART 3V3',91,21,.85)
    text(b,'GND',96,25,.7);text(b,'TX',95,27.54,.7);text(b,'RX',95,30.08,.7);text(b,'3V3',96,32.62,.7)
    text(b,'AI SHUNT',58,54.8,.7);text(b,'ADC',60,43,.7);text(b,'DAC',67,52,.7)
    text(b,'ANTENNA - KEEP CLEAR',75,-4,1,p.Dwgs_User)
    text(b,'PCB 100 x 80 mm / 4 layers / 1.6 mm',50,84,1.2,p.Dwgs_User)
    text(b,'M3 hole centres: 92 x 72 mm',50,87,1,p.Dwgs_User)
    # Assign design net classes without changing any schematic connectivity.
    pro=json.loads((PROJ/'chatgpt_astra_test2.kicad_pro').read_text())
    def nc(name,width,clearance=.2):return {'name':name,'clearance':clearance,'track_width':width,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.2,'diff_pair_gap':.15,'diff_pair_via_gap':.25,'wire_width':6,'bus_width':12,'line_style':0}
    pro['net_settings']['classes']=[nc('Default',.25),nc('Power24V',.75,.25),nc('Power3V3',.6),nc('Analog',.25,.25),nc('USB',.2)]
    pro['net_settings']['netclass_patterns']=[{'netclass':'Power24V','pattern':n} for n in ['VIN24','V24_PROT','SENSOR_PWR','*VIN_FUSED']]+[{'netclass':'Power3V3','pattern':'V3V3'}]+[{'netclass':'Analog','pattern':n} for n in ['AI_IN','AO_OUT','*AI_*','*DAC_*','*XTR_*']]+[{'netclass':'USB','pattern':'*USB_D*'}]
    pro['board']['design_settings']['rules']={'min_clearance':.15,'min_track_width':.15,'min_via_diameter':.6,'min_through_hole_diameter':.3,'min_hole_to_hole':.25,'min_copper_edge_clearance':.3,'min_silk_clearance':.15,'min_silk_text_height':.8,'min_silk_text_thickness':.12}
    (PROJ/'chatgpt_astra_test2.kicad_pro').write_text(json.dumps(pro,indent=2)+'\n')
    place_references(b,fps)
    b.BuildConnectivity();p.SaveBoard(str(PROJ/'chatgpt_astra_test2.kicad_pcb'),b)
    # The native filler requires a loaded project/settings context.
    p.GetSettingsManager().LoadProject(str((PROJ/'chatgpt_astra_test2.kicad_pro').resolve()))
    b=p.LoadBoard(str((PROJ/'chatgpt_astra_test2.kicad_pcb').resolve()))
    p.ZONE_FILLER(b).Fill(b.Zones())
    p.SaveBoard(str(PROJ/'chatgpt_astra_test2.kicad_pcb'),b)
    summary={'board_mm':[100,80],'module_overhang_mm':6.2,'layers':4,'thickness_mm':1.6,'schematic_footprints':len(fps),'mounting_holes':4,'nets':len(nets),'stage':'placement; routing pending','placement':PLACE}
    (OUT/'placement.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k!='placement'},indent=2))
    p.GetSettingsManager().UnloadProject(b.GetProject(),False)

if __name__=='__main__':build()
