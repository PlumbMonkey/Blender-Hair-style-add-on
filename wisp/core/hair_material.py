"""Realistic hair material — Principled Hair BSDF (Chiang), melanin driven.

Colour comes from physically based pigment values, not RGB. Cycles renders
the melanin model directly; EEVEE ignores the parametrization and always
shades the node's Color input, so Wisp also writes an approximate colour
derived from the same melanin values (see ``eevee_color``). One node, one
source of truth, both engines.
"""

import math

import bpy

# name: (melanin, melanin_redness, roughness, radial_roughness)
COLOR_PRESETS = {
    'BLACK': (0.95, 0.20, 0.28, 0.30),
    'DARK_BROWN': (0.80, 0.30, 0.28, 0.30),
    'BROWN': (0.75, 0.40, 0.30, 0.30),
    'LIGHT_BROWN': (0.50, 0.50, 0.33, 0.32),
    'BLONDE': (0.25, 0.40, 0.35, 0.35),
    'RED': (0.55, 0.95, 0.33, 0.32),
    'GREY': (0.10, 0.10, 0.38, 0.35),
}

def ensure_hair_material(curves_obj, name=None):
    """The Wisp hair material on ``curves_obj`` (created if missing)."""
    name = name or curves_obj.name + "_Material"
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        _build_nodes(mat)
    if not curves_obj.data.materials:
        curves_obj.data.materials.append(mat)
    else:
        curves_obj.data.materials[0] = mat
    return mat


def _build_nodes(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.location = (300, 0)
    bsdf = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    bsdf.name = "Wisp Hair"
    bsdf.location = (0, 0)
    bsdf.parametrization = 'MELANIN'
    nt.links.new(bsdf.outputs[0], out.inputs["Surface"])


# Chiang et al. 2016 pigment absorption (per unit concentration, RGB)
_EUMELANIN = (0.419, 0.697, 1.37)
_PHEOMELANIN = (0.187, 0.4, 1.05)


def eevee_color(melanin, redness, radial_roughness=0.3, darkness=0.7, desaturate=0.3):
    """Linear RGB for the Color input that makes EEVEE match the Cycles
    melanin look.

    Pigment absorption (mapped as in Cycles) → Chiang's absorption→colour
    inversion → pulled toward grey (Cycles' multiple scattering neutralises
    the tint) → pre-compensated for EEVEE's hair shading, which measured
    roughly as ``out ≈ 17·in^1.32`` (brightens and saturates dark input).
    """
    q = -math.log(max(1.0 - melanin, 1e-4))
    eu, ph = q * (1.0 - redness), q * redness
    sigma = [eu * a + ph * b for a, b in zip(_EUMELANIN, _PHEOMELANIN)]
    b = radial_roughness
    f = 5.969 - 0.215 * b + 2.532 * b ** 2 - 10.73 * b ** 3 + 5.574 * b ** 4 + 0.245 * b ** 5
    c = [math.exp(-math.sqrt(s) * f * darkness) for s in sigma]
    lum = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    c = [x * (1.0 - desaturate) + lum * desaturate for x in c]
    return tuple(min(1.0, (x / 8.3) ** 0.76) for x in c)


def _socket(node, name):
    """Input by name, including sockets hidden by the current
    parametrization (bpy's name lookup skips unavailable ones)."""
    for sock in node.inputs:
        if sock.name == name:
            return sock
    raise KeyError(name)


def _bsdf(mat):
    return mat.node_tree.nodes.get("Wisp Hair")


def _ensure_gradient(mat, bsdf):
    """Root→tip pigment gradient: Curves Info.Intercept drives Melanin
    (Cycles) through a Map Range and the EEVEE Color through a Mix. Added to
    older Wisp materials on the fly."""
    nt = mat.node_tree
    info = nt.nodes.get("Wisp Curves Info")
    if info is None:
        info = nt.nodes.new("ShaderNodeHairInfo")
        info.name = "Wisp Curves Info"
        info.location = (-700, 0)
    mr = nt.nodes.get("Wisp Melanin Gradient")
    if mr is None:
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.name = "Wisp Melanin Gradient"
        mr.location = (-400, 150)
    mix = nt.nodes.get("Wisp Color Gradient")
    if mix is None:
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.name = "Wisp Color Gradient"
        mix.location = (-400, -150)
    links = [(info.outputs["Intercept"], mr.inputs["Value"]),
             (mr.outputs["Result"], _socket(bsdf, "Melanin")),
             (info.outputs["Intercept"], mix.inputs["Factor"]),
             (mix.outputs["Result"], _socket(bsdf, "Color"))]
    for out, inp in links:
        if not any(l.from_socket == out for l in inp.links):
            nt.links.new(out, inp)
    return mr, mix


def _mix_inputs(mix):
    """(A, B) colour sockets of an RGBA Mix node."""
    rgba = [s for s in mix.inputs if s.type == 'RGBA']
    return rgba[0], rgba[1]


def apply_color(mat, melanin, redness, roughness=0.3, radial_roughness=0.3,
                random_color=0.08, random_roughness=0.15, coat=0.0, tint=(1.0, 1.0, 1.0),
                tip_lighten=0.08, root_darken=0.04):
    """Set the look. ``melanin`` is the mid-length value; roots are
    ``root_darken`` darker and tips ``tip_lighten`` lighter (sun-lightened
    ends), in both Cycles and EEVEE."""
    b = _bsdf(mat)
    if b is None:
        _build_nodes(mat)
        b = _bsdf(mat)
    b.parametrization = 'MELANIN'  # before touching inputs: sockets depend on it
    ins = b.inputs
    ins["Melanin"].default_value = melanin
    ins["Melanin Redness"].default_value = redness
    ins["Roughness"].default_value = roughness
    ins["Radial Roughness"].default_value = radial_roughness
    ins["Random Color"].default_value = random_color
    ins["Random Roughness"].default_value = random_roughness
    ins["Coat"].default_value = coat
    ins["Tint"].default_value = (*tint, 1.0)

    m_root = min(1.0, melanin + root_darken)
    m_tip = max(0.0, melanin - tip_lighten)
    mr, mix = _ensure_gradient(mat, b)
    mr.inputs["From Min"].default_value = 0.0
    mr.inputs["From Max"].default_value = 1.0
    mr.inputs["To Min"].default_value = m_root
    mr.inputs["To Max"].default_value = m_tip
    # EEVEE shades Color whatever the parametrization
    a_sock, b_sock = _mix_inputs(mix)
    for sock, m in ((a_sock, m_root), (b_sock, m_tip)):
        ec = eevee_color(m, redness, radial_roughness)
        sock.default_value = (*(c * t for c, t in zip(ec, tint)), 1.0)
    _socket(b, "Color").default_value = (*(c * t for c, t in zip(
        eevee_color(melanin, redness, radial_roughness), tint)), 1.0)
    return mat


def preset_values(key):
    return COLOR_PRESETS[key]
