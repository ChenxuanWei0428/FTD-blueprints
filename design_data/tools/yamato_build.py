"""Yamato (1945 fit), 1 block = 1 m.  Run: python -I design_data/tools/yamato_build.py
Based on t1_v4 via shipgen.Ship (root fields + ItemDictionary numbering, which fixes the load error).
Hull from yamato_hull.py: bow z=+2, stern z=-262 (u = -z), keel y=-11, main deck y=8.
Three gun tiers, every turret self-contained (AIO LWC on the turret) and with fire control
(laser targeter on each turret + hull directors / radars / AI); all loaders sunk into wells in the hull:
  main      3 x user '203mm CA Main Gun A' triple (46cm analogue), T2 superfiring on a barbette
  secondary 8 x official Severance (2 centreline superfiring like the 15.5cm triples, 6 on the beam like the 12.7cm HA)
  AA        38 x official Firecracker (25mm analogue), on deck edges, the deckhouse roof and the tower base
Materials: light-weight alloy, Metal below the waterline, heavy armour at barbettes / wells and the belt.
Propulsion like t1: 6 x official 'Goliath Serial Engine' steam engines (gearbox -> power pool), 6 Huge propellers
under the keel on Metal pylons, Ship's wheel + chair, 2 rudders, ~86 material tanks (APS ammo + boiler fuel)."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftd, yamato_hull as Y
from shipgen import Ship, CONSTRUCTABLES, MODS, shell26

H = Y.solid()
U = lambda c: -c[2]
s = Ship('Yamato')

def box(u0, u1, x, y0, y1): return {(xx, yy, -u) for u in range(u0, u1 + 1) for xx in range(-x, x + 1) for yy in range(y0, y1 + 1)}
def barbette(u, y0, y1, r):
    R = int(r) + 1
    return {(x, y, -uu) for uu in range(u - R, u + R + 1) for x in range(-R, R + 1) for y in range(y0, y1 + 1) if math.hypot(x, uu - u) <= r}

# ---------- superstructure solids (needed first: some turrets sink into them)
SUPS = set()
B1 = box(101, 115, 6, 9, 23)                         # secondary-1 platform (superfires over turret 2)
TOWER = box(112, 136, 10, 9, 20) | box(116, 132, 5, 21, 30) | box(118, 128, 4, 31, 38) | box(119, 126, 3, 39, 42)
ARMS = box(121, 123, 9, 41, 42)                      # rangefinder arms
FUNNEL = set()
for y in range(9, 29):
    sh = (y - 9) // 4; FUNNEL |= {(x, y, -u) for u in range(140 + sh, 153 + sh) for x in range(-4, 5)}
DECKHOUSE = box(137, 174, 9, 9, 16)
BARB2 = barbette(92, 9, 13, 8.5)                     # turret 2 barbette
BARB_S2 = barbette(176, 9, 17, 5.5)                  # aft secondary barbette
SUPS = B1 | TOWER | ARMS | FUNNEL | DECKHOUSE | BARB2 | BARB_S2
ALL = H | SUPS
top = lambda x, u: max(c[1] for c in ALL if c[0] == x and c[2] == -u)

# ---------- armament (planned before machinery so the wells are reserved)
APS = MODS + '/Core_APS/Assets/'
GUN = os.path.join(CONSTRUCTABLES, 'gun', '203mm CA Main Gun A.blueprint')
SEC = APS + 'Severance.blueprint'
AA = APS + 'Firecracker.blueprint'
for u, aft in ((72, False), (92, False), (192, True)):
    s.plan_turret(GUN, 0, -u, top(0, u), aft=aft, tier='main')
s.plan_turret(SEC, 0, -108, top(0, 108), tier='secondary')
s.plan_turret(SEC, 0, -176, top(0, 176), aft=True, tier='secondary')
for u in (120, 138, 156):
    for x in (-14, 14):
        s.plan_turret(SEC, x, -u, top(x, u), aft=(u == 156), tier='secondary')
for x in (-14, 14):                                                          # beam guns between T1 and T2
    s.plan_turret(SEC, x, -80, top(x, 80), tier='secondary')
for x in (-9, 9):                                                            # forecastle pair
    s.plan_turret(SEC, x, -30, top(x, 30), tier='secondary')
for x in (-7, 7):                                                            # quarterdeck pair, facing aft
    s.plan_turret(SEC, x, -246, top(x, 246), aft=True, tier='secondary')
OUT = lambda sx: 90 if sx > 0 else 270                                       # AA face outboard
AA_POS = [(sx * 17, u, OUT(sx)) for u in (88, 94, 100, 106, 112, 129, 147, 164, 170, 176, 182)
          for sx in (1, -1)]                                                # main deck edge
AA_POS += [(sx * 16, u, OUT(sx)) for u in (58, 64) for sx in (1, -1)]      # hull still narrowing here
AA_POS += [(sx * 10, u, OUT(sx)) for u in (44, 54) for sx in (1, -1)]         # forecastle
AA_POS += [(sx * 9, u, OUT(sx)) for u in (214, 221, 228) for sx in (1, -1)]   # quarterdeck
AA_POS += [(sx * 7, u, OUT(sx)) for u in (141, 148, 155, 162, 169) for sx in (1, -1)]  # deckhouse roof
AA_POS += [(sx * 8, u, OUT(sx)) for u in (118, 130) for sx in (1, -1)]        # tower base
for x, u, aft in AA_POS:
    s.plan_turret(AA, x, -u, top(x, u), aft=aft, tier='aa')

# ---------- propulsion like t1: steam engines (gearbox -> power pool) + Huge propellers under the keel
ENG = s.steam_plant(H, 'Goliath Serial Engine', 6, range(132, 206), [-9, 9, 0, -12, 12, -6, 6], [-10])
PROPS = s.huge_props(H, [-12, -8, -4, 4, 8, 12], 212)

BK = {c for c in H if U(c) % 8 == 0 and 16 <= U(c) <= 256}
DK = {c for c in H if c[1] == -1}
s.set_hull(H, BK, DK)

floor9 = {c for c in SUPS if c[1] == 9}
mast = {(0, y, -162) for y in range(17, 33)}
s.add_superstructure(SUPS, keep=floor9 | mast)
s.mount_turrets()

# ---------- AI core, fuel / ammo materials
ai = s.ai_core(list(range(112, 128)), [3, 4, 5, 6, -3, -4], -10)
helm = s.helm(range(116, 134), [0, 2, -2], range(0, 4))        # wheel + chair under the tower, as on t1
XS = [0, -2, 2, -4, 4, -6, 6, -8, 8, -10, 10, -12, 12]
tanks = []                                                     # magazines (APS ammo + boiler fuel): materials
for near, k in ((72, 14), (92, 14), (192, 14), (108, 6), (176, 6), (30, 4), (80, 4), (246, 4), (138, 8), (165, 12)):
    tanks += s.tanks(k, near, 20, 250, range(-10, -2), XS)

# ---------- steering + fire control directors
for x in (-2, 2):
    s.rudder(x, 256)
s.EXT += [('Range Finder (9m)', (0, 43, -122), 0),            # main 15 m rangefinder analogue (spans x -4..4)
          ('Telescope Camera Gimbal Tracker', (2, 44, -120), 0), ('Laser Range finder Tracker', (-2, 43, -120), 0),
          ('Radar Gimbal Tracker', (0, 43, -125), 0), ('Radar 360', (2, 43, -125), 0), ('Camera 360', (-2, 43, -125), 0),
          ('IR Camera 360', (0, 43, -119), 0),
          ('Range Finder (7m)', (0, 17, -160), 0),               # aft director on the deckhouse
          ('Radar 360', (0, 33, -162), 0)]                       # mainmast top

print(s.armour_scheme(well_tiers=('main', 'secondary'), target_wl=-3.5))   # HA only around ammo; lead keel ballast
print('ballast', s.BALLAST)
s.emit()
r = s.validate()
for k, v in r.items():
    print(k, v if k != 'support' else {kk: vv for kk, vv in v.items() if vv[0] is None or vv[1] is not None})
print('ai', ai, 'helm', helm, 'tanks', len(tanks), 'engines', [(e['anchor'], e['yaw']) for e in ENG], 'props', PROPS)
if __name__ == '__main__':
    out = os.path.join(CONSTRUCTABLES, 'Yamato.blueprint')
    s.save(out); print('saved', out)
