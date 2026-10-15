"""Procedural guide grooming — grow realistic guide strands from a scalp.

Every guide is "grown" from a scalp vertex: it leaves the skin along a
combing direction (away from the whorl/part, or forward + swept for the
fringe), gravity bends it down, and a collision shell around the body keeps
it off the head, face and shoulders. The shell grows from the root to the
``volume`` distance, which is what gives the hairstyle its body.

Lengths are expressed in *head units* (H = crown-to-chin distance) measured
down from the crown, so one hairstyle preset fits any head size:

    0.0 = crown   ~0.5 = eyes   1.0 = chin   ~1.3 = shoulders

Rules as per ``core/__init__``: no UI/props/context dependencies.
"""

import math
import random
from dataclasses import dataclass

from mathutils import Vector
from mathutils.bvhtree import BVHTree


@dataclass
class GroomParams:
    guide_spacing: float = 0.012  # metres between guide roots
    points: int = 24              # control points per guide
    fringe_length: float = 0.58   # tip height of the fringe (head units below crown)
    side_length: float = 1.06     # tip height over the ears
    back_length: float = 1.12     # tip height at the nape
    fringe_width: float = 50.0    # degrees either side of the face that count as fringe
    volume: float = 0.018         # metres the hair stands off the skin
    fringe_volume: float = 0.6    # fringe standoff as a fraction of volume (swoop vs. flat)
    lift: float = 0.3             # 0 = lies flat from the root, 1 = springs up/out
    stiffness: float = 0.35       # 0 = drops straight down, 1 = holds its combed direction
    part: float = -0.3            # -1..1 part position across the head (0 = centre)
    sweep: float = 0.35           # -1..1 sideways sweep of the fringe (+ = character's left)
    fringe_tilt: float = 0.0      # head units the fringe gets longer toward the character's left
    crowns: int = 1               # number of whorls on the crown (1-3)
    crown_spread: float = 0.35    # spacing of extra crowns, fraction of the scalp half-width
    crown_swirl: float = 0.3      # how much the hair spirals around each crown
    flick: float = 0.3            # 0..1 outward flip at the ends
    flare: float = 0.06           # 0..1 how much the sides fan out as they fall
    length_jitter: float = 0.06   # head units of random length variation (choppy ends)
    seed: int = 1


@dataclass
class HeadFrame:
    center: Vector      # scalp centre (x, y) at eye height
    crown_z: float
    eye_z: float
    chin_z: float
    half_width: float

    @property
    def unit(self):
        return max(1e-4, self.crown_z - self.chin_z)

    def z_at(self, head_units):
        return self.crown_z - head_units * self.unit


def _smoothstep(e0, e1, x):
    if e0 == e1:
        return 1.0 if x >= e1 else 0.0
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

def evaluated_world_mesh(obj, depsgraph, skip_material_keywords=()):
    """(verts, polys, vert_normals) of the evaluated mesh in world space.
    Polygons whose material name contains any of ``skip_material_keywords``
    are dropped (e.g. CC eyelash cards, which would confuse collision)."""
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    verts = [mw @ v.co for v in me.vertices]
    normals = [(nm @ v.normal).normalized() for v in me.vertices]
    skip = set()
    kws = [k.lower() for k in skip_material_keywords]
    if kws:
        for i, mat in enumerate(me.materials):
            if mat and any(k in mat.name.lower() for k in kws):
                skip.add(i)
    polys = [tuple(p.vertices) for p in me.polygons if p.material_index not in skip]
    ev.to_mesh_clear()
    return verts, polys, normals


def build_collider(meshes):
    """BVH over several (verts, polys) world-space meshes."""
    all_v, all_p = [], []
    for verts, polys in meshes:
        off = len(all_v)
        all_v.extend(verts)
        all_p.extend(tuple(i + off for i in p) for p in polys)
    return BVHTree.FromPolygons(all_v, all_p, all_triangles=False, epsilon=0.0)


