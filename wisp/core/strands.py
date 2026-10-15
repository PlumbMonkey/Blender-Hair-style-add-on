"""Strand (hair curves) helpers — Blender-side, UI-independent."""

from mathutils.kdtree import KDTree


def strands_name_for(target_obj):
    return f"Wisp_Strands_{target_obj.name}"


def find_strands(bpy_data, target_obj):
    if target_obj is None:
        return None
    return bpy_data.objects.get(strands_name_for(target_obj))


def scalp_kdtree(scalp_obj, scalp_group_name, min_weight=0.5):
    """KD-tree of world-space scalp vertex positions, or None."""
    vg = scalp_obj.vertex_groups.get(scalp_group_name)
    if vg is None:
        return None
    pts = []
    mw = scalp_obj.matrix_world
    for v in scalp_obj.data.vertices:
        try:
            if vg.weight(v.index) > min_weight:
                pts.append(mw @ v.co)
        except RuntimeError:
            pass
    if not pts:
        return None
    kd = KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(p, i)
    kd.balance()
    return kd


def offscalp_curve_indices(curves_obj, scalp_obj, scalp_group_name, max_dist=0.02):
    """Indices of curves whose root lies farther than ``max_dist`` from any
    scalp vertex."""
    kd = scalp_kdtree(scalp_obj, scalp_group_name)
    if kd is None:
        return []
    cd = curves_obj.data
    mw = curves_obj.matrix_world
    bad = []
    for ci in range(len(cd.curves)):
        root = mw @ cd.curves[ci].points[0].position
        _, _, dist = kd.find(root)
        if dist is None or dist > max_dist:
            bad.append(ci)
    return bad


def remove_curves_by_index(curves_obj, indices):
    """Remove curves by index (Curves.remove_curves, 4.1+). Returns count removed."""
    if not indices:
        return 0
    cd = curves_obj.data
    if not hasattr(cd, "remove_curves"):
        return 0
    cd.remove_curves(indices=indices)
    return len(indices)
