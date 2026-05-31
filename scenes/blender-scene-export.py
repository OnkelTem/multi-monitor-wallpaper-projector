import bpy
import json
import os

OBJECTS = [
    "m-left",
    "m-center",
    "m-right",
    "panorama",
]

scene_data = {}

# Camera
cam = bpy.data.objects["camera"]

scene_data["camera"] = {
    "location": list(cam.location),
    "rotation": list(cam.rotation_euler),
}

# Meshes
scene_data["objects"] = {}

for name in OBJECTS:
    obj = bpy.data.objects[name]

    verts = []

    for v in obj.data.vertices:
        world = obj.matrix_world @ v.co

        verts.append([
            world.x,
            world.y,
            world.z,
        ])

    scene_data["objects"][name] = {
        "vertices": verts,
    }

project_dir = os.path.dirname(bpy.data.filepath)

outfile = os.path.join(
    project_dir,
    "scene.json"
)

with open(outfile, "w", encoding="utf-8") as f:
    json.dump(
        scene_data,
        f,
        indent=2
    )

print("Saved:", outfile)
