"""Head follow — carry a rest-pose groom along with the head.

Blender's hair stack (Interpolate etc.) grows children on the body's *rest*
surface, so the groom is built and simulated in rest space and moved with
the head as the last step. Two empties give the motion as a matrix:

    anchor: parented to the head bone (moves with the head)
    rest:   parented to the armature object, frozen at the anchor's rest pose

    T = anchor_rel @ rest_rel⁻¹     (rest pose → current pose, hair space)

The "Wisp Follow Head" node group applies T (or T⁻¹ with Invert).
"""

import bpy

GROUP = "Wisp Follow Head"
VERSION = 1


def anchor_names(body):
    return f"Wisp_HeadAnchor_{body.name}", f"Wisp_HeadRest_{body.name}"


def find_anchors(body):
    if body is None:
        return None, None
    a, r = anchor_names(body)
    return bpy.data.objects.get(a), bpy.data.objects.get(r)


def ensure_anchors(context, body, arm, head_bone):
    """Create/refresh both empties. Call with the armature in REST pose."""
    if arm is None or not head_bone or head_bone not in arm.data.bones:
        return None, None
    coll = body.users_collection[0] if body.users_collection else context.scene.collection
    rest_world = arm.matrix_world @ arm.data.bones[head_bone].matrix_local
    objs = []
    for name, bone in zip(anchor_names(body), (head_bone, None)):
        o = bpy.data.objects.get(name)
        if o is None:
            o = bpy.data.objects.new(name, None)
            o.empty_display_size = 0.05
            o.hide_render = True
            coll.objects.link(o)
        o.parent = arm
        o.parent_type = 'BONE' if bone else 'OBJECT'
        o.parent_bone = bone or ""
        o.hide_viewport = False
        context.view_layer.update()
        o.matrix_world = rest_world
        o.hide_set(True)
        objs.append(o)
    context.view_layer.update()
    return objs[0], objs[1]


def follow_node_group():
    ng = bpy.data.node_groups.get(GROUP)
    if ng is not None and ng.library is None and ng.get("wisp_version") == VERSION:
        return ng
    if ng is not None:
        ng.name = GROUP + " (old)"
    from .nodes import new_geometry_group
    ng, gi, go = new_geometry_group(GROUP, inputs=(
        ("Anchor", 'NodeSocketObject'),
        ("Rest", 'NodeSocketObject'),
        ("Invert", 'NodeSocketBool'),
    ))
    N, L = ng.nodes, ng.links
    a = N.new("GeometryNodeObjectInfo"); a.transform_space = 'RELATIVE'; a.location = (-600, 200)
    r = N.new("GeometryNodeObjectInfo"); r.transform_space = 'RELATIVE'; r.location = (-600, -100)
    L.new(gi.outputs["Anchor"], a.inputs["Object"])
    L.new(gi.outputs["Rest"], r.inputs["Object"])
    rinv = N.new("FunctionNodeInvertMatrix"); rinv.location = (-350, -100)
    L.new(r.outputs["Transform"], rinv.inputs["Matrix"])
    t = N.new("FunctionNodeMatrixMultiply"); t.location = (-150, 100)
    L.new(a.outputs["Transform"], t.inputs[0])
    L.new(rinv.outputs["Matrix"], t.inputs[1])
    tinv = N.new("FunctionNodeInvertMatrix"); tinv.location = (50, -50)
    L.new(t.outputs["Matrix"], tinv.inputs["Matrix"])
    sw = N.new("GeometryNodeSwitch"); sw.input_type = 'MATRIX'; sw.location = (250, 50)
    L.new(gi.outputs["Invert"], sw.inputs["Switch"])
    L.new(t.outputs["Matrix"], sw.inputs["False"])
    L.new(tinv.outputs["Matrix"], sw.inputs["True"])
    tr = N.new("GeometryNodeTransform"); tr.location = (450, 0)
    tr.inputs["Mode"].default_value = "Matrix"
    L.new(gi.outputs["Geometry"], tr.inputs["Geometry"])
    L.new(sw.outputs[0], tr.inputs["Transform"])
    L.new(tr.outputs[0], go.inputs["Geometry"])
    ng["wisp_version"] = VERSION
    return ng
