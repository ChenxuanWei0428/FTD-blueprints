import sys,copy,json,collections,math
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ftd,edit,yamato_hull as Y
from edit import add,neg,N6,DIR2ROT,GUID
ASSETS="D:/SteamLibrary/steamapps/common/From The Depths/From_The_Depths_Data/StreamingAssets/Mods/Core_APS/Assets/"
TPL=ftd.load(r'C:/Users/chenx/Documents/From The Depths/Player Profiles/Austin/Constructables/t1_v4.blueprint')
LOWER={k.lower():k for k in GUID}
def G(n): return GUID[n] if n in GUID else GUID[LOWER[n.lower()]]
# ---------- empty vehicle from template
root=copy.deepcopy(TPL['Blueprint'])
for k in ('BLP','BLR','BCI','BlockIds','SCs','BlockStringData','BlockStringDataIds'): root[k]=[]
root.update(BlockData='',BP1=None,BP2=None,BEI=None,blueprintName='Yamato',Name=None,LocalPosition='0,0,0',LocalRotation='0,0,0,1',PersistentBlockIndex=-1,ContainedMaterialCost=0.0,designChanged=False)
d={'FileModelVersion':TPL['FileModelVersion'],'Name':'Yamato','Version':TPL['Version'],'SavedTotalBlockCount':0,'SavedMaterialCost':0.0,'ContainedMaterialCost':0.0,'ItemDictionary':{},'Blueprint':root}
e=edit.B.__new__(edit.B); e.d=d; e.b=root; e.log=[]; e.occ={}
def lid(guid):
    D=d['ItemDictionary']
    for k,v in D.items():
        if v==guid: return int(k)
    k=(max(map(int,D))+1) if D else 1; D[str(k)]=guid; return k
e.lid=lid
_append=e.append
def app(name,p,rot=0,color=0):
    b=root; b['BLP'].append('%d,%d,%d'%p); b['BLR'].append(rot); b['BCI'].append(color); b['BlockIds'].append(lid(G(name)))
    i=len(b['BLP'])-1; e._claim(i); return i
e.append=app
# ---------- geometry
H=Y.solid()
N26=[(a,b_,c_) for a in (-1,0,1) for b_ in (-1,0,1) for c_ in (-1,0,1) if (a,b_,c_)!=(0,0,0)]
S={c for c in H if any(add(c,dn) not in H for dn in N26)}
I=H-S
U=lambda c:-c[2]
BK={c for c in I if U(c)%8==0 and 16<=U(c)<=256}
DK={c for c in I if c[1]==-1}
STRUCT=S|BK|DK
AIR=I-BK-DK
# superstructure solids
def box(u0,u1,x,y0,y1): return {(xx,yy,-u) for u in range(u0,u1+1) for xx in range(-x,x+1) for yy in range(y0,y1+1)}
SUPS=set()
SUPS|=box(104,114,6,9,23)                      # secondary-1 platform (superfires over turret 2)
SUPS|=box(114,134,7,9,20)|box(116,132,5,21,30)|box(118,128,4,31,38)|box(119,126,3,39,42)
SUPS|=box(121,123,9,41,42)                     # rangefinder
for y in range(9,29):
    sh=(y-9)//4; SUPS|={(x,y,-u) for u in range(140+sh,153+sh) for x in range(-4,5)}
SUPS|=box(156,170,6,9,14)
# sponsons for the upper 12.7cm HA mounts (two-level stagger like the 1945 refit)
HA_LOW=[(sx*13,9,-u) for u in (124,138,152) for sx in (1,-1)]
HA_UP=[(sx*10,17,-u) for u in (131,145,159) for sx in (1,-1)]
for (x,y,z) in HA_UP:
    SUPS|={(xx,yy,z+dz) for xx in range(min(x-2,x+2),max(x-2,x+2)+1) for yy in range(9,17) for dz in range(-2,3)}
