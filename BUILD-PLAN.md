# Wisp — Hair Creator for Blender
*Build plan. Working title "Wisp" (a wisp of hair). Target: Blender 5.2 extension.*

**Vision:** select a head → set up scalp → draw a few strokes → pick Anime or Realistic → tweak a handful of sliders → done. Works on Character Creator (FBX) and VRoid (VRM) heads. See `docs/RESEARCH-AND-DESIGN.md` for the full analysis behind these choices.

**Golden rule:** every phase ends installable and testable in Blender. Simple and intuitive beats feature-complete — when in doubt, cut the option and pick a good default.

---

## Phase 0 — Scaffold (½ day) ✅ *done 2026-07-22*
Reset the repo for Blender 5.x, keeping what's reusable from v2.

- [x] New extension package `wisp/` (manifest, `build_wisp.py` → `dist/wisp-<ver>.zip`)
- [x] Keep/port: GN-builder utils (`core/nodes.py`), scalp auto-detect (`core/scalp_detect.py`, decoupled from UI props), geometry helpers (`core/geometry.py`)
- [x] `wisp/core/` module boundary established (no UI/props dependencies — see its docstring for the rules)
- [x] Installs and shows the "Wisp" N-panel — verified live (note: connected Blender reports **5.1.2**, so `blender_version_min` set to 5.1.0)

## Phase 1 — Head & Scalp Setup ✅ *core done 2026-07-22 (v0.2.0)*
The foundation: any head in, a usable scalp out.

- [x] Pipeline detection: CC / VRoid / generic from bone naming (`core/rig.py`); finds armature, head bone, body mesh from any selected part
- [x] Scalp auto-detect v3: **head-bone skin weights** + hairline/nape ratios + curvature ear-exclusion (`core/scalp_detect.py`) — the v2 mesh-only heuristic failed badly on full-body characters (117 verts vs 1322 correct on Nova); bone-based is the way
- [x] Paint-refine loop: Refine by Painting → weight paint WISP_SCALP → Finish Painting rebuilds regions
- [x] Region auto-split: Bangs / Sides L+R / Back / Crown vertex groups from scalp geometry
- [x] Non-destructive on rigged meshes (only adds vertex groups)
- [x] **Done when** verified: Nova (CC) 1322 scalp verts, Wei Li (VRoid) 585 — clean caps on both, two clicks each (`dist/verify_*.png`)
- [ ] Deferred to Phase 2: manual per-region paint editing; generic-head fallback polish

## Phase 2 — Strand Authoring
Drawing hair. The single most important UX in the tool.

- [ ] "Draw Strands" tool: curves drawn snapped to scalp surface (wraps Sculpt Curves add/draw)
- [ ] Mirror-X toggle; per-region default strand length
- [ ] Select / delete / smooth / grab strands; lock roots
- [ ] Strand list (simple outliner)
- [ ] **Done when:** sketching a rough hairstyle silhouette takes < 5 minutes and feels natural

## Phase 3 — Anime Mode MVP  → *first shippable*
Parametric strand meshes + toon look (the Anime Hair Studio model).

- [ ] GN strand mesh per curve: profile shape, width/taper float-curves, twist, resolution + auto-LOD
- [ ] Edits are non-destructive: reshaping params never loses drawn curves (keep the curve backbone — needed for VRM spring bones later)
- [ ] Toon hair shader nodegroup: base/shadow/highlight colors, threshold, anime highlight band
- [ ] 3 bundled presets (e.g. short spiky, bob + bangs, twin tails)
- [ ] **Done when:** a VRoid head gets presentable anime hair in ~10 minutes

## Phase 4 — Realistic Mode MVP ✅ *core done 2026-09-26 (v0.4.0)*
Guides + Blender's stock hair machinery (the Sisir model) — but the guides are **grown procedurally** from a hairstyle preset, not hand-drawn.

