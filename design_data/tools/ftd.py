import json,glob,os,collections
MODS="D:/SteamLibrary/steamapps/common/From The Depths/From_The_Depths_Data/StreamingAssets/Mods"
_cache=os.path.join(os.path.dirname(__file__),'items.json')
def items():
    if os.path.exists(_cache): return json.load(open(_cache))
    out={}
    for f in glob.glob(MODS+'/**/*.item',recursive=True)+glob.glob(MODS+'/**/*.itemduplicateandmodify',recursive=True):
        try:
            j=json.load(open(f,encoding='utf-8-sig')); c=j['ComponentId']
            si=j.get('SizeInfo') or {}
            out[c['Guid']]={'name':c['Name'],'file':f,'size':si,'weight':j.get('Weight'),'health':j.get('Health'),'ac':j.get('ArmourClass'),'cost':j.get('Cost'),'type':j.get('ItemType'),'code':j.get('Code')}
        except Exception as e: pass
    json.dump(out,open(_cache,'w'))
    return out
IT=items()
def load(p): return json.load(open(p,encoding='utf-8'))
def save(d,p): open(p,'w',encoding='utf-8').write(json.dumps(d,separators=(',',':'),ensure_ascii=False))
def walk(b,path=(),out=None):
    out=[] if out is None else out
    out.append((path,b))
    for i,s in enumerate(b.get('SCs') or []): walk(s,path+(i,),out)
    return out
def blocks(d,b):
    D=d['ItemDictionary']
    for i,(p,r,c,bid) in enumerate(zip(b['BLP'],b['BLR'],b['BCI'],b['BlockIds'])):
        g=D[str(bid)]; x,y,z=map(int,p.split(','))
        yield i,(x,y,z),r,c,bid,g,IT.get(g,{}).get('name',g)
import re
FWD={0:(0,0,1),1:(1,0,0),2:(0,0,-1),3:(-1,0,0),4:(0,-1,0),5:(0,-1,0),6:(0,-1,0),7:(0,-1,0),8:(0,1,0),9:(0,1,0),10:(0,1,0),11:(0,1,0),12:(0,0,1),13:(-1,0,0),14:(0,0,-1),15:(1,0,0),16:(0,0,1),17:(0,0,-1),18:(0,0,1),19:(0,0,-1),20:(1,0,0),21:(-1,0,0),22:(1,0,0),23:(-1,0,0)}
def length(g,name):
    s=IT.get(g,{}).get('size') or {}
    if s.get('SizePos'): return s['SizePos']['z']+1
    m=re.search(r'(\d)m',name)
    if m and re.search(r'beam|slope|offset|corner|wedge|Wedge|transition|Applique',name): return int(m.group(1))
    return 1
def occ(d,b):
    o={}
    for i,(x,y,z),r,c,bid,g,n in blocks(d,b):
        L=length(g,n); f=FWD.get(r,(0,0,1))
        for k in range(L): o[(x+f[0]*k,y+f[1]*k,z+f[2]*k)]=(i,n)
    return o
def weight(g):
    v=IT.get(g); 
    if not v: return 0
    if v['weight'] is not None: return v['weight']
    j=json.load(open(v['file'],encoding='utf-8-sig'))
    base=IT.get(j['IdToDuplicate']['Reference']['Guid'],{}).get('weight') or 0
    return base*j.get('CostWeightHealthScaling',1)*j.get('WeightScaling',1)
def bounds(o):
    xs=[c[0] for c in o]; ys=[c[1] for c in o]; zs=[c[2] for c in o]
    return (min(xs),max(xs)),(min(ys),max(ys)),(min(zs),max(zs))
def inside(o):
    (x0,x1),(y0,y1),(z0,z1)=bounds(o); x0-=1;x1+=1;y0-=1;y1+=1;z0-=1;z1+=1
    out=set(); st=[(x0,y0,z0)]
    while st:
        c=st.pop()
        if c in out or c in o: continue
        x,y,z=c
        if not(x0<=x<=x1 and y0<=y<=y1 and z0<=z<=z1): continue
        out.add(c)
        st+= [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),(x,y,z+1),(x,y,z-1)]
    ins=set((x,y,z) for x in range(x0,x1+1) for y in range(y0,y1+1) for z in range(z0,z1+1) if (x,y,z) not in out and (x,y,z) not in o)
    return ins,out
YAW={0:((1,0,0),(0,1,0),(0,0,1)),1:((0,0,-1),(0,1,0),(1,0,0)),2:((-1,0,0),(0,1,0),(0,0,-1)),3:((0,0,1),(0,1,0),(-1,0,0))}
WARN=set()
def cells_of(g,name,p,r):
    s=(IT.get(g,{}).get('size') or {})
    sn,sp=s.get('SizeNeg'),s.get('SizePos')
    if sn and sp and (sn['x'] or sn['y'] or sp['x'] or sp['y'] or sn['z']):
        if r in YAW:
            R,U,F=YAW[r]; out=[]
            for a in range(-sn['x'],sp['x']+1):
                for u in range(-sn['y'],sp['y']+1):
                    for f in range(-sn['z'],sp['z']+1):
                        out.append((p[0]+R[0]*a+U[0]*u+F[0]*f,p[1]+R[1]*a+U[1]*u+F[1]*f,p[2]+R[2]*a+U[2]*u+F[2]*f))
            return out
        WARN.add((name,r))
    L=length(g,name); f=FWD.get(r,(0,0,1))
    return [(p[0]+f[0]*k,p[1]+f[1]*k,p[2]+f[2]*k) for k in range(L)]
def occ(d,b):
    o={}
    for i,p,r,c,bid,g,n in blocks(d,b):
        for cc in cells_of(g,n,p,r): o[cc]=(i,n)
    return o
