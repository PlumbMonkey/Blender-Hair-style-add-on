"""Realistic groom stack — Blender's stock hair node assets as a modifier stack.

The guides object carries one Geometry Nodes modifier per stock asset
(Dynamics → Interpolate → Clump → Noise → Frizz → Smooth → Profile), exactly like a
hand-built Blender groom, so artists can open and tweak it with no Wisp
knowledge. Wisp only drives a handful of friendly values on top.
"""

import os

import bpy

HAIR_ASSET_FILE = os.path.join("assets", "nodes", "procedural_hair_node_assets.blend")
SIM_GROUP = "Wisp Hair Sim"  # see hair_sim.py for why not the stock Hair Dynamics

# (modifier name, stock node group) in stack order
STACK = (
    ("Wisp_Dynamics", "Wisp Hair Sim"),  # follows the skin; simulates when enabled
    ("Wisp_Interpolate", "Interpolate Hair Curves"),
    ("Wisp_Clump", "Clump Hair Curves"),
    ("Wisp_FringeClump", "Clump Hair Curves"),  # fine pointed pieces, fringe only
    ("Wisp_Noise", "Hair Curves Noise"),
    ("Wisp_Frizz", "Frizz Hair Curves"),
    ("Wisp_Smooth", "Smooth Hair Curves"),
    ("Wisp_Flyaways", "Wisp Flyaways"),  # ours: a sparse set of loose hairs
    ("Wisp_Profile", "Wisp Strand Profile"),  # ours: stock profile tapers linearly
    ("Wisp_Follow", "Wisp Follow Head"),  # ours: carries the rest-space groom with the head
)

FRINGE_GROUP = "WISP_FRINGE"  # scalp weights (written by Grow Hair) → fringe-only effects
DENSITY_GROUP = "WISP_DENSITY"  # scalp weights with the fringe thickness folded in


PROFILE_GROUP = "Wisp Strand Profile"


def profile_node_group():
    """Radius profile of a real hair: full thickness for most of its length,
    then a smooth taper to a fine tip. (The stock Set Hair Curve Profile
    tapers linearly from the root, which thins the lower half of a groom
    until it looks see-through.)"""
    ng = bpy.data.node_groups.get(PROFILE_GROUP)
    if ng is not None and ng.library is None:
        return ng
    from .nodes import new_geometry_group
    ng, gi, go = new_geometry_group(PROFILE_GROUP, inputs=(
        ("Radius", 'NodeSocketFloat'),
        ("Taper Start", 'NodeSocketFloat'),
        ("Tip Width", 'NodeSocketFloat'),
    ))
    N = ng.nodes
    param = N.new("GeometryNodeSplineParameter")
    rng = N.new("ShaderNodeMapRange")
    rng.interpolation_type = 'SMOOTHSTEP'
    rng.inputs["To Min"].default_value = 1.0
    rng.inputs["From Max"].default_value = 1.0
    mul = N.new("ShaderNodeMath")
    mul.operation = 'MULTIPLY'
    setr = N.new("GeometryNodeSetCurveRadius")
    L = ng.links
    L.new(param.outputs["Factor"], rng.inputs["Value"])
    L.new(gi.outputs["Taper Start"], rng.inputs["From Min"])
    L.new(gi.outputs["Tip Width"], rng.inputs["To Max"])
    L.new(rng.outputs["Result"], mul.inputs[0])
    L.new(gi.outputs["Radius"], mul.inputs[1])
    L.new(gi.outputs["Geometry"], setr.inputs["Curve"])
    L.new(mul.outputs["Value"], setr.inputs["Radius"])
    L.new(setr.outputs["Curve"], go.inputs["Geometry"])
    for i, n in enumerate((param, rng, mul, setr)):
        n.location = (-500 + i * 250, 0)
    return ng


FLYAWAY_GROUP = "Wisp Flyaways"


