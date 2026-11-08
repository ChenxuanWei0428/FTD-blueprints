# From the Depths — Ship-Building Rules

## Workflow
- Blueprints live in `Documents\From The Depths\Player Profiles\<profile>\Constructables` (profile: Austin; Documents may be redirected to OneDrive). The Steam install folder on D: does not hold blueprints.
- Only write blocks whose GUID is confirmed (see ftd_guids.csv; it lacks .itemduplicateandmodify variants such as beams and slopes, so read those from the game's Mods folder). For an unfamiliar system, build a small sample in-game, save and upload it, read its real GUIDs and layout, then replicate.
- Always save edits under a new file name (t1_v2, t1_v3, ...); never overwrite the original. Blueprints are tracked in a git repo.

## .blueprint file format
- JSON. `Blueprint.BLP` = "x,y,z" anchor positions, `BLR` = rotation index, `BCI` = color, `BlockIds` = local ids into ItemDictionary. The four arrays must stay parallel.
- `BlockData` is keyed by block index (each record starts with the index as a little-endian uint16), so **never delete or reorder blocks**. To change a block, replace its BlockIds/BLR in place and append fill blocks for any freed cells. Always append new blocks at the end.
- After adding blocks, update BlockCount, AliveCount, BlockState ("=0,N"), TotalBlockCount (includes all subconstruct blocks), the top-level SavedTotalBlockCount, and MinCords/MaxCords if bounds change.
- Rotation index → direction a multi-cell block extends from its anchor (inferred from t1; +z is the bow): 0:+z, 1:+x, 2:-z, 3:-x, 4-7:-y, 8-11:+y, 12:+z, 13:-x, 14:-z, 15:+x, 16:+z, 17:-z, 18:+z, 19:-z, 20:+x, 21:-x, 22:+x, 23:-x.
- Beam/slope length = number of cells occupied (a 4m beam occupies 4 cells).
- Turrets are entries in SCs. To copy one: deep-copy the SC, change LocalPosition (the turret base's coordinates in the parent), give it and every nested SC a new PersistentSubObjectIndex, then set the parent's PersistentSubObjectIndex to the highest value used. LocalRotation is a quaternion x,y,z,w; facing aft = "0,1,0,0".
- A turret base needs a parent block directly beneath it and free cells above; check the barrel's sweep radius at barrel height.
- Adding blocks inside a subconstruct: update that SC's BLP/BLR/BCI/BlockIds and counts, and add the same number to the TotalBlockCount of every ancestor.
- Watertightness check: 6-connected flood fill from outside. Slopes and offset blocks can leave diagonal gaps, so verify enclosure in code.

## Game mechanics
- Air pump: fills up to 3500 m³; one per sealed compartment.
- Laser system = Multipurpose Laser + Laser Coupler + cavities + pumps. Each pump makes 12 laser energy/s and costs 30 engine power/s (3m pump: 3x).
- Connection rules (from .item files): a cavity receives on its Forwards face, which must point at the coupler or the previous cavity; a pump receives on its Forwards face, pointing at a cavity (up to 4 sides); the multipurpose laser sends on all sides; couplers and transceivers receive on all sides.
- A turret's laser transceiver (rotation 4) points down and links to the hull transceiver it points at, so the hull transceiver must sit directly under the turret base.
- Lasers as CIWS: add a CIWS controller to the turret (an AIO CIWS works anywhere on the same construct; adjacency not required); also needs AI and munition warners. Set weapons to fire above water only (lasers attenuate heavily in water).
- AIO LWC (per its in-game description) fires weapons/turrets connected within 2 blocks along any of its six faces; it is not construct-wide. The Copperhead prefab carries its own AIO LWC on the turret, touching the ammo controller and turret block. Radar 360 receives its AI link from below.
- "Fire control computer" (火控计算机) is marked obsolete in-game; it is only for manual remote firing.
- APS ammo customisers need material storage somewhere on the vehicle (Material Storage Tank Large = 2x2x2).
- Huge propeller (3x3) attaches only by its Forwards face; it needs a block in front of its centre or it falls off.
- Multi-cell blocks with x/y size (RTG, battery, propeller, tank) occupy their full SizeNeg..SizePos box, not just a line along the facing.
- RTG: 15 energy/s per m³ (3x3 = 405/s); requires batteries plus an electric engine touching a battery. Batteries convert at most 90 energy/s per m³; electric engine: 1 energy → 1 power.
- Engine power must cover propulsion plus 30/s per laser pump.

## t1 status (author tag Kevin, game version 4.3.4.1)
- Single-shell alloy hull, about 23 wide × 24 tall × 131 long. Bow at z=+3, stern at z=-127, main deck y=1, raised midship deck at y=4 around z -41 to -73.
- The stern is raked: only y -2 to 1 reach z=-127, and the y=-7 bottom ends at z=-110. Propellers therefore hang under the keel.
- t1_v2: 5 watertight compartments (bulkheads at z=-39, -59, -79, -99; internal deck at y=1), 2200-2500 m³ each, one air pump on the bottom centerline of each.
- t1_v3: front Copperhead main gun at (0,2,-18), aft copy at (0,2,-115) facing aft; 10 laser turrets at (±3,4,-44), (±5,5,-64), (±5,5,-72), (±8,2,-110), (±8,2,-122).
- t1_v4:
  - One laser system under each turret: hull transceiver → multipurpose → coupler → 2 cavities → 4 pumps; 40 pumps total.
  - AIO CIWS at (0,2,-1) in every laser turret's elevation subconstruct.
  - Power room in compartment 4: 4× RTG 3x3 (1620 energy/s), 2× Battery Storage Large stacked at (0,-6/-5,-84), 2 electric engines.
  - AI mainframe + Naval AI card + Radar 360 at (5..6,-6..-5,-95).
  - 2 huge propellers under the keel at (±4,-9,-107); rudder at (0,-8,-109).
  - 4 munition warners on top of the two towers.
  - The deck support blocks under the midship and stern turrets were replaced in place with transceivers plus alloy cubes, so the deck slopes at (±5,4,-72) became cubes.
- t1_v4, rev 2 (2026-11-08; edited in place, old t1/t1_v2 deleted):
  - Laser turrets recessed like the user's front pair: the turret transceiver sits in the outer skin and only the combiner/optics layer is above it. Midship bases are now at (±5,2,-64/-72) with hull transceivers at y=1; stern bases at (±8,-1,-110/-122) with hull transceivers at y=-2. Old deck transceiver cells were refilled with alloy cubes.
  - Each laser: hull T → multipurpose → coupler → 3 cavities → 12 pumps (front pair 9, limited by two-layer space). 114 pumps total ≈ 3420 power/s.
  - Power: +6 RTG 3x3, +3 Battery Storage Large, each with an electric engine (z -82..-80). Totals: 10 RTG (4050 energy/s), 5 batteries, 5 engines. Engine at (2,-6,-82) moved to (2,-6,-84) so it touches a battery.
  - Propellers: heavy-armour pylons at (±4,-8/-9,-106) for their front attach face.
  - 4× Material Storage Tank Large at y -6..-5, z -41..-40.
  - Outer-shell alloy blocks with mean y ≤ -3 converted 1:1 to heavy armour shapes (684 blocks). Mass ≈ 4790; estimated waterline ≈ y -4.6, assuming air pumps keep the compartments dry.

## Generated blueprints / tooling
- `design_data/tools/`: `ftd.py` (parse, item names/sizes/weights from the game Mods folder, block footprints), `edit.py` (append/move/retype/carve builder that keeps the four arrays parallel and updates counts), `yamato_hull.py` + `yamato_build.py` (regenerates Yamato.blueprint: `python -I design_data/tools/yamato_build.py`).
- Lessons from generating a ship from scratch:
  - An empty `BlockData` ("") is valid; official prefabs use it.
  - Official APS designs in `Mods/Core_APS/Assets/*.blueprint` have the same schema as an SC. Embed one by deep-copying its `Blueprint`, remapping BlockIds through its own ItemDictionary, and setting LocalPosition/LocalRotation.
  - Build hull shells with 26-neighbour (diagonal) contact, or stepped corners leave pieces connected only diagonally (detached in game).
  - Anything placed inside open compartment air, such as a laser system, needs a pillar down to a deck or bulkhead.
  - Buoyancy calibrates to about 1 per submerged m³ (t1: mass 752 floated on the bottom layer). An all-alloy hull floats like a cork, so heavy armour sets the draft.

## Yamato (Yamato.blueprint, 1:1, 1 block = 1 m)
- Hull 263 × 39, keel y=-11, main deck y=8 (bow rises to ~13, aft deck y=6 from u≈208), bulbous bow, cut-up stern. Bow at z=+2, stern z=-262 (u = -z).
- 31 transverse bulkheads every 8 m (u 16-256) plus an internal deck at y=-1 → 64 compartments (≤ 2263 m³), one air pump each.
- Whole hull shell and barbettes are heavy armour; superstructure is alloy. Mass ≈ 61k, estimated waterline y≈-3.2, COM about 2 m forward of COB (slight bow-down trim).
- 1945-style armament (user asked for no lasers, closer to history):
  - Main battery: 3 × 9x9 Citrin at (0,9,-72), superfiring (0,14,-92) on a barbette, and aft (0,9,-192) facing aft. Citrin has 4 barrels and its own LWC. No heavy triple prefab exists in the game; Mamba is the only triple. Cutting Citrin down to 3 guns would need reindexing its nested BlockData, which I can't do safely.
  - 15.5cm triple secondaries: 2 × Mamba (AIO LWC, AA mantlets). One at (0,24,-108) on the platform ahead of the tower, superfiring over turret 2; one at (0,18,-176) on the aft barbette, superfiring over turret 3.
  - 12.7cm twin HA: 12 × 5x5 Cobalt (LWC, AA mantlets, IR camera). Lower level on deck at (±13,9,-124/-138/-152); upper level on sponsons at (±10,17,-131/-145/-159).
  - No 25mm guns; the game has no small prefab of that kind. No lasers or munition warners.
- Pagoda tower u 114-134 up to y=42 with rangefinder arm; raked funnel u 140-157; aft superstructure u 156-170 with mainmast at u 162.
- Fire control:
  - Tower top (y=43): Range Finder (9m) at u=122, telescope camera / laser rangefinder / radar gimbal trackers, Radar 360, Camera 360 and IR Camera 360.
  - Aft director: Range Finder (7m) at (0,15,-160). Radar 360 on top of the mainmast at (0,33,-162).
- AI core at (3,-10,-116):
  - Mainframe, with card slots in front and behind (cards sit on a slot's ±x sides) holding Naval AI, Target Prioritisation and Tracker Target Association.
  - 3 GPP processing cards facing the mainframe.
- Power room u 129-131: 8 RTG (3240 energy/s), 4 Battery Storage Large, each touching an electric engine. 8 material tanks near the magazines.
- 4 huge propellers at x=±5,±12, y=-10, z=-240, each on a heavy-armour pylon. 2 rudders at x=±4, z=-252.
