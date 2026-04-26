"""Scalp mask detection and generation."""

from mathutils import Vector

from .constants import SCALP_GROUP_NAME
from .geometry_utils import (
    compute_head_bounds,
    build_bmesh,
    world_vertex,
    safe_normal_world,
    vertex_curvature_score,
    cleanup_and_fill,
    apply_mask_to_group,
    ensure_vertex_group,
    clear_vertex_group,
)


def generate_scalp_mask(obj, props):
    bounds = compute_head_bounds(obj, props)
    if bounds is None:
        return 0

    bm = build_bmesh(obj)

    x_span = max(1e-6, bounds.max_v.x - bounds.min_v.x)
    ear_x_threshold = x_span * props.side_ear_zone_ratio * 0.5

    adjacency = {}
    selected = set()

    up = Vector((0.0, 0.0, 1.0))
    fwd = Vector((0.0, -1.0, 0.0))

    for v in bm.verts:
        adjacency[v.index] = [e.other_vert(v).index for e in v.link_edges]

    for v in bm.verts:
        wp = world_vertex(obj, v)
        wn = safe_normal_world(obj, v.normal)

        # Height filter with sideburn-dependent extension near ear zones
        x_dist_from_center = abs(wp.x - bounds.center.x)
        in_ear_zone = x_dist_from_center >= ear_x_threshold
        sideburn_drop = props.sideburn_length * (1.0 if in_ear_zone else 0.0)
        local_z_threshold = bounds.z_threshold - sideburn_drop
        height_ok = wp.z >= local_z_threshold

        # Normal filter
        up_dot = wn.dot(up)
        fwd_dot = wn.dot(fwd)
        radial = (wp - bounds.center)
        radial = radial.normalized() if radial.length else Vector((0, 0, 1))
        radial_dot = wn.dot(radial)

        normal_ok = (up_dot >= props.min_up_normal) or (radial_dot >= props.min_radial_normal)
        not_face_forward = fwd_dot <= props.max_forward_normal

        # Curvature filter
        curv = vertex_curvature_score(v)
        curvature_ok = curv <= props.max_curvature

        # Radial band filter
        dist = (wp - bounds.center).length
        rmin = bounds.radius * props.radius_min_ratio
        rmax = bounds.radius * props.radius_max_ratio
        radial_ok = (dist >= rmin) and (dist <= rmax)

        # Face exclusion plane
        face_plane = bounds.center.y - bounds.radius * props.face_exclusion_ratio
        front_ok = wp.y <= face_plane or in_ear_zone

        if height_ok and normal_ok and not_face_forward and curvature_ok and radial_ok and front_ok:
            selected.add(v.index)

    bm.free()

    selected = cleanup_and_fill(selected, adjacency, passes=props.cleanup_passes)
    apply_mask_to_group(obj, SCALP_GROUP_NAME, selected)
    return len(selected)


def ensure_hairline_group(obj, scalp_group_name, group_name="HAIRLINE_MASK", front_band=0.08):
    scalp_vg = obj.vertex_groups.get(scalp_group_name)
    if scalp_vg is None:
        return None

    hairline_vg = ensure_vertex_group(obj, group_name)
    clear_vertex_group(obj, hairline_vg)

    coords = []
    scalp_indices = []
    for v in obj.data.vertices:
        try:
            w = scalp_vg.weight(v.index)
            if w > 0.5:
                p = world_vertex(obj, v)
                coords.append(p)
                scalp_indices.append(v.index)
        except RuntimeError:
            pass

    if not coords:
        return hairline_vg

    y_min = min(p.y for p in coords)
    y_max = max(p.y for p in coords)
    band = (y_max - y_min) * max(0.02, front_band)
    threshold = y_min + band

    x_vals = [p.x for p in coords]
    x_min, x_max = min(x_vals), max(x_vals)
    x_span = max(1e-6, x_max - x_min)

    for idx in scalp_indices:
        p = world_vertex(obj, obj.data.vertices[idx])
        if p.y <= threshold:
            t = (p.x - x_min) / x_span
            arc = 1.0 - (2.0 * t - 1.0) ** 2
            w = max(0.0, min(1.0, 0.4 + 0.6 * arc))
            hairline_vg.add([idx], w, 'REPLACE')

    return hairline_vg
