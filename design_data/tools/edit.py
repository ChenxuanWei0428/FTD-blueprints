import sys,json,collections,copy
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ftd
GUID={v['name']:k for k,v in ftd.IT.items()}
DIR2ROT={(0,0,1):0,(1,0,0):1,(0,0,-1):2,(-1,0,0):3,(0,-1,0):4,(0,1,0):8}
def add(a,b): return (a[0]+b[0],a[1]+b[1],a[2]+b[2])
def neg(a): return (-a[0],-a[1],-a[2])
N6=[(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
class B:
    def __init__(s,path):
        s.d=ftd.load(path); s.b=s.d['Blueprint']; s.log=[]
        s.rebuild()
    def rebuild(s):
        s.occ=ftd.occ(s.d,s.b)  # cell -> (idx,name)
    def lid(s,guid):
        D=s.d['ItemDictionary']
        for k,v in D.items():
            if v==guid: return int(k)
        k=max(map(int,D))+1; D[str(k)]=guid; return k
    def name(s,i): return ftd.IT[s.d['ItemDictionary'][str(s.b['BlockIds'][i])]]['name']
    def pos(s,i): return tuple(map(int,s.b['BLP'][i].split(',')))
    def cells(s,i):
        g=s.d['ItemDictionary'][str(s.b['BlockIds'][i])]
        return ftd.cells_of(g,s.name(i),s.pos(i),s.b['BLR'][i])
    def free(s,c): return c not in s.occ
    def _claim(s,i):
        for c in s.cells(i):
            assert c not in s.occ or s.occ[c][0]==i, ('overlap',c,s.occ[c],s.name(i))
            s.occ[c]=(i,s.name(i))
    def _release(s,i):
        for c in s.cells(i):
            if s.occ.get(c,(None,))[0]==i: del s.occ[c]
    def append(s,name,p,rot=0,color=0):
        b=s.b; b['BLP'].append('%d,%d,%d'%p); b['BLR'].append(rot); b['BCI'].append(color); b['BlockIds'].append(s.lid(GUID[name]))
        i=len(b['BLP'])-1; s._claim(i); s.log.append(('add',name,p,rot)); return i
    def move(s,i,p,rot=None):
        s._release(i); s.b['BLP'][i]='%d,%d,%d'%p
        if rot is not None: s.b['BLR'][i]=rot
        s._claim(i); s.log.append(('move',s.name(i),p,rot))
    def retype(s,i,name,p=None,rot=None):
        s._release(i); s.b['BlockIds'][i]=s.lid(GUID[name])
        if p is not None: s.b['BLP'][i]='%d,%d,%d'%p
        if rot is not None: s.b['BLR'][i]=rot
        s._claim(i)
    def carve(s,c,fill_from=None):
        """free cell c occupied by a straight alloy beam / 1m block; returns True"""
        if c not in s.occ: return True
        i,n=s.occ[c]; cs=s.cells(i); k=cs.index(c); r=s.b['BLR'][i]
        mat='Alloy' if n.startswith('Alloy') or 'Light-weight' in n else None
        assert mat and (n.startswith('Alloy beam (') or 'Light-weight' in n), ('cannot carve',c,n)
        def piece(L): return 'Light-weight Alloy Block' if L==1 else 'Alloy beam (%dm)'%L
        left,right=cs[:k],cs[k+1:]
        s._release(i)
        if left: s.retype(i,piece(len(left)),left[0],r)
        if right:
            if left: s.append(piece(len(right)),right[0],r)
            else: s.retype(i,piece(len(right)),right[0],r)
        if not left and not right:
            return i  # caller must move block i somewhere (1m block)
        return None
    def finish(s):
        b=s.b; n=len(b['BLP'])
        assert len(b['BLR'])==len(b['BCI'])==len(b['BlockIds'])==n
        b['BlockCount']=n; b['AliveCount']=n; b['BlockState']='=0,%d'%n
        tot=0
        def T(x):
            t=x['BlockCount']+sum(T(c) for c in (x.get('SCs') or []))
            x['TotalBlockCount']=t; return t
        tot=T(b); s.d['SavedTotalBlockCount']=tot
        allc=[c for c in s.occ]
        xs=[c[0] for c in allc]; ys=[c[1] for c in allc]; zs=[c[2] for c in allc]
        b['MinCords']='%d,%d,%d'%(min(xs),min(ys),min(zs)); b['MaxCords']='%d,%d,%d'%(max(xs),max(ys),max(zs))