def scalp_samples(obj, depsgraph, group_name, min_weight=0.5):
    """World-space (position, normal) for every scalp vertex, plus scalp area."""
    vg = obj.vertex_groups.get(group_name)
    if vg is None:
        return [], 0.0
    gi = vg.index
    ev = obj.evaluated_get(depsgraph)
    me = ev.to_mesh()
    mw = obj.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    inside = set()
    for v in obj.data.vertices:  # weights live on the original mesh
        for g in v.groups:
            if g.group == gi and g.weight >= min_weight:
                inside.add(v.index)
                break
    samples = [(mw @ me.vertices[i].co, (nm @ me.vertices[i].normal).normalized())
               for i in sorted(inside)]
    area = 0.0
    for p in me.polygons:
        if all(i in inside for i in p.vertices):
            area += p.area
    area *= abs(mw.to_3x3().determinant()) ** (2.0 / 3.0)  # local -> world units
    ev.to_mesh_clear()
    return samples, area


def head_frame(samples, eye_z=None):
    """Landmarks from the scalp samples. ``eye_z`` (e.g. from eye bones)
    improves accuracy; otherwise it is estimated from the scalp shape."""
    xs = [p.x for p, _ in samples]
    ys = [p.y for p, _ in samples]
    zs = [p.z for p, _ in samples]
    crown = max(zs)
    center = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0.0))
    half_w = (max(xs) - min(xs)) / 2
    if eye_z is None:
        # scalp top-to-bottom is roughly crown→ear-top; eyes sit a bit lower
        eye_z = crown - 0.55 * (crown - min(zs)) - 0.02
    chin = eye_z - (crown - eye_z)  # eyes sit at ~half the head height
    center.z = eye_z
    return HeadFrame(center=center, crown_z=crown, eye_z=eye_z, chin_z=chin, half_width=half_w)


def pick_roots(samples, spacing, seed=1):
    """Poisson-disk-like subset of scalp samples at least ``spacing`` apart
    (grid-hashed dart throwing)."""
    rng = random.Random(seed)
    order = list(range(len(samples)))
    rng.shuffle(order)
    cell = spacing
    grid = {}
    kept = []
    for i in order:
        p = samples[i][0]
        key = (int(math.floor(p.x / cell)), int(math.floor(p.y / cell)), int(math.floor(p.z / cell)))
        ok = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid.get((key[0] + dx, key[1] + dy, key[2] + dz), ()):
                        if (q - p).length < spacing:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault(key, []).append(p)
            kept.append(samples[i])
    return kept


# --------------------------------------------------------------------------
# Growing
# --------------------------------------------------------------------------

FORWARD = Vector((0.0, -1.0, 0.0))  # CC / VRoid / Blender convention: face -Y
DOWN = Vector((0.0, 0.0, -1.0))


def _azimuth_deg(p, frame):
    """0 at the face, 180 at the back of the head."""
    dx = p.x - frame.center.x
    dy = p.y - frame.center.y
    return abs(math.degrees(math.atan2(dx, -dy)))


def _fringe_units(p, frame, gp):
    # tilt measured across the face (≈ half the head width), eye to eye
    x = (p.x - frame.center.x) / max(0.5 * frame.half_width, 1e-4)
    return gp.fringe_length + gp.fringe_tilt * max(-1.0, min(1.0, x))


def _tip_units(p, frame, gp):
    a = _azimuth_deg(p, frame)
    w_front = 1.0 - _smoothstep(gp.fringe_width * 0.8, gp.fringe_width * 1.2, a)
    w_back = _smoothstep(100.0, 160.0, a)
    side = gp.side_length + (gp.back_length - gp.side_length) * w_back
    fringe = _fringe_units(p, frame, gp)
    return side + (fringe - side) * w_front, w_front, side