def barbette(u,y0,y1,r=4.5):
    return {(x,y,-uu) for uu in range(u-5,u+6) for x in range(-5,6) for y in range(y0,y1+1) if math.hypot(x,uu-u)<=r}
BARB=barbette(92,9,13)|barbette(176,9,17)
SUPS-=H
SUP_SHELL={c for c in SUPS if any(add(c,dn) not in SUPS for dn in N26) or c[1]==9}
SUP_SHELL|={c for c in SUPS if c[1]==9}
BARB_SHELL={c for c in BARB if any(add(c,dn) not in BARB for dn in N26)}|{(0,y,-92) for y in range(9,14)}|{(0,y,-176) for y in range(9,18)}
SUP_SHELL|=BARB_SHELL
SUP_SHELL|={(0,y,-162) for y in range(15,33)}   # mainmast
for c in list(SUP_SHELL):
    if c in H: SUP_SHELL.discard(c)
# ---------- compartments + air pumps
comp_of={}; comps=[]
for c in AIR:
    if c in comp_of: continue
    k=len(comps); st=[c]; cs=[]
    comp_of[c]=k
    while st:
        x=st.pop(); cs.append(x)
        for dn in N6:
            n=add(x,dn)
            if n in AIR and n not in comp_of: comp_of[n]=k; st.append(n)
    comps.append(cs)
