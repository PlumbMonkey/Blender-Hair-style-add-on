"""Wisp Hair Sim — inextensible guide-hair dynamics in Geometry Nodes.

Why not Blender's stock "Hair Dynamics" asset: its XPBD constraints are
tuned in metres, so on scaled characters (Character Creator meshes are in
centimetres under a 0.01 rig) the hair stretches up to 100x. This solver
uses Follow-The-Leader length projection (Müller et al. 2012), which is a
hard constraint — hair can't stretch in any unit system.

Per frame, on the guide curves only (the interpolated children follow):
  1. target = rest guides carried with the head (Wisp Follow Head)
  2. verlet: pos += (pos - prev) * (1 - damping) + gravity * dt²
  3. shape memory: pull toward target, strongest at the root (root pinned)
  4. collision: push out of the collider mesh to ``Shell`` distance
  5. FTL: root→tip, each point is put back at its rest distance from
     the point before it
The result is mapped back to rest space (the stack interpolates children on
the rest surface; the final Wisp_Follow modifier moves everything with the
head). With Simulate off, the group outputs the rest guides unchanged.
"""

import bpy

GROUP = "Wisp Hair Sim"
VERSION = 12


def _new(nodes, idname, x, y, **props):
    n = nodes.new(idname)
    n.location = (x, y)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def _math(nodes, op, x, y, a=None, b=None):
    n = _new(nodes, "ShaderNodeMath", x, y, operation=op)
    if a is not None:
        n.inputs[0].default_value = a
    if b is not None:
        n.inputs[1].default_value = b
    return n


def _vmath(nodes, op, x, y):
    return _new(nodes, "ShaderNodeVectorMath", x, y, operation=op)


