# Procedural Scalp Hair Generator V2

A Blender addon that heuristically detects the scalp region of a head mesh and generates procedural hair using Geometry Nodes.

## Requirements

- **Blender 5.1+** (uses `NodeTree.interface` API and `layout.panel()` collapsible sections)

## Installation

### Option A: Install as Extension (Recommended)
1. Run `python build_zip.py` from the project root to create the distributable zip
2. In Blender: **Edit > Preferences > Extensions**
3. Use **Install from Disk** and select `procedural_scalp_hair_v2.1.0.zip`

### Option B: Install from ZIP (Legacy)
1. In Blender: **Edit > Preferences > Add-ons > Install…**
2. Select `procedural_scalp_hair_v2.1.0.zip`
3. Enable **"Procedural Scalp Hair Generator"** in the addon list

### Option C: Symlink for development
Link the `procedural_scalp_hair/` folder into your Blender extensions directory:

```
# Windows (run as admin)
mklink /D "%APPDATA%\Blender Foundation\Blender\5.1\extensions\user_default\procedural_scalp_hair" "D:\Dev Projects 2026\Hair Generator V2\procedural_scalp_hair"

# macOS / Linux
ln -s "/path/to/Hair Generator V2/procedural_scalp_hair" ~/.config/blender/5.1/extensions/user_default/procedural_scalp_hair
```

Then enable the addon in Blender preferences. Changes to code take effect after restarting Blender or reloading scripts (F3 > "Reload Scripts").

## Usage

1. Select a head mesh in the 3D viewport
2. Open the **HairGen** tab in the sidebar (N-panel)
3. Adjust scalp detection parameters, then click **Generate Scalp Mask**
4. Choose a style preset (Short / Medium / Long) or tune values manually
5. Click **Generate Hair**

## Project Structure

```
procedural_scalp_hair/
├── __init__.py              # Addon registration, bl_info
├── blender_manifest.toml    # Extension manifest (Blender 4.2+)
├── constants.py             # Shared string constants
├── geometry_utils.py        # Mesh/vertex math helpers
├── scalp_mask.py            # Heuristic scalp detection
├── hair_nodes.py            # Geometry Nodes tree builder
├── presets.py               # Style preset definitions
├── properties.py            # Blender PropertyGroup
├── operators.py             # Operator classes
└── panels.py                # UI panel (collapsible sections)
```

## Development

- `build_zip.py` — builds a distributable `.zip` from the addon folder
- The addon uses relative imports; always load via Blender's addon system, not `import procedural_scalp_hair` from a standalone script.