def _comb_direction(p, n, frame, gp, w_front):
    part_x = frame.center.x + gp.part * frame.half_width * 0.6
    # whorl: slightly behind the top of the head, on the part line
    whorl = Vector((part_x, frame.center.y + 0.35 * frame.half_width, 0.0))
    radial = _crown_flow(p, crown_points(whorl, frame, gp), gp.crown_swirl)
    # behind the whorl everything also flows down the back, so the crown
    # doesn't split open into a visible parting
    behind = _smoothstep(whorl.y, whorl.y + 0.6 * frame.half_width, p.y)
    radial = (radial + Vector((0.0, 0.8 * behind, 0.0))).normalized()
    # side hair near the face is swept back (framing the face, clear of the
    # cheek) — only the fringe combs forward
    if radial.y < 0.0:
        radial = Vector((radial.x, -0.5 * radial.y, 0.0)).normalized()
    # comb away from the part on top of the head
    away = 1.0 if p.x >= part_x else -1.0
    top = _smoothstep(frame.crown_z - 0.3 * frame.unit, frame.crown_z, p.z)
    # the part runs from the front hairline back to the whorl — not down the back
    top *= 1.0 - _smoothstep(whorl.y - 0.2 * frame.half_width, whorl.y + 0.2 * frame.half_width, p.y)
    flow = radial + Vector((away * 0.6 * top * (1.0 - w_front), 0.0, 0.0))
    # the fringe: forward, then swept
    fringe = FORWARD + Vector((gp.sweep, 0.0, 0.0))
    flow = flow.lerp(fringe, w_front)
    t = flow - n * flow.dot(n)
    if t.length < 1e-5:
        t = DOWN - n * DOWN.dot(n)
    return t.normalized()


def crown_points(whorl, frame, gp):
    """Whorl centres (x, y) — the main one on the part line, extras spread
    behind it to either side (typical placement for double/triple crowns)."""
    pts = [whorl]
    sp = gp.crown_spread * frame.half_width
    extra = ((-1.0, 0.8), (1.0, 0.8))
    for i in range(max(0, min(2, gp.crowns - 1))):
        dx, dy = extra[i]
        pts.append(Vector((whorl.x + dx * sp, whorl.y + dy * sp, 0.0)))
    return pts


def _crown_flow(p, crowns, swirl):
    """Horizontal hair direction from one or more whorls: each radiates
    outward with a slight spiral (alternating sense, as real multiple crowns
    tend to), blended by inverse-square distance so near a crown its own
    pattern dominates and between crowns the flows meet."""
    total = Vector((0.0, 0.0, 0.0))
    for i, c in enumerate(crowns):
        r = Vector((p.x - c.x, p.y - c.y, 0.0))
        d = r.length
        if d < 1e-5:
            continue
        r /= d
        sense = 1.0 if i % 2 == 0 else -1.0
        spiral = (r + Vector((-r.y, r.x, 0.0)) * swirl * sense).normalized()
        w = 1.0 / (d * d + 1e-4)
        total += spiral * w
    if total.length < 1e-6:
        return FORWARD.copy()
    return total.normalized()


