#!/usr/bin/env python3
"""
Generate config.json from scene.json and xrandr.
"""

import json
import os
import sys
import shutil
import subprocess
import re
import argparse


def load_scene(scene_path):
    with open(scene_path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_monitor_objects(scene):
    """Find m-left, m-center, m-right or detect by keywords."""
    objects = scene.get("objects", {})
    result = {}
    
    # Try exact match first
    for name in ["m-left", "m-center", "m-right"]:
        if name in objects:
            key = name.split("-")[1]  # left, center, right
            result[key] = name
    
    if len(result) == 3:
        return result
    
    # Fallback: search by keywords
    for key in ["left", "center", "right"]:
        for name in objects:
            if key in name.lower() and key not in result:
                result[key] = name
                break
    
    return result


def parse_xrandr_monitors(output):
    """Parse xrandr --listmonitors output."""
    monitors = []
    pattern = re.compile(r"^\s*(\d+):\s+\S+\s+(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)\s+(\S+)$")
    
    for line in output.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        
        monitors.append({
            "index": int(match.group(1)),
            "width": int(match.group(2)),
            "height": int(match.group(3)),
            "x": int(match.group(4)),
            "y": int(match.group(5)),
            "name": match.group(6),
        })
    
    return monitors


def suggest_mapping(monitors):
    """Order monitors by X position → left/center/right."""
    if len(monitors) < 3:
        return None
    
    ordered = sorted(monitors, key=lambda m: (m["x"], m["y"]))
    return {
        "left": ordered[0],
        "center": ordered[1],
        "right": ordered[2],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate config.json from scene.json and xrandr."
    )
    parser.add_argument(
        "--scene",
        default="scene.json",
        help="Path to scene.json (default: ./scene.json)",
    )
    args = parser.parse_args()
    
    if not os.path.exists(args.scene):
        print(f"Error: {args.scene} not found", file=sys.stderr)
        sys.exit(1)
    
    scene = load_scene(args.scene)
    monitor_objects = find_monitor_objects(scene)
    
    if len(monitor_objects) != 3:
        print("Error: Could not find left/center/right monitor objects in scene.json", file=sys.stderr)
        print(f"Found: {monitor_objects}", file=sys.stderr)
        sys.exit(1)
    
    # Run xrandr
    xrandr = shutil.which("xrandr")
    if not xrandr:
        print("Error: xrandr not found in PATH", file=sys.stderr)
        sys.exit(1)
    
    result = subprocess.run([xrandr, "--listmonitors"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: xrandr --listmonitors failed", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    
    monitors = parse_xrandr_monitors(result.stdout)
    if len(monitors) < 3:
        print(f"Error: Expected at least 3 monitors, found {len(monitors)}", file=sys.stderr)
        sys.exit(1)
    
    mapping = suggest_mapping(monitors)
    if not mapping:
        print("Error: Could not determine monitor layout", file=sys.stderr)
        sys.exit(1)
    
    # Build config
    outputs = {}
    for position, obj_name in monitor_objects.items():
        mon = mapping[position]
        outputs[obj_name] = {
            "width": mon["width"],
            "height": mon["height"],
            "output": f"{position}.jpg",
        }
    
    config = {
        "panorama_object": "panorama",
        "kde_apply": {
            "screens": {
                "left": mapping["left"]["index"],
                "center": mapping["center"]["index"],
                "right": mapping["right"]["index"],
            }
        },
        "outputs": outputs,
    }
    
    # Save
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    
    print("Generated config.json")
    print(f"  left  -> screen {mapping['left']['index']} ({mapping['left']['width']}x{mapping['left']['height']})")
    print(f"  center -> screen {mapping['center']['index']} ({mapping['center']['width']}x{mapping['center']['height']})")
    print(f"  right -> screen {mapping['right']['index']} ({mapping['right']['width']}x{mapping['right']['height']})")


if __name__ == "__main__":
    main()