- [x] Procedural guide groomer (`core/groom.py`): roots Poisson-sampled from WISP_SCALP; each guide combed (away from whorl/part, fringe forward+swept), bent by gravity, collided against a **least-squares ellipsoid head proxy** + a blurred ear/occiput **bulge map**, then relaxed so it bridges bumps. Lengths in *head units* (crown→chin) so presets fit any head
- [x] Stock-asset modifier stack (`core/hair_stack.py`): Interpolate → Clump → Noise → Frizz → Smooth → Profile, driven via 5.2's `modifier.properties.inputs` API (falls back to 5.1 ID-props)
- [x] Principled Hair material (`core/hair_material.py`): melanin presets; EEVEE ignores melanin and shades `Color`, so a matched colour is derived from the same melanin values
- [x] UI: Hairstyle preset → Shape sliders → **Grow Hair**; Detail sliders + Material update live
- [x] Hair object parented to the head bone — roots verified to stay on the scalp with the head rotated 25°
- [x] 5 presets: Mop Top, Bob, Shoulder Shag, Long Straight, Short Crop (only Mop Top tuned against a reference so far)
- [x] **Done when** verified: Nova (CC) matched to a reference photo (mop top, swept fringe over the eyes, chin-length flicked sides) — `dist/verify_nova_mop_top_*.png`
- [x] Round 2 (2026-09-26): Mop Top retuned against front/side/back photos — added face plane (side hair behind the cheekbones, nothing in front of the face below the fringe line), enclosing head proxy (90th-percentile scale), fringe_volume + face-width fringe tilt, part limited to the front, back-of-crown flow (no whorl gap), hair Tint; best with scalp Hairline ≈ 0.62
- [x] Round 3 (2026-09-26, target engine = **Cycles on the RTX 3070 / OptiX**, ~40 s per 1080p close-up at 128 spp): custom `Wisp Strand Profile` (full thickness, late smooth taper — stock profile tapers linearly → see-through ends); root→tip melanin gradient (Curves Info → Map Range / Mix, EEVEE too); fringe stubs below the fringe line become side hair; flick is now a length-preserving curl over the last 4 cm (old push made stacked horizontal "rungs"); Mop Top at 260/cm², r=0.08 mm (~190k hairs), melanin 0.78 / redness 0.62
- [x] Round 4 (2026-09-26): piecey fringe (`Wisp_FringeClump`, factor from a `WISP_FRINGE` scalp weight map the children inherit), `Wisp Flyaways` group, scalp cap (`Wisp_ScalpCap_<body>`, hair-coloured shell eroded 3 rings back from the hairline)
- [x] **Hair object now lives in the surface's space** (child of the body, identity transform — Blender's convention). All stack distances are converted metres → object units in `apply_style` (CC bodies are in cm under a 0.01 rig). Guides are grown with the armature in REST pose. Interpolate uses the Resting Surface (`add_rest_position_attribute`)
- [x] **Dynamics** (`core/hair_sim.py`, "Wisp Hair Sim"): own GN solver on the guides — Deform Curves on Surface target → verlet + gravity → shape memory (root pinned) → body collision → Follow-The-Leader length projection (hard, unit-proof). ~60 fps on 284 guides; Bake/Free buttons wrap the simulation-nodes cache ops. The stock *Hair Dynamics* asset was rejected: its XPBD constraints are metre-tuned, so on the cm-scaled CC mesh hair stretched ×100 (×7 even in object space)
- [ ] **Next session: the user's notes, 2026-09-26** (Nova, Mop Top):
  - Relax the side on the user's LEFT in the renders (= Nova's right, −X, the heavy-fringe side): it juts out too far and looks stiff. Likely less volume/lift/inflation there and a softer drape; consider a per-side volume control
  - Fringe a bit longer and thicker, but it should only PARTIALLY cover one eye (currently covers the right eye fully) → more fringe density/root area, less tilt
  - Natural movement "as he flops it around" (head flicks/flips while performing) → tune the Wisp Hair Sim (lower stiffness/damping, maybe per-region stiffness), test on a head-flick clip
  - The user has **3 crowns (whorls)** on his scalp → add multi-whorl support to the groomer (currently one whorl on the part line); ask for their locations (a top-down photo)
- [ ] Next: dynamics on a real performance clip (Calibration action is an extreme test — fast snaps); cap edge fade; tune under Ghost Circuit stage/comic lighting

- [ ] Tune the other 4 presets against references; test on a VRoid head
- [ ] Length/density painting (wrap Sculpt Curves brushes on the hair object)

