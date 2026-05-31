# ADR-003: scene.json (geometry) and config.json (projection)

**Context:** Blender scene geometry (camera position, monitor and panorama
quads) must be separated from user projection configuration (screenshots,
monitor resolutions).

**Decision:** scene.json is a read-only Blender export (vertices, camera).
config.json is a user-facing config with projection and screenshot paths.
init-config.py generates config.json from scene.json + actual screens
via xrandr.

**Consequences:** When the scene is rebuilt, only scene.json is updated;
config.json is preserved. init-config.py is run once.