def flyaway_node_group():
    """A random ``Amount`` of hairs wander loose from the groom, growing
    toward the tip — the stray hairs that make a groom read as real."""
    ng = bpy.data.node_groups.get(FLYAWAY_GROUP)
    if ng is not None and ng.library is None:
        if "Noise Scale" in {i.name for i in ng.interface.items_tree}:
            return ng
        ng.name = FLYAWAY_GROUP + " (old)"  # pre-0.4 layout: rebuild
    from .nodes import new_geometry_group
    ng, gi, go = new_geometry_group(FLYAWAY_GROUP, inputs=(
        ("Amount", 'NodeSocketFloat'),
        ("Distance", 'NodeSocketFloat'),
        ("Seed", 'NodeSocketInt'),
        ("Noise Scale", 'NodeSocketFloat'),
    ))
    N, L = ng.nodes, ng.links
    rnd = N.new("FunctionNodeRandomValue")
    rnd.data_type = 'BOOLEAN'
    per_curve = N.new("GeometryNodeFieldOnDomain")
    per_curve.domain = 'CURVE'
    per_curve.data_type = 'BOOLEAN'
    param = N.new("GeometryNodeSplineParameter")
    sq = N.new("ShaderNodeMath")
    sq.operation = 'POWER'
    sq.inputs[1].default_value = 2.0
    pos = N.new("GeometryNodeInputPosition")
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 40.0
    centre = N.new("ShaderNodeVectorMath")
    centre.operation = 'SUBTRACT'
    centre.inputs[1].default_value = (0.5, 0.5, 0.5)
    k = N.new("ShaderNodeMath")
    k.operation = 'MULTIPLY'
    scale = N.new("ShaderNodeVectorMath")
    scale.operation = 'SCALE'
    setp = N.new("GeometryNodeSetPosition")
    L.new(gi.outputs["Amount"], rnd.inputs["Probability"])
    L.new(gi.outputs["Seed"], rnd.inputs["Seed"])
    L.new(rnd.outputs["Value"], per_curve.inputs[0])  # 5.x: one output per data type
    L.new(param.outputs["Factor"], sq.inputs[0])
    L.new(sq.outputs[0], k.inputs[0])
    L.new(gi.outputs["Distance"], k.inputs[1])
    L.new(pos.outputs["Position"], noise.inputs["Vector"])
    L.new(gi.outputs["Noise Scale"], noise.inputs["Scale"])
    L.new(noise.outputs["Color"], centre.inputs[0])
    L.new(centre.outputs["Vector"], scale.inputs[0])
    L.new(k.outputs[0], scale.inputs["Scale"])
    L.new(gi.outputs["Geometry"], setp.inputs["Geometry"])
    L.new(per_curve.outputs[0], setp.inputs["Selection"])
    L.new(scale.outputs["Vector"], setp.inputs["Offset"])
    L.new(setp.outputs["Geometry"], go.inputs["Geometry"])
    return ng


def stock_node_group(name):
    """The stock hair node group ``name``, appended once and reused."""
    if name == PROFILE_GROUP:
        return profile_node_group()
    if name == FLYAWAY_GROUP:
        return flyaway_node_group()
    if name == "Wisp Follow Head":
        from .head_follow import follow_node_group
        return follow_node_group()
    if name == SIM_GROUP:
        from .hair_sim import sim_node_group
        return sim_node_group()
    ng = bpy.data.node_groups.get(name)
    if ng is not None and ng.library is None:
        return ng
    path = os.path.join(bpy.utils.system_resource('DATAFILES'), HAIR_ASSET_FILE)
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        if name not in src.node_groups:
            raise RuntimeError(f"Stock hair asset '{name}' not found in {path}")
        dst.node_groups = [name]
    return dst.node_groups[0]


def _socket_id(node_group, socket_name):
    for item in node_group.interface.items_tree:
        if item.item_type == 'SOCKET' and item.in_out == 'INPUT' and item.name == socket_name:
            return item.identifier
    raise KeyError(f"{node_group.name}: no input '{socket_name}'")


def _typed_input(mod, sid):
    """5.2+: inputs are RNA structs under ``mod.properties.inputs``;
    5.1 and older: plain ID properties on the modifier (returns None)."""
    props = getattr(mod, "properties", None)
    if props is None:
        return None
    return getattr(props.inputs, sid, None)


def set_input(mod, socket_name, value):
    """Set a modifier input by its display name."""
    sid = _socket_id(mod.node_group, socket_name)
    typed = _typed_input(mod, sid)
    if typed is not None:
        typed.value = value
    else:
        mod[sid] = value


def get_input(mod, socket_name):
    sid = _socket_id(mod.node_group, socket_name)
    typed = _typed_input(mod, sid)
    return typed.value if typed is not None else mod[sid]


