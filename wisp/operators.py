"""Wisp operators — head setup, scalp, strands and realistic grooming."""

import bpy

from .constants import SCALP_GROUP_NAME, REGION_GROUP_MAP
from .core.rig import find_armature, detect_pipeline, find_head_bone, find_body_mesh, find_eye_z
from .core import groom
from .core.hair_names import hair_name_for, find_hair
from .core.hair_stack import apply_style
from .core.hair_material import ensure_hair_material, apply_color, eevee_color
from .core.hair_stack import FRINGE_GROUP, DENSITY_GROUP
from .core import scalp_cap
from .core.scalp_detect import ScalpDetectParams, detect_scalp, split_scalp_regions
from .core.strands import (
    strands_name_for,
    find_strands,
    offscalp_curve_indices,
    remove_curves_by_index,
)

BRUSH_ASSET_PATH = "brushes/essentials_brushes-curve_sculpt.blend/Brush/{}"


def _activate_curves_brush(name):
    bpy.ops.brush.asset_activate(
        asset_library_type='ESSENTIALS',
        relative_asset_identifier=BRUSH_ASSET_PATH.format(name),
    )
    return bpy.context.scene.tool_settings.curves_sculpt.brush


def _apply_add_brush_defaults(brush, settings):
    cs = brush.curves_sculpt_settings
    cs.curve_length = settings.strand_length
    cs.points_per_curve = 8
    cs.add_amount = 1

PIPELINE_LABELS = {
    'CC': "Character Creator",
    'VROID': "VRoid",
    'GENERIC': "Generic",
}


class WISP_OT_setup_head(bpy.types.Operator):
    """Detect the character pipeline, armature, head bone and body mesh
    from the active object (select any part of the character)"""
    bl_idname = "wisp.setup_head"
    bl_label = "Set Up Character"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if obj is None:
            self.report({'ERROR'}, "Select any part of the character first")
            return {'CANCELLED'}

        arm = obj if obj.type == 'ARMATURE' else find_armature(obj)
        pipeline = detect_pipeline(arm)
        head_bone = find_head_bone(arm)
        body = obj if (obj.type == 'MESH' and arm is None) else find_body_mesh(arm, pipeline)

        if body is None:
            self.report({'ERROR'}, "No body mesh found on this character")
            return {'CANCELLED'}

        s = context.scene.wisp
        s.target = body
        s.armature_name = arm.name if arm else ""
        s.head_bone = head_bone or ""
        s.pipeline = pipeline

        msg = f"{PIPELINE_LABELS[pipeline]}: body '{body.name}'"
        msg += f", head bone '{head_bone}'" if head_bone else ", no head bone (generic mode)"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class WISP_OT_detect_scalp(bpy.types.Operator):
    """Detect the scalp on the body mesh and split it into regions"""
    bl_idname = "wisp.detect_scalp"
    bl_label = "Detect Scalp"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.wisp.target is not None

    def execute(self, context):
        s = context.scene.wisp
        obj = s.target
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        params = ScalpDetectParams(hairline_ratio=s.hairline, nape_ratio=s.nape)
        count = detect_scalp(obj, SCALP_GROUP_NAME, params, head_bone_name=s.head_bone or None)
        if count == 0:
            self.report({'WARNING'}, "No scalp detected — adjust Hairline/Nape or check setup")
            return {'CANCELLED'}

        counts = split_scalp_regions(obj, SCALP_GROUP_NAME, REGION_GROUP_MAP)
        self.report({'INFO'}, f"Scalp: {count} verts | " +
                    ", ".join(f"{k.title()}: {v}" for k, v in counts.items()))
        return {'FINISHED'}


class WISP_OT_paint_scalp(bpy.types.Operator):
    """Refine the scalp mask by weight painting (paint = scalp, erase = skin)"""
    bl_idname = "wisp.paint_scalp"
    bl_label = "Refine by Painting"

    @classmethod
    def poll(cls, context):
        s = context.scene.wisp
        return s.target is not None and s.target.vertex_groups.get(SCALP_GROUP_NAME)

    def execute(self, context):
        s = context.scene.wisp
        obj = s.target
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        context.view_layer.objects.active = obj
        obj.vertex_groups.active = obj.vertex_groups[SCALP_GROUP_NAME]
        bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
        self.report({'INFO'}, "Painting WISP_SCALP — click Finish Painting when done")
        return {'FINISHED'}