class HeadProxy:
    """Axis-aligned ellipsoid fitted to the scalp — the cranium the hair
    drapes over. Smooth and convex, so strands slide off it predictably
    (the real mesh has ears and brow ridges that snag guides)."""

    def __init__(self, center, radii):
        self.center = Vector(center)
        self.radii = Vector(radii)

    @classmethod
    def fit(cls, points):
        """Least-squares ``Ax²+By²+Cz²+Dx+Ey+Fz = 1``; falls back to the
        bounding box if the fit is degenerate."""
        import numpy as np
        P = np.array([tuple(p) for p in points], dtype=float)
        lo, hi = P.min(axis=0), P.max(axis=0)
        mid = (lo + hi) / 2
        Q = P - mid  # condition the system
        M = np.column_stack([Q[:, 0] ** 2, Q[:, 1] ** 2, Q[:, 2] ** 2, Q[:, 0], Q[:, 1], Q[:, 2]])
        try:
            A, B, C, D, E, F = np.linalg.lstsq(M, np.ones(len(Q)), rcond=None)[0]
            if min(A, B, C) <= 0:
                raise ValueError("not an ellipsoid")
            c = np.array([-D / (2 * A), -E / (2 * B), -F / (2 * C)])
            g = 1 + D * D / (4 * A) + E * E / (4 * B) + F * F / (4 * C)
            radii = np.sqrt(g / np.array([A, B, C]))
            if not np.all(np.isfinite(radii)) or radii.max() > 3 * (hi - lo).max():
                raise ValueError("unstable fit")
            # the LSQ surface cuts through the scalp; grow it until it
            # encloses ~90% of it so Volume means distance from the skull
            u = (P - (c + mid)) / radii
            radii = radii * float(np.percentile(np.sqrt((u * u).sum(axis=1)), 90))
            return cls(c + mid, radii)
        except (ValueError, np.linalg.LinAlgError):
            half = (hi - lo) / 2
            return cls((mid[0], mid[1], lo[2]), (half[0], half[1], hi[2] - lo[2]))

    inflation_grid = None  # [az_bin][z_bin] metres, see build_inflation

    def build_inflation(self, points, frame, face_half_angle=55.0, az_bins=36, z_step=0.01):
        """Record how far the real head sticks out beyond the ellipsoid
        (ears, mastoids, occiput) outside the face, as a dilated + blurred
        bulge map, so hair rounds smoothly over the ears instead of stepping."""
        z0 = frame.chin_z
        nz = max(2, int((frame.crown_z - z0) / z_step) + 2)
        grid = [[0.0] * nz for _ in range(az_bins)]
        for p in points:
            if p.z < z0 or p.z > frame.crown_z:
                continue
            az = math.degrees(math.atan2(p.x - self.center.x, -(p.y - self.center.y)))
            if abs(az) < face_half_angle:
                continue
            off = self.nearest_raw(p)[2]
            if off <= 0.0:
                continue
            ai = int((az + 180.0) / 360.0 * az_bins) % az_bins
            zi = min(nz - 1, int((p.z - z0) / z_step))
            grid[ai][zi] = max(grid[ai][zi], off)

        def neighbours(g, a, z):
            for da in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    zz = z + dz
                    if 0 <= zz < nz:
                        yield g[(a + da) % az_bins][zz]

        grid = [[max(neighbours(grid, a, z)) for z in range(nz)] for a in range(az_bins)]  # dilate
        for _ in range(3):  # blur
            grid = [[sum(neighbours(grid, a, z)) / len(list(neighbours(grid, a, z)))
                     for z in range(nz)] for a in range(az_bins)]
        self.inflation_grid = grid
        self._z0, self._zstep, self._az_bins = z0, z_step, az_bins

    def inflation(self, p):
        g = self.inflation_grid
        if g is None:
            return 0.0
        az = math.degrees(math.atan2(p.x - self.center.x, -(p.y - self.center.y)))
        fa = (az + 180.0) / 360.0 * self._az_bins - 0.5
        fz = min(max((p.z - self._z0) / self._zstep - 0.5, 0.0), len(g[0]) - 1.001)
        a0 = int(math.floor(fa)); ta = fa - a0
        z0 = int(fz); tz = fz - z0
        def at(a, z):
            return g[a % self._az_bins][z]
        top = at(a0, z0) * (1 - ta) + at(a0 + 1, z0) * ta
        bot = at(a0, z0 + 1) * (1 - ta) + at(a0 + 1, z0 + 1) * ta
        return top * (1 - tz) + bot * tz

    def nearest_raw(self, p):
        """(surface point, outward normal, signed offset) — radial
        projection, accurate enough for a near-spherical head."""
        u = Vector(((p.x - self.center.x) / self.radii.x,
                    (p.y - self.center.y) / self.radii.y,
                    (p.z - self.center.z) / self.radii.z))
        if u.length < 1e-6:
            u = Vector((0.0, 0.0, 1.0))
        s = u.normalized()
        hit = Vector((self.center.x + s.x * self.radii.x,
                      self.center.y + s.y * self.radii.y,
                      self.center.z + s.z * self.radii.z))
        nrm = Vector((s.x / self.radii.x, s.y / self.radii.y, s.z / self.radii.z)).normalized()
        return hit, nrm, (p - hit).dot(nrm)


