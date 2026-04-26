"""Operators for scalp mask and hair generation."""

import bpy

from .constants import SCALP_GROUP_NAME
from .geometry_utils import get_active_mesh
from .scalp_mask import generate_scalp_mask, ensure_hairline_group
from .hair_nodes import ensure_hair_modifier
from .presets import apply_style_preset


def _ensure_object_mode(context):
    """Switch to Object mode if not already there. Returns True if mode was changed."""
    if context.active_object and context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
        return True
    return False


class PMK_OT_ApplyPreset(bpy.types.Operator):
    bl_idname = "pmk_hair.apply_preset"
    bl_label = "Apply Hairstyle Preset"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.pmk_hair_props
        apply_style_preset(props, props.style_preset)
        self.report({'INFO'}, f"Applied preset: {props.style_preset}")
        return {'FINISHED'}


class PMK_OT_GenerateScalpMask(bpy.types.Operator):
    bl_idname = "pmk_hair.generate_scalp_mask"
    bl_label = "Generate Scalp Mask"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = get_active_mesh(context)
        if obj is None:
            self.report({'ERROR'}, "Select a mesh object first")
            return {'CANCELLED'}

        _ensure_object_mode(context)

        props = context.scene.pmk_hair_props
        try:
            count = generate_scalp_mask(obj, props)
        except Exception as ex:
            self.report({'ERROR'}, f"Scalp mask generation failed: {ex}")
            return {'CANCELLED'}

        if count == 0:
            self.report({'WARNING'}, "No scalp vertices detected. Tune thresholds.")
        else:
            ensure_hairline_group(
                obj,
                SCALP_GROUP_NAME,
                group_name="HAIRLINE_MASK",
                front_band=props.hairline_height,
            )
            self.report({'INFO'}, f"SCALP_MASK generated with {count} vertices")

        return {'FINISHED'}


class PMK_OT_GenerateHair(bpy.types.Operator):
    bl_idname = "pmk_hair.generate_hair"
    bl_label = "Generate Hair"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = get_active_mesh(context)
        if obj is None:
            self.report({'ERROR'}, "Select a mesh object first")
            return {'CANCELLED'}

        if obj.vertex_groups.get(SCALP_GROUP_NAME) is None:
            self.report({'ERROR'}, "SCALP_MASK missing. Run Generate Scalp Mask first.")
            return {'CANCELLED'}

        _ensure_object_mode(context)

        props = context.scene.pmk_hair_props

        try:
            ensure_hairline_group(
                obj,
                SCALP_GROUP_NAME,
                group_name="HAIRLINE_MASK",
                front_band=props.hairline_height,
            )
            ensure_hair_modifier(obj, props)
        except Exception as ex:
            self.report({'ERROR'}, f"Hair generation failed: {ex}")
            return {'CANCELLED'}

        self.report({'INFO'}, "Geometry Nodes hair generated")
        return {'FINISHED'}


class PMK_OT_ResetDefaults(bpy.types.Operator):
    bl_idname = "pmk_hair.reset_defaults"
    bl_label = "Reset to Defaults"
    bl_description = "Reset all hair generation parameters to their default values"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.pmk_hair_props
        for key in props.__annotations__:
            props.property_unset(key)
        self.report({'INFO'}, "All parameters reset to defaults")
        return {'FINISHED'}
