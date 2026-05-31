# ADR-002: Crop and Wallpaper as separate tools

**Context:** Wallpaper generation requires two distinct operations:
interactive crop area selection and batch generation from Blender geometry.
Combining both in a single script complicates both the UI and the pipeline.

**Decision:** crop.py is an interactive cropper with aspect ratio lock that
saves crop.json + source.jpg. wallpaper.py is a batch generator that reads
source.jpg and config.json, with no UI. Pipeline: crop → wallpaper.

**Consequences:** Two runs instead of one, but each script is simple and
reusable. source.jpg is the single interface between them.