class WISP_OT_finish_painting(bpy.types.Operator):
    """Return to object mode and rebuild scalp regions from the edited mask"""
    bl_idname = "wisp.finish_painting"
    bl_label = "Finish Painting"

    def execute(self, context):
        bpy.ops.object.mode_set(mode='OBJECT')
        s = context.scene.wisp
        if s.target:
            counts = split_scalp_regions(s.target, SCALP_GROUP_NAME, REGION_GROUP_MAP)
            if counts:
                self.report({'INFO'}, "Regions rebuilt from painted mask")
        return {'FINISHED'}


class WISP_OT_draw_strands(bpy.types.Operator):
    """Create (or continue editing) the strand set and start drawing on the
    head with the Add brush. Draw strokes on the scalp; use the brush
    buttons to comb, smooth or delete"""
    bl_idname = "wisp.draw_strands"
    bl_label = "Draw Strands"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.scene.wisp.target is not None

    def execute(self, context):
        s = context.scene.wisp
        body = s.target
        strands = find_strands(bpy.data, body)

        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if strands is None:
            bpy.ops.object.select_all(action='DESELECT')
            body.select_set(True)
            context.view_layer.objects.active = body
            bpy.ops.object.curves_empty_hair_add()
            strands = context.active_object
            strands.name = strands_name_for(body)
            strands.data.name = strands.name

        strands.data.use_mirror_x = s.mirror_x
        bpy.ops.object.select_all(action='DESELECT')
        strands.select_set(True)
        context.view_layer.objects.active = strands
        bpy.ops.object.mode_set(mode='SCULPT_CURVES')

        try:
            brush = _activate_curves_brush("Add")
            _apply_add_brush_defaults(brush, s)
        except Exception as ex:
            self.report({'WARNING'}, f"Draw mode active, but brush setup failed: {ex}")
            return {'FINISHED'}

        self.report({'INFO'}, "Drawing strands — stroke on the scalp")
        return {'FINISHED'}


class WISP_OT_strand_brush(bpy.types.Operator):
    """Switch the active strand sculpting brush"""
    bl_idname = "wisp.strand_brush"
    bl_label = "Strand Brush"

    brush: bpy.props.StringProperty()

    @classmethod
    def poll(cls, context):
        return context.mode == 'SCULPT_CURVES'

    def execute(self, context):
        try:
            brush = _activate_curves_brush(self.brush)
        except Exception as ex:
            self.report({'ERROR'}, f"Brush '{self.brush}' failed: {ex}")
            return {'CANCELLED'}
        if self.brush == "Add":
            _apply_add_brush_defaults(brush, context.scene.wisp)
        return {'FINISHED'}


class WISP_OT_trim_offscalp(bpy.types.Operator):
    """Delete strands whose root is not on the scalp"""
    bl_idname = "wisp.trim_offscalp"
    bl_label = "Remove Off-Scalp Strands"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.wisp
        return s.target is not None and find_strands(bpy.data, s.target) is not None

    def execute(self, context):
        s = context.scene.wisp
        strands = find_strands(bpy.data, s.target)
        was_sculpt = context.mode == 'SCULPT_CURVES'
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bad = offscalp_curve_indices(strands, s.target, SCALP_GROUP_NAME, max_dist=0.02)
        removed = remove_curves_by_index(strands, bad)

        if was_sculpt:
            context.view_layer.objects.active = strands
            bpy.ops.object.mode_set(mode='SCULPT_CURVES')
        self.report({'INFO'}, f"Removed {removed} off-scalp strand(s)")
        return {'FINISHED'}


class WISP_OT_finish_strands(bpy.types.Operator):
    """Leave strand drawing mode"""
    bl_idname = "wisp.finish_strands"
    bl_label = "Finish Strands"

    def execute(self, context):
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}


SHAPE_FIELDS = ("fringe_length", "side_length", "back_length", "fringe_width", "volume", "fringe_volume",
                "lift", "stiffness", "part", "sweep", "fringe_tilt", "flick", "flare",
                "crowns", "crown_spread", "crown_swirl",
                "length_jitter", "guide_spacing", "seed")

# collide with clothes that sit near the hair (collars, hoods), never with hair
CLOTHING_HINTS = ("shirt", "top", "jacket", "hood", "coat", "dress", "sweater", "hoodie")


def _collision_meshes(body, depsgraph):
    """[(verts, polys)] of the body (minus eyelash cards) first, then any
    upper-body clothing on the same rig."""
    verts, polys, _ = groom.evaluated_world_mesh(body, depsgraph, ("eyelash",))
    meshes = [(verts, polys)]
    arm = find_armature(body)
    if arm is not None:
        for o in arm.children_recursive:
            if o.type == 'MESH' and o is not body and o.visible_get() and any(
                    h in o.name.lower() for h in CLOTHING_HINTS):
                v, p, _ = groom.evaluated_world_mesh(o, depsgraph)
                meshes.append((v, p))
    return meshes


