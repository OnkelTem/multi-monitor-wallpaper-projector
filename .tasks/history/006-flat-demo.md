# 006 — wallpaper.py: `--flat` mode without projection

## Описание

Добавить в `wallpaper.py` флаг `--flat`, при котором генерация обоев
делается без перспективной проекции — прямой crop панорамы под aspect
ratio каждого монитора.

Нужно для демонстрации: сфотографировать мониторы с проекцией и без,
чтобы показать разницу.

## Файл

`wallpaper.py`

## Изменения

### 1. Новый аргумент `--flat`

```python
parser.add_argument(
    "--flat",
    action="store_true",
    help="Generate flat crops without 3D projection",
)
```

### 2. Новая функция `render_monitor_flat()`

```python
def render_monitor_flat(panorama_img, dst_size, position):
    """
    Direct crop of panorama to target aspect ratio, no projection.
    position: 'left', 'center', 'right' — determines horizontal offset.
    """
    width, height = dst_size
    target_aspect = width / height
    pano_h, pano_w = panorama_img.shape[:2]

    # Crop to target aspect ratio
    if pano_w / pano_h > target_aspect:
        crop_h = pano_h
        crop_w = int(crop_h * target_aspect)
    else:
        crop_w = pano_w
        crop_h = int(crop_w / target_aspect)

    # Horizontal position
    if position == 'left':
        x = 0
    elif position == 'right':
        x = pano_w - crop_w
    else:  # 'center' / default
        x = (pano_w - crop_w) // 2

    y = (pano_h - crop_h) // 2
    cropped = panorama_img[y:y + crop_h, x:x + crop_w]
    return cv2.resize(cropped, (width, height), interpolation=cv2.INTER_LANCZOS4)
```

### 3. Определение позиции монитора

В `config["outputs"]` ключи: `m-left`, `m-center`, `m-right`.
Извлечение позиции из имени объекта:

```python
def get_monitor_position(obj_name):
    name_lower = obj_name.lower()
    if "left" in name_lower:
        return "left"
    elif "right" in name_lower:
        return "right"
    else:
        return "center"
```

### 4. Ветвление в цикле рендера

```python
for obj_name, out_cfg in config["outputs"].items():
    if args.flat:
        position = get_monitor_position(obj_name)
        result = render_monitor_flat(img, (out_cfg["width"], out_cfg["height"]), position)
    else:
        monitor_quad = vertices_to_quad(objects[obj_name]["vertices"])
        result = render_monitor(img, pano_quad, monitor_quad, camera_pos,
                                (out_cfg["width"], out_cfg["height"]))

    output_path = get_output_path(args.project_dir, out_cfg["output"])
    cv2.imwrite(output_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print("Saved:", output_path)
```

### 5. Имена выходных файлов

Без суффикса — те же `left.jpg`, `center.jpg`, `right.jpg`.
Отдельный запуск: `wallpaper.py --flat dir/` перезаписывает flat-версии.

## Пример использования

```bash
# Нормальная проекция
python wallpaper.py wallpapers/panorama/

# Flat (без проекции) — для демонстрации
python wallpaper.py --flat wallpapers/panorama/
```

## Проверка

1. Запустить `python wallpaper.py --flat wallpapers/panorama/`
2. Проверить, что `left.jpg` — левая треть панорамы, правильный aspect
3. Проверить, что `center.jpg` — центр панорамы
4. Проверить, что `right.jpg` — правая треть панорамы
5. Сравнить с обычным запуском (без `--flat`) — должна быть видна разница
   в перспективе
