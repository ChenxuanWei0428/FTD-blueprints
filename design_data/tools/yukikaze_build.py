"""Yukikaze (Kagero-class destroyer, 1945 fit), 1 block = 1 m.  Run: python -I design_data/tools/yukikaze_build.py
Based on t1_v4 (root fields + ItemDictionary).  Bow at z=0, stern at z=-118 (u = -z).
Keel y=-4, main deck y=5, forecastle deck y=7 (u<40, sheer to the bow).  Counter stern: for u>=99 the hull bottom
steps up to y=0, so the two shaft lines leave the hull through that transverse face.
Guns: Severance x2 (main), Firecracker x4 (AA), Porcupine x2 (torpedo); loaders sunk in hull wells.
Materials: alloy, Metal below the waterline, heavy armour only around the gun wells.
Propulsion like t1: 2 x official 'Quadratic Steam Engine' (gearbox -> power pool) + 2 Huge propellers, wheel + chair.
Old: 2 x official '36K_prop' steam engines (small boilers, medium piston, medium 3m shaft propeller), rotated
180 deg so the propellers are aft.  No RTG / batteries."""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ftd
from shipgen import Ship, CONSTRUCTABLES, MODS

L = 118; HB = 5.4; STEP_U = 99


def hb(u):                       # half-beam at the deck
    if u < 32: return HB * (u / 32) ** 0.55
    if u > 92: return HB - (u - 92) / (L - 92) * 1.7
    return HB


def y_bottom(u):
    if u < 16: return round(-4 + (16 - u) / 16 * 9)          # raked stem / forefoot
    if u >= STEP_U: return 0                                 # counter stern above the propellers
    return -4


def deck(u):
    if u < 40: return 7 + max(0, round((12 - u) / 6))        # forecastle with sheer
    return 5


DEADRISE = {0: 0.45, 1: 0.75, 2: 0.92}

H = set()
for u in range(0, L + 1):
    yb, yt = y_bottom(u), deck(u)
    for y in range(yb, yt + 1):
        w = hb(u) * DEADRISE.get(y - yb, 1.0)
        for x in range(-6, 7):
            if abs(x) <= w - 0.4:
                H.add((x, y, -u))

s = Ship('Yukikaze')
top = lambda x, u: max(c[1] for c in H if c[0] == x and c[2] == -u)

# ---------------- armament first: gun mechanisms are sunk into wells in the hull (only gun houses above deck)
APS = MODS + '/Core_APS/Assets/'; MIS = MODS + '/Core_Missile/Assets/'
MAIN = APS + 'Severance.blueprint'          # 12.7cm analogue: single AIO turret, loaders y0-5 below the barrel
AA = APS + 'Firecracker.blueprint'          # 25mm analogue: AIO flak turret, loaders below the barrel
TORP = MIS + 'Porcupine Torpedo Launcher.blueprint'
s.plan_turret(MAIN, 0, -26, top(0, 26), tier='main')
s.plan_turret(MAIN, 0, -94, top(0, 94), aft=True, tier='main')
for x in (-3, 3):
    s.plan_turret(AA, x, -42, top(x, 42), aft=True, tier='aa')
    s.plan_turret(AA, x, -73, top(x, 73), tier='aa')
s.plan_turret(TORP, 0, -56, top(0, 56), tier='torpedo')
s.plan_turret(TORP, 0, -79, top(0, 79), tier='torpedo')

# ---------------- steam propulsion (it carves its spaces out of the hull)
ENG = s.steam_plant(H, 'Quadratic Steam Engine', 2, range(60, 92), [0, 1, -1], [-2, -1, 0])   # gearbox -> power pool
PROPS = s.huge_props(H, [-2, 2], 96)                                                    # like t1, under the keel

BULK = {c for c in H if -c[2] in range(10, L, 10) or -c[2] == 40}
s.set_hull(H, BULK)

# ---------------- superstructure (hollow alloy shells on deck)
def box(u0, u1, xr, y0, y1):
    return {(x, y, -u) for u in range(u0, u1 + 1) for x in range(-xr, xr + 1) for y in range(y0, y1 + 1)}

bridge = box(31, 39, 3, 8, 13) | box(32, 37, 2, 14, 14)          # bridge + compass deck
funnel1 = box(46, 52, 2, 6, 13)
funnel2 = box(64, 70, 2, 6, 12)
aft = box(84, 88, 2, 6, 9)
foremast = {(0, y, -38) for y in range(14, 21)}
mainmast = {(0, y, -86) for y in range(10, 16)}
for solid in (bridge, funnel1, funnel2, aft):
    s.add_superstructure(solid)
s.add_superstructure(set(), keep=foremast | mainmast)
s.mount_turrets()

# ---------------- AI / fuel (boilers burn Materials) inside the hull
ai = s.ai_core(list(range(50, 70)), [0], -3)
tanks = []                                                   # magazines (APS ammo + boiler fuel)
for near, n in ((26, 6), (94, 6), (58, 6)):
    tanks += s.tanks(n, near, 14, 98, range(-3, 4), [0, -1, 1, -2, 2])
helm = s.helm(range(30, 46), [0, 1, -1], range(-3, 5))

# ---------------- steering
s.rudder(0, 114)

# ---------------- fire control (bridge top y=15, masts)
s.EXT += [('Range Finder (5m)', (0, 15, -33), 0),
          ('Laser Range finder Tracker', (2, 15, -35), 0), ('Camera 360', (-2, 15, -35), 0),
          ('Telescope Camera Gimbal Tracker', (0, 16, -35), 0),
          ('Radar 360', (0, 21, -38), 0),            # foremast (Type 22 / 13 radar)
          ('Radar 360', (0, 16, -86), 0)]            # mainmast

print(s.armour_scheme(well_tiers=('main',)))                              # alloy / Metal below WL / HA only around ammo
s.emit()
r = s.validate()
for k, v in r.items():
    print(k, v)
print('ai', ai, 'helm', helm, 'tanks', len(tanks), 'engines', [(e['anchor'], e['yaw']) for e in ENG], 'props', PROPS)
if __name__ == '__main__':
    out = os.path.join(CONSTRUCTABLES, 'Yukikaze.blueprint')
    s.save(out); print('saved', out)