def set_input_attribute(mod, socket_name, attribute_name):
    """Drive a field input from a named attribute (e.g. a vertex group)."""
    sid = _socket_id(mod.node_group, socket_name)
    typed = _typed_input(mod, sid)
    if typed is not None:
        typed.type = 'ATTRIBUTE'
        typed.attribute_name = attribute_name
    else:
        mod[sid + "_use_attribute"] = True
        mod[sid + "_attribute_name"] = attribute_name


def ensure_stack(curves_obj):
    """Create any missing stack modifiers (in order). Returns {name: modifier}."""
    mods = {}
    for mod_name, group_name in STACK:
        mod = curves_obj.modifiers.get(mod_name)
        if mod is None or mod.type != 'NODES':
            mod = curves_obj.modifiers.new(mod_name, 'NODES')
        if group_name in (PROFILE_GROUP, FLYAWAY_GROUP, SIM_GROUP, "Wisp Follow Head"):
            ng = stock_node_group(group_name)  # ours: always the current layout
            if mod.node_group is not ng:
                # a fresh modifier: re-pointing an existing one keeps stale
                # input values when a socket's type changed (e.g. vector → float)
                old = mod.node_group
                idx = curves_obj.modifiers.find(mod_name)
                curves_obj.modifiers.remove(mod)
                mod = curves_obj.modifiers.new(mod_name, 'NODES')
                mod.node_group = ng
                curves_obj.modifiers.move(len(curves_obj.modifiers) - 1, idx)
                if old is not None and old.users == 0:
                    bpy.data.node_groups.remove(old)
        elif mod.node_group is None or not mod.node_group.name.startswith(group_name):
            mod.node_group = stock_node_group(group_name)
        mods[mod_name] = mod
    # enforce order
    for i, (mod_name, _) in enumerate(STACK):
        idx = curves_obj.modifiers.find(mod_name)
        if idx != i:
            curves_obj.modifiers.move(idx, i)
    return mods