def parent_to_head(context, obj, arm, head_bone):
    """Parent to the head bone, keeping the world transform, so the object
    follows the head."""
    if arm is None or not head_bone or head_bone not in arm.data.bones:
        return
    world = obj.matrix_world.copy()
    obj.parent = arm
    obj.parent_type = 'BONE'
    obj.parent_bone = head_bone
    context.view_layer.update()
    obj.matrix_world = world
    context.view_layer.update()


def write_fringe_weights(body, depsgraph, frame, gp, strength, thickness=1.0):
    """WISP_FRINGE = strength × fringe membership (read by the fringe-only
    clump), and WISP_DENSITY = scalp weight scaled so that, with the stack's
    density raised by ``thickness``, only the fringe gets extra hair."""
    scalp = body.vertex_groups.get(SCALP_GROUP_NAME)
    if scalp is None:
        return
    vg = body.vertex_groups.get(FRINGE_GROUP) or body.vertex_groups.new(name=FRINGE_GROUP)
    dens = body.vertex_groups.get(DENSITY_GROUP) or body.vertex_groups.new(name=DENSITY_GROUP)
    thickness = max(1.0, thickness)
    ev = body.evaluated_get(depsgraph)
    me = ev.to_mesh()
    mw = body.matrix_world
    si = scalp.index
    for v in body.data.vertices:
        w = next((g.weight for g in v.groups if g.group == si), 0.0)
        if w <= 0.0:
            continue
        f = groom.fringe_weight(mw @ me.vertices[v.index].co, frame, gp)
        vg.add([v.index], strength * f * w, 'REPLACE')
        dens.add([v.index], w * (1.0 + (thickness - 1.0) * f) / thickness, 'REPLACE')
    ev.to_mesh_clear()


def ensure_scalp_cap(context, body, depsgraph, arm, s):
    built = scalp_cap.build_scalp_cap(body, depsgraph, SCALP_GROUP_NAME)
    remove_scalp_cap(body)
    if built is None:
        return None
    verts, polys = built
    name = scalp_cap.cap_name_for(body)
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], polys)
    me.shade_smooth() if hasattr(me, "shade_smooth") else None
    cap = bpy.data.objects.new(name, me)
    (body.users_collection[0] if body.users_collection else context.scene.collection).objects.link(cap)
    root_melanin = min(1.0, s.melanin + 0.06)
    color = tuple(c * t for c, t in zip(eevee_color(root_melanin, s.redness), s.tint))
    me.materials.append(scalp_cap.ensure_cap_material(color))
    parent_to_head(context, cap, arm, s.head_bone)
    return cap


def remove_scalp_cap(body):
    cap = bpy.data.objects.get(scalp_cap.cap_name_for(body))
    if cap is not None:
        me = cap.data
        bpy.data.objects.remove(cap)
        if me.users == 0:
            bpy.data.meshes.remove(me)


