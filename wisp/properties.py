"""Wisp scene settings."""

import bpy
from bpy.props import (
    PointerProperty,
    StringProperty,
    FloatProperty,
    BoolProperty,
    IntProperty,
    EnumProperty,
    FloatVectorProperty,
)

from .presets import HAIRSTYLE_PRESETS, COLOR_LABELS


def _mesh_only(self, obj):
    return obj.type == 'MESH'


# --- live updates ----------------------------------------------------------

def _hair_obj(settings):
    from .core.hair_names import find_hair
    return find_hair(bpy.data, settings.target)


def _update_detail(self, context):
    hair = _hair_obj(self)
    if hair is None:
        return
    from .core.hair_stack import apply_style
    from .constants import SCALP_GROUP_NAME
    apply_style(hair, self, SCALP_GROUP_NAME)


def _update_color(self, context):
    hair = _hair_obj(self)
    if hair is None or not hair.data.materials:
        return
    from .core.hair_material import apply_color
    apply_color(hair.data.materials[0], self.melanin, self.redness,
                self.roughness, 0.3, random_color=self.color_variation, tint=tuple(self.tint),
                tip_lighten=self.tip_lighten)


def _load_hairstyle(self, context):
    p = HAIRSTYLE_PRESETS[self.hairstyle]
    for k, v in {**p['shape'], **p['detail']}.items():
        setattr(self, k, v)
    if 'color' in p:
        self.hair_color = p['color']
    for k, v in p.get('material', {}).items():
        setattr(self, k, v)


def _load_color(self, context):
    from .core.hair_material import preset_values
    mel, red, rough, _ = preset_values(self.hair_color)
    self.melanin, self.redness, self.roughness = mel, red, rough


def _sync_mirror(settings, context):
    from .core.strands import find_strands
    strands = find_strands(bpy.data, settings.target)
    if strands:
        strands.data.use_mirror_x = settings.mirror_x


def _detail(name, default, lo, hi, desc, subtype='NONE', precision=3):
    return FloatProperty(name=name, default=default, min=lo, max=hi, description=desc,
                         subtype=subtype, precision=precision, update=_update_detail)


