"""Wisp — simple, intuitive hair creation for Blender 5.1+.

Anime and realistic hair for Character Creator (FBX), VRoid (VRM), and
generic heads. See BUILD-PLAN.md at the repo root.
"""

import bpy

from . import properties
from . import operators
from .ui import panels

_ALL_CLASSES = (
    *operators.CLASSES,
    *panels.CLASSES,
)


def register():
    properties.register()
    for cls in _ALL_CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_ALL_CLASSES):
        bpy.utils.unregister_class(cls)
    properties.unregister()
