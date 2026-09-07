"""Generate the revision-A KiCad schematic and its project-local libraries.

All schematic objects have deterministic UUIDs. Run only to regenerate the
generated design; manual schematic edits should be preserved separately first.
"""
from pathlib import Path
import re, json, uuid, copy, math, shutil

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'CAD/chatgpt_astra_test2'
LIBROOT = Path('C:/Users/fnk/Documents/KiCad/Kicad-Libraries/kicad_8_libs')

def parse(t):
    toks = re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|[^\s()]+', t)
    stack=[]; root=[]; cur=root
    for s in toks:
        if s=='(':
            n=[]; cur.append(n); stack.append(cur); cur=n
        elif s==')': cur=stack.pop()
        else: cur.append(s)
    return root[0]

def q(s): return json.dumps(str(s), ensure_ascii=False)
def uq(s): return json.loads(s) if s.startswith('"') else s
def children(n,key): return [v for v in n if isinstance(v,list) and v and v[0]==key]
def child(n,key): return next(iter(children(n,key)),None)
def dump(n): return '('+' '.join(dump(v) if isinstance(v,list) else v for v in n)+')'
def uid(s): return str(uuid.uuid5(uuid.NAMESPACE_URL,'esp32-loop-reva/'+s))
cache={}
def stock(lib,name):
    if lib not in cache:
        cache[lib]=parse((LIBROOT/'kicad-symbols'/f'{lib}.kicad_sym').read_text(encoding='utf8'))
    n=copy.deepcopy(next(v for v in children(cache[lib],'symbol') if uq(v[1])==name))
    ext=child(n,'extends')
    if ext:
        base=stock(lib,uq(ext[1])); basename=uq(base[1])
        for v in children(base,'symbol'): v[1]=q(uq(v[1]).replace(basename+'_',name+'_',1))
        props={uq(v[1]):v for v in children(n,'property')}
        base=[v for v in base if not(isinstance(v,list) and v[0]=='property' and uq(v[1]) in props)]
        base.extend(props.values()); base[1]=q(name); n=base
    return n

def pins(n):
    out=[]
    for sub in children(n,'symbol'):
        for p in children(sub,'pin'):
            a=child(p,'at')
            out.append((uq(child(p,'number')[1]),uq(child(p,'name')[1]),p[1],tuple(map(float,a[1:]))))
    return out

SYMS={}; BOM=[]; EXPECTED={}; FPS={}
GLOBALS={'VIN24','GND','V24_PROT','V3V3','SENSOR_PWR','AI_IN','AO_OUT',
         'I2C_SDA','I2C_SCL','AO_ENABLE','AO_FAULT_N','SYS_OK','ADC_RDY'}
ROOT_ID='a269929a-5104-4f3f-907a-1d34fef46421'

def library_symbol(lib,name):
    key=lib+'_'+name
    if key not in SYMS:
        n=stock(lib,name); old=uq(n[1]); n[1]=q(key)
        for s in children(n,'symbol'): s[1]=q(uq(s[1]).replace(old+'_',key+'_',1))
        SYMS[key]=n
    return key

def custom(name, pin_defs, footprint, url):
    # pin_defs = (number, name, electrical type, side); one unit, ordinary IC body.
    groups={s:[p for p in pin_defs if p[3]==s] for s in ('L','R')}
    h=max(len(g) for g in groups.values())*2.54+2.54
    n=parse(f'(symbol {q(name)} (pin_names (offset 0.635)) (in_bom yes) (on_board yes) '
            f'(property "Reference" "U" (at 0 {h/2+5} 0) (effects (font (size 1.27 1.27)))) '
            f'(property "Value" {q(name)} (at 0 {h/2+2} 0) (effects (font (size 1.27 1.27)))) '
            f'(property "Footprint" {q(footprint)} (at 0 0 0) (effects (font (size 1.27 1.27)) hide)) '
            f'(property "Datasheet" {q(url)} (at 0 0 0) (effects (font (size 1.27 1.27)) hide)) '
            f'(symbol {q(name+"_0_1")} (rectangle (start -12.7 {h/2}) (end 12.7 {-h/2}) (stroke (width 0) (type default)) (fill (type background)))) '
            f'(symbol {q(name+"_1_1")}))')
    for side,ps in groups.items():
        for i,(num,pname,typ,_) in enumerate(ps):
            x=-17.78 if side=='L' else 17.78; y=(len(ps)-1)*1.27-i*2.54
            child(n,'symbol')
            n[-1].append(parse(f'(pin {typ} line (at {x} {y} {0 if side=="L" else 180}) (length 5.08) (name {q(pname)} (effects (font (size 1.27 1.27)))) (number {q(num)} (effects (font (size 1.27 1.27)))))'))
    SYMS[name]=n
    return name

