#!/usr/bin/env python3
"""
Интерактивный кадрирователь с клавиатурным управлением.
Заблокированный aspect ratio панорамы из scene.json.
"""

import json
import os
import sys
import cv2
import numpy as np
import argparse
import tkinter as tk
from PIL import Image, ImageTk


def vertices_to_quad(vertices):
    pts = np.array(vertices, dtype=np.float32)
    return np.array([
        pts[2],
        pts[3],
        pts[1],
        pts[0],
    ], dtype=np.float32)


def get_quad_size(quad):
    width = float(np.linalg.norm(quad[1] - quad[0]))
    height = float(np.linalg.norm(quad[3] - quad[0]))
    if width <= 0.0 or height <= 0.0:
        raise ValueError("Quad has invalid size")
    return width, height


def main():
    parser = argparse.ArgumentParser(
        description="Interactive crop tool with panorama aspect ratio lock."
    )
    parser.add_argument(
        "--scene",
        default="scene.json",
        help="Path to scene.json (default: ./scene.json)",
    )
    parser.add_argument(
        "--dir",
        default=None,
        help="Output directory name (default: image filename without extension)",
    )
    parser.add_argument(
        "image",
        help="Path to the input image",
    )
    args = parser.parse_args()

    if not os.path.exists(args.scene):
        print(f"Error: {args.scene} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.scene, "r", encoding="utf-8") as f:
        scene = json.load(f)

    # Find panorama object
    panorama_name = None
    for name in scene.get("objects", {}):
        if "panorama" in name.lower():
            panorama_name = name
            break
    if not panorama_name:
        print("Error: No panorama object found in scene.json", file=sys.stderr)
        sys.exit(1)

    panorama = scene["objects"][panorama_name]
    pano_quad = vertices_to_quad(panorama["vertices"])
    pano_width, pano_height = get_quad_size(pano_quad)
    target_aspect = pano_width / pano_height

    img = cv2.imread(args.image)
    if img is None:
        print(f"Error: Cannot load image '{args.image}'", file=sys.stderr)
        sys.exit(1)

    img_h, img_w = img.shape[:2]

    output_dir = args.dir if args.dir else os.path.splitext(os.path.basename(args.image))[0]
    os.makedirs(output_dir, exist_ok=True)

    # Load persisted crop if available
    crop_json_path = os.path.join(output_dir, "crop.json")
    loaded = False
    if os.path.exists(crop_json_path):
        with open(crop_json_path, "r") as f:
            saved = json.load(f)
        sx, sy, sw, sh = saved["x"], saved["y"], saved["width"], saved["height"]
        if (0 <= sx < img_w and 0 <= sy < img_h
                and sw > 0 and sh > 0
                and sx + sw <= img_w and sy + sh <= img_h):
            crop_x, crop_y, crop_w, crop_h = sx, sy, sw, sh
            loaded = True

    if not loaded:
        crop_w = img_w
        crop_h = int(round(crop_w / target_aspect))
        if crop_h > img_h:
            crop_h = img_h
            crop_w = int(round(crop_h * target_aspect))
        crop_x = (img_w - crop_w) // 2
        crop_y = (img_h - crop_h) // 2

    move_h = (crop_w < img_w)
    move_v = (crop_h < img_h)

    step = 10
    big_step = 100

    MAX_DISPLAY_W = 1920
    MAX_DISPLAY_H = 1080

    display_scale = min(1.0, MAX_DISPLAY_W / img_w, MAX_DISPLAY_H / img_h)
    disp_w = int(img_w * display_scale)
    disp_h = int(img_h * display_scale)

    # tkinter window
    root = tk.Tk()
    root.title("Crop")
    exit_flag = False

    def on_close():
        nonlocal exit_flag
        exit_flag = True
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    label = tk.Label(root)

    centered = False

    def update():
        nonlocal centered
        if exit_flag:
            return

        # Resize full image to display size FIRST, then draw overlay
        display = cv2.resize(img, (disp_w, disp_h), interpolation=cv2.INTER_LANCZOS4)
        overlay = display.copy()
        dx = int(crop_x * display_scale)
        dy = int(crop_y * display_scale)
        dw = int(crop_w * display_scale)
        dh = int(crop_h * display_scale)
        cv2.rectangle(overlay, (dx, dy), (dx + dw, dy + dh), (0, 0, 0), -1)
        display = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
        cv2.rectangle(display, (dx, dy), (dx + dw, dy + dh), (0, 255, 0), 2)

        # Convert to tkinter-compatible image (no PIL resize needed)
        display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(display_rgb)
        tk_img = ImageTk.PhotoImage(pil_img)
        label.config(image=tk_img)
        label.image = tk_img  # keep reference

        if not centered:
            centered = True
            x = (root.winfo_screenwidth() - disp_w) // 2
            y = (root.winfo_screenheight() - disp_h) // 2
            root.geometry(f"+{x}+{y}")

        root.after(30, update)

    def on_key(event):
        nonlocal crop_x, crop_y, crop_w, crop_h, move_h, move_v, output_dir

        if event.keysym == "Escape":
            root.destroy()
            sys.exit(0)
        elif event.keysym == "Return":
            root.destroy()

            # Save crop.json
            crop_data = {"x": crop_x, "y": crop_y, "width": crop_w, "height": crop_h}
            with open(os.path.join(output_dir, "crop.json"), "w") as f:
                json.dump(crop_data, f, indent=2)

            # Save cropped image as source.jpg
            crop_img = img[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
            cv2.imwrite(os.path.join(output_dir, "source.jpg"), crop_img)
            print(f"Saved: {output_dir}/source.jpg ({crop_w}x{crop_h})")
            sys.exit(0)

        elif event.keysym in ("w", "W", "Up") and move_v:
            crop_y = max(0, crop_y - step)
        elif event.keysym in ("s", "S", "Down") and move_v:
            crop_y = min(img_h - crop_h, crop_y + step)
        elif event.keysym in ("a", "A", "Left") and move_h:
            crop_x = max(0, crop_x - step)
        elif event.keysym in ("d", "D", "Right") and move_h:
            crop_x = min(img_w - crop_w, crop_x + step)
        elif event.keysym in ("plus", "equal"):
            new_w = min(img_w, int(crop_w * 1.1))
            new_h = int(round(new_w / target_aspect))
            if new_h <= img_h:
                crop_x = max(0, min(crop_x - (new_w - crop_w) // 2, img_w - new_w))
                crop_y = max(0, min(crop_y - (new_h - crop_h) // 2, img_h - new_h))
                crop_w = new_w
                crop_h = new_h
        elif event.keysym in ("minus", "underscore"):
            new_w = max(100, int(crop_w / 1.1))
            new_h = int(round(new_w / target_aspect))
            if new_h <= img_h:
                crop_x = max(0, min(crop_x + (crop_w - new_w) // 2, img_w - new_w))
                crop_y = max(0, min(crop_y + (crop_h - new_h) // 2, img_h - new_h))
                crop_w = new_w
                crop_h = new_h
        elif event.keysym in ("r", "R"):
            crop_w = img_w
            crop_h = int(round(crop_w / target_aspect))
            if crop_h > img_h:
                crop_h = img_h
                crop_w = int(round(crop_h * target_aspect))
            crop_x = (img_w - crop_w) // 2
            crop_y = (img_h - crop_h) // 2
            move_h = (crop_w < img_w)
            move_v = (crop_h < img_h)

    root.bind("<Key>", on_key)
    update()
    label.pack()
    label.focus_set()
    root.mainloop()


if __name__ == "__main__":
    main()