def _dome_hug(q, head, vol, band=0.025):
    """How far hair may stand off beyond its shell: tight on the dome (it
    rests on the hair beneath), loosening smoothly through ``band`` metres
    around the head's widest point, then free (None). A hard on/off switch
    leaves a visible crease round the head."""
    w = _smoothstep(head.center.z - band, head.center.z + band, q.z)
    if w <= 0.0:
        return None
    return 0.6 * vol + (1.0 - w) * 0.05


FACE_HALF_WIDTH = 0.6  # face edge, as a fraction of the scalp half-width
MIN_FRINGE_LENGTH = 0.05  # metres; shorter fringe strands become side hair
BODY_SHELL = 0.004  # clearance from the real skin/clothes (nose, ears, neck, shoulders)


def _collide(p, head, body, shell, hug=None):
    """Keep ``p`` ``shell`` outside the head proxy (and, with ``hug``, no
    further than ``shell + hug`` — hair resting on the hair beneath it),
    then clear the real body mesh."""
    hit, nrm, off = head.nearest_raw(p)
    shell += head.inflation(p)  # smooth bulge over ears / occiput
    if off < shell:
        p = hit + nrm * shell
    elif hug is not None and off > shell + hug:
        p = hit + nrm * (shell + hug)
    if body is not None:
        for _ in range(2):
            bhit, bn, _, _ = body.find_nearest(p)
            if bhit is None or (p - bhit).dot(bn) >= BODY_SHELL:
                break
            p = bhit + bn * BODY_SHELL
    return p