RES=set()       # air cells reserved for functional blocks
PUMPS=[]
for cs in comps:
    zs=sorted(c[2] for c in cs); zc=zs[len(zs)//2]; ymin=min(c[1] for c in cs)
    cand=sorted([c for c in cs if add(c,(0,-1,0)) in STRUCT],key=lambda c:(abs(c[2]-zc)+abs(c[0]),c[1]))
    p=cand[0]; RES.add(p); PUMPS.append((p,len(cs)))
# ---------- subconstructs
def remap(sc,srcdict):
    sc['BlockIds']=[lid(srcdict[str(i)]) for i in sc['BlockIds']]
    for s in sc.get('SCs') or []: remap(s,srcdict)
def embed(sc_src,srcdict,pos,facing_aft=False):
    sc=copy.deepcopy(sc_src); remap(sc,srcdict)
    sc['LocalPosition']='%d,%d,%d'%pos; sc['LocalRotation']='0,1,0,0' if facing_aft else '0,0,0,1'
    root['SCs'].append(sc); return sc
CIT=ftd.load(ASSETS+'9x9Citrin.blueprint')
COP=TPL['Blueprint']['SCs'][0]; LAS_SC=TPL['Blueprint']['SCs'][1]
MAIN=[('Main turret 1',CIT,(0,9,-72),False),('Main turret 2',CIT,(0,14,-92),False),('Main turret 3',CIT,(0,9,-192),True)]
MAMBA=ftd.load(ASSETS+'Mamba.blueprint'); COBALT=ftd.load(ASSETS+'5x5Cobalt.blueprint')
SEC=[('15.5cm triple 1',(0,24,-108),False),('15.5cm triple 2',(0,18,-176),True)]
TURRETS=[]
for n,p,pos,aft in MAIN: embed(p['Blueprint'],p['ItemDictionary'],pos,aft); TURRETS.append((n,pos))
for n,pos,aft in SEC: embed(MAMBA['Blueprint'],MAMBA['ItemDictionary'],pos,aft); TURRETS.append((n,pos))
for pos in HA_LOW+HA_UP: embed(COBALT['Blueprint'],COBALT['ItemDictionary'],pos); TURRETS.append(('12.7cm twin HA',pos))
# ---------- lasers (recessed like the user's t1 front pair)
LASER_POS=[]   # historical refit: no lasers
for p in LASER_POS: RES|={p,add(p,(0,1,0))}
def okc(c,used): return c in AIR and c not in RES and c not in used
def layout(Tn,used,foreign,ncav=3):
    best=None
    for d1 in N6:
        M=add(Tn,d1)
        if not okc(M,used): continue
        for d2 in N6:
            C=add(M,d2)
            if C==Tn or not okc(C,used): continue
            for d3 in N6:
                if d3==neg(d2): continue
                V=[add(C,tuple(a*k for a in d3)) for k in range(1,ncav+1)]
                if not all(okc(v,used) for v in V) or Tn in V or M in V: continue
                core=[M,C]+V
                if any(add(c,dn) in foreign for c in core for dn in N6): continue
                taken=set(core)|{Tn}; P=[]
                for v in V:
                    for p in [dn for dn in N6 if dn not in (d3,neg(d3))]:
                        c=add(v,p)
                        if c not in taken and okc(c,used): P.append((c,v)); taken.add(c)
                if best is None or len(P)>len(best[4]): best=(M,C,d3,V,P)
    return best
used=set(); foreign=set(); LASERS=[]
for p in LASER_POS:
    Tn=add(p,(0,-1,0)); assert okc(Tn,used)
    M,C,d3,V,P=layout(Tn,used,foreign)
    blk=[('Laser Transceiver',Tn,0),('Multipurpose Laser',M,0),('Laser Coupler',C,0)]+[('Laser Cavity',v,DIR2ROT[neg(d3)]) for v in V]
    blk+=[('Laser Pump',c,DIR2ROT[(v[0]-c[0],v[1]-c[1],v[2]-c[2])]) for c,v in P]
    for n,c,r in blk: RES.add(c)
    # support pillar: straight down from a core block to the structure below
    pillar=None
    for n,c,r in blk:
        if n=='Laser Pump': continue
        col=[]; q=add(c,(0,-1,0))
        while q in AIR and q not in RES: col.append(q); q=add(q,(0,-1,0))
        if q in STRUCT and (pillar is None or len(col)<len(pillar)): pillar=col
    assert pillar is not None,('no pillar',p)
    for q in pillar: RES.add(q); blk.append(('Light-weight Alloy Block',q,0))
    used|={c for _,c,_ in blk}; foreign|={Tn,M,C,*V}
    LASERS.append((p,blk)); embed(LAS_SC,TPL['ItemDictionary'],p)
NPUMPS=sum(sum(1 for n,_,_ in blk if n=='Laser Pump') for _,blk in LASERS)
# ---------- functional blocks inside compartments (searched placement)
FUNC=[]   # (name,anchor,rot)
def cells_for(name,p,r=0): return ftd.cells_of(G(name),name,p,r)
def place(name,urange,yrange,xorder,need=None,r=0):
    for u in urange:
        for y in yrange:
            for x in xorder:
                p=(x,y,-u); cs=cells_for(name,p,r)
                if all(c in AIR and c not in RES for c in cs) and (need is None or need(p)):
                    RES.update(cs); FUNC.append((name,p,r)); return p
    raise RuntimeError('no room for '+name)
def on_floor(name):
    def f(p):
        cs=cells_for(name,p); ymin=min(c[1] for c in cs)
        return any((c[0],ymin-1,c[2]) in STRUCT or (c[0],ymin-1,c[2]) in RES for c in cs if c[1]==ymin)
    return f
# AI core deep amidships: mainframe, 2 card slots (cards on their left/right), 3 GPP cards
AI_LAYOUT=[('AI Mainframe',(0,0,0),0),('AI Card Slot',(0,0,1),0),('(CARD) Naval AI',(1,0,1),0),('Target Prioritisation',(-1,0,1),0),
           ('AI Card Slot',(0,0,-1),0),('(CARD) Tracker Target Association',(1,0,-1),0),
           ('General Purpose Processing Card',(1,0,0),3),('General Purpose Processing Card',(-1,0,0),1),('General Purpose Processing Card',(0,1,0),4)]
def ai_fit(p):
    return all(add(p,o) in AIR and add(p,o) not in RES for _,o,_ in AI_LAYOUT) and add(p,(0,-1,0)) in STRUCT
mf=None
for u in range(116,124):
    for x in (3,4,5,6,-3):
        if ai_fit((x,-10,-u)): mf=(x,-10,-u); break
    if mf: break
assert mf,'no room for AI core'
for n,o,r in AI_LAYOUT: FUNC.append((n,add(mf,o),r)); RES.add(add(mf,o))
# power plant: 12 RTG + 6 battery/engine pairs, engine rooms u 130-170
POWER=collections.defaultdict(list)
for _ in range(8): POWER['RTG'].append(place('RTG (3x3m)',range(129,172),range(-10,-3),[-12,-8,-4,4,8,12,0],need=on_floor('RTG (3x3m)')))
def eng_ok(p):
    q=(p[0]+2,p[1],p[2]); return q in AIR and q not in RES
for _ in range(4):
    p=place('Battery Storage Large',range(129,172),range(-10,-1),[-10,-6,-2,2,6,10],need=lambda p:eng_ok(p) and on_floor('Battery Storage Large')(p))
    q=(p[0]+2,p[1],p[2]); FUNC.append(('Electric Engine',q,0)); RES.add(q); POWER['Battery'].append(p)
# material storage near the magazines
for _ in range(8): place('Material Storage Tank Large',list(range(62,100))+list(range(182,205)),range(-10,-4),[-6,-3,0,3,6],need=on_floor('Material Storage Tank Large'))
# ---------- propulsion (outside the hull)
EXT=[]  # (name,anchor,rot) outside hull
def minH(x,z):
    ys=[y for y in range(-12,15) if (x,y,z) in H]; return min(ys) if ys else None
for x in (-12,-5,5,12):
    zf=-239; zp=-240
    yc=min(minH(x+dx,zp) for dx in (-1,0,1))-4
    EXT.append(('Huge propeller',(x,yc,zp),0))
    for y in range(yc,minH(x,zf)): EXT.append(('PYLON',(x,y,zf),0))
for x in (-4,4):
    z=-252; EXT.append(('Boat Rudder',(x,minH(x,z)-1,z),0))
# fire control: main director on the tower top, aft director, radars (Type 21 / Type 13 analogues)
EXT+=[('Range Finder (9m)',(0,43,-122),0),            # main 15 m rangefinder analogue (spans x -4..4)
      ('Telescope Camera Gimbal Tracker',(2,44,-120),0),('Laser Range finder Tracker',(-2,43,-120),0),
      ('Radar Gimbal Tracker',(0,43,-125),0),('Radar 360',(2,43,-125),0),('Camera 360',(-2,43,-125),0),
      ('IR Camera 360',(0,43,-119),0),
      ('Range Finder (7m)',(0,15,-160),0),               # aft director on the aft superstructure
      ('Radar 360',(0,33,-162),0)]                       # mainmast top
# ---------- armour height from buoyancy (≈1 buoyancy per submerged m³, as calibrated on t1)
W_AL=ftd.IT[G('Light-weight Alloy Block')]['weight']; W_HA=ftd.IT[G('Heavy Armour')]['weight']
def sc_mass(s,D):
    m=sum(ftd.weight(D[str(i)]) for i in s['BlockIds'])
    return m+sum(sc_mass(c,D) for c in s.get('SCs') or [])
FIXED=sum(ftd.weight(G(n)) for n,_,_ in FUNC)+sum(ftd.weight(G(n)) for _,blk in LASERS for n,_,_ in blk)+len(PUMPS)*ftd.weight(G('Air Pump'))
FIXED+=sum(ftd.weight(G(n)) for n,_,_ in EXT if n!='PYLON')
FIXED+=sum(sc_mass(s,d['ItemDictionary']) for s in root['SCs'])
LAYER=collections.Counter(c[1] for c in H)
def waterline(mass):
    cum=0
    for y in range(-12,16):
        if cum+LAYER[y]>=mass: return y-0.5+(mass-cum)/LAYER[y]
        cum+=LAYER[y]
def total_mass(hay):
    ha=sum(1 for c in S if c[1]<=hay)
    al=len(STRUCT)-ha+len(SUP_SHELL)
    return FIXED+ha*W_HA+al*W_AL+sum(W_HA for n,_,_ in EXT if n=='PYLON')
HA_CELLS=set(S)|BARB_SHELL
def total_mass2():
    return FIXED+len(HA_CELLS)*W_HA+(len(STRUCT)+len(SUP_SHELL)-len(HA_CELLS))*W_AL+sum(W_HA for n,_,_ in EXT if n=='PYLON')
MASS=total_mass2(); WL=waterline(MASS)
# ---------- emit blocks
NAMES={('AL',1):'Light-weight Alloy Block',('HA',1):LOWER['heavy armour']}
for n in (2,3,4): NAMES[('AL',n)]='Alloy beam (%dm)'%n; NAMES[('HA',n)]='Heavy armour beam (%dm)'%n
runs=collections.defaultdict(list)
for c in STRUCT|SUP_SHELL:
    runs[(c[0],c[1],'HA' if c in HA_CELLS else 'AL')].append(c[2])
for (x,y,m),zs in runs.items():
    zs.sort(); i=0
    while i<len(zs):
        j=i
        while j+1<len(zs) and zs[j+1]==zs[j]+1 and j-i<3: j+=1
        app(NAMES[(m,j-i+1)],(x,y,zs[i]),0); i=j+1
for p,_ in PUMPS: app('Air Pump',p,0)
for n,p,r in FUNC: app(n,p,r)
for _,blk in LASERS:
    for n,p,r in blk: app(n,p,r)
for n,p,r in EXT: app(LOWER['heavy armour'] if n=='PYLON' else n,p,r)
# persistent indices
k=0
def pidx(s):
    global k
    for c in s.get('SCs') or []:
        k+=1; c['PersistentSubObjectIndex']=k; pidx(c)
pidx(root); root['PersistentSubObjectIndex']=k
e.finish()
cost=0.0
for p_,s in ftd.walk(root):
    for i in s['BlockIds']:
        g=d['ItemDictionary'][str(i)]; it=ftd.IT[g]; c=(it.get('cost') or {}).get('Material')
        if c is None:
            j=json.load(open(it['file'],encoding='utf-8-sig')); base=ftd.IT[j['IdToDuplicate']['Reference']['Guid']]
            c=(base.get('cost') or {}).get('Material',0)*j.get('CostWeightHealthScaling',1)*j.get('CostScaling',1)
        cost+=c
d['SavedMaterialCost']=round(cost,1)
# ---------- validation
cells=set(e.occ); start=(0,-11,-100); seen={start}; st=[start]
while st:
    c=st.pop()
    for dn in N6:
        n=add(c,dn)
        if n in cells and n not in seen: seen.add(n); st.append(n)
DETACHED=collections.Counter(e.occ[c][1] for c in cells-seen)
ins,out=ftd.inside(e.occ)
LEAK=sum(1 for c in AIR if c in out)
SUPPORT={}
for s in root['SCs']:
    p=tuple(map(int,s['LocalPosition'].split(','))); SUPPORT[p]=(e.occ.get(add(p,(0,-1,0)),(0,None))[1], e.occ.get(p,(0,None))[1])
num=0;den=0
for c,(i,n) in e.occ.items():
    w=ftd.weight(d['ItemDictionary'][str(root['BlockIds'][i])])/max(1,len(e.cells(i))); num+=w*c[2]; den+=w
COMZ=num/den
sub=[c for c in H if c[1]<WL]; COBZ=sum(c[2] for c in sub)/len(sub)

if __name__=='__main__':
    out=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','Yamato.blueprint')
    ftd.save(d,out)
    print('saved',out,'blocks',root['BlockCount'],'detached',dict(DETACHED),'leaks',LEAK,'WL',round(WL,2),'mass',round(MASS))
