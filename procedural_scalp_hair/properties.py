"""Blender property definitions for the addon."""

import bpy
from bpy.props import (
    FloatProperty,
    IntProperty,
    EnumProperty,
)


class PMKHairProperties(bpy.types.PropertyGroup):
    # Head/scalp detection heuristics
    head_upper_fraction: FloatProperty(
        name="Head Upper Fraction",
        default=0.35,
        min=0.15,
        max=0.60,
        description="Upper body fraction assumed to contain the head",
    )
    scalp_height_ratio: FloatProperty(
        name="Scalp Height",
        default=0.40,
        min=0.15,
        max=0.85,
        description="Relative head height threshold for scalp seed region",
    )
    min_up_normal: FloatProperty(
        name="Min Up Normal",
        default=-0.05,
        min=-1.0,
        max=1.0,
        description="Minimum Z component for allowed scalp normals",
    )
    min_radial_normal: FloatProperty(
        name="Min Radial Normal",
        default=0.15,
        min=-1.0,
        max=1.0,
        description="Minimum outward normal relative to head center",
    )
    max_forward_normal: FloatProperty(
        name="Max Forward Normal",
        default=0.55,
        min=-1.0,
        max=1.0,
        description="Reject normals strongly pointing toward face front",
    )
    max_curvature: FloatProperty(
        name="Max Curvature",
        default=0.78,
        min=0.1,
        max=2.2,
        description="Maximum average normal-angle (radians) for scalp smoothness",
    )
    radius_min_ratio: FloatProperty(
        name="Radius Min",
        default=0.35,
        min=0.0,
        max=1.5,
        description="Minimum radial distance ratio from head center",
    )
    radius_max_ratio: FloatProperty(
        name="Radius Max",
        default=1.08,
        min=0.2,
        max=2.0,
        description="Maximum radial distance ratio from head center",
    )
    face_exclusion_ratio: FloatProperty(
        name="Face Exclusion",
        default=0.08,
        min=-0.3,
        max=0.6,
        description="Moves exclusion plane to reduce nose/cheek inclusion",
    )
    side_ear_zone_ratio: FloatProperty(
        name="Ear Zone Width",
        default=0.56,
        min=0.2,
        max=0.95,
        description="Lateral zone where scalp extends downward for sideburns",
    )
    sideburn_length: FloatProperty(
        name="Sideburn Length",
        default=0.06,
        min=0.0,
        max=0.25,
        subtype='DISTANCE',
        description="Downward extension near ears (meters in world scale)",
    )
    cleanup_passes: IntProperty(
        name="Cleanup Passes",
        default=2,
        min=0,
        max=5,
    )

    # Hair generation controls
    style_preset: EnumProperty(
        name="Preset",
        items=[
            ('SHORT', "Short", "Short style: dense, low length"),
            ('MEDIUM', "Medium", "Medium style"),
            ('LONG', "Long", "Long style: gravity-influenced"),
        ],
        default='MEDIUM',
    )
    density: FloatProperty(name="Density", default=520.0, min=50.0, max=2000.0)
    length: FloatProperty(name="Length", default=0.11, min=0.005, max=0.8)
    noise: FloatProperty(name="Noise", default=0.06, min=0.0, max=0.6)
    clump: FloatProperty(name="Clump", default=0.18, min=0.0, max=1.0)
    direction_bias: FloatProperty(
        name="Direction Bias",
        default=0.15,
        min=-1.0,
        max=1.0,
        description="Positive = outward lift, negative = gravity/downward tendency",
    )
    hairline_height: FloatProperty(name="Hairline Height", default=0.08, min=0.01, max=0.3)
    hairline_curve: FloatProperty(name="Hairline Curvature", default=0.6, min=0.0, max=1.0)