class WispSettings(bpy.types.PropertyGroup):
    target: PointerProperty(
        name="Body Mesh",
        type=bpy.types.Object,
        poll=_mesh_only,
        description="Mesh containing the scalp skin",
    )
    armature_name: StringProperty(default="")
    head_bone: StringProperty(default="")
    pipeline: StringProperty(default="")

    hairline: FloatProperty(
        name="Hairline",
        default=0.55, min=0.30, max=0.80,
        description="Front hairline height on the head (lower = more forehead covered)",
    )
    nape: FloatProperty(
        name="Nape",
        default=0.30, min=0.05, max=0.60,
        description="How far down the back of the head the scalp reaches",
    )

    # --- Strands (Phase 2) ---
    strand_length: FloatProperty(
        name="Strand Length",
        default=0.15, min=0.01, max=1.0,
        subtype='DISTANCE',
        description="Length of newly drawn strands",
    )
    mirror_x: BoolProperty(
        name="Mirror X",
        default=True,
        description="Symmetrize strand drawing and editing across X",
        update=lambda self, ctx: _sync_mirror(self, ctx),
    )

    # --- Realistic hairstyle: shape (applied by Grow Hair) ---
    hairstyle: EnumProperty(
        name="Hairstyle",
        items=[(k, v['label'], v['description']) for k, v in HAIRSTYLE_PRESETS.items()],
        default='MOP_TOP',
        update=_load_hairstyle,
        description="Starting point for the groom — loads the shape and detail sliders",
    )
    fringe_length: FloatProperty(
        name="Fringe", default=0.56, min=0.15, max=2.5,
        description="Where the fringe ends, in head heights below the crown (0.5 ≈ eyes, 1 ≈ chin)")
    side_length: FloatProperty(
        name="Sides", default=1.06, min=0.2, max=3.0,
        description="Where the sides end, in head heights below the crown (1 ≈ chin, 1.3 ≈ shoulders)")
    back_length: FloatProperty(
        name="Back", default=1.12, min=0.2, max=3.5,
        description="Where the back ends, in head heights below the crown")
    fringe_width: FloatProperty(
        name="Fringe Width", default=50.0, min=0.0, max=90.0,
        description="How far round the face (degrees either side) the fringe reaches")
    volume: FloatProperty(
        name="Volume", default=0.012, min=0.002, max=0.06, subtype='DISTANCE', precision=3,
        description="How far the hair stands off the head")
    fringe_volume: FloatProperty(
        name="Fringe Volume", default=0.6, min=0.0, max=2.0,
        description="How far the fringe stands off the forehead, relative to Volume (low = flat, high = swoop)")
    lift: FloatProperty(
        name="Root Lift", default=0.3, min=0.0, max=1.0,
        description="How much the hair springs up from the roots")
    stiffness: FloatProperty(
        name="Stiffness", default=0.35, min=0.0, max=1.0,
        description="0 = drops straight down, 1 = holds its combed direction")
    part: FloatProperty(
        name="Part", default=-0.3, min=-1.0, max=1.0,
        description="Part position across the head (0 = centre, + = character's left)")
    sweep: FloatProperty(
        name="Fringe Sweep", default=0.5, min=-1.0, max=1.0,
        description="Sideways sweep of the fringe (+ = toward the character's left)")
    fringe_tilt: FloatProperty(
        name="Fringe Tilt", default=0.1, min=-0.5, max=0.5,
        description="How much longer the fringe gets toward the character's left (+) or right (-)")
    flick: FloatProperty(
        name="Flick", default=0.8, min=0.0, max=1.0,
        description="Outward flip at the ends")
    flare: FloatProperty(
        name="Flare", default=0.02, min=0.0, max=0.5,
        description="How much the sides fan out as they fall")
    length_jitter: FloatProperty(
        name="Choppiness", default=0.06, min=0.0, max=0.4,
        description="Random length variation at the ends")
    fringe_thickness: FloatProperty(
        name="Fringe Thickness", default=1.0, min=1.0, max=3.0,
        description="Extra hair in the fringe relative to the rest of the head (applied on Grow Hair)")
    fringe_pieces: FloatProperty(
        name="Fringe Pieces", default=0.7, min=0.0, max=1.0,
        description="Gathers the fringe tips into pointed, piecey sections (applied on Grow Hair)")
    scalp_cap: BoolProperty(
        name="Scalp Cap", default=True,
        description="Add a thin hair-coloured shell under the hair so partings and the crown never show bright skin")
    crowns: IntProperty(name="Crowns", default=1, min=1, max=3,
                        description="Number of whorls on the crown — the hair radiates from each")
    crown_spread: FloatProperty(name="Crown Spread", default=0.35, min=0.05, max=1.0,
                                description="Spacing of the extra crowns")
    crown_swirl: FloatProperty(name="Crown Swirl", default=0.3, min=0.0, max=1.5,
                               description="How much the hair spirals around each crown")
    guide_spacing: FloatProperty(
        name="Guide Spacing", default=0.012, min=0.005, max=0.04, subtype='DISTANCE', precision=3,
        description="Distance between guide strands (smaller = more detail, slower)")
    seed: IntProperty(name="Seed", default=1, min=0)

    # --- Realistic hairstyle: detail (live) ---
    density: _detail("Density", 150.0, 5.0, 400.0, "Hairs per cm² of scalp (human ≈ 150–250)", precision=0)
    playback: EnumProperty(
        name="Playback Quality",
        items=[('FULL', "Full", "Viewport shows the finished groom (slow on animation)"),
               ('FAST', "Fast", "Viewport shows fewer, unstyled hairs — for scrubbing and playback"),
               ('GUIDES', "Guides", "Viewport shows only the simulated guide strands — real-time")],
        default='FAST', update=_update_detail,
        description="Viewport only — renders always use the full groom")
    viewport: _detail("Viewport %", 0.3, 0.01, 1.0, "Fraction of hairs shown in the viewport (renders use all)", 'FACTOR', 2)
    clump: _detail("Clump", 0.5, 0.0, 1.0, "How strongly hairs gather into locks", 'FACTOR', 2)
    clump_shape: _detail("Clump Shape", 0.2, -1.0, 1.0, "Lock profile (+ = pointed tips)", 'NONE', 2)
    clump_size: _detail("Lock Size", 0.008, 0.002, 0.04, "Distance between lock centres", 'DISTANCE')
    tip_spread: _detail("Tip Spread", 0.001, 0.0, 0.02, "How far lock tips fan apart", 'DISTANCE', 4)
    noise: _detail("Waviness", 0.003, 0.0, 0.03, "Soft, large waves", 'DISTANCE', 4)
    noise_scale: _detail("Wave Scale", 5.0, 0.5, 30.0, "Wave frequency", 'NONE', 1)
    frizz: _detail("Frizz", 0.0006, 0.0, 0.01, "Fine per-hair flyaways", 'DISTANCE', 4)
    smooth: _detail("Smooth", 0.5, 0.0, 1.0, "Smooths out guide kinks", 'FACTOR', 2)
    taper_start: _detail("Tip Taper", 0.75, 0.0, 0.98, "Where along the hair the tip taper begins (lower = longer, finer tips)", 'FACTOR', 2)
    flyaways: _detail("Flyaways", 0.03, 0.0, 0.2, "Fraction of hairs that wander loose from the groom", 'FACTOR', 3)
    flyaway_distance: _detail("Flyaway Reach", 0.02, 0.0, 0.08, "How far flyaways stray at their tips", 'DISTANCE')
    radius: _detail("Thickness", 0.00012, 0.00002, 0.001, "Radius of one hair at the root", 'DISTANCE', 5)

    # --- Dynamics (live) ---
    dynamics: BoolProperty(name="Dynamics", default=False, update=_update_detail,
                           description="Simulate the hair (sways, bounces, settles). Off = the hair rigidly follows the skin")
    dyn_stiffness: _detail("Hair Stiffness", 0.25, 0.0, 1.0, "How strongly the hair holds its styled shape while moving", 'FACTOR', 2)
    dyn_damping: _detail("Damping", 0.15, 0.0, 1.0, "Share of motion lost each frame — higher settles faster", 'FACTOR', 2)
    dyn_root_hold: _detail("Root Hold", 0.35, 0.0, 0.8, "How much of each hair, from the root, keeps its styled shape while moving (keeps the scalp covered)", 'FACTOR', 2)
    dyn_collision: BoolProperty(name="Collide with Body", default=True, update=_update_detail,
                                description="Keep simulated hair out of the head, neck and shoulders")

    # --- Material ---
    hair_color: EnumProperty(
        name="Colour",
        items=[(k, v, "") for k, v in COLOR_LABELS.items()],
        default='DARK_BROWN',
        update=_load_color,
    )
    melanin: FloatProperty(name="Melanin", default=0.80, min=0.0, max=1.0, update=_update_color,
                           description="Pigment amount: 0 = white/blonde, 1 = black")
    redness: FloatProperty(name="Redness", default=0.30, min=0.0, max=1.0, update=_update_color,
                           description="Share of red pigment (pheomelanin)")
    roughness: FloatProperty(name="Roughness", default=0.28, min=0.05, max=1.0, update=_update_color,
                             description="Lower = shinier hair")
    tip_lighten: FloatProperty(name="Sun-Lightened Tips", default=0.08, min=0.0, max=0.4, update=_update_color,
                               description="How much lighter the tips are than the roots")
    tint: FloatVectorProperty(name="Tint", subtype='COLOR', size=3, default=(1.0, 1.0, 1.0),
                              min=0.0, max=1.0, update=_update_color,
                              description="Multiplies the pigment colour (e.g. warm gold for sun-lightened hair)")
    color_variation: FloatProperty(name="Variation", default=0.08, min=0.0, max=1.0, update=_update_color,
                                   description="Per-strand colour variation")


def register():
    bpy.utils.register_class(WispSettings)
    bpy.types.Scene.wisp = PointerProperty(type=WispSettings)


def unregister():
    del bpy.types.Scene.wisp
    bpy.utils.unregister_class(WispSettings)
