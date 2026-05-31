# 002 — Рефакторинг: init-config, crop, wallpaper

## Мотивация

Убрать ручное создание `config.json`, интерактивное кадрирование изображений, упрощение `wallpaper.py` с удалением `prepare_panorama_image()` и переходом на предварительно обрезанные source.jpg.

## Пайплайн

```bash
# Шаг 0 — один раз при настройке сцены: создать config.json под текущий xrandr
python init-config.py

# Шаг 1 — для каждой картинки: откадрировать под aspect панорамы
python crop.py panorama.jpg

# Шаг 2 — сгенерировать обои (читает source.jpg из директории картинки)
python wallpaper.py panorama/

# Шаг 3 — применить на KDE
python apply-kde-wallpapers.py panorama/
```

---

## 1. Новый скрипт `init-config.py`

### Назначение

Автоматически генерирует `config.json` на основе `scene.json` и текущего `xrandr`.

### Интерфейс

```
python init-config.py
python init-config.py --scene scene.json
```

- `--scene` — путь к scene.json, по умолчанию `./scene.json`

### Алгоритм

1. Загрузить `scene.json`.
2. Найти объекты мониторов: `m-left`, `m-center`, `m-right`. Если имя не совпадает — искать по ключевым словам `left`, `center`, `right`.
3. Запустить `xrandr --listmonitors`.
4. Распарсить вывод: для каждого монитора извлечь индекс, разрешение (W×H), позицию (+X+Y).
5. Отсортировать мониторы по X → назначить left (самый левый), center, right (самый правый).
6. Для каждого монитора взять его нативное разрешение как размер выхода.
7. Сохранить `config.json`:

```json
{
  "panorama_object": "panorama",
  "kde_apply": {
    "screens": {
      "left": <screen_index>,
      "center": <screen_index>,
      "right": <screen_index>
    }
  },
  "outputs": {
    "<left_object_name>": {
      "width": <xrandr_width>,
      "height": <xrandr_height>,
      "output": "left.jpg"
    },
    "<center_object_name>": {
      "width": <xrandr_width>,
      "height": <xrandr_height>,
      "output": "center.jpg"
    },
    "<right_object_name>": {
      "width": <xrandr_width>,
      "height": <xrandr_height>,
      "output": "right.jpg"
    }
  }
}
```

### Зависимости

- `json`, `os`, `sys`, `shutil`, `subprocess`, `re` — стандартная библиотека.

---

## 2. `crop.py` — scene.json по умолчанию

### Интерфейс

```bash
python crop.py image.jpg
python crop.py --scene scene.json image.jpg
```

### Изменения относительно текущей версии

- Если `--scene` не указан, искать `scene.json` в текущей рабочей директории (`os.getcwd()`). Если не нашли — ошибка.
- Всё остальное без изменений.

---

## 3. `wallpaper.py` — рефакторинг

### Интерфейс

```bash
python wallpaper.py project_dir/
python wallpaper.py --scene scene.json --config config.json project_dir/
```

### Изменения

**Аргументы командной строки:**
- Первый аргумент — путь к директории проекта (например `panorama/`)
- `--scene` — путь к scene.json, по умолчанию `./scene.json`
- `--config` — путь к config.json, по умолчанию `./config.json`

Запуск: `main(sys.argv[1])` (принимает только project_dir, scene и config читает сам).

**Удалить функцию `prepare_panorama_image()` целиком.**

**В `main()`:**
- Загрузить `scene.json` из `--scene`
- Загрузить `config.json` из `--config`
- Читать image не из аргумента, а из `{project_dir}/source.jpg`
- Если `source.jpg` не найден — ошибка
- Вычислить aspect ratio panorama quad
- Вычислить aspect ratio `source.jpg` (через `img.shape`)
- Если `abs(aspect_img - aspect_pano) / aspect_pano > 0.01` (отклонение более 1%) — выйти с ошибкой, напечатав оба aspect ratio
- Далее — как сейчас: render_monitor для каждого монитора

**В `get_output_path()`:**
- Оставить `output_dir = source_name` (source_name = имя директории проекта = `os.path.basename(project_dir.rstrip("/\\"))`)
- `os.makedirs(output_dir, exist_ok=True)` остаётся
- return `os.path.join(output_dir, output_name)`

---

## 4. `apply-kde-wallpapers.py` — убрать subcommands

После удаления `discover` остаётся только `apply`, так что subparser не нужен. CLI упрощается:

```bash
python apply-kde-wallpapers.py [--config config.json] [--dry-run] <directory>
```

**Удалить:**
- Функцию `build_parser()` (заменить на прямой `argparse`)
- Подпарсеры `discover` и `apply`
- Функцию `discover()`
- Функцию `parse_xrandr_monitors()`
- Функцию `suggest_mapping_from_monitors()`
- Импорт `re` (больше не используется)

**Изменить `main()`:**
- Вместо `args = parser.parse_args(argv)` → прямое чтение `--config`, `--dry-run` и позиционного аргумента `directory`
- Убрать `args.command` — скрипт всегда делает apply
- Вызывать `apply_wallpapers(args.directory, args.config, args.dry_run)` напрямую

**Оставить без изменений:**
- `apply_wallpapers()`
- `build_wallpaper_script()`
- `run_command()`
- `resolve_qdbus_command()`
- `get_image_paths()`
- `get_screen_mapping()`
- `load_config()`

**Новый CLI:**
```
usage: apply-kde-wallpapers.py [-h] [--config CONFIG] [--dry-run] directory

Apply left.jpg, center.jpg, right.jpg from a generated directory to KDE Plasma screens.

positional arguments:
  directory        Directory containing left.jpg, center.jpg, right.jpg

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to config.json with KDE screen mapping (default: ./config.json)
  --dry-run        Print the planned KDE assignments without changing the desktop
```

---

## 5. Файловая структура

```
текущая_директория/
├── scene.json              # геометрия сцены (экспорт из Blender)
├── config.json             # конфиг (генерируется init-config.py)
├── init-config.py          # новый скрипт
├── crop.py                 # кадрирователь
├── wallpaper.py            # генератор обоев
├── apply-kde-wallpapers.py # применение на KDE
├── panorama.jpg            # исходная картинка (пример)
└── panorama/               # рабочая директория картинки
    ├── crop.json
    ├── source.jpg
    ├── left.jpg
    ├── center.jpg
    └── right.jpg
```

## Файлы для создания
- `init-config.py`

## Файлы для модификации
- `crop.py` — добавить `--scene` с дефолтом
- `wallpaper.py` — удалить prepare_panorama_image, переделать аргументы, проверять aspect ratio
- `apply-kde-wallpapers.py` — удалить discover, убрать subparser, прямой CLI

## Файлы для удаления
- ничего не удаляем, старые файлы остаются

## Зависимости
- `opencv-python` (cv2) — crop.py, wallpaper.py
- `numpy` — crop.py, wallpaper.py
- Всё остальное — стандартная библиотека
