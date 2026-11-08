"""Reusable pieces for generating a ship blueprint (used by yukikaze_build.py / yamato_build.py).

Everything is based on t1_v4.blueprint: root fields, VehicleData, AuthorDetails and its ItemDictionary numbering.
(Load fix 2026-11-08: every construct's ItemNumber, e.g. 740 = 'Vehicle' for the root and the turret block
item for a subconstruct, must be a key of ItemDictionary, otherwise the game throws KeyNotFoundException.)

Typical flow:
    s = Ship('Name')
    shafts = s.steam_shaft(H, prefab, xs, ys, ...)   # plan engines + shaft lines first (they carve the hull)
    s.set_hull(H, bulkheads, decks)                  # shell (26-conn), compartments, air pumps
    s.add_superstructure(cells)
    s.embed_prefab(path, pos, aft)
    s.place(...), s.ai_core(...), s.EXT += [...]
    s.armour_up_to(y) / s.armour_auto(); s.emit(); s.validate(); s.save(path)
"""
import os, sys, copy, json, collections, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftd, edit
from edit import add, neg, N6, DIR2ROT, GUID

HERE = os.path.dirname(os.path.abspath(__file__))
CONSTRUCTABLES = os.path.abspath(os.path.join(HERE, '..', '..'))
MODS = ftd.MODS
TEMPLATE = os.path.join(CONSTRUCTABLES, 't1_v4.blueprint')
N26 = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) != (0, 0, 0)]
LOWER = {k.lower(): k for k in GUID}


def G(n):
    return GUID[n] if n in GUID else GUID[LOWER[n.lower()]]


def shell26(cells):
    return {c for c in cells if any(add(c, d) not in cells for d in N26)}


def name_of(g):
    return ftd.IT.get(g, {}).get('name', g)


