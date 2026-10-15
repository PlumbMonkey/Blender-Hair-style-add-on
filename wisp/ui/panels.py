"""Wisp workflow panel."""

import bpy

from ..constants import PANEL_CATEGORY, SCALP_GROUP_NAME


class WISP_PT_main(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = PANEL_CATEGORY
    bl_label = "Wisp Hair Creator"

    def draw(self, context):
        layout = self.layout
        s = context.scene.wisp

        # --- Head Setup (Phase 1) ---
        header, body = layout.panel("wisp_sec_head", default_closed=False)
        header.label(text="Head Setup", icon='COMMUNITY')
        if body:
            col = body.column()
            col.operator("wisp.setup_head", icon='VIEWZOOM')
            if s.target:
                pipeline = s.pipeline or "?"
                col.label(text=f"{pipeline}: {s.target.name}", icon='CHECKMARK')
                if s.head_bone:
                    col.label(text=f"Head bone: {s.head_bone}", icon='BONE_DATA')

        # --- Scalp (Phase 1) ---
        header, body = layout.panel("wisp_sec_scalp", default_closed=False)
        header.label(text="Scalp", icon='BRUSH_DATA')
        if body:
            col = body.column()
            col.enabled = s.target is not None
            col.prop(s, "hairline", slider=True)
            col.prop(s, "nape", slider=True)
            col.operator("wisp.detect_scalp", icon='SHADERFX')
            in_paint = (context.active_object is not None
                        and context.active_object.mode == 'WEIGHT_PAINT')
            if in_paint:
                col.operator("wisp.finish_painting", icon='CHECKMARK')
            else:
                col.operator("wisp.paint_scalp", icon='BRUSH_DATA')

        # --- Strands (Phase 2) ---
        header, body = layout.panel("wisp_sec_strands", default_closed=False)
        header.label(text="Strands", icon='CURVES')
        if body:
            from ..core.strands import find_strands
            import bpy as _bpy
            strands = find_strands(_bpy.data, s.target)
            col = body.column()
            col.enabled = s.target is not None
            in_sculpt = context.mode == 'SCULPT_CURVES'

            col.prop(s, "strand_length")
            col.prop(s, "mirror_x", toggle=True)
            if not in_sculpt:
                col.operator("wisp.draw_strands", icon='GREASEPENCIL')
            else:
                grid = col.grid_flow(columns=3, align=True)
                for name, icon in (
                    ("Add", 'ADD'), ("Comb", 'CURVES'), ("Smooth", 'MOD_SMOOTH'),
                    ("Grow/Shrink", 'FULLSCREEN_ENTER'), ("Slide", 'VIEW_PAN'), ("Delete", 'X'),
                ):
                    op = grid.operator("wisp.strand_brush", text=name.split("/")[0], icon=icon)
                    op.brush = name
                col.operator("wisp.trim_offscalp", icon='SHADERFX')
                col.operator("wisp.finish_strands", icon='CHECKMARK')
            if strands:
                col.label(text=f"{len(strands.data.curves)} strands", icon='INFO')

        # --- Hairstyle (realistic) ---
        from ..core.hair_names import find_hair
        hair = find_hair(bpy.data, s.target)
        has_scalp = s.target is not None and s.target.vertex_groups.get(SCALP_GROUP_NAME) is not None

        header, body = layout.panel("wisp_sec_style", default_closed=False)
        header.label(text="Hairstyle", icon='OUTLINER_OB_CURVES')
        if body:
            col = body.column()
            col.enabled = has_scalp
            col.prop(s, "hairstyle", text="")
            sub, sub_body = col.panel("wisp_sec_shape", default_closed=False)
            sub.label(text="Shape")
            if sub_body:
                c = sub_body.column(align=True)
                c.label(text="Length (head heights below crown)")
                c.prop(s, "fringe_length", slider=True)
                c.prop(s, "side_length", slider=True)
                c.prop(s, "back_length", slider=True)
                c = sub_body.column(align=True)
                c.prop(s, "fringe_width")
                c.prop(s, "sweep", slider=True)
                c.prop(s, "fringe_tilt", slider=True)
                c.prop(s, "part", slider=True)
                c = sub_body.column(align=True)
                c.prop(s, "crowns")
                sub_c = c.column(align=True)
                sub_c.enabled = s.crowns > 1
                sub_c.prop(s, "crown_spread", slider=True)
                c.prop(s, "crown_swirl", slider=True)
                c = sub_body.column(align=True)
                c.prop(s, "volume")
                c.prop(s, "fringe_volume", slider=True)
                c.prop(s, "lift", slider=True)
                c.prop(s, "stiffness", slider=True)
                c.prop(s, "flare", slider=True)
                c.prop(s, "flick", slider=True)
                c.prop(s, "length_jitter", slider=True)
                c.prop(s, "fringe_thickness", slider=True)
                c.prop(s, "fringe_pieces", slider=True)
                c.prop(s, "scalp_cap")
                adv, adv_body = sub_body.panel("wisp_sec_shape_adv", default_closed=True)
                adv.label(text="Guides")
                if adv_body:
                    adv_body.prop(s, "guide_spacing")
                    adv_body.prop(s, "seed")
            row = col.row()
            row.scale_y = 1.4
            row.operator("wisp.grow_hair", icon='OUTLINER_OB_CURVES',
                         text="Regrow Hair" if hair else "Grow Hair")
            if not has_scalp:
                col.label(text="Detect the scalp first", icon='INFO')

            sub, sub_body = col.panel("wisp_sec_detail", default_closed=False)
            sub.label(text="Detail (live)")
            if sub_body:
                c = sub_body.column(align=True)
                c.enabled = hair is not None
                c.prop(s, "density")
                c.prop(s, "viewport", slider=True)
                c.prop(s, "radius")
                c.prop(s, "taper_start", slider=True)
                c = sub_body.column(align=True)
                c.enabled = hair is not None
                c.prop(s, "clump", slider=True)
                c.prop(s, "clump_shape", slider=True)
                c.prop(s, "clump_size")
                c.prop(s, "tip_spread")
                c = sub_body.column(align=True)
                c.enabled = hair is not None
                c.prop(s, "noise")
                c.prop(s, "noise_scale")
                c.prop(s, "frizz")
                c.prop(s, "flyaways", slider=True)
                c.prop(s, "flyaway_distance")
                c.prop(s, "smooth", slider=True)

        # --- Dynamics ---
        header, body = layout.panel("wisp_sec_dynamics", default_closed=True)
        header.prop(s, "dynamics", text="")
        header.label(text="Dynamics", icon='PHYSICS')
        if body:
            col = body.column(align=True)
            col.enabled = hair is not None
            body.prop(s, "playback", expand=True)
            col.prop(s, "dyn_stiffness", slider=True)
            col.prop(s, "dyn_root_hold", slider=True)
            col.prop(s, "dyn_damping")
            col.prop(s, "dyn_collision")
            row = body.row(align=True)
            row.enabled = hair is not None and s.dynamics
            row.operator("wisp.bake_dynamics", icon='REC')
            row.operator("wisp.free_dynamics", icon='TRASH', text="")
            body.label(text="Plays from the scene's start frame", icon='INFO')

        # --- Material ---
        header, body = layout.panel("wisp_sec_material", default_closed=False)
        header.label(text="Material", icon='MATERIAL')
        if body:
            col = body.column(align=True)
            col.enabled = hair is not None
            col.prop(s, "hair_color", text="")
            col.prop(s, "melanin", slider=True)
            col.prop(s, "redness", slider=True)
            col.prop(s, "roughness", slider=True)
            col.prop(s, "color_variation", slider=True)
            col.prop(s, "tip_lighten", slider=True)
            col.prop(s, "tint")

        # --- Pipeline ---
        header, body = layout.panel("wisp_sec_export", default_closed=True)
        header.label(text="Pipeline", icon='EXPORT')
        if body:
            col = body.column()
            col.enabled = bool(s.armature_name)
            col.operator("wisp.apply_motion", icon='ARMATURE_DATA')
            col.label(text="e.g. an iClone 8 FBX export of this character", icon='INFO')


CLASSES = (WISP_PT_main,)
