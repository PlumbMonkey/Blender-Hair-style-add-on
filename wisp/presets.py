"""Realistic hairstyle presets.

Each preset sets the *shape* (GroomParams fields, used when growing guides)
and the *detail* (hair stack values, applied live). Lengths are head units
below the crown: ~0.5 eyes, 1.0 chin, ~1.3 shoulders, 2+ mid-back.
"""

HAIRSTYLE_PRESETS = {
    'MOP_TOP': dict(
        label="Mop Top", description="Side part, fringe swept over one eye, jaw-to-collar length that flips out",
        # tuned against front/side/back reference photos (Nova, 2026-09-26);
        # best with the scalp Hairline at ~0.62 so no stubs grow on the forehead
        # 2026-09-29: fringe longer/thicker but only partly over the right eye
        shape=dict(fringe_length=0.50, side_length=0.92, back_length=1.18, fringe_width=55.0,
                   volume=0.017, fringe_volume=1.1, lift=0.4, stiffness=0.2, part=0.5, sweep=-0.7,
                   fringe_tilt=-0.3, flick=0.4, flare=0.0, length_jitter=0.04, fringe_pieces=0.7,
                   fringe_thickness=1.6),
        detail=dict(clump=0.35, clump_shape=0.0, clump_size=0.01, tip_spread=0.0005,
                    noise=0.005, noise_scale=3.0, frizz=0.0003,
                    density=260.0, radius=0.00008, taper_start=0.75, flyaways=0.03, flyaway_distance=0.02),
        color='BROWN',
        material=dict(melanin=0.78, redness=0.62, roughness=0.25, tint=(1.0, 0.88, 0.7),  # tuned in Cycles
                      tip_lighten=0.05),
    ),
    'BOB': dict(
        label="Bob", description="Jaw-length blunt bob with brow-length fringe",
        shape=dict(fringe_length=0.42, side_length=0.95, back_length=0.95, fringe_width=45.0,
                   volume=0.010, fringe_volume=0.6, lift=0.25, stiffness=0.4, part=0.0, sweep=0.0, fringe_tilt=0.0,
                   flick=0.0, flare=0.0, length_jitter=0.02),
        detail=dict(clump=0.35, clump_shape=0.0, clump_size=0.006, noise=0.002, frizz=0.0004),
    ),
    'SHAG': dict(
        label="Shoulder Shag", description="Layered shoulder-length shag with curtain fringe",
        shape=dict(fringe_length=0.55, side_length=1.3, back_length=1.4, fringe_width=40.0,
                   volume=0.02, fringe_volume=0.8, lift=0.5, stiffness=0.45, part=0.0, sweep=0.0, fringe_tilt=0.0,
                   flick=0.6, flare=0.06, length_jitter=0.15),
        detail=dict(clump=0.65, clump_shape=0.4, clump_size=0.01, noise=0.006, frizz=0.0012),
    ),
    'LONG_STRAIGHT': dict(
        label="Long Straight", description="Long straight hair with a side part, no fringe",
        shape=dict(fringe_length=1.5, side_length=2.2, back_length=2.4, fringe_width=35.0,
                   volume=0.010, fringe_volume=0.6, lift=0.2, stiffness=0.3, part=-0.4, sweep=-0.3, fringe_tilt=0.0,
                   flick=0.0, flare=0.0, length_jitter=0.08),
        detail=dict(clump=0.4, clump_shape=0.2, clump_size=0.008, noise=0.003, frizz=0.0005),
    ),
    'SHORT_CROP': dict(
        label="Short Crop", description="Short textured crop",
        shape=dict(fringe_length=0.3, side_length=0.35, back_length=0.55, fringe_width=45.0,
                   volume=0.008, fringe_volume=1.0, lift=0.6, stiffness=0.8, part=-0.3, sweep=0.2, fringe_tilt=0.0,
                   flick=0.0, flare=0.0, length_jitter=0.03),
        detail=dict(clump=0.6, clump_shape=0.5, clump_size=0.005, noise=0.002, frizz=0.0008),
    ),
}

COLOR_LABELS = {
    'BLACK': "Black",
    'DARK_BROWN': "Dark Brown",
    'BROWN': "Brown",
    'LIGHT_BROWN': "Light Brown",
    'BLONDE': "Blonde",
    'RED': "Red",
    'GREY': "Grey",
}
