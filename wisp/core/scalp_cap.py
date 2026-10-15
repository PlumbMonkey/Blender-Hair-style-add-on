"""Scalp cap — a thin hair-coloured shell under the groom.

Standard grooming practice: wherever the hair parts or thins (whorl, part
line, between locks) the eye sees hair colour instead of bright skin. The
cap is built from the WISP_SCALP faces, pulled back from the hairline so
the forehead stays skin, lifted just off the scalp, and parented like the
hair so it follows the head. Non-destructive: the body mesh is untouched.
"""

import bmesh
import bpy


def cap_name_for(target_obj):
    return f"Wisp_ScalpCap_{target_obj.name}"


def build_scalp_cap(body, depsgraph, scalp_group, lift=0.0012, erode_rings=3, min_weight=0.5):
    """(verts, faces) in world space, or None if the scalp is empty."""
    vg = body.vertex_groups.get(scalp_group)
    if vg is None:
        return None
    gi = vg.index
    inside = {v.index for v in body.data.vertices
              if any(g.group == gi and g.weight >= min_weight for g in v.groups)}
    ev = body.evaluated_get(depsgraph)
    me = ev.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(me)
    ev.to_mesh_clear()
    bm.verts.ensure_lookup_table()
    keep = set(inside)
    for _ in range(erode_rings):  # stay behind the hairline
        edge = {v.index for v in bm.verts if v.index in keep
                and any(n.index not in keep for e in v.link_edges for n in (e.other_vert(v),))}
        keep -= edge
    faces = [f for f in bm.faces if all(v.index in keep for v in f.verts)]
    if not faces:
        bm.free()
        return None
    mw = body.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    remap, verts = {}, []
    for f in faces:
        for v in f.verts:
            if v.index not in remap:
                remap[v.index] = len(verts)
                verts.append(mw @ v.co + (nm @ v.normal).normalized() * lift)
    polys = [[remap[v.index] for v in f.verts] for f in faces]
    bm.free()
    return verts, polys


def ensure_cap_material(color):
    mat = bpy.data.materials.get("Wisp_ScalpCap")
    if mat is None:
        mat = bpy.data.materials.new("Wisp_ScalpCap")
        mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.6
    mat.diffuse_color = (*color, 1.0)
    return mat
