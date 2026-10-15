# Hair Tool Research & Design Notes
*July 2026 — analysis of Sisir v1.1, Anime Hair Studio, and our prior addon, plus a proposed Blender tool concept.*

---

## 1. Sisir v1.1 (standalone, realistic strand grooming)

Compiled Qt6 + DirectX 12 app (no source shipped; personal-use license). Feature set reconstructed from binary strings, its site, and shipped libraries (Alembic, assimp, draco, OpenEXR).

### Architecture: three modules, one pipeline
- **Curves module (F1)** — author sparse *guide* curves
- **Hair module (F2)** — amplify guides into dense hair + style it
- **Render module (R)** — physically-based hair rendering

The pipeline is strictly: **import head (OBJ) → draw guides → simulate/drape → interpolate to dense hair → mask/style → export (Alembic/PLY)**.

### Key features worth learning from
- **Physics-first grooming.** Guides are simulated: gravity (hold G for temporary gravity+damping), bend stiffness, damping, solver iterations, mesh collision + collision thickness. You *drape* hair rather than sculpt every curve.
- **Hair Ties** — the standout idea. Place a tie, it binds guides passing through it (ponytails, buns in seconds). Ties are draggable/slidable along guides; clumping can target ties ("Clump to Hair Ties").
- **Small tool set:** Draw Guides, Drag Smooth, Paint Length, Paint Mask, Parting tool, Draw Trim, Precision Eraser, Hair Transplant (reuse groom from another scene).
- **Guide interpolation:** density in strands/cm², affine or barycentric interpolation, "Match Closest Guide" option.
- **Modifier-style styling params:** Clumping (root/mid/tip tightness + thickness), Sub-clumps (count/spread), Frizz (root/mid/tip), randomized clump counts, hue/saturation randomness.
- **Masks as images:** distribution mask, length mask — loadable textures, plus painted vertex masks with brush radius/intensity.
- **Realistic shading:** melanin + melanin redness, cuticle tilt, azimuthal roughness, dual scattering, SSS — i.e., Marschner-family parameters (Blender's Principled Hair BSDF exposes almost the identical set).
- **Layers, Hair Sets** (multiple grooms per scene, per-set materials), mirror mode, units-aware export.

### Simplicity lessons
1. Guides + interpolation keeps user-authored data tiny (~dozens of curves).
2. Physics does the heavy lifting for natural shapes.
3. A handful of paint tools (length, mask, trim, part) replaces dozens of parameters.
4. Modules hide irrelevant UI.

---

## 2. Anime Hair Studio (web, stylized/anime)

Client-rendered web app. Feature set from full UI extraction.

### Core model: the strand is a parametric object
Each strand = a curve + procedural tube/ribbon mesh regenerated from parameters:
- **Width curve, depth curve, taper curve** (editable point curves w/ linear-smooth-constant interpolation), profile with vertical offset, twist
- **Topology:** radial segments × along-curve segments, plus **dynamic density** (auto vert reduction, "aggressiveness" slider, live vert/tri counts)
- Editing a default reshapes all strands in a group *non-destructively* (curve positions preserved)

### Scalp system
- Region-colored scalp guide: **Bangs, Side Bangs L/R, Side L/R, Back** — paintable regions
- Curve-lattice scalp fit: scale/width/depth/height sliders per zone + hairline rows to fit any imported head mesh; mirror X
- Strands root to the scalp with a scalp offset

### Tools
- **Place Strand** (click on scalp), **Draw Strand** (brush presets: Standard, 3-Strand Clump, Coil), **Braid tool** (Classic Braid, Chain Links — instanced braid geometry along a drawn curve with width/depth/segment length/rotation)
- **Move/Pull** with rigidity + head collision; contextual 2D plane drawing (snapped views); "continue from tip"
- **Proportional edit** (falloff, lock root), **hierarchy edit** (parent strands → recursive transforms)
- **Clump guides:** member strands follow a guide with influence, spread, depth spread, tip fan, roll

### Organization & look
- **Layers:** Bottom / Mid / Top / Accent with per-layer spacing offsets
- **Presets:** full hairstyles (twin tails, bowl cut, braided buns, ahoge...), element presets, user-saved presets
- **Built-in toon shader:** base/shadow/highlight colors, shadow threshold+softness, back gradient, angel-ring highlight (width, softness, strength, shift, detail)
- Export OBJ; undo; strand outliner

### Simplicity lessons
1. Anime hair = **tens of chunky strands**, so direct per-strand manipulation is viable and intuitive.
2. Parametric strand meshes = infinitely revisable, no destructive modeling.
3. Region scalp + presets give beginners instant structure.
4. Braids/coils as *instanced geometry along a curve* — cheap and perfect-looking.
5. The anime shader is part of the tool; look is guaranteed.

---

## 3. Our prior attempt (procedural_scalp_hair v2)

One-shot pipeline: heuristic scalp detect → vertex-group mask → GN tree (distribute points → instance straight line curves → noise offset). Sliders: density, length, noise, clump, direction bias.

**Why it fell short:** no authoring. Both reference tools succeed because *the user draws sparse structure and the system amplifies it*. Pure proceduralism can't express intent (parting, bangs, ponytail, flow direction). Also: instanced straight lines + noise ≠ hair; no surface flow, no interpolation, no styling pass, no material story.

**What's reusable:** the extension scaffolding (manifest, build, panel structure), scalp auto-detect as a *starting point* for a paintable mask, the GN-builder utility code.

---

## 4. Proposed tool: "HairCraft" (working name) — a Blender-native hybrid

### Guiding principle
Don't re-implement what Blender 4/5 already ships. Blender has: the Curves object + Sculpt Curves mode (add/comb/pinch/puff brushes with surface snapping), the bundled **hair node-group assets** (Interpolate Hair Curves, Clump, Frizz, Curl, Braid, Roll, Trim...), **Principled Hair BSDF** (melanin model ≈ Sisir's shading), curve-to-mesh, and Alembic I/O. Our addon is the **workflow layer** that makes these one-click and adds what's missing.