def grow_guide(root, normal, frame, head, body, gp, rng):
    """Polyline (list of Vectors) for one guide, resampled to gp.points.
    ``head`` is a HeadProxy, ``body`` an optional BVHTree of skin/clothes."""
    tip_units, w_front, side_units = _tip_units(root, frame, gp)
    # hairline roots that sit at/below the fringe line would only grow into
    # stubs — on a real head that hair sweeps sideways with the side hair
    if w_front > 0.5 and root.z - frame.z_at(tip_units) < MIN_FRINGE_LENGTH:
        w_front, tip_units = 0.0, side_units
    jitter = rng.uniform(-gp.length_jitter, gp.length_jitter)
    tip_units += jitter
    tip_z = frame.z_at(tip_units)
    side_tip_z = frame.z_at(side_units + jitter)
    if tip_z > root.z - 0.025:
        tip_z = root.z - 0.025

    step = 0.004
    comb = _comb_direction(root, normal, frame, gp, w_front)
    d = (comb + normal * (0.1 + 0.6 * gp.lift)).normalized()
    root_shell = 0.0015
    vol = gp.volume * (1.0 + (gp.fringe_volume - 1.0) * w_front)  # fringe standoff
    # distance over which the strand gives in to gravity (stiff hair holds longer)
    grav = min(1.0, step / (0.01 + 0.07 * gp.stiffness))
    # where the strand "wants" to hang: down, leaning with the fringe sweep
    # and fanning out on the sides
    radial = Vector((root.x - frame.center.x, root.y - frame.center.y, 0.0))
    radial = radial.normalized() if radial.length > 1e-5 else Vector()
    # side hair beside the face hangs slightly back, clear of the cheek
    frontness = max(0.0, -radial.y) * (1.0 - w_front)
    fall = (DOWN
            + Vector((gp.sweep * 0.55 * w_front, 0.2 * frontness, 0.0))
            + radial * gp.flare * (1.0 - w_front)).normalized()

    # The face plane: just behind the cheekbones. Side hair is kept behind it
    # below the brow (it frames the face instead of covering the cheek), and
    # nothing in front of it hangs lower than the fringe line.
    face_y = head.center.y - 0.35 * head.radii.y
    brow_z = frame.eye_z + 0.25 * (frame.crown_z - frame.eye_z)
    fringe_z = frame.z_at(_fringe_units(root, frame, gp))
    state = {"side": w_front < 0.5}  # fringe that sweeps past the face becomes side hair

    def constrain(q):
        # the limit slopes in over a few cm around the brow (side hair sweeps
        # back diagonally) — a hard step leaves a crease round the head
        if state["side"]:
            limit = face_y - 0.08 * _smoothstep(brow_z - 0.01, brow_z + 0.04, q.z)
            if q.y < limit:
                q = Vector((q.x, limit, q.z))
        return q

    pts = [root.copy()]
    p = root.copy()
    arc = 0.0
    max_len = frame.unit * 2.5
    # the fringe's sideways lean only lasts while it's in front of the face;
    # past the face edge it curtains straight down, close to the head
    face_edge = FACE_HALF_WIDTH * frame.half_width
    past_max = 0.0
    while arc < max_len and len(pts) < 600:
        past = _smoothstep(face_edge, face_edge + 0.3 * frame.half_width, abs(p.x - frame.center.x))
        past_max = max(past_max, past)
        if past_max > 0.5:
            state["side"] = True
        lean = gp.sweep * 0.55 * w_front * (1.0 - past)
        fall_now = (DOWN
                    + Vector((lean, 0.2 * frontness, 0.0))
                    + radial * gp.flare * (1.0 - w_front)).normalized()
        # once past the face, the swept fringe drops (instead of sliding on
        # around the head at brow height)
        g_now = max(grav, 0.5 * past * w_front)
        d = (d * (1.0 - g_now) + fall_now * g_now).normalized()
        q = p + d * step
        # the fringe stands off the forehead by fringe_volume, but past the
        # face edge it settles back to the side volume
        v_here = vol + (gp.volume - vol) * past
        shell = root_shell + (v_here - root_shell) * _smoothstep(0.0, 0.05, arc)
        # hair rests on the upper dome (and the fringe on the forehead)
        # instead of flying off; below that it hangs free
        brow = w_front > 0.5 and past < 0.5 and q.z > frame.eye_z + 0.2 * (frame.crown_z - frame.eye_z)
        q = _collide(q, head, body, shell, hug=0.6 * v_here if brow else _dome_hug(q, head, v_here))
        q = constrain(q)
        seg = q - p
        if seg.length < 1e-6:
            break
        q = p + seg.normalized() * step
        d = seg.normalized()
        pts.append(q)
        p = q
        arc += step
        # fringe hair that has swept past the face keeps going as side hair
        # (ending it at the fringe line leaves a ledge jutting out at the temple)
        tip_now = tip_z + (min(tip_z, side_tip_z) - tip_z) * past_max * w_front
        in_front = p.y < face_y and past_max < 0.5
        if p.z <= tip_now or (in_front and p.z <= fringe_z):
            break

    pts = _relax(pts, head, body, root_shell, vol, frame, w_front, constrain)
    pts = _flick(pts, frame, gp.flick * (1.0 - w_front))  # fringes don't flip out
    return _resample(pts, gp.points)


