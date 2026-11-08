# From the Depths — Ship-Building Rules

## Workflow
- Blueprints live in `Documents\From The Depths\Player Profiles\<profile>\Constructables` (profile: Austin; Documents may be redirected to OneDrive). The Steam install folder on D: does not hold blueprints.
- Only write blocks whose GUID is confirmed (see ftd_guids.csv; it lacks .itemduplicateandmodify variants such as beams and slopes, so read those from the game's Mods folder). For an unfamiliar system, build a small sample in-game, save and upload it, read its real GUIDs and layout, then replicate.
- Always save edits under a new file name (t1_v2, t1_v3, ...); never overwrite the original. Blueprints are tracked in a git repo.

## .blueprint file format
- JSON. `Blueprint.BLP` = "x,y,z" anchor positions, `BLR` = rotation index, `BCI` = color, `BlockIds` = local ids into ItemDictionary. The four arrays must stay parallel.
- `BlockData` is keyed by block index (each record starts with the index as a little-endian uint16), so **never delete or reorder blocks**. To change a block, replace its BlockIds/BLR in place and append fill blocks for any freed cells. Always append new blocks at the end.
- **Every construct's `ItemNumber` must be a key of the file's ItemDictionary.** The root uses 740 = 'Vehicle' in t1; a turret subconstruct uses its turret-block item. Otherwise loading fails with `KeyNotFoundException: The given key '740'` in `BlueprintFile.UpdateConstructAndChildren` (seen in `Documents/From The Depths/Logs/*.txt`). When embedding a prefab, remap its ItemNumber through its own dictionary, like BlockIds.
- Subconstructs must use the 4.3.4.1 schema the game saves: `BlockState` ('=0,N', or '0' for one block), `AliveCount` = N, `ContainedMaterialCost`, `AuthorDetails` and GameVersion '4.3.4.1'.
  - Some official prefabs are older. 5x5Cobalt (2.5.1) has `Id` / `LastAliveBlock` / `IndexOfFirstBlockNeedingFullRepairCost` and no BlockState / AliveCount.
  - `shipgen.Ship._remap` converts them when embedding.
- Game logs for load errors: `Documents/From The Depths/Logs/<version>_<date>.txt`.
- After adding blocks, update BlockCount, AliveCount, BlockState ("=0,N"), TotalBlockCount (includes all subconstruct blocks), the top-level SavedTotalBlockCount, and MinCords/MaxCords if bounds change.
- Rotation index → (forward, up); right = up × forward. Fixed 2026-11-08: tested against every game prefab, which must have no overlapping multi-cell blocks. The old list had 13/15 wrong.
  - 0-3: forward +z/+x/-z/-x, up +y.
  - 4-7: forward -y, up +z/+x/-z/-x.
  - 8-11: forward +y, up +z/+x/-z/-x.
  - 12-15: forward +z/+x/-z/-x, up -y (upside down).
  - 16-19: forward +z/-z/+z/-z, up +x/+x/-x/-x.
  - 20-23: forward +x/-x/+x/-x, up +z/+z/-z/-z.
  - The table is `ftd.ROT`; `ftd.rot_map(r, M)` rotates an index (e.g. `ftd.yaw180`).
- Beam/slope length = number of cells occupied (a 4m beam occupies 4 cells).
- Turrets are entries in SCs. To copy one: deep-copy the SC, change LocalPosition (the turret base's coordinates in the parent), give it and every nested SC a new PersistentSubObjectIndex, then set the parent's PersistentSubObjectIndex to the highest value used. LocalRotation is a quaternion x,y,z,w; facing aft = "0,1,0,0".
- A turret base needs a parent block directly beneath it and free cells above; check the barrel's sweep radius at barrel height.
- Adding blocks inside a subconstruct: update that SC's BLP/BLR/BCI/BlockIds and counts, and add the same number to the TotalBlockCount of every ancestor.
- Watertightness check: 6-connected flood fill from outside. Slopes and offset blocks can leave diagonal gaps, so verify enclosure in code.

## Materials (user rule, 2026-11-08)
- Ordinary structure: Light-weight Alloy (轻质合金).
- Below the waterline: Metal (金属).
- Key spots only: Heavy Armour (重装甲), mainly a ring around the ammunition. That means the hull cells around the gun wells, where loaders and clips sit, and a one-block ring around the material/ammo tanks. All superstructure is alloy (user, 2026-11-08b: "重装甲还是太多…上层建筑全用轻也没关系").
- Never armour the whole ship in heavy armour.
- shipgen: `Ship.armour_scheme(well_tiers=..., target_wl=...)` applies this.
  - HA goes on hull cells (not superstructure) touching the chosen tiers' wells, plus a ring around every Material Storage Tank (free air cells around it are filled with HA).
  - Metal goes on the hull shell below the waterline; everything else is alloy.
  - `belt` and `extra_ha` exist but are off by default.
  - Steam struts are Metal Blocks.
- Draft and trim come from keel ballast, not armour. **Lead Block** (weight 2.0, same as HA, cheap; in-game description: "Perfect for keels and counter balances") fills the lowest 3 interior layers.
  - `target_wl` sets how many lead blocks to add. They are centred so that COM z = COB z.
  - Large ships need it: without ballast, Yamato floated at y -9 with its propellers out of the water.

## Turrets (user rule, 2026-11-08: loaders inside the ship, every turret linked and with fire control)
- Use only self-contained turrets with an **AIO LWC** on the turret. Old prefabs with a plain `Local Weapon Controller` (5x5Cobalt, Cuprum, Bromine, Gallium, Zirconium, Citrin, Ruby, Pearl, Simple*mAPS) show up pink / unlinked in game; don't use them.
- Use turrets whose ammo mechanism sits *below* the firing layer, so it can be sunk into the hull:
  - 203mm (user `gun/`): loaders at y1-2, barrels at y3.
  - Severance: loaders at y0-5, barrel at y8, well radius 3.2.
  - Firecracker: loaders at y2-5, barrel at y7, 3x3 well.
  - Also suitable: Prang, Purgation, Decimator, Bombastic.
  - Mamba and Copperhead have their loaders on the barrel layer, so they cannot be sunk.
- `Ship.plan_turret(path, x, z, top, aft, tier)` must run before `set_hull` / `add_superstructure`. It carves a cylindrical well (per-layer radius + 0.5) through all loader layers, so only the gun house stands above the deck. `aft` is a bool or a yaw of 0/90/180/270 (90 = barrels to +x).
- `mount_turrets()` embeds the turrets and adds a Laser Targeter on top of any turret without one.
- `validate()` reports SC-vs-hull overlap, SC-vs-SC overlap (barrels into a neighbour) and open wells.

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

## Propulsion (user rule 2026-11-08: every ship must move, do it like t1, with steam engines)
- Copy t1's working setup:
  - Huge propellers (power-pool propellers) under the keel. Each faces forward and attaches by its Forwards face to a Metal pylon that reaches up to the hull bottom.
  - Boat rudders.
  - AI mainframe with the Naval AI card.
  - Ship's wheel with an Articulated chair behind it.
- Use official steam *power* engines (boilers → pistons → cranks → **gearbox**). The gearbox "converts the mechanical energy of the rotating crank shaft into power that can be used by other components on the vehicle", i.e. the power pool the Huge propellers draw from. Size per ship:
  - Goliath Serial Engine: 13×8×11, large boilers.
  - Quadratic Steam Engine: 6×2×10, small boilers / medium pistons.
  - Others: Goliath Parallel, Tandem 6000 (6×2×7), Foursquare, Mammoth, Mongrel.
- Boilers burn Materials, so give the ship plenty of tanks; the same materials feed the APS ammo customisers.
- shipgen:
  - `Ship.steam_plant(H, prefab, n, urange, xs, ys)` places engines in the hull interior, carved out as engine rooms; call it before `set_hull`.
  - `Ship.huge_props(H, xs, u)` adds the propellers and pylons.
  - `Ship.helm(...)` adds the wheel and chair.
  - `Ship.tanks(k, near_u, ...)` packs magazines near a turret.
- The power output of the steam engines vs the Huge propellers' demand is not checked offline. If a ship is slow in game, add engines.

## Steam shaft propulsion (Core_SteamEngine `*_prop`, no longer used for Yamato/Yukikaze)
- Official designs live in `Mods/Core_SteamEngine/Assets/*.blueprint`. The `*_prop` ones are complete mechanical drives: boiler → steam controller → piston → cased crank → gearbox → transmission → axis-shifting gears → shaft → 2m sealed shaft → hull block → shaft → shaft propeller. They are built along +z with the propeller at +z, so rotate them 180° (`ftd.yaw180`) for a stern propeller.
  - 36K_prop: small boilers, Medium 3m propeller.
  - 90K_prop: medium boilers, Medium 5m propeller.
  - 180K_4_prop: large boiler, Large 7m propeller.
- A 2m sealed shaft's second metre may pass through any block, which then acts as the seal. So the shaft leaves the hull through a transverse face: sealed shaft just inside, the hull block is the seal, and the shafts plus propeller sit outboard.
- Boilers burn Materials, so carry material tanks. No RTG or batteries are needed for propulsion.
- Long outboard shafts get struts. The official 180K design has a Metal Block beside its shaft.
- `Ship.steam_shaft()` plans this automatically. It finds the stern-most hull cell on the shaft line, rebuilds the outboard part with the propeller clear of the hull, and slides the engine forward until it fits inside the hull interior.

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
  - Outer-shell alloy blocks with mean y ≤ -3 converted 1:1 to heavy armour shapes (684 blocks).
  - rev 3 (material rule): those became the matching Metal shapes, except 17 hull blocks within 2 m of the material tanks, which stay heavy armour (rev 4, "HA only around ammo"). Backups in the session scratchpad: `t1_v4.before_metal.blueprint` (rev 2) and `t1_v4.rev3.blueprint`.

## Generated blueprints / tooling
- `design_data/tools/`: `ftd.py` (parse, item names/sizes/weights from the game Mods folder, block footprints), `edit.py` (append/move/retype/carve builder that keeps the four arrays parallel and updates counts), `yamato_hull.py` + `yamato_build.py` (regenerates Yamato.blueprint: `python -I design_data/tools/yamato_build.py`), `shipgen.py` (reusable `Ship` class: hull shell/bulkheads/compartments/pumps, superstructure shells, prefab embedding, functional-block placement, AI core, power, propellers, armour, emit, validate) + `yukikaze_build.py` (regenerates Yukikaze.blueprint).
- Lessons from generating a ship from scratch:
  - An empty `BlockData` ("") is valid; official prefabs use it.
  - Generated ships start from t1_v4 (root fields, VehicleData, AuthorDetails, the ItemDictionary numbering); see `shipgen.Ship`.
  - Official APS designs in `Mods/Core_APS/Assets/*.blueprint` have the same schema as an SC. Embed one by deep-copying its `Blueprint`, remapping BlockIds through its own ItemDictionary, and setting LocalPosition/LocalRotation.
  - Build hull shells with 26-neighbour (diagonal) contact, or stepped corners leave pieces connected only diagonally (detached in game).
  - Anything placed inside open compartment air, such as a laser system, needs a pillar down to a deck or bulkhead.
  - Buoyancy calibrates to about 1 per submerged m³ (t1: mass 752 floated on the bottom layer). An all-alloy hull floats like a cork, so heavy armour sets the draft.
  - On a slim hull, a heavy-armour shell weighs more than it displaces: Yukikaze sank to the deck with HA shell up to y=6. With the material rule (`armour_scheme`) this no longer applies.

## Yamato (Yamato.blueprint, 1:1, 1 block = 1 m)
- Hull 263 × 39, keel y=-11, main deck y=8 (bow rises to ~13, aft deck y=6 from u≈208), bulbous bow, cut-up stern. Bow at z=+2, stern z=-262 (u = -z).
- 31 transverse bulkheads every 8 m (u 16-256) plus an internal deck at y=-1 → 64 compartments (≤ 2263 m³), one air pump each.
- Materials (rev 2026-11-08c):
  - Alloy everywhere, including all superstructure and the barbettes above deck; Metal below the waterline.
  - Heavy armour (2759 cells) only around ammo: hull cells around the main/secondary wells and rings around the 16 material tanks.
  - Lead keel ballast: 21019 cells in the lowest 3 interior layers.
- Mass ≈ 58.3k, waterline y = -3.5 (propellers submerged), COM z -130.2 vs COB -129.8. 41798 blocks including turrets.
- 2026-11-08 rebuild (the first version would not load, see the ItemNumber rule): `yamato_build.py` now uses shipgen/t1 base.
- Armament (three tiers, all AIO LWC, all loaders sunk in wells, no Cobalt):
  - Main: 3 × user 203mm triple at (0,6,-72), superfiring (0,11,-92) on a r=8.5 barbette, and aft (0,6,-192) facing aft.
  - Secondary: 8 × Severance.
    - Two on the centreline, superfiring like the 15.5cm triples: (0,18,-108) on the forward platform, and (0,12,-176) on the aft barbette facing aft.
    - Six on the beam at (±14,3,-120/-138/-156), standing in for the 12.7cm HA guns; the aft pair faces aft.
  - AA: 38 × Firecracker, all facing outboard, each with an added Laser Targeter:
    - main deck edge x=±17 at u 100/106/112/164/170/176/182;
    - forecastle x=±10 at u 44/54;
    - quarterdeck x=±9 at u 214/221/228;
    - deckhouse roof x=±7 at u 141-169;
    - tower base x=±8 at u 118/130.
- Pagoda tower u 112-136 (base x±10) up to y=42 with rangefinder arm; forward platform u 101-115; raked funnel u 140-157; deckhouse u 137-174 (x±9, roof y=16) with mainmast at u 162.
- Fire control:
  - Tower top (y=43): Range Finder (9m) at u=122, telescope camera / laser rangefinder / radar gimbal trackers, Radar 360, Camera 360 and IR Camera 360.
  - Aft director: Range Finder (7m) at (0,17,-160). Radar 360 on top of the mainmast at (0,33,-162).
- AI core at (3,-10,-116):
  - Mainframe, with card slots in front and behind (cards sit on a slot's ±x sides) holding Naval AI, Target Prioritisation and Tracker Target Association.
  - 3 GPP processing cards facing the mainframe.
- Propulsion (rev 2026-11-08d, t1-style):
  - 6 × Goliath Serial Engine at y -10, u 132-168.
  - 6 Huge propellers at (±4/±8/±12, -13, -212) on Metal pylons.
  - 2 rudders at x=±2, u=256.
  - Ship's wheel + chair at (0,0,-116/-117) under the tower.
- Ammo: 86 Material Storage Tank Large in magazines under each turret group, each ring-armoured with heavy armour.
- More guns: 14 Severance (added beam pair at u80, forecastle pair at u30, quarterdeck pair at u246 facing aft) and 50 Firecracker (more on the deck edge at u 58/64/88/94/129/147). 67 turrets in total.
- Heavy armour 6277 cells (wells + tank rings), lead ballast 16.5k, mass ≈ 58.3k, waterline -3.5, COM z -130.0 vs COB -129.8. 43820 blocks.

## Yukikaze (Yukikaze.blueprint, Kagero-class destroyer, 1945 fit, 1:1)
- 2026-11-08 rebuild on the shipgen/t1 base; the first version would not load. Regenerate with `yukikaze_build.py`.
- Hull 118 × 11, keel y=-4, main deck y=5, forecastle y=7 for u<40 with sheer to the bow.
  - Counter stern: for u≥99 the bottom steps up to y=0, so the shafts leave the hull through that transverse face.
  - Bulkheads every 10 m plus u=40, giving 12 compartments, one air pump each.
- Materials: alloy, with Metal below the waterline. Heavy armour only around ammo: the two main-gun wells and a ring around the 6 material tanks, which are now amidships at u≈58. No ballast needed. Mass ≈ 2470, waterline ≈ -0.6, COM z -58.4 vs COB -57.6. 2947 blocks including turrets.
- Propulsion (rev 2026-11-08d, t1-style):
  - 2 × Quadratic Steam Engine at (0,-1,-60) and (0,-1,-78).
  - 2 Huge propellers at (±2,-6,-96).
  - Rudder at u=114.
  - Wheel + chair at (0,-3,-31).
- Ammo: 18 material tanks in three magazines near the fore gun, the aft gun and amidships. Mass ≈ 3230, waterline ≈ +0.3, COM z -58.9 vs COB -57.7.
- Armament:
  - Main: 2 × Severance with loaders sunk in wells, at (0,2,-26) and aft (0,0,-94) facing aft. The bridge moved to u 31-39 to make room.
  - AA: 4 × Firecracker at (±3,0,-42), facing aft so they clear the forecastle, and (±3,0,-73).
  - 61cm quad torpedoes: 2 × Porcupine at (0,6,-56) and (0,6,-79). Funnels are at u 46-52 and 64-70; the aft deckhouse is at u 84-88.
- Fire control:
  - Bridge top (y=15): Range Finder (5m), Laser Range finder Tracker, Camera 360, Telescope Camera Gimbal Tracker.
  - Radar 360 on the foremast (0,21,-38) and mainmast (0,16,-86).
- AI core at (0,-3,-52).