### Two modes, one shared core

**Shared core (both modes)**
1. **Scalp setup:** auto-detect (from v2) → paintable mask → optional region painting (bangs / sides / back / crown, à la Anime Hair Studio)
2. **Guide/strand authoring:** draw curves snapped to the scalp surface (wraps Sculpt Curves "Add" + Draw); mirror-X toggle; per-region default lengths
3. **One workflow panel** that walks top-to-bottom: Scalp → Strands → Style → Material → Export (progressive disclosure, Sisir-style modules)

**Anime mode** (Anime Hair Studio's model, done with Geometry Nodes)
- Each guide curve gets a parametric **strand mesh**: profile, width/taper float-curves, twist, radial/length resolution — a GN modifier per hair object, non-destructive
- **Braid/coil strand types:** instanced braid geometry along the curve
- **Layers** via curve attributes (bottom/mid/top/accent) with spacing offsets
- **Toon hair shader:** ramp-based base/shadow/highlight + anime highlight band, built as a nodegroup material preset
- Hairstyle **presets** = bundled .blend assets (curves + params), appendable and mirror-aware

**Realistic mode** (Sisir's model, using Blender's stock hair assets)
- Guides → **Interpolate Hair Curves** (density, per-region masks)
- Style stack presets chaining stock nodes: Clump (root/mid/tip), Frizz, Curl, Noise — exposed as 5–10 friendly sliders, not a node editor
- **Length/density painting** = thin wrappers over Sculpt Curves brushes
- **Principled Hair BSDF presets** (melanin slider + redness + roughness; named presets: black/brown/blonde/red/grey)
- Optional quick-drape: Blender hair simulation preset for gravity settle (Sisir's killer convenience)

**Later, differentiating features (borrow the best ideas)**
- **Hair Tie object** (empty + radius): guides within radius get pulled through it — ponytails/buns in one gesture. Nobody in the Blender addon space does this simply.
- Hair **cards baking** for game export; ABC export presets
- Preset "transplant" between .blend files

### Why this can be simpler than both references
- Sisir/AHS had to build viewport, physics, and renderer from scratch — 90% of their code. Inside Blender all of that is free; our entire budget goes to **workflow UX**.
- Target UX: *select head → click "Set Up Scalp" → draw 5–20 strokes → pick mode + preset → tweak 6 sliders → done.*

---

## 5. Phased build plan (draft)

| Phase | Deliverable | Notes |
|---|---|---|
| **0** | Repo reset, keep extension scaffolding; decide Blender min version (4.2 LTS vs 5.x) | half day |
| **1** | Shared core: scalp mask (auto+paint), region painting, "draw strands on scalp" wrapper, workflow panel skeleton | the foundation everything sits on |
| **2** | Anime mode MVP: parametric strand GN (profile/taper/twist), toon shader, mirror, 3 presets | first shippable value |
| **3** | Realistic mode MVP: interpolation + clump/frizz/curl slider stack, Principled Hair presets, length/density paint | mostly wiring stock assets |
| **4** | Braid/coil strand types, layers, hairstyle preset library, quick-drape sim | breadth |
| **5** | Hair ties, cards baking, ABC export presets, docs, polish | differentiation |

Each phase ends installable and testable in Blender (we have the Blender MCP for live verification).

### Decisions & constraints (updated after review)
- **Target: Blender 5.2** (user's current version). Ships as an extension — that's just packaging; the value of staying inside Blender is the free viewport/sculpt/physics/render stack.
- **Model pipelines to support:** FBX heads from Character Creator (realistic mode's natural audience) and VRM from VRoid Studio (anime mode's natural audience). Implications:
  - Hair must bind to **rigged, animated** heads (head-bone parenting / surface deform), not static meshes
  - Normalize CC vs VRoid scale/orientation on setup
  - **VRM spring-bone export** for anime hair = major differentiator for VTuber creators
- **Licensing:** `bpy`-based code is effectively GPL. Selling GPL addons is standard (Blender Market model); commercial, in-house, and open-source options all remain open. Learning from Sisir/AHS feature sets is fine — no code, assets, names, or branding may be copied.
- **Clothing tool synergy:** the Phase 1 core (surface drawing, region masks, parametric GN generation, fitting/collision, presets, toon/PBR materials) is ~60% reusable for a future clothing creator ("draw panels on body" vs "draw strands on scalp"). Build the core as a reusable module.

### Remaining open question
- Anime strands: mesh output only, or keep a curves twin for future sim/spring-bone generation? (Leaning: keep the curves twin — needed for VRM spring bones anyway.)

---

## Sources
- Sisir site: https://sisir-hair-tool.netlify.app/ · binary analysis of Sisir.exe v1.1.202607122158
- Anime Hair Studio: https://ludetools.github.io/Animehairstudio/
- Prior addon: `procedural_scalp_hair/` in this repo