def _relax(pts, head, body, root_shell, vol, frame, w_front, constrain=None, spacing=0.008, iterations=14):
    """Smooth the grown polyline and re-collide, so strands bridge over
    bumps (ears, brow) in a curve the way stiff real hair does, instead of
    stepping out sharply where they hit them. Root stays fixed; length is
    restored after each pass."""
    if len(pts) < 4:
        return pts
    total = sum((b - a).length for a, b in zip(pts, pts[1:]))
    n = max(4, int(total / spacing) + 1)
    pts = _resample(pts, n)
    seg = total / (n - 1)
    shells = [root_shell + (vol - root_shell) * _smoothstep(0.0, 0.05, i * seg) for i in range(n)]
    for _ in range(iterations):
        sm = [pts[0]]
        for i in range(1, n - 1):
            sm.append(pts[i] * 0.5 + (pts[i - 1] + pts[i + 1]) * 0.25)
        sm.append(pts[-1] * 0.5 + pts[-2] * 0.5)
        out = [sm[0]]
        for i in range(1, n):
            q = out[-1] + (sm[i] - out[-1]).normalized() * seg
            q = _collide(q, head, body, shells[i], hug=_dome_hug(q, head, vol))
            if constrain is not None:
                q = constrain(q)
            out.append(q)
        pts = out
    return pts


def _flick(pts, frame, amount, curl_length=0.04, max_angle=75.0):
    """Curl the last ``curl_length`` metres of the strand outward — a
    smooth flip that keeps the strand's length (a positional push instead
    makes short horizontal hooks that stack into visible ridges)."""
    from mathutils import Quaternion
    if amount <= 0 or len(pts) < 4:
        return pts
    segs = [b - a for a, b in zip(pts, pts[1:])]
    total = sum(s.length for s in segs)
    out_dir = Vector((pts[-1].x - frame.center.x, pts[-1].y - frame.center.y, 0.0))
    if out_dir.length < 1e-5:
        return pts
    out_dir.normalize()
    new_pts = [pts[0].copy()]
    walked = 0.0
    for seg in segs:
        length = seg.length
        walked += length
        from_tip = total - walked
        d = seg.normalized() if length > 1e-9 else seg
        if from_tip < curl_length and length > 1e-9:
            t = 1.0 - from_tip / curl_length
            angle = math.radians(max_angle) * amount * t ** 1.5
            axis = d.cross(out_dir)
            if axis.length > 1e-6:
                d = Quaternion(axis.normalized(), angle) @ d
        new_pts.append(new_pts[-1] + d * length)
    return new_pts


def _resample(pts, count):
    if len(pts) < 2:
        return [pts[0]] * count
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + (b - a).length)
    total = acc[-1]
    out = []
    j = 0
    for k in range(count):
        s = total * k / (count - 1)
        while j < len(acc) - 2 and acc[j + 1] < s:
            j += 1
        seg = acc[j + 1] - acc[j]
        t = 0.0 if seg <= 0 else (s - acc[j]) / seg
        out.append(pts[j].lerp(pts[j + 1], min(1.0, max(0.0, t))))
    return out


def grow_guides(samples, frame, body, gp, head=None, skin_points=None):
    """Pick roots and grow every guide. Returns list of point lists.
    ``body``: BVHTree of skin/clothes (or None); ``head``: HeadProxy
    (fitted to the scalp when omitted); ``skin_points``: world-space body
    vertices used to round the proxy over the ears (optional)."""
    if head is None:
        head = HeadProxy.fit([p for p, _ in samples])
        if skin_points:
            head.build_inflation(skin_points, frame)
    roots = pick_roots(samples, gp.guide_spacing, gp.seed)
    rng = random.Random(gp.seed * 7919 + 17)
    return [grow_guide(p, n, frame, head, body, gp, rng) for p, n in roots]


def write_guides(curves_data, guides):
    """Replace all curves in a Curves datablock with ``guides`` (world ==
    object space; the guides object is kept at the identity transform)."""
    if len(curves_data.curves):
        curves_data.remove_curves()
    if not guides:
        return
    curves_data.add_curves([len(g) for g in guides])
    flat = [c for g in guides for p in g for c in p]
    curves_data.position_data.foreach_set("vector", flat)


def fringe_weight(p, frame, gp):
    """0..1 — how much a scalp point belongs to the fringe (same blend the
    guides use), for fringe-only effects further down the stack."""
    return _tip_units(p, frame, gp)[1]
