# From the Depths — Ship-Building Rules

## Workflow
- Blueprints live in `Documents\From The Depths\Player Profiles\<profile>\Constructables` (profile: Austin; Documents may be redirected to OneDrive). The Steam install folder on D: does not hold blueprints.
- Only write blocks whose GUID is confirmed (see ftd-guids.md). For an unfamiliar system, build a small sample in-game, save and upload it, read its real GUIDs and layout, then replicate.
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
- AIO LWC and AIO CIWS control weapons from anywhere on the same construct. Radar 360 receives its AI link from below.
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