class Ship:
    def __init__(self, name, template=TEMPLATE):
        tpl = ftd.load(template)
        self.tpl = tpl
        root = copy.deepcopy(tpl['Blueprint'])
        for k in ('BLP', 'BLR', 'BCI', 'BlockIds', 'SCs', 'BlockStringData', 'BlockStringDataIds'):
            root[k] = []
        root.update(BlockData='', BP1=None, BP2=None, BEI=None, blueprintName=name, Name=None,
                    LocalPosition='0,0,0', LocalRotation='0,0,0,1',
                    ContainedMaterialCost=0.0, designChanged=False)
        self.d = {'FileModelVersion': tpl['FileModelVersion'], 'Name': name, 'Version': tpl['Version'],
                  'SavedTotalBlockCount': 0, 'SavedMaterialCost': 0.0, 'ContainedMaterialCost': 0.0,
                  'ItemDictionary': dict(tpl['ItemDictionary']), 'Blueprint': root}
        self.root = root          # ItemNumber stays t1's 740 ('Vehicle'), which is in the copied dictionary
        e = edit.B.__new__(edit.B)
        e.d = self.d; e.b = root; e.log = []; e.occ = {}
        self.e = e
        self.RES = set()      # interior cells claimed by functional blocks
        self.FUNC = []        # (name, anchor, rot) inside compartments
        self.MECH = []        # (name, anchor, rot) engines / shafts (inside and outside the hull)
        self.EXT = []         # (name, anchor, rot) outside hull / on superstructure; 'PYLON' = HA cube
        self.SUP = set()
        self.VOID = set()     # hull cells taken by machinery (removed from structure and air)
        self.TAKEN = set()    # every cell claimed by planned machinery (inside or outside)
        self.SHAFTS = []
        self.WELLS = set()    # cells carved out of hull / superstructure for sunk turret mechanisms
        self.TURRETS = []     # planned turrets (see plan_turret)
        self.HA = set(); self.ME = set(); self.WL = None; self.HAY = None

    # ---------- dictionary / block emission
    def lid(self, guid):
        D = self.d['ItemDictionary']
        for k, v in D.items():
            if v == guid:
                return int(k)
        k = (max(map(int, D)) + 1) if D else 1
        D[str(k)] = guid
        return k

    def app(self, name, p, rot=0):
        b = self.root
        b['BLP'].append('%d,%d,%d' % p); b['BLR'].append(rot); b['BCI'].append(0)
        b['BlockIds'].append(self.lid(G(name)))
        i = len(b['BLP']) - 1
        self.e._claim(i)
        return i

    def cells_for(self, name, p, r=0):
        return ftd.cells_of(G(name), name, p, r)

    # ---------- steam propulsion (official Core_SteamEngine '*_prop' prefabs, rotated 180 deg so the prop is aft)
    def steam_shaft(self, H, prefab, xs, ys, l_out=(2, 30), max_prop_top=None, z_search=80, keep_lockers=False):
        """Plan one engine + shaft + propeller.  The prefab's own outboard part (shafts, sealed shaft, the hull plate,
        propeller) is rebuilt: the engine sits inside the hull, the shaft runs aft along (x_s, y_s), a sealed shaft
        sits just inside the stern-most hull cell of that line (that hull cell is the seal), then outboard shafts
        and the propeller.  Returns the plan or raises."""
        P = ftd.load(MODS + '/Core_SteamEngine/Assets/' + prefab + '.blueprint')
        D = P['ItemDictionary']
        bl = [(p, r, D[str(bid)]) for i, p, r, c, bid, g, n in ftd.blocks(P, P['Blueprint'])]
        cell_owner = {}
        for k, (p, r, g) in enumerate(bl):
            for c in ftd.cells_of(g, name_of(g), p, r):
                cell_owner[c] = k
        kp = next(k for k, (p, r, g) in enumerate(bl) if name_of(g).lower().endswith('propeller'))
        pp = bl[kp][0]; lx, ly = pp[0], pp[1]
        drop = {kp}; z = pp[2] - 1; shaft_g = sealed_g = None; shaft_r = sealed_r = 0
        while (lx, ly, z) in cell_owner:
            k = cell_owner[(lx, ly, z)]; n = name_of(bl[k][2]).lower()
            if not ('shaft' in n or n == 'metal block'):
                break
            if 'sealed' in n:
                sealed_g, sealed_r = bl[k][2], bl[k][1]
            elif 'shaft' in n and shaft_g is None:
                shaft_g, shaft_r = bl[k][2], bl[k][1]
            drop.add(k); z -= 1
        z_first = z + 1                       # first outboard-line cell (prefab z) after the engine
        for k, (p, r, g) in enumerate(bl):
            n = name_of(g)
            if n == 'Metal Block' or (not keep_lockers and 'Material Storage' in n):
                drop.add(k)
        engine = [bl[k] for k in range(len(bl)) if k not in drop]
        prop_g, prop_r = bl[kp][2], bl[kp][1]
        R = lambda r: ftd.rot_map(r, ftd.yaw180)
        I = H - shell26(H)

        def place_engine(x_s, y_s, z_start):
            out = []; cells = []
            for p, r, g in engine:
                q = (x_s - (p[0] - lx), y_s + (p[1] - ly), z_start - (p[2] - z_first))
                rr = R(r); out.append((name_of(g), q, rr)); cells += ftd.cells_of(g, name_of(g), q, rr)
            return out, cells

        for y_s in ys:
            for x_s in xs:
                line = sorted(c[2] for c in H if c[0] == x_s and c[1] == y_s)
                if not line:
                    continue
                z_out = line[0]
                if (x_s, y_s, z_out + 1) not in H:
                    continue
                # outboard: shafts then propeller, all outside the hull and clear of other machinery
                prop = None
                for L in range(l_out[0], l_out[1] + 1):
                    zs = [z_out - k for k in range(1, L + 1)]
                    zp = z_out - L - 1
                    disk = ftd.cells_of(prop_g, name_of(prop_g), (x_s, y_s, zp), R(prop_r))
                    if max_prop_top is not None and max(c[1] for c in disk) > max_prop_top:
                        break
                    outc = [(x_s, y_s, zz) for zz in zs] + disk
                    if all(c not in H and c not in self.TAKEN for c in outc):
                        prop = (zs, zp, disk); break
                    if any((x_s, y_s, zz) in H for zz in zs):
                        break
                if prop is None:
                    continue
                for z_start in range(z_out + 1, z_out + z_search):
                    inner = [(x_s, y_s, zz) for zz in range(z_out + 1, z_start + 1)]
                    if not all(c in H and c not in self.TAKEN for c in inner):
                        break
                    eng, ecells = place_engine(x_s, y_s, z_start)
                    if all(c in I and c not in self.TAKEN for c in ecells) and len(set(ecells)) == len(ecells) \
                            and not set(ecells) & set(inner):
                        zs, zp, disk = prop
                        blocks = eng + [(name_of(shaft_g), c, R(shaft_r)) for c in inner if c[2] > z_out + 1]
                        blocks.append((name_of(sealed_g), (x_s, y_s, z_out + 1), R(sealed_r)))
                        outb = [(name_of(shaft_g), (x_s, y_s, zz), R(shaft_r)) for zz in zs]
                        outb.append((name_of(prop_g), (x_s, y_s, zp), R(prop_r)))
                        # struts (like the Metal Block next to the shaft in the official 180K design):
                        # heavy-armour columns from the hull bottom down onto long outboard shafts, every 6 m
                        struts = []
                        for zz in zs[3::6]:
                            ys_hull = [yy for yy in range(y_s + 1, y_s + 40) if (x_s, yy, zz) in H]
                            if ys_hull:
                                col = [(x_s, yy, zz) for yy in range(y_s + 1, ys_hull[0])]
                                if col and not any(c in self.TAKEN for c in col):
                                    struts += col
                        self.EXT += [('PYLON', c, 0) for c in struts]
                        self.MECH += blocks + outb
                        self.VOID |= set(ecells) | set(inner)
                        self.TAKEN |= set(ecells) | set(inner) | {(x_s, y_s, zz) for zz in zs} | set(disk) | set(struts)
                        plan = dict(prefab=prefab, line=(x_s, y_s), seal_z=z_out, engine_z=(z_start + 1, max(c[2] for c in ecells)),
                                    prop_z=zp, outboard=len(zs), inboard_shaft=len(inner) - 1,
                                    blocks=len(blocks) + len(outb))
                        self.SHAFTS.append(plan)
                        return plan
        raise RuntimeError('no fit for steam shaft %s at x=%s y=%s' % (prefab, xs, ys))


    # ---------- t1-style propulsion: steam engines feeding the power pool + Huge propellers under the keel
    YAWV = {0: lambda v: v, 90: lambda v: (v[2], v[1], -v[0]), 180: lambda v: (-v[0], v[1], -v[2]),
            270: lambda v: (-v[2], v[1], v[0])}

    def steam_plant(self, H, prefab, n, urange, xs, ys, yaws=(0, 90, 180, 270)):
        """Place n copies of an official Core_SteamEngine power engine (boilers -> pistons -> cranks -> gearbox;
        the gearbox puts power into the vehicle power pool, like t1's electric engines) inside the hull interior.
        The engine room is carved out of the hull (VOID).  Call before set_hull.  Returns the anchors."""
        P = ftd.load(MODS + '/Core_SteamEngine/Assets/' + prefab + '.blueprint')
        D = P['ItemDictionary']
        bl = [(p, r, D[str(bid)]) for i, p, r, c, bid, g, nm in ftd.blocks(P, P['Blueprint'])]
        I = H - shell26(H)
        placed = []
        variants = {}
        for yaw in yaws:
            M = self.YAWV[yaw]; out = []; cells = []
            for p, r, g in bl:
                q = M(p); rr = ftd.rot_map(r, M); out.append((name_of(g), q, rr))
                cells += ftd.cells_of(g, name_of(g), q, rr)
            x0 = min(c[0] for c in cells); x1 = max(c[0] for c in cells)
            y0 = min(c[1] for c in cells); z0 = min(c[2] for c in cells); z1 = max(c[2] for c in cells)
            off = (-(x0 + x1) // 2, -y0, -(z0 + z1) // 2)
            variants[yaw] = ([(nm, add(q, off), rr) for nm, q, rr in out], [add(c, off) for c in cells])
        for u in urange:
            for y in ys:
                for x in xs:
                    for yaw in yaws:
                        blocks, cells = variants[yaw]
                        a = (x, y, -u)
                        wc = [add(c, a) for c in cells]
                        if all(c in I and c not in self.TAKEN for c in wc) and len(set(wc)) == len(wc):
                            self.MECH += [(nm, add(q, a), rr) for nm, q, rr in blocks]
                            self.VOID |= set(wc); self.TAKEN |= set(wc)
                            placed.append(dict(prefab=prefab, anchor=a, yaw=yaw, cells=len(wc)))
                            if len(placed) == n:
                                self.ENGINES = getattr(self, 'ENGINES', []) + placed
                                return placed
        raise RuntimeError('only %d of %d %s fit' % (len(placed), n, prefab))

    def huge_props(self, H, xs, u):
        """t1-style Huge propellers (3x3, facing forward) hanging under the hull bottom at station u; each one
        attaches by its Forwards face to a Metal pylon that goes up to the hull bottom (like t1's)."""
        out = []
        for x in xs:
            zf = -u + 1
            ybx = min(c[1] for c in H if c[0] == x and c[2] == zf)          # hull bottom above the pylon
            yb = min(c[1] for c in H if abs(c[0] - x) <= 1 and c[2] in (zf, -u))  # lowest hull cell near the disk
            yc = yb - 2; p = (x, yc, -u)
            disk = self.cells_for('Huge propeller', p, 0)
            pyl = [(x, yy, zf) for yy in range(yc, ybx)]
            assert not any(c in H or c in self.TAKEN for c in disk + pyl), ('prop clash', x, u)
            self.EXT.append(('Huge propeller', p, 0)); self.EXT += [('PYLON', c, 0) for c in pyl]
            self.TAKEN |= set(disk) | set(pyl); out.append(p)
        self.PROPS = getattr(self, 'PROPS', []) + out
        return out

    def helm(self, urange, xs, ys):
        """Ship's wheel with an Articulated chair behind it, as on t1 (wheel = water-mode vehicle controller)."""
        def chair_ok(p):
            c = (p[0], p[1], p[2] - 1)
            return self.free_air(c) and add(c, (0, -1, 0)) in self.STRUCT | self.RES
        p = self.place("Ship's wheel", urange, ys, xs, need=chair_ok)
        c = (p[0], p[1], p[2] - 1); self.RES.add(c); self.FUNC.append(('Articulated chair', c, 0))
        return p

    def tanks(self, k, near_u, umin, umax, ys, xs, name='Material Storage Tank Large'):
        """k material tanks (APS ammo + boiler fuel) packed into a magazine nearest to station near_u."""
        order = sorted(range(umin, umax + 1), key=lambda u: abs(u - near_u))
        out = []
        for _ in range(k):
            try:
                out.append(self.place(name, order, ys, xs))
            except RuntimeError:
                break
        return out

    # ---------- hull
    def set_hull(self, H, bulkhead_cells=frozenset(), deck_cells=frozenset(), min_pump_comp=8):
        H = set(H) - self.WELLS
        self.H = H
        S = shell26(H)
        I = H - S
        self.S = S - self.VOID
        self.BK = {c for c in I if c in bulkhead_cells} - self.VOID
        self.DK = {c for c in I if c in deck_cells} - self.VOID
        self.STRUCT = self.S | self.BK | self.DK
        self.AIR = I - self.BK - self.DK - self.VOID
        seen = {}; self.comps = []
        for c in self.AIR:
            if c in seen:
                continue
            k = len(self.comps); st = [c]; cs = []; seen[c] = k
            while st:
                x = st.pop(); cs.append(x)
                for dn in N6:
                    n = add(x, dn)
                    if n in self.AIR and n not in seen:
                        seen[n] = k; st.append(n)
            self.comps.append(cs)
        self.PUMPS = []
        for cs in self.comps:
            if len(cs) < min_pump_comp:
                continue
            zs = sorted(c[2] for c in cs); zc = zs[len(zs) // 2]
            cand = sorted([c for c in cs if add(c, (0, -1, 0)) in self.STRUCT],
                          key=lambda c: (abs(c[2] - zc) + abs(c[0]), c[1]))
            if cand:
                self.RES.add(cand[0]); self.PUMPS.append((cand[0], len(cs)))

    def add_superstructure(self, solid, keep=frozenset()):
        solid = set(solid) - self.H - self.WELLS
        self.SUP |= (shell26(solid) | set(keep)) - self.H - self.TAKEN - self.WELLS

    def minH(self, x, z):
        ys = [y for y in range(-40, 80) if (x, y, z) in self.H]
        return min(ys) if ys else None

    # ---------- subconstructs
    OLD_SC_KEYS = ('Id', 'LastAliveBlock', 'IndexOfFirstBlockNeedingFullRepairCost')

    def _remap(self, sc, srcdict):
        """Remap ids into our dictionary and convert the construct to the 4.3.4.1 subconstruct schema that the
        game itself saves (see t1's turrets).  Old prefabs (e.g. 5x5Cobalt, GameVersion 2.5.1) lack
        BlockState / AliveCount / AuthorDetails and carry Id / LastAliveBlock instead."""
        sc['BlockIds'] = [self.lid(srcdict[str(i)]) for i in sc['BlockIds']]
        if sc.get('ItemNumber') is not None and str(sc['ItemNumber']) in srcdict:
            sc['ItemNumber'] = self.lid(srcdict[str(sc['ItemNumber'])])
        n = len(sc['BLP'])
        for k in self.OLD_SC_KEYS:
            sc.pop(k, None)
        sc['BlockCount'] = n
        sc['AliveCount'] = n
        sc['BlockState'] = '0' if n == 1 else '=0,%d' % n
        sc.setdefault('ContainedMaterialCost', 0.0)
        sc.setdefault('AuthorDetails', copy.deepcopy(self.tpl['Blueprint']['AuthorDetails']))
        sc['GameVersion'] = self.tpl['Blueprint']['GameVersion']
        sc['SerialisedInfo'] = {'JsonDictionary': (sc.get('SerialisedInfo') or {}).get('JsonDictionary') or {}, 'IsEmpty': True}
        for s in sc.get('SCs') or []:
            self._remap(s, srcdict)
        def T(x):
            t = x['BlockCount'] + sum(T(c) for c in (x.get('SCs') or []))
            x['TotalBlockCount'] = t; return t
        T(sc)

    YAW_Q = {0: '0,0,0,1', 90: '0,0.7071068,0,0.7071068', 180: '0,1,0,0', 270: '0,-0.7071068,0,0.7071068'}

    @staticmethod
    def yaw_of(aft):
        return {False: 0, True: 180}.get(aft, aft) if isinstance(aft, bool) else int(aft) % 360

    def embed(self, sc_src, srcdict, pos, aft=False):
        """aft: False/True (0/180 deg) or a yaw in degrees 0/90/180/270 (90 = barrels to +x / starboard)."""
        sc = copy.deepcopy(sc_src); self._remap(sc, srcdict)
        sc['LocalPosition'] = '%d,%d,%d' % pos
        sc['LocalRotation'] = self.YAW_Q[self.yaw_of(aft)]
        sc['PersistentBlockIndex'] = -1
        self.root['SCs'].append(sc)
        return sc

    def embed_prefab(self, path, pos, aft=False):
        p = ftd.load(path)
        return self.embed(p['Blueprint'], p['ItemDictionary'], pos, aft)


    # ---------- sunk turrets: everything that loads the gun sits below the deck, inside a well
    _PROFILES = {}

    @classmethod
    def turret_profile(cls, path):
        if path in cls._PROFILES:
            return cls._PROFILES[path]
        d = ftd.load(path); b = d['Blueprint']
        cells = []
        for i, p, r, c, bid, g, n in ftd.blocks(d, b):
            for cc in ftd.cells_of(g, n, p, r):
                cells.append((cc, n))
        fire = [c[1] for c, n in cells if any(k in n.lower() for k in ('firing piece', 'launcher', 'lens'))]
        fy = min(fire) if fire else 1
        load = [c[1] for c, n in cells if c[1] < fy and any(k in n for k in ('loader', 'Clip', 'Feeder', 'Customiser', 'Ammo'))]
        sink = (max(load) + 1) if load else 0          # layers that go below the deck
        rad = collections.defaultdict(float)
        for c, n in cells:
            rad[c[1]] = max(rad[c[1]], math.hypot(c[0], c[2]))
        names = collections.Counter(n for c, n in cells)
        pr = dict(fy=fy, sink=sink, rad=dict(rad), cells=[c for c, n in cells], names=names)
        cls._PROFILES[path] = pr
        return pr

    def plan_turret(self, path, x, z, top, aft=False, tier='', margin=0.5, sink=None):
        """Plan a turret at column (x, z) whose local deck top is y=top.  Its lowest `sink` layers (all ammo
        loaders, clips, feeders, customisers) go into a cylindrical well carved out of the hull / superstructure,
        so only the gun house and barrels stand above the deck.  Call before set_hull / add_superstructure."""
        pr = self.turret_profile(path)
        k = pr['sink'] if sink is None else sink
        ty = top + 1 - k
        well = set()
        for ly in range(k):
            r = pr['rad'].get(ly, 0.0) + margin; R = int(r) + 1
            for dx in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    if math.hypot(dx, dz) <= r:
                        well.add((x + dx, ty + ly, z + dz))
        bad = well & self.TAKEN
        assert not bad, ('turret well hits machinery', path, sorted(bad)[:5])
        self.WELLS |= well; self.TAKEN |= well
        t = dict(path=path, pos=(x, ty, z), aft=aft, tier=tier, well=well, name=os.path.basename(path)[:-10])
        self.TURRETS.append(t)
        return t

    def sc_world_cells(self, t):
        x0, y0, z0 = t['pos']; out = []
        for (x, y, z) in t.get('path_cells') or self.turret_profile(t['path'])['cells']:
            yaw = self.yaw_of(t['aft'])
            dx, dz = {0: (x, z), 90: (z, -x), 180: (-x, -z), 270: (-z, x)}[yaw]
            out.append((x0 + dx, y0 + y, z0 + dz))
        return out

    def _sc_append(self, sc, name, p, rot=0):
        sc['BLP'].append('%d,%d,%d' % p); sc['BLR'].append(rot); sc['BCI'].append(0)
        sc['BlockIds'].append(self.lid(G(name)))
        n = len(sc['BLP']); sc['BlockCount'] = sc['AliveCount'] = n; sc['BlockState'] = '=0,%d' % n
        def T(x):
            t = x['BlockCount'] + sum(T(c) for c in (x.get('SCs') or []))
            x['TotalBlockCount'] = t; return t
        T(sc)

    def mount_turrets(self, laser_targeter=True):
        """Embed every planned turret.  Fire control: each turret carries its own AIO LWC (all chosen prefabs do);
        a Laser Targeter (timed / flak fuse setting) is added on top of any turret that lacks one."""
        for t in self.TURRETS:
            sc = self.embed_prefab(t['path'], t['pos'], t['aft'])
            t['sc'] = sc
            pr = self.turret_profile(t['path'])
            if laser_targeter and not pr['names'].get('Laser Targeter'):
                occ = set(pr['cells']); ytop = max(c[1] for c in occ)
                cand = sorted([c for c in occ if c[1] >= ytop - 1 and (c[0], c[1] + 1, c[2]) not in occ and c[0] != 0],
                              key=lambda c: (-c[1], c[2], abs(c[0])))
                if not cand:
                    cand = sorted([c for c in occ if (c[0], c[1] + 1, c[2]) not in occ], key=lambda c: -c[1])
                c = cand[0]; p = (c[0], c[1] + 1, c[2])
                self._sc_append(sc, 'Laser Targeter', p, 0)
                t['path_cells'] = pr['cells'] + [p]
                t['laser_targeter'] = p
        return self.TURRETS

    # ---------- functional placement inside compartments
    def free_air(self, c):
        return c in self.AIR and c not in self.RES

    def on_floor(self, name, p, r=0):
        cs = self.cells_for(name, p, r); ymin = min(c[1] for c in cs)
        below = self.STRUCT | self.RES | self.VOID
        return any((c[0], ymin - 1, c[2]) in below for c in cs if c[1] == ymin)

    def place(self, name, urange, yrange, xorder, need=None, r=0):
        for u in urange:
            for y in yrange:
                for x in xorder:
                    p = (x, y, -u); cs = self.cells_for(name, p, r)
                    if all(self.free_air(c) for c in cs) and self.on_floor(name, p, r) and (need is None or need(p)):
                        self.RES.update(cs); self.FUNC.append((name, p, r))
                        return p
        raise RuntimeError('no room for ' + name)

    def ai_core(self, urange, xs, y):
        layout = [('AI Mainframe', (0, 0, 0), 0), ('AI Card Slot', (0, 0, 1), 0), ('(CARD) Naval AI', (1, 0, 1), 0),
                  ('Target Prioritisation', (-1, 0, 1), 0), ('AI Card Slot', (0, 0, -1), 0),
                  ('(CARD) Tracker Target Association', (1, 0, -1), 0),
                  ('General Purpose Processing Card', (1, 0, 0), 3), ('General Purpose Processing Card', (-1, 0, 0), 1)]
        for u in urange:
            for x in xs:
                m = (x, y, -u)
                if all(self.free_air(add(m, o)) for _, o, _ in layout) and add(m, (0, -1, 0)) in self.STRUCT:
                    for n, o, r in layout:
                        self.FUNC.append((n, add(m, o), r)); self.RES.add(add(m, o))
                    return m
        raise RuntimeError('no room for AI core')

    def rudder(self, x, u):
        z = -u; self.EXT.append(('Boat Rudder', (x, self.minH(x, z) - 1, z), 0))

    # ---------- mass / buoyancy
    def _sc_mass(self, s):
        D = self.d['ItemDictionary']
        return sum(ftd.weight(D[str(i)]) for i in s['BlockIds']) + sum(self._sc_mass(c) for c in s.get('SCs') or [])

    def fixed_mass(self):
        m = sum(ftd.weight(G(n)) for n, _, _ in self.FUNC + self.MECH) + len(self.PUMPS) * ftd.weight(G('Air Pump'))
        m += sum(ftd.weight(G('Metal Block') if n == 'PYLON' else G(n)) for n, _, _ in self.EXT)
        return m + sum(self._sc_mass(s) for s in self.root['SCs'])

    def waterline(self, mass):
        layer = collections.Counter(c[1] for c in self.H); cum = 0
        for y in range(min(layer), max(layer) + 1):
            if cum + layer[y] >= mass:
                return y - 0.5 + (mass - cum) / layer[y]
            cum += layer[y]
        return None

    def armour_up_to(self, hay, extra=frozenset()):
        """Heavy armour on hull-shell cells with y <= hay (plus extra cells)."""
        w_al = ftd.IT[G('Light-weight Alloy Block')]['weight']; w_ha = ftd.IT[G('Heavy Armour')]['weight']
        self.HA = {c for c in self.S if c[1] <= hay} | set(extra)
        n_struct = len(self.STRUCT) + len(self.SUP)
        self.MASS = self.fixed_mass() + len(self.HA) * w_ha + (n_struct - len(self.HA)) * w_al
        self.WL = self.waterline(self.MASS); self.HAY = hay
        return hay, self.MASS, self.WL

    def armour_auto(self, margin=0.0, extra=frozenset()):
        """Highest HA band that still ends below the resulting waterline (wl >= hay + 0.5 + margin)."""
        best = None
        for hay in range(min(c[1] for c in self.H), max(c[1] for c in self.H) + 1):
            _, m, wl = self.armour_up_to(hay, extra)
            if wl is not None and wl >= hay + 0.5 + margin:
                best = hay
        return self.armour_up_to(best, extra)


    AMMO = ('Material Storage Tank Large', 'Material Storage Tank', 'Ammo Box')

    def armour_scheme(self, well_tiers=None, ammo_ring=True, belt=None, belt_dy=(-2, 1), extra_ha=frozenset(), iters=8,
                      target_wl=None, ballast_layers=3):
        """User material rule (2026-11-08b): light-weight alloy everywhere (all superstructure too), Metal on the
        hull shell below the waterline, heavy armour only around ammunition:
          - hull cells touching the turret wells of `well_tiers` (that is where the loaders / clips are),
          - a one-block HA ring around every ammo / material tank (free air cells around it are filled),
          - optional `belt` (u-range) and `extra_ha`, off by default.  Iterates the waterline."""
        w = lambda n: ftd.IT[G(n)]['weight']
        wal, wme, wha = w('Light-weight Alloy Block'), w('Metal Block'), w(LOWER['heavy armour'])
        W = set()
        for t in self.TURRETS:
            if well_tiers is None or t['tier'] in well_tiers:
                W |= t['well']
        HA0 = {c for c in self.STRUCT if any(add(c, d) in W for d in N26)}
        self.FILL = set(); self.LEAD = set()
        if ammo_ring:
            for n, p, r in self.FUNC:
                if n in self.AMMO:
                    cs = set(self.cells_for(n, p, r))
                    for c in cs:
                        for d in N26:
                            q = add(c, d)
                            if q in cs:
                                continue
                            if q in self.STRUCT:
                                HA0.add(q)
                            elif q in self.AIR and q not in self.RES:
                                self.FILL.add(q)
            self.AIR -= self.FILL; self.RES |= self.FILL
        HA0 |= self.FILL | (set(extra_ha) & self.STRUCT)
        allc = self.STRUCT | self.SUP | self.FILL
        fixed = self.fixed_mass()
        wl = self.waterline(fixed + len(allc) * wal)
        for _ in range(iters):
            HA = set(HA0)
            if belt:
                HA |= {c for c in self.S if belt[0] <= -c[2] <= belt[1] and wl + belt_dy[0] <= c[1] <= wl + belt_dy[1]}
            ME = {c for c in self.S if c[1] < wl} - HA
            mass = fixed + len(HA) * wha + len(ME) * wme + (len(allc) - len(HA) - len(ME)) * wal
            wl = self.waterline(mass)
        if target_wl is not None:
            # keel ballast (Lead Block, "perfect for keels and counter balances"): fill the lowest interior layers,
            # as many cells as needed for the target waterline, centred so that COM z = COB z
            wlead = w('Lead Block')
            sub = [c for c in self.H if c[1] < target_wl]
            cob = sum(c[2] for c in sub) / len(sub)
            ME = {c for c in self.S if c[1] < target_wl} - HA
            base = fixed + len(HA) * wha + len(ME) * wme + (len(allc) - len(HA) - len(ME)) * wal
            need = self.waterline_mass(target_wl) - base
            n = max(0, int(need / (wlead - wal * 0)))
            com = self._com_estimate(HA, ME, allc, wal, wme, wha, fixed, base)
            zl = (cob * (base + n * wlead) - com * base) / max(1e-9, n * wlead) if n else cob
            floor = {}
            for c in self.AIR:
                k = (c[0], c[2]); floor[k] = min(floor.get(k, 99), c[1])
            cand = [c for c in self.AIR if c not in self.RES and c[1] - floor[(c[0], c[2])] < ballast_layers]
            cand.sort(key=lambda c: (abs(c[2] - zl), c[1], abs(c[0])))
            self.LEAD = set(cand[:n]); self.AIR -= self.LEAD; self.RES |= self.LEAD
            mass = base + len(self.LEAD) * wlead; wl = self.waterline(mass)
            self.BALLAST = dict(cells=len(self.LEAD), wanted=n, z_target=round(zl, 1), cob=round(cob, 1))
        self.HA, self.ME, self.MASS, self.WL = HA, ME, mass, wl
        return dict(ha=len(HA), ammo_ring_fill=len(self.FILL), lead=len(self.LEAD), metal=len(ME), alloy=len(allc) - len(HA) - len(ME),
                    mass=round(mass), wl=round(wl, 2))

    def waterline_mass(self, wl):
        layer = collections.Counter(c[1] for c in self.H); m = 0
        for y in range(min(layer), max(layer) + 1):
            if y + 0.5 <= wl:
                m += layer[y]
            elif y - 0.5 < wl:
                m += layer[y] * (wl - (y - 0.5))
        return m

    def _com_estimate(self, HA, ME, allc, wal, wme, wha, fixed, base):
        num = 0.0
        for c in allc:
            num += (wha if c in HA else wme if c in ME else wal) * c[2]
        for n, p, r in self.FUNC + self.MECH:
            num += ftd.weight(G(n)) * p[2]
        for p, _ in self.PUMPS:
            num += ftd.weight(G('Air Pump')) * p[2]
        for n, p, r in self.EXT:
            num += ftd.weight(G('Metal Block') if n == 'PYLON' else G(n)) * p[2]
        for sc in self.root['SCs']:
            num += self._sc_mass(sc) * int(sc['LocalPosition'].split(',')[2])
        return num / base

    # ---------- write blocks
    def emit(self):
        names = {('AL', 1): 'Light-weight Alloy Block', ('HA', 1): LOWER['heavy armour'], ('ME', 1): 'Metal Block'}
        for n in (2, 3, 4):
            names[('AL', n)] = 'Alloy beam (%dm)' % n; names[('HA', n)] = 'Heavy armour beam (%dm)' % n
            names[('ME', n)] = 'Metal beam (%dm)' % n; names[('PB', n)] = 'Lead beam (%dm)' % n
        names[('PB', 1)] = 'Lead Block'
        runs = collections.defaultdict(list)
        for c in self.STRUCT | self.SUP | getattr(self, 'FILL', set()):
            runs[(c[0], c[1], 'HA' if c in self.HA else 'ME' if c in self.ME else 'AL')].append(c[2])
        for c in getattr(self, 'LEAD', set()):
            runs[(c[0], c[1], 'PB')].append(c[2])
        for (x, y, m), zs in runs.items():
            zs.sort(); i = 0
            while i < len(zs):
                j = i
                while j + 1 < len(zs) and zs[j + 1] == zs[j] + 1 and j - i < 3:
                    j += 1
                self.app(names[(m, j - i + 1)], (x, y, zs[i]), 0); i = j + 1
        for p, _ in self.PUMPS:
            self.app('Air Pump', p, 0)
        for n, p, r in self.FUNC + self.MECH:
            self.app(n, p, r)
        for n, p, r in self.EXT:
            self.app('Metal Block' if n == 'PYLON' else n, p, r)
        k = 0
        def pidx(s):
            nonlocal k
            for c in s.get('SCs') or []:
                k += 1; c['PersistentSubObjectIndex'] = k; pidx(c)
        pidx(self.root); self.root['PersistentSubObjectIndex'] = k
        self.e.finish()
        cost = 0.0
        for _, s in ftd.walk(self.root):
            for i in s['BlockIds']:
                g = self.d['ItemDictionary'][str(i)]; it = ftd.IT[g]; c = (it.get('cost') or {}).get('Material')
                if c is None:
                    j = json.load(open(it['file'], encoding='utf-8-sig'))
                    base = ftd.IT[j['IdToDuplicate']['Reference']['Guid']]
                    c = (base.get('cost') or {}).get('Material', 0) * j.get('CostWeightHealthScaling', 1) * j.get('CostScaling', 1)
                cost += c
        self.d['SavedMaterialCost'] = round(cost, 1)

    # ---------- checks
    def check_item_numbers(self):
        D = self.d['ItemDictionary']; bad = []
        for path, s in ftd.walk(self.root):
            if str(s.get('ItemNumber')) not in D:
                bad.append((path, s.get('ItemNumber')))
            for i in s['BlockIds']:
                if str(i) not in D:
                    bad.append((path, 'block id', i))
        return bad

    def validate(self):
        e = self.e; cells = set(e.occ)
        start = min(cells, key=lambda c: (c[1], abs(c[0]), abs(c[2])))
        start = next(iter(self.S))
        seen = {start}; st = [start]
        while st:
            c = st.pop()
            for dn in N6:
                n = add(c, dn)
                if n in cells and n not in seen:
                    seen.add(n); st.append(n)
        detached = collections.Counter(e.occ[c][1] for c in cells - seen)
        ins, out = ftd.inside(e.occ)
        leaks = sum(1 for c in self.AIR if c in out)
        support = {}
        for s in self.root['SCs']:
            p = tuple(map(int, s['LocalPosition'].split(',')))
            support[(s['blueprintName'], p)] = (e.occ.get(add(p, (0, -1, 0)), (0, None))[1], e.occ.get(p, (0, None))[1])
        num = den = 0
        for c, (i, n) in e.occ.items():
            w = ftd.weight(self.d['ItemDictionary'][str(self.root['BlockIds'][i])]) / max(1, len(e.cells(i)))
            num += w * c[2]; den += w
        for sc in self.root['SCs']:                      # turrets at their mounts
            w = self._sc_mass(sc); num += w * int(sc['LocalPosition'].split(',')[2]); den += w
        sub = [c for c in self.H if c[1] < self.WL]
        # turret checks: SC blocks vs hull blocks and vs each other; well walls closed
        sc_cells = {}; sc_overlap = collections.Counter(); hull_overlap = collections.Counter()
        for t in self.TURRETS:
            key = t['name'] + str(t['pos'])
            for c in self.sc_world_cells(t):
                if c in sc_cells and sc_cells[c] != key:
                    sc_overlap[(sc_cells[c], key)] += 1
                sc_cells[c] = key
                if c in e.occ:
                    hull_overlap[(key, e.occ[c][1])] += 1
        open_wells = []
        for t in self.TURRETS:
            for c in t['well']:
                for dn in N6:
                    n = add(c, dn)
                    if dn != (0, 1, 0) and n not in self.WELLS and n not in e.occ:
                        open_wells.append((t['name'], t['pos'], n)); break
        mats = collections.Counter('HA' if c in self.HA else 'ME' if c in self.ME else 'AL' for c in self.STRUCT | self.SUP | getattr(self, 'FILL', set()))
        tiers = collections.Counter(t['tier'] + ':' + t['name'] for t in self.TURRETS)
        return dict(blocks=self.root['BlockCount'], total=self.d['SavedTotalBlockCount'], detached=dict(detached),
                    leaks=leaks, support=support, mass=round(self.MASS), waterline=round(self.WL, 2),
                    materials=dict(mats), turrets=dict(tiers), sc_overlap=dict(sc_overlap), sc_hull_overlap=dict(hull_overlap),
                    open_wells=open_wells[:10], n_open_wells=len(open_wells), com_z=round(num / den, 1), cob_z=round(sum(c[2] for c in sub) / len(sub), 1),
                    cost=self.d['SavedMaterialCost'], compartments=len(self.comps), pumps=len(self.PUMPS),
                    max_compartment=max(n for _, n in self.PUMPS), item_number_problems=self.check_item_numbers(),
                    shafts=self.SHAFTS)

    def save(self, path):
        ftd.save(self.d, path)
