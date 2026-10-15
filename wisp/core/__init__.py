"""Wisp core — shared engine module.

Everything in this package is designed to be reusable by Drape (the
clothing tool). Rules for code that lives here:

- No dependency on Wisp UI, operators, or PropertyGroups.
  Functions take plain parameter objects (dataclasses) or explicit args.
  Blender PropertyGroups with matching attribute names may be passed in,
  but must never be required.
- bpy/bmesh/mathutils are allowed (this is Blender-side code), but keep
  scene-state assumptions out: no bpy.context reads inside core logic —
  callers pass objects explicitly.

Contents:
- geometry:      mesh math, bounds, curvature, vertex-group helpers
- scalp_detect:  heuristic surface-region detection (scalp today,
                 generalizable to body regions for Drape)
- nodes:         Geometry Nodes builder utilities
- groom:         procedural guide growth (head proxy, collision, presets-agnostic)
- hair_stack:    stock hair node assets as a modifier stack (5.2 inputs API)
- hair_material: Principled Hair (melanin) with an EEVEE-matched colour
"""
