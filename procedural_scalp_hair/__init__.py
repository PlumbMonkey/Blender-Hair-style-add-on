bl_info = {
    "name": "Procedural Scalp Hair Generator",
    "author": "PMK Studio",
    "version": (2, 1, 0),
    "blender": (5, 1, 0),
    "location": "View3D > Sidebar > HairGen",
    "description": "Detect scalp mask heuristically and generate procedural hair with Geometry Nodes",
    "category": "Object",
    "doc_url": "",
    "tracker_url": "",
}

import bpy
from bpy.props import PointerProperty

from .properties import PMKHairProperties
from .operators import (
    PMK_OT_ApplyPreset,
    PMK_OT_GenerateScalpMask,
    PMK_OT_GenerateHair,
    PMK_OT_ResetDefaults,
)
from .panels import PMK_PT_HairPanel


classes = (
    PMKHairProperties,
    PMK_OT_ApplyPreset,
    PMK_OT_GenerateScalpMask,
    PMK_OT_GenerateHair,
    PMK_OT_ResetDefaults,
    PMK_PT_HairPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.pmk_hair_props = PointerProperty(type=PMKHairProperties)


def unregister():
    if hasattr(bpy.types.Scene, "pmk_hair_props"):
        del bpy.types.Scene.pmk_hair_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