def sim_node_group():
    ng = bpy.data.node_groups.get(GROUP)
    if ng is not None and ng.library is None and ng.get("wisp_version") == VERSION:
        return ng
    if ng is not None:
        ng.name = GROUP + " (old)"
    from .nodes import new_geometry_group
    ng, gi, go = new_geometry_group(GROUP, inputs=(
        ("Simulate", 'NodeSocketBool'),
        ("Collider", 'NodeSocketObject'),
        ("Gravity", 'NodeSocketFloat'),  # m/s²; a vector modifier input doesn't reach the group in 5.2
        ("Stiffness", 'NodeSocketFloat'),
        ("Damping", 'NodeSocketFloat'),
        ("Shell", 'NodeSocketFloat'),
        ("Max Points", 'NodeSocketInt'),
        ("Anchor", 'NodeSocketObject'),
        ("Rest", 'NodeSocketObject'),
        ("Root Hold", 'NodeSocketFloat'),  # fraction of each strand held near-rigid
    ))
    N, L = ng.nodes, ng.links
    gi.location = (-2200, 0)

    # --- target: guides deformed with the skin, + rest segment lengths -----

    cop = _new(N, "GeometryNodeCurveOfPoint", -1900, -200)          # Index in Curve
    idx = _new(N, "GeometryNodeInputIndex", -1900, -350)
    prev_i = _math(N, 'SUBTRACT', -1700, -350, b=1.0)
    L.new(idx.outputs[0], prev_i.inputs[0])
    pos_in = _new(N, "GeometryNodeInputPosition", -1900, -500)
    samp_prev = _new(N, "GeometryNodeSampleIndex", -1500, -400, data_type='FLOAT_VECTOR', domain='POINT')
    L.new(gi.outputs["Geometry"], samp_prev.inputs["Geometry"])
    L.new(pos_in.outputs[0], samp_prev.inputs["Value"])
    L.new(prev_i.outputs[0], samp_prev.inputs["Index"])
    seg = _vmath(N, 'DISTANCE', -1300, -400)
    L.new(pos_in.outputs[0], seg.inputs[0])
    L.new(samp_prev.outputs[0], seg.inputs[1])
    is_root = _new(N, "FunctionNodeCompare", -1300, -200, data_type='INT', operation='EQUAL')
    L.new(cop.outputs["Index in Curve"], is_root.inputs[0])  # 5.x: only the active type's sockets
    rest_len = _new(N, "GeometryNodeSwitch", -1100, -300, input_type='FLOAT')
    L.new(is_root.outputs[0], rest_len.inputs["Switch"])
    L.new(seg.outputs["Value"], rest_len.inputs["False"])
    store_rest = _new(N, "GeometryNodeStoreNamedAttribute", -900, 200, data_type='FLOAT', domain='POINT')
    store_rest.inputs["Name"].default_value = "wisp_rest_len"
    # rest lengths are measured on the undeformed guides (the Position field
    # and the neighbour sample must read the same geometry), then deformed
    L.new(gi.outputs["Geometry"], store_rest.inputs["Geometry"])
    L.new(rest_len.outputs[0], store_rest.inputs["Value"])
    # posed target: the rest guides carried along with the head
    from .head_follow import follow_node_group
    fl = follow_node_group()
    deform = N.new("GeometryNodeGroup"); deform.node_tree = fl; deform.location = (-700, 450)
    L.new(store_rest.outputs[0], deform.inputs["Geometry"])
    L.new(gi.outputs["Anchor"], deform.inputs["Anchor"])
    L.new(gi.outputs["Rest"], deform.inputs["Rest"])
    target = deform  # posed target geometry carrying rest lengths

    # --- simulation zone -----------------------------------------------------
    sin = _new(N, "GeometryNodeSimulationInput", -700, 200)
    sout = _new(N, "GeometryNodeSimulationOutput", 2600, 200)
    sin.pair_with_output(sout)
    L.new(target.outputs[0], sin.inputs["Geometry"])

    pos = _new(N, "GeometryNodeInputPosition", -700, -100)
    prev = _new(N, "GeometryNodeInputNamedAttribute", -700, -250, data_type='FLOAT_VECTOR')
    prev.inputs["Name"].default_value = "wisp_prev"
    prev_or_pos = _new(N, "GeometryNodeSwitch", -500, -250, input_type='VECTOR')
    L.new(prev.outputs["Exists"], prev_or_pos.inputs["Switch"])
    L.new(pos.outputs[0], prev_or_pos.inputs["False"])
    L.new(prev.outputs["Attribute"], prev_or_pos.inputs["True"])

    vel = _vmath(N, 'SUBTRACT', -300, -150)
    L.new(pos.outputs[0], vel.inputs[0])
    L.new(prev_or_pos.outputs[0], vel.inputs[1])
    keep = _math(N, 'SUBTRACT', -500, -450, a=1.0)
    L.new(gi.outputs["Damping"], keep.inputs[1])
    vel_d = _vmath(N, 'SCALE', -100, -150)
    L.new(vel.outputs[0], vel_d.inputs[0])
    L.new(keep.outputs[0], vel_d.inputs["Scale"])
    dt2 = _math(N, 'MULTIPLY', -300, -450)
    L.new(sin.outputs["Delta Time"], dt2.inputs[0])
    L.new(sin.outputs["Delta Time"], dt2.inputs[1])
    # world "down" expressed in this object's axes and units
    selfo = _new(N, "GeometryNodeSelfObject", -900, -700)
    sinfo = _new(N, "GeometryNodeObjectInfo", -700, -700, transform_space='ORIGINAL')
    L.new(selfo.outputs[0], sinfo.inputs["Object"])
    winv = _new(N, "FunctionNodeInvertMatrix", -500, -700)
    L.new(sinfo.outputs["Transform"], winv.inputs["Matrix"])
    neg = _math(N, 'MULTIPLY', -700, -900, b=-1.0)
    L.new(gi.outputs["Gravity"], neg.inputs[0])
    gxyz = _new(N, "ShaderNodeCombineXYZ", -500, -900)
    L.new(neg.outputs[0], gxyz.inputs["Z"])
    gdir = _new(N, "FunctionNodeTransformDirection", -300, -800)
    L.new(gxyz.outputs[0], gdir.inputs["Direction"])
    L.new(winv.outputs["Matrix"], gdir.inputs["Transform"])
    grav = _vmath(N, 'SCALE', -100, -450)
    L.new(gdir.outputs[0], grav.inputs[0])
    L.new(dt2.outputs[0], grav.inputs["Scale"])
    step = _vmath(N, 'ADD', 100, -250)
    L.new(vel_d.outputs[0], step.inputs[0])
    L.new(grav.outputs[0], step.inputs[1])
    moved = _vmath(N, 'ADD', 300, -150)
    L.new(pos.outputs[0], moved.inputs[0])
    L.new(step.outputs[0], moved.inputs[1])

    # shape memory toward the skin-following target (root fully pinned)
    tpos = _new(N, "GeometryNodeSampleIndex", 100, 300, data_type='FLOAT_VECTOR', domain='POINT')
    L.new(target.outputs[0], tpos.inputs["Geometry"])
    L.new(pos_in.outputs[0], tpos.inputs["Value"])
    L.new(idx.outputs[0], tpos.inputs["Index"])
    par = _new(N, "GeometryNodeSplineParameter", 100, 500)
    one_minus = _math(N, 'SUBTRACT', 300, 500, a=1.0)
    L.new(par.outputs["Factor"], one_minus.inputs[1])
    sq = _math(N, 'POWER', 500, 500, b=1.5)  # style memory: strongest at the root, fading to the tip
    L.new(one_minus.outputs[0], sq.inputs[0])
    w_soft = _math(N, 'MULTIPLY', 700, 500)
    L.new(sq.outputs[0], w_soft.inputs[0])
    L.new(gi.outputs["Stiffness"], w_soft.inputs[1])
    # root zone: the first "Root Hold" of each strand keeps its styled shape
    # (on a real head the surrounding hair holds the roots in place), easing
    # out smoothly so there's no kink where the free length begins
    hold = _new(N, "ShaderNodeMapRange", 700, 800, interpolation_type='SMOOTHSTEP')
    L.new(par.outputs["Factor"], hold.inputs["Value"])
    hold.inputs["From Min"].default_value = 0.0
    L.new(gi.outputs["Root Hold"], hold.inputs["From Max"])
    hold.inputs["To Min"].default_value = 0.9
    hold.inputs["To Max"].default_value = 0.0
    w = _math(N, 'MAXIMUM', 900, 500)
    L.new(w_soft.outputs[0], w.inputs[0])
    L.new(hold.outputs["Result"], w.inputs[1])
    cop2 = _new(N, "GeometryNodeCurveOfPoint", 500, 700)
    root2 = _new(N, "FunctionNodeCompare", 700, 700, data_type='INT', operation='EQUAL')
    L.new(cop2.outputs["Index in Curve"], root2.inputs[0])
    w_root = _new(N, "GeometryNodeSwitch", 900, 600, input_type='FLOAT')
    L.new(root2.outputs[0], w_root.inputs["Switch"])
    L.new(w.outputs[0], w_root.inputs["False"])
    w_root.inputs["True"].default_value = 1.0
    pulled = _new(N, "ShaderNodeMix", 1100, 100, data_type='VECTOR')
    L.new(w_root.outputs[0], pulled.inputs["Factor"])
    L.new(moved.outputs[0], pulled.inputs[4])   # A (vector)
    L.new(tpos.outputs[0], pulled.inputs[5])    # B (vector)

    store_prev = _new(N, "GeometryNodeStoreNamedAttribute", 700, 150, data_type='FLOAT_VECTOR', domain='POINT')
    store_prev.inputs["Name"].default_value = "wisp_prev"
    L.new(sin.outputs["Geometry"], store_prev.inputs["Geometry"])
    L.new(pos.outputs[0], store_prev.inputs["Value"])
    set_new = _new(N, "GeometryNodeSetPosition", 1300, 150)
    L.new(store_prev.outputs[0], set_new.inputs["Geometry"])
    L.new(next(o for o in pulled.outputs if o.type == 'VECTOR'), set_new.inputs["Position"])

    # collision: keep points Shell outside the collider surface
    oinfo = _new(N, "GeometryNodeObjectInfo", 1100, -600, transform_space='RELATIVE')
    L.new(gi.outputs["Collider"], oinfo.inputs["Object"])
    near = _new(N, "GeometryNodeSampleNearestSurface", 1300, -500, data_type='FLOAT_VECTOR')
    nrm = _new(N, "GeometryNodeInputNormal", 1100, -800)
    L.new(oinfo.outputs["Geometry"], near.inputs["Mesh"])
    L.new(nrm.outputs[0], near.inputs["Value"])
    near_pos = _new(N, "GeometryNodeSampleNearestSurface", 1300, -800, data_type='FLOAT_VECTOR')
    pos_c = _new(N, "GeometryNodeInputPosition", 1100, -950)
    L.new(oinfo.outputs["Geometry"], near_pos.inputs["Mesh"])
    L.new(pos_c.outputs[0], near_pos.inputs["Value"])
    pos_now = _new(N, "GeometryNodeInputPosition", 1300, -1100)
    diff = _vmath(N, 'SUBTRACT', 1550, -900)
    L.new(pos_now.outputs[0], diff.inputs[0])
    L.new(near_pos.outputs[0], diff.inputs[1])
    nn = _vmath(N, 'NORMALIZE', 1550, -600)
    L.new(near.outputs[0], nn.inputs[0])
    off = _vmath(N, 'DOT_PRODUCT', 1750, -800)
    L.new(diff.outputs[0], off.inputs[0])
    L.new(nn.outputs[0], off.inputs[1])
    inside = _new(N, "FunctionNodeCompare", 1950, -800, data_type='FLOAT', operation='LESS_THAN')
    L.new(off.outputs["Value"], inside.inputs[0])
    L.new(gi.outputs["Shell"], inside.inputs[1])
    push = _vmath(N, 'SCALE', 1950, -600)
    L.new(nn.outputs[0], push.inputs[0])
    L.new(gi.outputs["Shell"], push.inputs["Scale"])
    out_pos = _vmath(N, 'ADD', 2150, -700)
    L.new(near_pos.outputs[0], out_pos.inputs[0])
    L.new(push.outputs[0], out_pos.inputs[1])
    not_root = _new(N, "FunctionNodeBooleanMath", 1950, -1000, operation='NOT')
    L.new(root2.outputs[0], not_root.inputs[0])
    # only shallow penetrations are real: a point far "behind" its nearest
    # surface is next to thin geometry (eyelashes, lips, the far side of the
    # neck) and pushing it through would fling the hair across the head
    depth = _math(N, 'MULTIPLY', 1950, -1150, b=-5.0)
    L.new(gi.outputs["Shell"], depth.inputs[0])
    shallow = _new(N, "FunctionNodeCompare", 2150, -1150, data_type='FLOAT', operation='GREATER_THAN')
    L.new(off.outputs["Value"], shallow.inputs[0])
    L.new(depth.outputs[0], shallow.inputs[1])
    both = _new(N, "FunctionNodeBooleanMath", 2150, -1300, operation='AND')
    L.new(inside.outputs[0], both.inputs[0])
    L.new(shallow.outputs[0], both.inputs[1])
    sel_c = _new(N, "FunctionNodeBooleanMath", 2150, -950, operation='AND')
    L.new(both.outputs[0], sel_c.inputs[0])
    L.new(not_root.outputs[0], sel_c.inputs[1])
    set_col = _new(N, "GeometryNodeSetPosition", 1600, 150)
    L.new(set_new.outputs[0], set_col.inputs["Geometry"])
    L.new(sel_c.outputs[0], set_col.inputs["Selection"])
    L.new(out_pos.outputs[0], set_col.inputs["Position"])
    # inelastic contact: a pushed-out point keeps no velocity from the push
    # (otherwise every push is read back as motion and hair "launches" off
    # the neck and shoulders)
    col_prev = _new(N, "GeometryNodeStoreNamedAttribute", 1700, 0, data_type='FLOAT_VECTOR', domain='POINT')
    col_prev.inputs["Name"].default_value = "wisp_prev"
    L.new(set_col.outputs[0], col_prev.inputs["Geometry"])
    L.new(sel_c.outputs[0], col_prev.inputs["Selection"])
    L.new(out_pos.outputs[0], col_prev.inputs["Value"])

    # FTL length projection, root → tip (one point index per iteration)
    rin = _new(N, "GeometryNodeRepeatInput", 1800, 150)
    rout = _new(N, "GeometryNodeRepeatOutput", 2400, 150)
    rin.pair_with_output(rout)
    L.new(gi.outputs["Max Points"], rin.inputs["Iterations"])
    L.new(col_prev.outputs[0], rin.inputs["Geometry"])
    cop3 = _new(N, "GeometryNodeCurveOfPoint", 1800, 450)
    it1 = _math(N, 'ADD', 1800, 600, b=1.0)
    L.new(rin.outputs["Iteration"], it1.inputs[0])
    this_pt = _new(N, "FunctionNodeCompare", 2000, 500, data_type='INT', operation='EQUAL')
    L.new(cop3.outputs["Index in Curve"], this_pt.inputs[0])
    L.new(it1.outputs[0], this_pt.inputs[1])
    idx3 = _new(N, "GeometryNodeInputIndex", 1800, 750)
    pi3 = _math(N, 'SUBTRACT', 2000, 750, b=1.0)
    L.new(idx3.outputs[0], pi3.inputs[0])
    pos3 = _new(N, "GeometryNodeInputPosition", 1800, 900)
    sp3 = _new(N, "GeometryNodeSampleIndex", 2200, 750, data_type='FLOAT_VECTOR', domain='POINT')
    L.new(rin.outputs["Geometry"], sp3.inputs["Geometry"])
    L.new(pos3.outputs[0], sp3.inputs["Value"])
    L.new(pi3.outputs[0], sp3.inputs["Index"])
    d3 = _vmath(N, 'SUBTRACT', 2200, 950)
    L.new(pos3.outputs[0], d3.inputs[0])
    L.new(sp3.outputs[0], d3.inputs[1])
    n3 = _vmath(N, 'NORMALIZE', 2350, 950)
    L.new(d3.outputs[0], n3.inputs[0])
    rl = _new(N, "GeometryNodeInputNamedAttribute", 2200, 1100, data_type='FLOAT')
    rl.inputs["Name"].default_value = "wisp_rest_len"
    s3 = _vmath(N, 'SCALE', 2500, 950)
    L.new(n3.outputs[0], s3.inputs[0])
    L.new(rl.outputs["Attribute"], s3.inputs["Scale"])
    p3 = _vmath(N, 'ADD', 2650, 850)
    L.new(sp3.outputs[0], p3.inputs[0])
    L.new(s3.outputs[0], p3.inputs[1])
    set3 = _new(N, "GeometryNodeSetPosition", 2250, 300)
    L.new(rin.outputs["Geometry"], set3.inputs["Geometry"])
    L.new(this_pt.outputs[0], set3.inputs["Selection"])
    L.new(p3.outputs[0], set3.inputs["Position"])
    L.new(set3.outputs[0], rout.inputs["Geometry"])

    # Dynamic FTL velocity correction (Müller et al. 2012): the length
    # projection moves points, and plain verlet would read that as velocity
    # (it compounds into hair flying off). Store "previous" so that next
    # frame's velocity excludes 90% of this frame's correction:
    #   prev_next = prev_start + 0.9 · (after_FTL − before_FTL)
    pos_a = _new(N, "GeometryNodeInputPosition", 2450, 450)
    idx_a = _new(N, "GeometryNodeInputIndex", 2450, 600)
    before = _new(N, "GeometryNodeSampleIndex", 2650, 550, data_type='FLOAT_VECTOR', domain='POINT')
    L.new(col_prev.outputs[0], before.inputs["Geometry"])
    L.new(pos_a.outputs[0], before.inputs["Value"])
    L.new(idx_a.outputs[0], before.inputs["Index"])
    corr = _vmath(N, 'SUBTRACT', 2850, 500)
    L.new(pos_a.outputs[0], corr.inputs[0])
    L.new(before.outputs[0], corr.inputs[1])
    corr9 = _vmath(N, 'SCALE', 3000, 500)
    L.new(corr.outputs[0], corr9.inputs[0])
    corr9.inputs["Scale"].default_value = 0.9
    prev_a = _new(N, "GeometryNodeInputNamedAttribute", 2850, 700, data_type='FLOAT_VECTOR')
    prev_a.inputs["Name"].default_value = "wisp_prev"
    new_prev = _vmath(N, 'ADD', 3150, 600)
    L.new(prev_a.outputs["Attribute"], new_prev.inputs[0])
    L.new(corr9.outputs[0], new_prev.inputs[1])
    st_prev = _new(N, "GeometryNodeStoreNamedAttribute", 3300, 300, data_type='FLOAT_VECTOR', domain='POINT')
    st_prev.inputs["Name"].default_value = "wisp_prev"
    L.new(rout.outputs["Geometry"], st_prev.inputs["Geometry"])
    L.new(new_prev.outputs[0], st_prev.inputs["Value"])
    L.new(st_prev.outputs[0], sout.inputs["Geometry"])  # (inputs[0] is Skip)

    # The cached sim geometry loses the curves' surface link, which Interpolate
    # needs — so copy the simulated positions back onto the live guides.
    sim_pos = _new(N, "GeometryNodeInputPosition", 2650, -250)
    idx_o = _new(N, "GeometryNodeInputIndex", 2650, -400)
    take = _new(N, "GeometryNodeSampleIndex", 2850, -250, data_type='FLOAT_VECTOR', domain='POINT')
    L.new(sout.outputs["Geometry"], take.inputs["Geometry"])
    L.new(sim_pos.outputs[0], take.inputs["Value"])
    L.new(idx_o.outputs[0], take.inputs["Index"])
    back = _new(N, "GeometryNodeSetPosition", 3050, -100)
    L.new(target.outputs[0], back.inputs["Geometry"])
    L.new(take.outputs[0], back.inputs["Position"])
    # back to rest space (the stack interpolates on the rest surface; the
    # final Wisp_Follow modifier carries everything with the head)
    to_rest = N.new("GeometryNodeGroup"); to_rest.node_tree = fl; to_rest.location = (3150, -300)
    L.new(back.outputs["Geometry"], to_rest.inputs["Geometry"])
    L.new(gi.outputs["Anchor"], to_rest.inputs["Anchor"])
    L.new(gi.outputs["Rest"], to_rest.inputs["Rest"])
    to_rest.inputs["Invert"].default_value = True

    # Simulate off → the skin-following guides
    sw = _new(N, "GeometryNodeSwitch", 3250, 0, input_type='GEOMETRY')
    L.new(gi.outputs["Simulate"], sw.inputs["Switch"])
    L.new(store_rest.outputs[0], sw.inputs["False"])
    L.new(to_rest.outputs[0], sw.inputs["True"])
    L.new(sw.outputs[0], go.inputs["Geometry"])
    go.location = (3450, 0)
    ng["wisp_version"] = VERSION  # only once fully built
    return ng
