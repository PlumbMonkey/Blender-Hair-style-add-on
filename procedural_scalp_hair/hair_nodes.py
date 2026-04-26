"""Geometry Nodes hair system builder."""

import bpy

from .constants import SCALP_GROUP_NAME, MODIFIER_NAME, NODE_GROUP_NAME


def set_input_default(node_group, socket_name, value):
    """Set the default value for a node group input socket (Blender 4.0+ API)."""
    for item in node_group.interface.items_tree:
        if (
            item.item_type == 'SOCKET'
            and item.in_out == 'INPUT'
            and item.name == socket_name
        ):
            item.default_value = value
            return


def build_hair_geometry_nodes(modifier, props):
    ng = bpy.data.node_groups.new(NODE_GROUP_NAME, 'GeometryNodeTree')
    modifier.node_group = ng

    nodes = ng.nodes
    links = ng.links
    nodes.clear()

    gi = nodes.new("NodeGroupInput")
    go = nodes.new("NodeGroupOutput")
    gi.location = (-900, 0)
    go.location = (900, 0)

    ng.interface.new_socket(name="Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket(name="Density", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket(name="Length", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket(name="Noise", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket(name="Clump", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket(name="Direction Bias", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket(name="Sideburn Length", in_out='INPUT', socket_type='NodeSocketFloat')
    ng.interface.new_socket(name="Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')

    set_input_default(ng, "Density", props.density)
    set_input_default(ng, "Length", props.length)
    set_input_default(ng, "Noise", props.noise)
    set_input_default(ng, "Clump", props.clump)
    set_input_default(ng, "Direction Bias", props.direction_bias)
    set_input_default(ng, "Sideburn Length", props.sideburn_length)

    named_attr = nodes.new("GeometryNodeInputNamedAttribute")
    named_attr.location = (-680, 200)
    named_attr.data_type = 'FLOAT'
    named_attr.inputs["Name"].default_value = SCALP_GROUP_NAME

    separate = nodes.new("GeometryNodeSeparateGeometry")
    separate.location = (-420, 0)

    distribute = nodes.new("GeometryNodeDistributePointsOnFaces")
    distribute.location = (-180, 0)
    distribute.distribute_method = 'POISSON'

    random_val = nodes.new("FunctionNodeRandomValue")
    random_val.location = (-180, -220)
    random_val.data_type = 'FLOAT'
    random_val.inputs[2].default_value = 0.75
    random_val.inputs[3].default_value = 1.25

    curve_line = nodes.new("GeometryNodeCurvePrimitiveLine")
    curve_line.location = (50, -100)
    curve_line.mode = 'POINTS'

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    instance.location = (250, 0)

    realize = nodes.new("GeometryNodeRealizeInstances")
    realize.location = (430, 0)

    set_curve_radius = nodes.new("GeometryNodeSetCurveRadius")
    set_curve_radius.location = (600, 0)
    set_curve_radius.inputs["Radius"].default_value = 0.0018

    resample = nodes.new("GeometryNodeResampleCurve")
    resample.location = (760, -140)
    resample.mode = 'COUNT'
    resample.inputs["Count"].default_value = 8

    set_position = nodes.new("GeometryNodeSetPosition")
    set_position.location = (980, -40)

    noise_tex = nodes.new("ShaderNodeTexNoise")
    noise_tex.location = (760, -340)
    noise_tex.inputs["Scale"].default_value = 6.0

    combine_xyz = nodes.new("ShaderNodeCombineXYZ")
    combine_xyz.location = (980, -260)

    join_geo = nodes.new("GeometryNodeJoinGeometry")
    join_geo.location = (1160, 0)

    normal = nodes.new("GeometryNodeInputNormal")
    normal.location = (-360, -260)

    scale_normal = nodes.new("ShaderNodeVectorMath")
    scale_normal.location = (-140, -280)
    scale_normal.operation = 'SCALE'

    tilt_mix = nodes.new("ShaderNodeMath")
    tilt_mix.location = (50, -280)
    tilt_mix.operation = 'MULTIPLY'

    # Connections
    links.new(gi.outputs["Geometry"], separate.inputs["Geometry"])
    links.new(named_attr.outputs["Attribute"], separate.inputs["Selection"])

    links.new(separate.outputs["Selection"], distribute.inputs["Mesh"])
    links.new(gi.outputs["Density"], distribute.inputs["Density Max"])

    links.new(gi.outputs["Length"], curve_line.inputs["End"])
    links.new(random_val.outputs["Value"], curve_line.inputs["End"])

    links.new(distribute.outputs["Points"], instance.inputs["Points"])
    links.new(curve_line.outputs["Curve"], instance.inputs["Instance"])

    links.new(instance.outputs["Instances"], realize.inputs["Geometry"])
    links.new(realize.outputs["Geometry"], set_curve_radius.inputs["Curve"])
    links.new(set_curve_radius.outputs["Curve"], resample.inputs["Curve"])
    links.new(resample.outputs["Curve"], set_position.inputs["Geometry"])

    links.new(noise_tex.outputs["Fac"], combine_xyz.inputs["X"])
    links.new(noise_tex.outputs["Fac"], combine_xyz.inputs["Y"])
    links.new(gi.outputs["Noise"], combine_xyz.inputs["Z"])
    links.new(combine_xyz.outputs["Vector"], set_position.inputs["Offset"])

    links.new(normal.outputs["Normal"], scale_normal.inputs["Vector"])
    links.new(gi.outputs["Direction Bias"], scale_normal.inputs["Scale"])
    links.new(scale_normal.outputs["Vector"], instance.inputs["Rotation"])

    links.new(gi.outputs["Length"], random_val.inputs[2])
    links.new(gi.outputs["Length"], random_val.inputs[3])

    links.new(gi.outputs["Clump"], tilt_mix.inputs["Value"])
    links.new(gi.outputs["Sideburn Length"], tilt_mix.inputs[1])

    links.new(separate.outputs["Inverted"], join_geo.inputs["Geometry"])
    links.new(set_position.outputs["Geometry"], join_geo.inputs["Geometry"])
    links.new(join_geo.outputs["Geometry"], go.inputs["Geometry"])


def ensure_hair_modifier(obj, props):
    mod = obj.modifiers.get(MODIFIER_NAME)
    if mod is None or mod.type != 'NODES':
        mod = obj.modifiers.new(name=MODIFIER_NAME, type='NODES')

    if mod.node_group:
        old_ng = mod.node_group
        mod.node_group = None
        if old_ng.users == 0:
            bpy.data.node_groups.remove(old_ng, do_unlink=True)

    build_hair_geometry_nodes(mod, props)
    return mod
