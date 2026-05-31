# AGENTS.md — for AI assistants

## Architecture

```
scene.json ──→ init-config.py ──→ config.json
                                        │
crop.py ←── scene.json                  │
    │                                    │
    ├── crop.json                        │
    └── source.jpg                       │
         │                               │
         └──→ wallpaper.py ←── config.json + scene.json
                    │
                    ├── center.jpg
                    ├── left.jpg
                    └── right.jpg
                         │
                         └──→ apply-kde-wallpapers.py
```

### Principles

- Each script is an independent CLI, no shared modules
- All scripts use `.venv/bin/python3` (opencv-python, numpy, Pillow)
- `scene.json` is the single source of scene geometry
- `config.json` is the projection + screenshots config (generated, not hand-edited)

### scene.json — critical fields

| Field | Description |
|-------|-------------|
| `objects.*panorama*.vertices` | 4 vertices of the panorama quad → aspect ratio ~4.912 |
| `objects.*monitor*.vertices` | 4 vertices of the monitor quad |
| `camera.position` | Camera position |
| `camera.rotation` | Camera rotation (radians) |

### Important nuances

- Panorama plane aspect ratio changes when the scene is rebuilt in Blender
- `crop.py` locks axes: if crop_w == img_w → left/right movement is forbidden
- `wallpaper.py` checks source.jpg aspect ratio against panorama quad (>1% deviation → error)
- output_dir = source file name (not `dist/`)
- tkinter instead of OpenCV because OpenCV's GTK backend does not handle WM_DELETE_WINDOW correctly
- `apply-kde-wallpapers.py` is a flat CLI, no subparsers

### Common errors

1. `Pillow not installed` → `.venv/bin/pip install Pillow`
2. `aspect ratio mismatch` → source.jpg doesn't match panorama quad, re-run crop.py
3. `scene.json not found` → run from directory with scene.json or use `--scene`
