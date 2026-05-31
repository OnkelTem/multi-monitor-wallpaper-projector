import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


IMAGE_NAMES = ("left", "center", "right")
DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def get_screen_mapping(config):
    kde_apply = config.get("kde_apply")
    if not isinstance(kde_apply, dict):
        raise ValueError("Missing 'kde_apply' section in config.json")

    screens = kde_apply.get("screens")
    if not isinstance(screens, dict):
        raise ValueError("Missing 'kde_apply.screens' section in config.json")

    mapping = {}
    for image_name in IMAGE_NAMES:
        if image_name not in screens:
            raise ValueError(f"Missing KDE screen mapping for '{image_name}'")

        try:
            mapping[image_name] = int(screens[image_name])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid KDE screen index for '{image_name}'") from exc

    return mapping


def get_image_paths(directory_path):
    base_dir = Path(directory_path).expanduser().resolve()
    if not base_dir.is_dir():
        raise ValueError(f"Image directory does not exist: {base_dir}")

    image_paths = {}
    missing = []
    for image_name in IMAGE_NAMES:
        image_path = base_dir / f"{image_name}.jpg"
        if image_path.is_file():
            image_paths[image_name] = image_path
        else:
            missing.append(str(image_path))

    if missing:
        raise ValueError("Missing required image files:\n- " + "\n- ".join(missing))

    return image_paths


def resolve_qdbus_command():
    for command_name in ("qdbus", "qdbus6"):
        resolved = shutil.which(command_name)
        if resolved:
            return resolved

    raise RuntimeError("Neither qdbus nor qdbus6 is available in PATH")


def run_command(command):
    return subprocess.run(command, capture_output=True, text=True, check=False)


def build_wallpaper_script(screen_index, image_path):
    image_uri = image_path.resolve().as_uri()

    return (
        "(function() {"
        f"var d = desktopForScreen({screen_index});"
        "if (!d) { return 'missing-desktop'; }"
        "d.wallpaperPlugin = 'org.kde.image';"
        "d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];"
        f"d.writeConfig('Image', {json.dumps(image_uri)});"
        "return 'ok';"
        "})()"
    )


def apply_wallpapers(directory_path, config_path, dry_run):
    config = load_config(config_path)
    mapping = get_screen_mapping(config)
    image_paths = get_image_paths(directory_path)
    qdbus_command = resolve_qdbus_command()

    assignments = [(image_name, mapping[image_name], image_paths[image_name]) for image_name in IMAGE_NAMES]

    if dry_run:
        print("Dry run: KDE wallpaper assignments")
        for image_name, screen_index, image_path in assignments:
            print(f"  {image_name}.jpg -> screen {screen_index}: {image_path}")
        return 0

    for image_name, screen_index, image_path in assignments:
        script = build_wallpaper_script(screen_index, image_path)
        command = [
            qdbus_command,
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
            script,
        ]
        result = run_command(command)
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            raise RuntimeError(
                f"Failed to set {image_name}.jpg on screen {screen_index}: {details or 'unknown qdbus error'}"
            )

        response = (result.stdout or "").strip().strip('"')
        if response and response != "ok":
            raise RuntimeError(
                f"Failed to set {image_name}.jpg on screen {screen_index}: PlasmaShell returned {response}"
            )

        print(f"Applied {image_name}.jpg to screen {screen_index}")

    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Apply generated left/center/right wallpapers to KDE Plasma monitors.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to config.json with KDE screen mapping.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned KDE assignments without changing the desktop.",
    )
    parser.add_argument(
        "directory",
        help="Directory containing left.jpg, center.jpg, and right.jpg.",
    )

    args = parser.parse_args(argv)

    try:
        return apply_wallpapers(args.directory, args.config, args.dry_run)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