def footprint_local(fp):
    if not fp: return ''
    if fp not in FPS:
        lib,name=fp.split(':'); src=LIBROOT/'kicad-footprints'/(lib+'.pretty')/(name+'.kicad_mod')
        if not src.exists(): raise FileNotFoundError(src)
        dest=PROJECT/'libraries/LoopIO.pretty'; dest.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dest/src.name)
        FPS[fp]='LoopIO:'+name
    return FPS[fp]

def fmt(v): return f'{v:.4f}'.rstrip('0').rstrip('.') if v else '0'

class Sheet:
    def __init__(self,name,title,page):
        self.name=name; self.title=title; self.page=page; self.id=ROOT_ID if page==1 else uid(name)
        self.path='/'+ROOT_ID if page==1 else '/'+ROOT_ID+'/'+uid('sheet-'+name)
        self.objects=[]; self.used=set(); self.counter=0;self.terminals=[]
        self.note(15,15,title,2.54)
        self.note(15,22,'ESP32 / 24 V / 4-20 mA     |     Rev A - engineering prototype     |     2026-09-07',1.27)
    def oid(self): self.counter+=1; return uid(self.name+'/'+str(self.counter))
    def note(self,x,y,t,size=1.27):
        self.objects.append(f'(text {q(t)} (at {x} {y} 0) (effects (font (size {size} {size})) (justify left top)) (uuid {self.oid()}))')
    def line(self,x1,y1,x2,y2):
        self.objects.append(f'(polyline (pts (xy {x1} {y1}) (xy {x2} {y2})) (stroke (width 0.254) (type default)) (uuid {self.oid()}))')
    def section(self,x,y,title,desc=''):
        self.note(x,y,title,1.8); self.line(x,y+5,min(x+110,400),y+5)
        if desc:self.note(x,y+8,desc,1.05)
    def wire(self,a,b):
        if a==b:return
        self.objects.append(f'(wire (pts (xy {fmt(a[0])} {fmt(a[1])}) (xy {fmt(b[0])} {fmt(b[1])})) (stroke (width 0) (type default)) (uuid {self.oid()}))')
    def label(self,net,x,y,justify='left'):
        # Global labels link sheet interfaces, ordinary labels stay within their sheet.
        if net in GLOBALS:
            rot=180 if justify=='right' else 0
            self.objects.append(f'(global_label {q(net)} (shape bidirectional) (at {fmt(x)} {fmt(y)} {rot}) (effects (font (size 1.0 1.0)) (justify {justify})) (uuid {self.oid()}) (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {fmt(x)} {fmt(y)} {rot}) (effects (font (size 1 1)) hide)))')
        else:
            self.objects.append(f'(label {q(net)} (at {fmt(x)} {fmt(y)} 0) (effects (font (size 1.0 1.0)) (justify {justify} bottom)) (uuid {self.oid()}))')
    def add(self,ref,key,x,y,nets,value=None,fp=None,angle=0,desc=''):
        x=round(round(x/1.27)*1.27,4);y=round(round(y/1.27)*1.27,4)
        n=SYMS[key]; self.used.add(key); objid=uid(ref)
        props={uq(p[1]):uq(p[2]) for p in children(n,'property')}
        value=value or props.get('Value',key)
        fp=footprint_local(fp if fp is not None else props.get('Footprint',''))
        nn={str(k):v for k,v in nets.items()}
        coords={}; ar=math.radians(angle)
        for num,pname,typ,(px,py,pa) in pins(n):
            xx=x+px*math.cos(ar)-py*math.sin(ar); yy=y-px*math.sin(ar)-py*math.cos(ar)
            coords[num]=(round(xx,4),round(yy,4),round((pa+angle)%360))
        # Every physical pin must be explicitly connected or marked unused.
        assert set(nn)==set(coords),(ref,set(coords)-set(nn),set(nn)-set(coords))
        top=min(v[1] for v in coords.values()); bottom=max(v[1] for v in coords.values())
        passive=ref[0] in 'RCLDF' and len(coords)==2
        px=x+3 if passive and angle==0 and ref[0] in 'RCLF' else x
        py=y-1.5 if passive and angle==0 and ref[0] in 'RCLF' else top-(10 if ref.startswith('U') else 8 if ref.startswith('J') else 5)
        just=' (justify left)' if px!=x else ''
        if ref.startswith('U') and any(v[2]==270 for v in coords.values()):
            px=x-12.7;just=' (justify right)'
        o=f'(symbol (lib_id {q("LoopIO:"+key)}) (at {x} {y} {angle}) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {objid})'
        o+=f'(property "Reference" {q(ref)} (at {px} {py} 0) (effects (font (size 1.27 1.27)){just}))'
        o+=f'(property "Value" {q(value)} (at {px} {py+2.54} 0) (effects (font (size 1.1 1.1)){just}))'
        for pn,pv in [('Footprint',fp),('Datasheet',props.get('Datasheet','')),('Description',desc)]:
            o+=f'(property {q(pn)} {q(pv)} (at {x} {y} 0) (effects (font (size 1 1)) hide))'
        for num in coords: o+=f'(pin {q(num)} (uuid {uid(ref+"/"+num)}))'
        o+=f'(instances (project "chatgpt_astra_test2" (path {q(self.path)} (reference {q(ref)}) (unit 1)))))'
        self.objects.append(o)
        seen={};vertical_groups={}
        for num,(xx,yy,pa) in coords.items():
            net=nn[num]
            if (xx,yy) in seen:
                assert seen[(xx,yy)]==net,(ref,'stacked net mismatch')
                continue
            seen[(xx,yy)]=net
            if net is None:
                self.objects.append(f'(no_connect (at {fmt(xx)} {fmt(yy)}) (uuid {self.oid()}))'); continue
            dx,dy={0:(-6.35,0),180:(6.35,0),90:(0,6.35),270:(0,-6.35)}[pa]
            end=(round(xx+dx,4),round(yy+dy,4));self.wire((xx,yy),end)
            vg=(net,pa,end[1])
            if pa in (90,270) and vg in vertical_groups:
                self.wire(vertical_groups[vg],end)
                self.objects.append(f'(junction (at {fmt(vertical_groups[vg][0])} {fmt(end[1])}) (diameter 0) (color 0 0 0 0) (uuid {self.oid()}))')
                continue
            vertical_groups[vg]=end
            li=len(self.objects)
            self.label(net,*end,'right' if pa in (0,90,270) else 'left')
            self.terminals.append((net,end,pa,li))
        EXPECTED[ref]={'sheet':self.name,'pins':nn,'symbol':key,'footprint':fp}
        if not ref.startswith('#'):BOM.append({'Reference':ref,'Value':value,'Footprint':fp,'Datasheet':props.get('Datasheet',''),'Description':desc})
        return coords
    def save(self):
        # Join adjacent, aligned supply/return branches into visible rails.
        # Reject a rail if another terminal would be shorted by its segment.
        groups={}
        for net,end,pa,li in self.terminals:
            if pa in (90,270) and net in {'GND','V3V3','V24_PROT','VIN_FUSED'}:
                groups.setdefault((net,end[1],pa),[]).append((end[0],li))
        for (net,y,pa),points in groups.items():
            points.sort()
            for (x1,li1),(x2,li2) in zip(points,points[1:]):
                if x2-x1>100 or x2==x1:continue
                if any(n!=net and abs(p[1]-y)<0.01 and x1<=p[0]<=x2 for n,p,_,_ in self.terminals):continue
                self.wire((x1,y),(x2,y));self.objects[li2]=''
                for x in (x1,x2):self.objects.append(f'(junction (at {fmt(x)} {fmt(y)}) (diameter 0) (color 0 0 0 0) (uuid {self.oid()}))')
        ls=[]
        for key in sorted(self.used):
            n=copy.deepcopy(SYMS[key]); n[1]=q('LoopIO:'+key);ls.append(dump(n))
        header=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid {self.id}) (paper "A3") (title_block (title {q(self.title)}) (date "2026-09-07") (rev "A - prototype") (company "ESP32 Loop I/O") (comment 1 "Engineering review required before fabrication")) (lib_symbols {" ".join(ls)})'
        if self.page==1:header+='(sheet_instances (path "/" (page "1")))'
        (PROJECT/(self.name+'.kicad_sch')).write_text(header+'\n'+'\n'.join(self.objects)+'\n(embedded_fonts no))\n',encoding='utf8')

