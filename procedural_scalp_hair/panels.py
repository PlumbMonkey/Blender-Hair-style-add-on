"""UI Panel for the HairGen sidebar tab."""

import bpy


class PMK_PT_HairPanel(bpy.types.Panel):
    bl_label = "Procedural Scalp Hair"
    bl_idname = "PMK_PT_hair_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "HairGen"

    def draw(self, context):
        layout = self.layout
        props = context.scene.pmk_hair_props

        # --- Scalp Detection Section ---
        header, body = layout.panel("PMK_scalp_detection", default_closed=False)
        header.label(text="Scalp Detection", icon='MOD_VERTEX_WEIGHT')
        if body:
            body.prop(props, "head_upper_fraction")
            body.prop(props, "scalp_height_ratio")
            body.prop(props, "face_exclusion_ratio")
            body.prop(props, "sideburn_length")
            body.prop(props, "cleanup_passes")

            adv_header, adv_body = body.panel("PMK_scalp_advanced", default_closed=True)
            adv_header.label(text="Advanced Thresholds")
            if adv_body:
                adv_body.prop(props, "min_up_normal")
                adv_body.prop(props, "min_radial_normal")
                adv_body.prop(props, "max_forward_normal")
                adv_body.prop(props, "max_curvature")
                adv_body.prop(props, "radius_min_ratio")
                adv_body.prop(props, "radius_max_ratio")
                adv_body.prop(props, "side_ear_zone_ratio")

            body.operator("pmk_hair.generate_scalp_mask", icon='GROUP_VERTEX')

        # --- Hair Generation Section ---
        header2, body2 = layout.panel("PMK_hair_generation", default_closed=False)
        header2.label(text="Hair Generation", icon='PARTICLE_HAIR')
        if body2:
            row = body2.row(align=True)
            row.prop(props, "style_preset", text="")
            row.operator("pmk_hair.apply_preset", text="Apply")

            body2.prop(props, "density")
            body2.prop(props, "length")
            body2.prop(props, "noise")
            body2.prop(props, "clump")
            body2.prop(props, "direction_bias")
            body2.prop(props, "hairline_height")
            body2.prop(props, "hairline_curve")
            body2.operator("pmk_hair.generate_hair", icon='MOD_NODES')

        # --- Footer ---
        layout.separator()
        row = layout.row()
        row.operator("pmk_hair.reset_defaults", icon='LOOP_BACK')
        layout.label(text="Vertex Group Output: SCALP_MASK", icon='INFO')