def apply_style(curves_obj, style, scalp_group=None):
    """Push a style (any object with the attributes below) into the stack.

    density       hairs per cm² of scalp
    viewport      0..1 fraction shown in the viewport
    clump         0..1 how strongly hairs gather into locks
    clump_shape   -1..1 clump profile (+ = tighter at the tips)
    clump_size    metres between lock centres
    tip_spread    metres the clump tips fan apart
    noise         metres of large, soft waviness
    noise_scale   waviness frequency
    frizz         metres of fine, per-hair flyaway
    smooth        0..1 smoothing of the guide shapes
    radius        root radius of one hair, metres
    """
    mods = ensure_stack(curves_obj)
    # Style values are real-world metres; node inputs are in the hair
    # object's space, which is the surface's (e.g. CC meshes are in cm).
    s = curves_obj.matrix_world.to_scale().x or 1.0
    u = 1.0 / s  # object units per metre
    surface = curves_obj.data.surface
    has_rest = surface is not None and getattr(surface, "add_rest_position_attribute", False)

    from .head_follow import find_anchors
    anchor, rest = find_anchors(surface)
    m = mods["Wisp_Follow"]
    set_input(m, "Anchor", anchor)
    set_input(m, "Rest", rest)
    set_input(m, "Invert", False)

    m = mods["Wisp_Dynamics"]
    set_input(m, "Anchor", anchor)
    set_input(m, "Rest", rest)
    set_input(m, "Simulate", bool(getattr(style, "dynamics", False)))
    for b in getattr(m, "bakes", ()):
        if b.bake_mode != 'ANIMATION':
            b.bake_mode = 'ANIMATION'  # a simulation steps through time
    if surface is not None and getattr(style, "dyn_collision", True):
        set_input(m, "Collider", surface)
    else:
        set_input(m, "Collider", None)
    set_input(m, "Gravity", 9.81)  # m/s²; converted to object space inside the sim
    set_input(m, "Stiffness", getattr(style, "dyn_stiffness", 0.5))
    set_input(m, "Root Hold", getattr(style, "dyn_root_hold", 0.3))
    set_input(m, "Damping", getattr(style, "dyn_damping", 0.1))
    set_input(m, "Shell", 0.004 * u)
    npts = max((len(c.points) for c in curves_obj.data.curves), default=2)
    set_input(m, "Max Points", max(1, npts - 1))

    m = mods["Wisp_Interpolate"]
    set_input(m, "Resting Surface", has_rest)  # interpolate in rest pose: no jitter when animated
    set_input(m, "Follow Surface Normal", False)
    set_input(m, "Part by Mesh Islands", False)
    set_input(m, "Interpolation Guides", 5)
    thick = max(1.0, getattr(style, "fringe_thickness", 1.0))
    use_dens = surface is not None and surface.vertex_groups.get(DENSITY_GROUP) is not None
    # thicker fringe: raise the density everywhere and let WISP_DENSITY thin
    # everything but the fringe back down (a mask can only remove hair)
    set_input(m, "Density", style.density * 10000.0 * s * s * (thick if use_dens else 1.0))
    set_input(m, "Viewport Amount", style.viewport)
    if use_dens:
        set_input_attribute(m, "Density Mask", DENSITY_GROUP)
    elif scalp_group:
        set_input_attribute(m, "Density Mask", scalp_group)

    m = mods["Wisp_Clump"]
    set_input(m, "Factor", style.clump)
    set_input(m, "Shape", style.clump_shape)
    set_input(m, "Tip Spread", style.tip_spread * u)
    set_input(m, "Preserve Length", True)
    # Interpolate's guide_curve_index points at guides that no longer exist
    # after interpolation, so let Clump pick its own lock centres instead.
    set_input(m, "Existing Guide Map", False)
    set_input(m, "Guide Distance", style.clump_size * u)

    # Non-cumulative: cumulative offsets pack the same number of kinks into
    # short strands as long ones, which turns fringes into fuzz.
    m = mods["Wisp_FringeClump"]
    set_input(m, "Shape", 0.6)  # pointed pieces
    set_input(m, "Tip Spread", 0.0)
    set_input(m, "Preserve Length", True)
    set_input(m, "Existing Guide Map", False)
    set_input(m, "Guide Distance", 0.005 * u)
    if curves_obj.data.surface and curves_obj.data.surface.vertex_groups.get(FRINGE_GROUP):
        set_input_attribute(m, "Factor", FRINGE_GROUP)  # weights carry fringe_piece strength
    else:
        set_input(m, "Factor", 0.0)

    m = mods["Wisp_Noise"]
    set_input(m, "Cumulative Offset", False)
    set_input(m, "Distance", style.noise * u)
    set_input(m, "Scale", style.noise_scale * s)
    set_input(m, "Shape", 0.7)
    set_input(m, "Preserve Length", True)

    m = mods["Wisp_Frizz"]
    set_input(m, "Cumulative Offset", False)
    set_input(m, "Distance", style.frizz * u)
    set_input(m, "Shape", 0.8)
    set_input(m, "Preserve Length", True)

    m = mods["Wisp_Smooth"]
    set_input(m, "Amount", style.smooth)
    set_input(m, "Iterations", 6)
    set_input(m, "Lock Tips", False)

    m = mods["Wisp_Flyaways"]
    set_input(m, "Amount", getattr(style, "flyaways", 0.03))
    set_input(m, "Distance", getattr(style, "flyaway_distance", 0.02) * u)
    set_input(m, "Seed", 7)
    set_input(m, "Noise Scale", 40.0 * s)

    m = mods["Wisp_Profile"]
    set_input(m, "Radius", style.radius * u)
    set_input(m, "Taper Start", getattr(style, "taper_start", 0.75))
    set_input(m, "Tip Width", 0.08)

    # viewport-only quality (renders always use every modifier)
    quality = getattr(style, "playback", 'FULL')
    styling = {"Wisp_Clump", "Wisp_FringeClump", "Wisp_Noise", "Wisp_Frizz", "Wisp_Smooth", "Wisp_Flyaways"}
    for name, mod in mods.items():
        if quality == 'GUIDES':
            on = name in ("Wisp_Dynamics", "Wisp_Follow")
        elif quality == 'FAST':
            on = name not in styling
        else:
            on = True
        mod.show_viewport = on
        mod.show_render = True
    if quality == 'FAST':
        set_input(mods["Wisp_Interpolate"], "Viewport Amount", min(style.viewport, 0.03))

    curves_obj.update_tag()
    return mods
