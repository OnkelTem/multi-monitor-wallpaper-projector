import json
import os
import sys
import cv2
import numpy as np
import argparse


# ----------------------------
# utils: vertices → quad
# ----------------------------
def vertices_to_quad(vertices):
    """
    Вершины всегда в порядке [BL, BR, TL, TR].
    Преобразуем в quad [TL, TR, BR, BL].
    """
    pts = np.array(vertices, dtype=np.float32)
    return np.array([
        pts[2],  # TL
        pts[3],  # TR
        pts[1],  # BR
        pts[0],  # BL
    ], dtype=np.float32)


def get_quad_size(quad):
    width = float(np.linalg.norm(quad[1] - quad[0]))
    height = float(np.linalg.norm(quad[3] - quad[0]))

    if width <= 0.0 or height <= 0.0:
        raise ValueError("Quad has invalid size")

    return width, height


def build_world_grid(quad, width, height):
    tl, tr, br, bl = quad

    u = np.linspace(0.0, 1.0, width, dtype=np.float32)
    v = np.linspace(0.0, 1.0, height, dtype=np.float32)
    uu, vv = np.meshgrid(u, v)

    return (
        tl * (1.0 - uu)[..., None] * (1.0 - vv)[..., None]
        + tr * uu[..., None] * (1.0 - vv)[..., None]
        + br * uu[..., None] * vv[..., None]
        + bl * (1.0 - uu)[..., None] * vv[..., None]
    )


def render_monitor(panorama_img, panorama_quad, monitor_quad, camera_pos, dst_size):
    width, height = dst_size
    world_points = build_world_grid(monitor_quad, width, height)

    origin = panorama_quad[0]
    u_axis = panorama_quad[1] - panorama_quad[0]
    v_axis = panorama_quad[3] - panorama_quad[0]
    normal = np.cross(u_axis, v_axis)

    rays = world_points - camera_pos
    numerator = np.dot(normal, origin - camera_pos)
    denominator = np.sum(rays * normal, axis=2)

    valid = np.abs(denominator) > 1e-6
    t = np.zeros_like(denominator, dtype=np.float32)
    t[valid] = numerator / denominator[valid]
    valid &= t > 0.0

    intersections = camera_pos + rays * t[..., None]
    delta = intersections - origin

    uu = float(np.dot(u_axis, u_axis))
    uv = float(np.dot(u_axis, v_axis))
    vv = float(np.dot(v_axis, v_axis))
    det = uu * vv - uv * uv

    if abs(det) < 1e-8:
        raise ValueError("Panorama plane is degenerate")

    rhs_u = np.sum(delta * u_axis, axis=2)
    rhs_v = np.sum(delta * v_axis, axis=2)

    pano_u = (rhs_u * vv - rhs_v * uv) / det
    pano_v = (rhs_v * uu - rhs_u * uv) / det

    valid &= (pano_u >= 0.0) & (pano_u <= 1.0) & (pano_v >= 0.0) & (pano_v <= 1.0)

    map_x = (pano_u * (panorama_img.shape[1] - 1)).astype(np.float32)
    map_y = ((1.0 - pano_v) * (panorama_img.shape[0] - 1)).astype(np.float32)

    map_x[~valid] = -1.0
    map_y[~valid] = -1.0

    return cv2.remap(
        panorama_img,
        map_x,
        map_y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def get_output_path(project_dir, configured_output):
    source_name = os.path.basename(project_dir.rstrip("/\\"))
    output_name = os.path.splitext(os.path.basename(configured_output))[0] + ".jpg"
    output_dir = source_name

    os.makedirs(output_dir, exist_ok=True)

    return os.path.join(output_dir, output_name)


# ----------------------------
# flat mode helpers
# ----------------------------
def get_monitor_position(obj_name):
    name_lower = obj_name.lower()
    if "left" in name_lower:
        return "left"
    elif "right" in name_lower:
        return "right"
    else:
        return "center"


def render_monitor_flat(panorama_img, dst_size, position):
    width, height = dst_size
    target_aspect = width / height
    pano_h, pano_w = panorama_img.shape[:2]

    if pano_w / pano_h > target_aspect:
        crop_h = pano_h
        crop_w = int(crop_h * target_aspect)
    else:
        crop_w = pano_w
        crop_h = int(crop_w / target_aspect)

    if position == 'left':
        x = 0
    elif position == 'right':
        x = pano_w - crop_w
    else:
        x = (pano_w - crop_w) // 2

    y = (pano_h - crop_h) // 2
    cropped = panorama_img[y:y + crop_h, x:x + crop_w]
    return cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LANCZOS4)


# ----------------------------
# main
# ----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Generate monitor wallpapers from a cropped panorama image."
    )
    parser.add_argument(
        "--scene",
        default="scene.json",
        help="Path to scene.json (default: ./scene.json)",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to config.json (default: ./config.json)",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Generate flat crops without 3D projection",
    )
    parser.add_argument(
        "project_dir",
        help="Project directory containing source.jpg",
    )
    args = parser.parse_args()

    if not os.path.exists(args.scene):
        print(f"Error: {args.scene} not found", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.config):
        print(f"Error: {args.config} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.scene, "r", encoding="utf-8") as f:
        scene = json.load(f)

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    source_path = os.path.join(args.project_dir, "source.jpg")
    if not os.path.exists(source_path):
        print(f"Error: {source_path} not found", file=sys.stderr)
        print("Run crop.py first to create the cropped source image.", file=sys.stderr)
        sys.exit(1)

    img = cv2.imread(source_path)
    if img is None:
        print(f"Error: Cannot load {source_path}", file=sys.stderr)
        sys.exit(1)

    objects = scene["objects"]
    camera_pos = np.array(scene["camera"]["location"], dtype=np.float32)

    panorama_name = config["panorama_object"]
    if panorama_name not in objects:
        print(f"Error: Panorama object '{panorama_name}' not found in scene.json", file=sys.stderr)
        sys.exit(1)

    panorama = objects[panorama_name]
    pano_quad = vertices_to_quad(panorama["vertices"])
    pano_width, pano_height = get_quad_size(pano_quad)
    pano_aspect = pano_width / pano_height

    img_h, img_w = img.shape[:2]
    img_aspect = img_w / img_h

    # Verify aspect ratio matches (within 1%)
    if abs(img_aspect - pano_aspect) / pano_aspect > 0.01:
        print(
            f"Error: Image aspect ratio ({img_aspect:.4f}) does not match "
            f"panorama aspect ratio ({pano_aspect:.4f})",
            file=sys.stderr,
        )
        print("Use crop.py to crop the image to match the panorama aspect ratio.", file=sys.stderr)
        sys.exit(1)

    for obj_name, out_cfg in config["outputs"].items():

        if args.flat:
            position = get_monitor_position(obj_name)
            result = render_monitor_flat(
                img,
                (out_cfg["width"], out_cfg["height"]),
                position,
            )
        else:
            if obj_name not in objects:
                print(f"Error: Object '{obj_name}' not found in scene.json", file=sys.stderr)
                sys.exit(1)

            monitor_quad = vertices_to_quad(objects[obj_name]["vertices"])

            result = render_monitor(
                img,
                pano_quad,
                monitor_quad,
                camera_pos,
                (out_cfg["width"], out_cfg["height"]),
            )

        output_path = get_output_path(args.project_dir, out_cfg["output"])
        cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])

        print("Saved:", output_path)


if __name__ == "__main__":
    main()