**Gotchas learned (don't relearn these):**
- Clump after Interpolate must NOT use "Existing Guide Map" — `guide_curve_index` points at guides that no longer exist → huge blocky clumps
- Noise/Frizz with **Cumulative Offset** kink short strands (fringes) into fuzz — keep it off
- End **flick** must be off for the fringe (tips curl toward the camera → fuzzy band)
- Colliding against the real head mesh or its convex hull snags on the ears (tufts, climbing loops) → ellipsoid proxy + bulge map
- Hidden node sockets (e.g. `Color` in Melanin mode) aren't reachable via `inputs["name"]` — iterate
- 5.2 node API: Random Value / Compare only expose the active data type's sockets (index 0/1); Simulation Output input 0 is **Skip**, Simulation Input output 0 is **Delta Time** — link zone sockets by name
- A simulation zone's cached curves lose the surface link Interpolate needs — copy simulated positions back onto the live guides
- Matrix modifier inputs can't be set from Python — wire them inside a group

### Round 5 (2026-09-29)
- [x] Side relaxed (fringe lean + volume fade past the face edge; swept fringe continues as side hair and obeys the face plane; hair rests on the head down to its widest point with a smooth release; face-plane limit slopes in around the brow) — fixes the stiff wedge, shelves and the brow "headband" crease
- [x] Fringe longer/thicker, partial cover of one eye (`fringe_thickness` via a `WISP_DENSITY` weight map; Mop Top preset updated)
- [x] Multi-crown flow field (`crowns` 1-3, spread, swirl) — Nova has 3 crowns; positions still unknown (ask for a top-down photo)
- [x] **iClone round-trip** chosen over FBX hair (FBX can't carry strand hair): animate Nova in iClone, export FBX, **Wisp → Pipeline → Apply Motion (FBX)** retargets onto the Blender armature (`core/motion.py`: rest-offset retarget when rests match, world-orientation copy when they don't; imported objects/actions removed; previous action kept with a fake user). Verified exact (≤1.4 mm) on a Blender-exported Calibration clip. The FBX importer shifts frames by +1. The rest-offset path is untested until a real iClone export arrives
- [x] Head-bang clip (user's FBX import, `Armature.001`, action `5847765473280_TempMotion`, 126 f @ 60 fps, identical CC rig) put on Nova by assigning the action + its 6 shape-key slots (Calibration kept with a fake user)
- [x] **Hair now follows the body in any pose**: the groom is built/simulated in REST space and the final `Wisp_Follow` modifier ("Wisp Follow Head") carries it with the head via two empties (`Wisp_HeadAnchor_<body>` on the head bone, `Wisp_HeadRest_<body>` frozen at rest). Before this, Interpolate grew children on the rest surface so posed hair floated at the rest position
- [x] Sim fixes found on the head-bang: rest lengths measured before deformation (hair was ×7.8 long); gravity was silently 0 (a vector modifier input doesn't reach the group in 5.2 → float + Transform Direction inside); swapped Wisp groups now get a *fresh* modifier (re-pointing kept a stale vector value); sim bake entry forced to ANIMATION (new ones default to STILL = no time steps); DFTL velocity correction (plain FTL compounds into runaway); inelastic collisions; shallow-penetration-only collision; Root Hold zone (first 35% keeps its style → scalp never exposed)
- [x] Defaults now stiffness 0.25, damping 0.15 (≈ air drag), root hold 0.35
- [ ] Tune Wisp Hair Sim on real iClone performance motion

## Phase 5 — Styling Breadth
The features that make people love it.

- [ ] Braid & coil strand types (instanced geometry along curve)
- [ ] Layers: bottom / mid / top / accent with spacing offsets
- [ ] **Hair Tie** object: guides within radius pull through it → ponytails/buns in one gesture
- [ ] Quick-drape: one-click gravity settle (sim preset, then bake)
- [ ] Hairstyle preset save/load (user library)

## Phase 6 — Pipeline & Ship
- [ ] Bind hair to head bone / surface deform; survives animation
- [ ] **VRM spring-bone generation + export** (anime mode; VTuber market)
- [ ] Hair cards baking for game export; Alembic export preset
- [ ] Docs + demo video; package for Blender Market / GitHub per licensing decision

---

*Order of phases 3 and 4 can swap depending on which pipeline you need first. Verify each phase live via the Blender MCP.*