def build():
    def key(lib,name):return library_symbol(lib,name)
    R=key('Device','R'); C=key('Device','C'); D=key('Device','D'); TVS=key('Device','D_TVS'); Z=key('Device','D_Zener')
    L=key('Device','L'); F=key('Device','Fuse'); FLAG=key('power','PWR_FLAG'); TP=key('Connector','TestPoint')
    rfp='Resistor_SMD:R_0805_2012Metric'; cfp='Capacitor_SMD:C_0805_2012Metric'; dfp='Diode_SMD:D_SOD-123'
    def r(s,ref,x,y,val,a,b,fp=rfp):s.add(ref,R,x,y,{'1':a,'2':b},val,fp)
    def c(s,ref,x,y,val,a,b='GND',fp=cfp):s.add(ref,C,x,y,{'1':a,'2':b},val,fp)
    def diode(s,ref,x,y,val,a,k,fp=dfp):s.add(ref,D,x,y,{'1':k,'2':a},val,fp)
    def flag(s,ref,x,y,net):s.add(ref,FLAG,x,y,{'1':net},fp='')
    def tp(s,ref,x,y,net):s.add(ref,TP,x,y,{'1':net},net,'TestPoint:TestPoint_Pad_D1.5mm')
    root=Sheet('chatgpt_astra_test2','01 / SYSTEM INTERFACES',1)
    power=Sheet('power','02 / POWER AND SENSOR SUPPLY',2)
    mcu=Sheet('controller','03 / ESP32 AND USB',3)
    ai=Sheet('analog_input','04 / PROTECTED CURRENT INPUT',4)
    ao=Sheet('analog_output','05 / PRECISION CURRENT OUTPUT',5)
    sheets=[root,power,mcu,ai,ao]
    for s,(x,y) in zip(sheets[1:],[(170,60),(300,60),(170,150),(300,150)]):
        root.objects.append(f'(sheet (at {x} {y}) (size 90 35) (fields_autoplaced yes) (stroke (width 0) (type default)) (fill (color 0 0 0 0)) (uuid {uid("sheet-"+s.name)}) (property "Sheetname" {q(s.title)} (at {x} {y-1} 0) (effects (font (size 1.27 1.27)) (justify left bottom))) (property "Sheetfile" {q(s.name+".kicad_sch")} (at {x} {y+36} 0) (effects (font (size 1.27 1.27)) (justify left top))) (instances (project "chatgpt_astra_test2" (path "/{ROOT_ID}" (page "{s.page}")))))')
    root.section(20,35,'FIELD TERMINALS','All returns and USB ground are common. No galvanic isolation.')
    conn2=key('Connector_Generic','Conn_01x02');conn3=key('Connector_Generic','Conn_01x03')
    tfp='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal'
    root.add('J1',conn2,85,65,{'1':'VIN24','2':'GND'},'18-30 V DC',tfp)
    root.add('J2',conn3,85,110,{'1':'SENSOR_PWR','2':'AI_IN','3':'GND'},'CURRENT INPUT','TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3-5.08_1x03_P5.08mm_Horizontal')
    root.add('J3',conn2,85,155,{'1':'AO_OUT','2':'GND'},'CURRENT OUTPUT',tfp)
    root.note(20,190,'INPUT: two-wire sensor + to J2.1, sensor - to J2.2.\nExternally powered source: signal to J2.2, return to J2.3.\nOUTPUT: passive receiver + to J3.1, receiver - to J3.2.\nDo not connect AO to an actively powered loop input.',1.4)
    root.note(170,108,'VIN24 -> protected 24 V + 3.3 V\nSENSOR_PWR: approximately 40 mA limit',1.27)
    root.note(300,108,'USB-C programming; 24 V board power required\nI2C, output enable and fault monitoring',1.27)
    root.note(170,198,'AI_IN -> limiter -> 100 ohm shunt -> ADC\nNominal range: 4-20 mA; measure 0-25 mA',1.27)
    root.note(300,198,'DAC -> XTR111 -> protected sourcing output\n4-20 mA into 0-500 ohms, including cable',1.27)
    root.note(20,235,'VALIDATION TARGETS\nRoom-temperature accuracy after calibration: +/-16 uA. 10 samples/s.\nBench-check miswire response, startup transients and loop compliance.\nNo IEC surge qualification or temperature accuracy claim at this revision.',1.27)
    flag(root,'#FLG01',125,65,'VIN24');flag(root,'#FLG02',125,90,'GND')

    # Power: TPS26600 PWP pinout; RTN remains distinct from system GND.
    power.section(20,35,'24 V ENTRY / eFUSE','RTN is the internal reference: never short it to system GND.')
    power.add('F1',F,40,65,{'1':'VIN24','2':'VIN_FUSED'},'500mA / >=60V','Fuse:Fuse_1206_3216Metric')
    power.add('D1',TVS,85,65,{'1':'VIN_FUSED','2':'GND'},'SMBJ33CA','Diode_SMD:D_SMB')
    c(power,'C1',125,65,'100n / 100V','VIN_FUSED')
    ef=key('Power_Management','TPS26600PWP')
    power.add('U1',ef,80,125,{'1':'VIN_FUSED','2':'VIN_FUSED','3':'EF_UV','4':None,'5':'EF_OV','6':'EF_RTN','7':'VIN_FUSED','8':'EF_RTN','9':'GND','10':None,'11':'EF_ILIM','12':'EF_DVDT','13':None,'14':None,'15':'V24_PROT','16':'V24_PROT','17':'EF_RTN'},'TPS26600PWPR')
    r(power,'R1',30,185,'130k / 0.1%','VIN_FUSED','EF_UV');r(power,'R2',70,185,'10k / 0.1%','EF_UV','EF_RTN')
    r(power,'R3',110,185,'274k / 0.1%','VIN_FUSED','EF_OV');r(power,'R4',150,185,'10k / 0.1%','EF_OV','EF_RTN')
    r(power,'R5',30,225,'30.1k / 1%','EF_ILIM','EF_RTN');c(power,'C2',80,225,'10n / 50V','EF_DVDT','EF_RTN')
    c(power,'C3',125,225,'22u / 63V','V24_PROT',fp='Capacitor_SMD:C_1210_3225Metric')
    diode(power,'D2',130,145,'SS110','GND','V24_PROT','Diode_SMD:D_SMA')
    power.note(20,250,'UV rising approx. 16.66 V; OV rising approx. 33.80 V.\nCurrent limit approx. 399 mA. Auto-retry current limiting.\nFLT unused: avoids reverse-input coupling into MCU ground.',1.1)
    power.section(180,35,'3.3 V / 1 A BUCK','400 kHz. Short VIN-CIN-PGND loop; minimize switch-node copper.')
    power.add('U2',key('Regulator_Switching','LMR36510ADDA'),225,85,{'1':'GND','2':'V24_PROT','3':'V24_PROT','4':None,'5':'BUCK_FB','6':'BUCK_VCC','7':'BUCK_BOOT','8':'BUCK_SW','9':'GND'},'LMR36510ADDAR')
    power.add('L1',L,300,80,{'1':'BUCK_SW','2':'V3V3'},'22uH / Isat >=2A','Inductor_SMD:L_Bourns_SRN6045TA')
    c(power,'C4',185,130,'2.2u / 100V','V24_PROT',fp='Capacitor_SMD:C_1210_3225Metric')
    c(power,'C5',225,130,'220n / 100V','V24_PROT')
    c(power,'C6',270,130,'100n / 16V','BUCK_BOOT','BUCK_SW');c(power,'C7',320,130,'1u / 16V','BUCK_VCC')
    for ref,x in [('C8',185),('C9',230),('C10',275)]:c(power,ref,x,175,'22u / 10V','V3V3',fp='Capacitor_SMD:C_1206_3216Metric')
    r(power,'R6',320,175,'100k / 0.1%','V3V3','BUCK_FB');r(power,'R7',370,175,'43.2k / 0.1%','BUCK_FB','GND')
    flag(power,'#FLG03',375,80,'V3V3');flag(power,'#FLG04',150,65,'VIN_FUSED')
    power.section(185,205,'SENSOR SUPPLY / 40 mA LIMIT','All LT3092 current returns through its load; no ground branch.')
    lt=custom('LT3092EST', [('3','IN','passive','L'),('1','SET','passive','L'),('2','OUT / TAB','passive','R')], 'Package_TO_SOT_SMD:SOT-223-3_TabPin2','https://www.analog.com/media/en/technical-documentation/data-sheets/lt3092.pdf')
    power.add('U3',lt,220,240,{'3':'V24_PROT','1':'SENS_SET','2':'SENS_RAW'},'LT3092EST#PBF')
    r(power,'R8',285,235,'40.2k / 0.1%','SENS_SET','SENSOR_PWR');r(power,'R9',345,235,'10R / 0.1%','SENS_RAW','SENSOR_PWR')

    # MCU, supervisor, USB and user controls.
    mcu.section(20,35,'ESP32-S3-WROOM-1-N8','No PSRAM. GPIO19/20 reserved for native USB. Antenna keepout required.')
    mod=key('RF_Module','ESP32-S3-WROOM-1'); mn={num:None for num,*_ in pins(SYMS[mod])}
    mn.update({'1':'GND','40':'GND','41':'GND','2':'V3V3','3':'ESP_EN','27':'BOOT_N','12':'I2C_SDA','17':'I2C_SCL','18':'AO_ENABLE','19':'AO_FAULT_N','20':'ADC_RDY','37':'UART_TX','36':'UART_RX','13':'USB_DM_MCU','14':'USB_DP_MCU','21':'LED_STATUS'})
    mcu.add('U4',mod,80,100,mn,'ESP32-S3-WROOM-1-N8')
    c(mcu,'C11',30,165,'10u / 10V','V3V3');c(mcu,'C12',80,165,'100n / 16V','V3V3')
    r(mcu,'R10',30,205,'10k','V3V3','ESP_EN');r(mcu,'R11',80,205,'10k','V3V3','BOOT_N');c(mcu,'C13',130,205,'1u / 10V','ESP_EN')
    sw=key('Switch','SW_Push');swfp='Button_Switch_SMD:SW_SPST_TL3342'
    mcu.add('SW1',sw,35,245,{'1':'ESP_EN','2':'GND'},'RESET',swfp);mcu.add('SW2',sw,100,245,{'1':'BOOT_N','2':'GND'},'BOOT',swfp)
    mcu.section(170,35,'SUPERVISION / I2C / DEBUG','SYS_OK disconnects ADC and inhibits AO below 3.08 V nominal.')
    mcu.add('U5',key('Power_Supervisor','TPS3839DBZ'),215,80,{'1':'GND','2':'SYS_OK','3':'V3V3'},'TPS3839G33DBZR')
    diode(mcu,'D3',275,80,'BAT54W','ESP_EN','SYS_OK')
    c(mcu,'C14',180,125,'100n / 16V','V3V3');r(mcu,'R12',225,125,'4.7k','V3V3','I2C_SDA');r(mcu,'R13',275,125,'4.7k','V3V3','I2C_SCL')
    r(mcu,'R14',180,170,'1k','LED_STATUS','LED_A')
    mcu.add('D4',key('Device','LED'),230,170,{'1':'GND','2':'LED_A'},'GREEN','LED_SMD:LED_0805_2012Metric')
    mcu.add('J5',key('Connector_Generic','Conn_01x04'),280,210,{'1':'GND','2':'UART_TX','3':'UART_RX','4':'V3V3'},'UART / 3.3 V ONLY','Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical')
    mcu.note(170,240,'I2C: ADS1115 0x48; DAC80501 0x49 (A0 tied to VDD).\nBOOT held low during RESET enters ROM download mode.\nSYS_OK is supply supervision, not a firmware watchdog.',1.1)
    mcu.section(310,35,'USB-C / DATA ONLY','No VBUS-to-board power connection.')
    uc=key('Connector','USB_C_Receptacle_USB2.0_16P');un={num:None for num,*_ in pins(SYMS[uc])}
    for num in ['A1','A12','B1','B12','S1']:un[num]='GND'
    for num in ['A4','A9','B4','B9']:un[num]='USB_VBUS'
    for num in ['A6','B6']:un[num]='USB_DP'
    for num in ['A7','B7']:un[num]='USB_DM'
    un.update({'A5':'USB_CC1','B5':'USB_CC2'})
    mcu.add('J4',uc,345,95,un,'USB-C','Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12')
    r(mcu,'R15',330,155,'5.1k / 1%','USB_CC1','GND');r(mcu,'R16',380,155,'5.1k / 1%','USB_CC2','GND')
    mcu.add('U6',key('Power_Protection','USBLC6-2SC6'),350,205,{'1':'USB_DP','6':'USB_DP_ESD','3':'USB_DM','4':'USB_DM_ESD','5':'USB_VBUS','2':'GND'},'USBLC6-2SC6')
    r(mcu,'R17',325,238,'22R','USB_DP_ESD','USB_DP_MCU');r(mcu,'R18',375,238,'22R','USB_DM_ESD','USB_DM_MCU')

    # Input: floating 30 mA limiter, independent clamp, powered-off switch.
    ai.section(20,35,'FIELD INPUT / 30 mA LIMIT','Two-terminal limiter preserves DC loop current through shunt.')
    diode(ai,'D5',40,65,'BAV21W','AI_IN','AI_DIODE')
    r(ai,'R19',105,65,'33R / pulse rated','AI_DIODE','AI_PROT','Resistor_SMD:R_1206_3216Metric')
    ai.add('D6',Z,45,105,{'1':'AI_PROT','2':'GND'},'BZX85C33 / 1.3W','Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal')
    ai.add('U7',lt,90,145,{'3':'AI_PROT','1':'AI_SET','2':'AI_LIMIT_OUT'},'LT3092EST#PBF')
    r(ai,'R20',30,195,'30.1k / 0.1%','AI_SET','AI_SHUNT');r(ai,'R21',100,195,'10R / 0.1%','AI_LIMIT_OUT','AI_SHUNT')
    r(ai,'R22',70,240,'100R / 0.01% / 10ppm','AI_SHUNT','GND','Resistor_SMD:R_1206_3216Metric')
    tp(ai,'TP1',130,240,'AI_SHUNT')
    ai.section(165,35,'ADC FAULT CLAMP / DISCONNECT','3 V shunt clamp is independent of the board supply.')
    r(ai,'R23',185,75,'1k / 0.1%','AI_SHUNT','AI_CLAMP')
    ai.add('U8',key('Reference_Voltage','LM4040DBZ-3'),250,75,{'1':'AI_CLAMP','2':'GND','3':None},'LM4040AIM3-3.0')
    diode(ai,'D7',220,115,'BAT54W','GND','AI_CLAMP')
    mux=custom('TMUX1511PWR',[('1','SEL1','input','L'),('2','S1','passive','L'),('3','D1','passive','R'),('4','SEL2','input','L'),('5','S2','passive','L'),('6','D2','passive','R'),('7','GND','power_in','L'),('8','D3','passive','R'),('9','S3','passive','L'),('10','SEL3','input','L'),('11','D4','passive','R'),('12','S4','passive','L'),('13','SEL4','input','L'),('14','VDD','power_in','R')], 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm','https://www.ti.com/lit/ds/symlink/tmux1511.pdf')
    ai.add('U9',mux,225,170,{'1':'SYS_OK','2':'AI_CLAMP','3':'AI_ADC','4':'GND','5':'GND','6':None,'7':'GND','8':None,'9':'GND','10':'GND','11':None,'12':'GND','13':'GND','14':'V3V3'})
    c(ai,'C15',180,235,'100n / 16V','V3V3');c(ai,'C16',250,235,'100n / 16V','AI_ADC')
    ai.section(300,35,'16-BIT ADC / I2C 0x48','PGA +/-4.096 V; AIN0 single-ended. Average for 10 Hz reporting.')
    ai.add('U10',key('Analog_ADC','ADS1115IDGS'),345,100,{'1':'GND','2':'ADC_RDY','3':'GND','4':'AI_ADC','5':'GND','6':'GND','7':'GND','8':'V3V3','9':'I2C_SDA','10':'I2C_SCL'},'ADS1115IDGSR')
    c(ai,'C17',315,160,'100n / 16V','V3V3');c(ai,'C18',370,160,'1u / 16V','V3V3')
    r(ai,'R24',315,205,'10k','V3V3','ADC_RDY');tp(ai,'TP2',370,205,'AI_ADC')
    ai.note(300,235,'100 ohm: 0.4 V @ 4 mA; 2 V @ 20 mA.\nNominal ADC step: 1.25 uA at +/-4.096 V.\nCalibration includes ADC loading and clamp leakage.\nCheck turn-on surge and clamp recovery on bench.',1.1)

    # DAC and current source. The 3 V XTR regulator keeps OD high with MCU off.
    ao.section(20,35,'16-BIT DAC / I2C 0x49','Zero-scale startup. REF-DIV=1, BUFF-GAIN=1 -> 2.5 V range.')
    dac=custom('DAC80501ZDGS',[('1','VDD','power_in','L'),('2','VOUT','output','R'),('3','NC','no_connect','R'),('4','AGND','power_in','L'),('5','SPI2C','input','L'),('6','SCLK/SCL','input','L'),('7','SYNC/A0','input','L'),('8','SDIN/SDA','bidirectional','L'),('9','NC','no_connect','R'),('10','VREFIO','bidirectional','R')], 'Package_SO:VSSOP-10_3x3mm_P0.5mm','https://www.ti.com/lit/ds/symlink/dac80501.pdf')
    ao.add('U11',dac,80,85,{'1':'V3V3','2':'DAC_RAW','3':None,'4':'GND','5':'V3V3','6':'I2C_SCL','7':'V3V3','8':'I2C_SDA','9':None,'10':'DAC_REF'},'DAC80501ZDGSR')
    c(ao,'C19',30,140,'100n / 16V','V3V3');c(ao,'C20',80,140,'1u / 16V','V3V3');c(ao,'C21',130,140,'100n / 16V','DAC_REF')
    r(ao,'R25',30,190,'1k','DAC_RAW','DAC_FILTER');c(ao,'C22',90,190,'1u / 16V','DAC_FILTER');tp(ao,'TP3',140,190,'DAC_FILTER')
    ao.note(20,225,'Iout = 10 * VIN / RSET. RSET = 1.00 kohm.\n0.4 V -> 4 mA; 2.0 V -> 20 mA.\nFirmware limits normal commands to calibrated 4-20 mA.\nDAC range allows diagnostic current up to 25 mA.',1.2)
    ao.section(170,35,'XTR111 / DEFAULT DISABLED','OD pull-up uses XTR local regulator, independent of MCU power.')
    ao.add('U12',key('Interface_CurrentLoop','XTR111AxDGQ'),220,90,{'1':'V24_PROT','2':'XTR_IS','3':'XTR_GATE','4':'XTR_REG','5':'XTR_REG','6':'DAC_FILTER','7':'XTR_SET','8':'AO_FAULT_N','9':'XTR_OD','10':'GND','11':'GND'},'XTR111AIDGQR')
    c(ao,'C23',180,145,'100n / 50V','V24_PROT');c(ao,'C24',225,145,'1u / 16V','XTR_REG');r(ao,'R26',275,145,'1k / 0.01% / 10ppm','XTR_SET','GND')
    r(ao,'R27',180,195,'10k','XTR_REG','XTR_OD');r(ao,'R28',230,195,'10k','V3V3','AO_FAULT_N')
    nfet=key('Transistor_FET','2N7002')
    ao.add('Q1',nfet,195,245,{'1':'AO_ENABLE','2':'OD_MID','3':'XTR_OD'},'2N7002')
    ao.add('Q2',nfet,265,245,{'1':'SYS_OK','2':'GND','3':'OD_MID'},'2N7002')
    r(ao,'R29',145,245,'100k','AO_ENABLE','GND')
    ao.section(305,35,'OUTPUT PASS STAGE / TERMINAL','100 V P-MOSFET; TO-220 provides prototype thermal margin.')
    ao.add('Q3',key('Transistor_FET','IRF9540N'),345,85,{'1':'XTR_GATE','2':'AO_DRAIN','3':'PMOS_SOURCE'},'IRF9540NPBF')
    r(ao,'R30',320,130,'15R','XTR_IS','PMOS_SOURCE')
    ao.add('Q4',key('Transistor_BJT','MMBT3906'),380,130,{'1':'PMOS_SOURCE','2':'XTR_IS','3':'XTR_GATE'},'MMBT3906')
    r(ao,'R31',320,175,'15R','AO_DRAIN','AO_FILTER')
    c(ao,'C25',380,175,'10n / 100V','AO_FILTER')
    diode(ao,'D8',330,215,'BAV21W','AO_FILTER','AO_OUT')
    ao.add('D9',TVS,380,215,{'1':'AO_OUT','2':'GND'},'SMBJ33CA','Diode_SMD:D_SMB')
    ao.note(305,240,'PNP limit approx. 33-37 mA; not a precision setpoint.\nD8 blocks external positive loop power.\nNegative AO miswire increases MOSFET dissipation.\nVerify SOA, startup glitch and capacitive-load stability.',1.05)

    # Library and metadata are local to the project, no user library edits.
    for s in sheets:s.save()
    libdir=PROJECT/'libraries';libdir.mkdir(exist_ok=True)
    (libdir/'LoopIO.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+'\n'.join(dump(n) for n in SYMS.values())+'\n)\n',encoding='utf8')
    (PROJECT/'sym-lib-table').write_text('(sym_lib_table (lib (name "LoopIO") (type "KiCad") (uri "${KIPRJMOD}/libraries/LoopIO.kicad_sym") (options "") (descr "Project-local symbols; KiCad stock plus datasheet-derived parts")))\n',encoding='utf8')
    (PROJECT/'fp-lib-table').write_text('(fp_lib_table (lib (name "LoopIO") (type "KiCad") (uri "${KIPRJMOD}/libraries/LoopIO.pretty") (options "") (descr "Project-local KiCad footprints")))\n',encoding='utf8')
    out=ROOT/'DOCUMENTATION/schematic_review';out.mkdir(exist_ok=True)
    (out/'connectivity_intent.json').write_text(json.dumps(EXPECTED,indent=2),encoding='utf8')
    (out/'components.json').write_text(json.dumps(BOM,indent=2),encoding='utf8')
    print(f'Generated {len(sheets)} sheets, {len(BOM)} components, {len(FPS)} footprint types.')

if __name__=='__main__': build()