class WISP_OT_grow_hair(bpy.types.Operator):
    """Grow a realistic groom from the scalp using the hairstyle shape
    settings: guide strands + Blender's hair node stack + hair material.
    Re-run after changing the shape sliders; detail and colour update live"""
    bl_idname = "wisp.grow_hair"
    bl_label = "Grow Hair"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        s = context.scene.wisp
        return s.target is not None and s.target.vertex_groups.get(SCALP_GROUP_NAME) is not None

    def execute(self, context):
        s = context.scene.wisp
        body = s.target
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        arm = bpy.data.objects.get(s.armature_name) if s.armature_name else None
        # groom in the rest pose: the hair follows the skin's deformation from
        # its rest shape, so guides must be authored against it
        pose_state = None
        if arm is not None and arm.type == 'ARMATURE':
            pose_state = arm.data.pose_position
            arm.data.pose_position = 'REST'
            context.view_layer.update()
        if not getattr(body, "add_rest_position_attribute", True):
            body.add_rest_position_attribute = True  # lets the hair deform with the skin
        try:
            return self._grow(context, s, body, arm)
        finally:
            if pose_state is not None:
                arm.data.pose_position = pose_state
                context.view_layer.update()

    def _grow(self, context, s, body, arm):
        dg = context.evaluated_depsgraph_get()
        samples, _area = groom.scalp_samples(body, dg, SCALP_GROUP_NAME)
        if len(samples) < 10:
            self.report({'ERROR'}, "Scalp is empty — run Detect Scalp first")
            return {'CANCELLED'}

        frame = groom.head_frame(samples, find_eye_z(arm))
        meshes = _collision_meshes(body, dg)
        collider = groom.build_collider(meshes)
        gp = groom.GroomParams(**{k: getattr(s, k) for k in SHAPE_FIELDS})
        guides = groom.grow_guides(samples, frame, collider, gp, skin_points=meshes[0][0])

        hair = self._ensure_hair_object(context, body, arm, s.head_bone)
        inv = hair.matrix_world.inverted()
        groom.write_guides(hair.data, [[inv @ p for p in g] for g in guides])
        self._attach(context, hair)

        from .core.head_follow import ensure_anchors
        ensure_anchors(context, body, arm, s.head_bone)  # armature is in REST here
        write_fringe_weights(body, dg, frame, gp, s.fringe_pieces, s.fringe_thickness)
        if s.scalp_cap:
            ensure_scalp_cap(context, body, dg, arm, s)
        else:
            remove_scalp_cap(body)

        apply_style(hair, s, SCALP_GROUP_NAME)
        mat = ensure_hair_material(hair)
        apply_color(mat, s.melanin, s.redness, s.roughness, 0.3, random_color=s.color_variation,
                    tint=tuple(s.tint), tip_lighten=s.tip_lighten)

        self.report({'INFO'}, f"Grew {len(guides)} guides → {hair.name}")
        return {'FINISHED'}

    @staticmethod
    def _ensure_hair_object(context, body, arm, head_bone):
        name = hair_name_for(body)
        hair = bpy.data.objects.get(name)
        if hair is None:
            data = bpy.data.hair_curves.new(name)
            hair = bpy.data.objects.new(name, data)
            coll = body.users_collection[0] if body.users_collection else context.scene.collection
            coll.objects.link(hair)
        # Blender's hair convention: the curves live in the surface's space
        # (child of it, identity transform). Roots then follow the skin's
        # deformation, and Hair Dynamics simulates in a consistent space.
        if hair.parent is not body or hair.parent_type != 'OBJECT':
            hair.parent = body
            hair.parent_type = 'OBJECT'
        hair.matrix_parent_inverse.identity()
        hair.matrix_basis.identity()
        context.view_layer.update()
        hair.data.surface = body
        uv = body.data.uv_layers.active
        if uv is not None:
            hair.data.surface_uv_map = uv.name
        return hair

    @staticmethod
    def _attach(context, hair):
        """Bind guide roots to the surface (surface_uv_coordinate) so the
        Interpolate node can grow children from the scalp."""
        prev_active = context.view_layer.objects.active
        prev_sel = list(context.selected_objects)
        for o in prev_sel:
            o.select_set(False)
        hair.select_set(True)
        context.view_layer.objects.active = hair
        try:
            bpy.ops.curves.snap_curves_to_surface(attach_mode='NEAREST')
        finally:
            hair.select_set(False)
            for o in prev_sel:
                o.select_set(True)
            context.view_layer.objects.active = prev_active


class _HairSimOp:
    @classmethod
    def poll(cls, context):
        s = context.scene.wisp
        return find_hair(bpy.data, s.target) is not None

    def _run(self, context, op):
        hair = find_hair(bpy.data, context.scene.wisp.target)
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        prev_sel = list(context.selected_objects)
        prev_active = context.view_layer.objects.active
        for o in prev_sel:
            o.select_set(False)
        hair.select_set(True)
        context.view_layer.objects.active = hair
        try:
            return op(selected=True)
        finally:
            hair.select_set(False)
            for o in prev_sel:
                o.select_set(True)
            context.view_layer.objects.active = prev_active


class WISP_OT_bake_dynamics(_HairSimOp, bpy.types.Operator):
    """Bake the hair simulation over the scene frame range, so renders and
    scrubbing use the cached motion"""
    bl_idname = "wisp.bake_dynamics"
    bl_label = "Bake Hair Dynamics"

    def execute(self, context):
        if not context.scene.wisp.dynamics:
            self.report({'WARNING'}, "Turn Dynamics on first")
            return {'CANCELLED'}
        self._run(context, bpy.ops.object.simulation_nodes_cache_bake)
        return {'FINISHED'}


class WISP_OT_free_dynamics(_HairSimOp, bpy.types.Operator):
    """Delete the baked hair simulation"""
    bl_idname = "wisp.free_dynamics"
    bl_label = "Free Bake"

    def execute(self, context):
        self._run(context, bpy.ops.object.simulation_nodes_cache_delete)
        return {'FINISHED'}


