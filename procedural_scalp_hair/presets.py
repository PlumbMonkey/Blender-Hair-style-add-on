"""Style presets for hair generation."""


def apply_style_preset(props, preset):
    if preset == 'SHORT':
        props.length = 0.045
        props.density = 780.0
        props.noise = 0.02
        props.clump = 0.08
        props.direction_bias = 0.25
    elif preset == 'MEDIUM':
        props.length = 0.11
        props.density = 520.0
        props.noise = 0.06
        props.clump = 0.18
        props.direction_bias = 0.15
    elif preset == 'LONG':
        props.length = 0.22
        props.density = 340.0
        props.noise = 0.12
        props.clump = 0.28
        props.direction_bias = -0.12