class WISP_OT_apply_motion(bpy.types.Operator):
    """Apply an animation from an FBX (e.g. exported from iClone) to this
    character's armature. Bones are matched by name; the FBX's own objects
    are removed afterwards. The armature's current action is kept in the
    file (fake user) and the new one is made active"""
    bl_idname = "wisp.apply_motion"
    bl_label = "Apply Motion (FBX)"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype='FILE_PATH')
    filter_glob: bpy.props.StringProperty(default="*.fbx", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        s = context.scene.wisp
        return bool(s.armature_name) and bpy.data.objects.get(s.armature_name) is not None

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        import os
        from .core import motion
        s = context.scene.wisp
        target = bpy.data.objects[s.armature_name]
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        before = set(bpy.data.objects)
        before_actions = set(bpy.data.actions)
        try:
            bpy.ops.import_scene.fbx(filepath=self.filepath, use_anim=True)
        except Exception as ex:
            self.report({'ERROR'}, f"FBX import failed: {ex}")
            return {'CANCELLED'}
        imported = [o for o in bpy.data.objects if o not in before]
        source = next((o for o in imported if o.type == 'ARMATURE'), None)
        try:
            if source is None or source.animation_data is None or source.animation_data.action is None:
                self.report({'ERROR'}, "No animated armature in that FBX")
                return {'CANCELLED'}
            names = motion.matching_bones(source, target)
            if len(names) < 10:
                self.report({'ERROR'}, f"Only {len(names)} bone names match this character's rig")
                return {'CANCELLED'}
            f0, f1 = (int(round(v)) for v in source.animation_data.action.frame_range)
            keyed = self._transfer(context, source, target, names, f0, f1)
        finally:
            for o in imported:
                data = o.data
                bpy.data.objects.remove(o)
                if data is not None and data.users == 0:
                    if isinstance(data, bpy.types.Armature):
                        bpy.data.armatures.remove(data)
                    elif isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
            for a in set(bpy.data.actions) - before_actions:
                if a is (target.animation_data.action if target.animation_data else None):
                    continue  # the freshly keyed motion
                a.use_fake_user = False  # the FBX importer protects its actions
                if a.users == 0:
                    bpy.data.actions.remove(a)

        new_action = target.animation_data.action
        if new_action is not None:
            new_action.name = "Motion_" + os.path.splitext(os.path.basename(self.filepath))[0]
        sc = context.scene
        sc.frame_start, sc.frame_end = f0, f1
        sc.frame_set(f0)
        hair = find_hair(bpy.data, s.target)
        if hair is not None and s.dynamics:
            bpy.ops.wisp.free_dynamics()
        self.report({'INFO'}, f"Applied {len(names)} bones × {keyed} frames ({f0}–{f1})")
        return {'FINISHED'}

    @staticmethod
    def _transfer(context, source, target, names, f0, f1):
        from .core import motion
        sc = context.scene
        # keep the previous action safe, then key into a fresh one
        ad = target.animation_data_create()
        if ad.action is not None:
            ad.action.use_fake_user = True
        ad.action = None
        # the hair doesn't need evaluating while we bake
        s = sc.wisp
        heavy = [o for o in (find_hair(bpy.data, s.target),
                             bpy.data.objects.get(scalp_cap.cap_name_for(s.target)) if s.target else None) if o]
        was_hidden = {o: o.hide_viewport for o in heavy}
        for o in heavy:
            o.hide_viewport = True
        offsets, _mode = motion.rest_offsets(source, target, names)
        pbs = target.pose.bones
        try:
            for f in range(f0, f1 + 1):
                sc.frame_set(f)
                basis = motion.target_basis(source, target, names, offsets)
                for n in names:
                    pb = pbs[n]
                    pb.matrix_basis = basis[n]
                    pb.keyframe_insert("location", frame=f, group=n)
                    if pb.rotation_mode == 'QUATERNION':
                        pb.keyframe_insert("rotation_quaternion", frame=f, group=n)
                    elif pb.rotation_mode == 'AXIS_ANGLE':
                        pb.keyframe_insert("rotation_axis_angle", frame=f, group=n)
                    else:
                        pb.keyframe_insert("rotation_euler", frame=f, group=n)
        finally:
            for o, h in was_hidden.items():
                o.hide_viewport = h
        return f1 - f0 + 1


CLASSES = (
    WISP_OT_setup_head,
    WISP_OT_detect_scalp,
    WISP_OT_paint_scalp,
    WISP_OT_finish_painting,
    WISP_OT_draw_strands,
    WISP_OT_strand_brush,
    WISP_OT_trim_offscalp,
    WISP_OT_finish_strands,
    WISP_OT_grow_hair,
    WISP_OT_bake_dynamics,
    WISP_OT_free_dynamics,
    WISP_OT_apply_motion,
)
