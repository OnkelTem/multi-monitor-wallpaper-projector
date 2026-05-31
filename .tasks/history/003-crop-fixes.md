# 003 — Уточнения crop.py: блокировка осей, масштаб окна, параметр --dir

## Изменения

### 1. Блокировка осей перемещения

**Проблема:** При начальной установке рамки:

- Если `img_aspect < pano_aspect` → рамка на 100% ширины (`crop_w == img_w`). Двигаться можно только вверх/вниз.
- Если `img_aspect > pano_aspect` → рамка на 100% высоты (`crop_h == img_h`). Двигаться можно только влево/вправо.
- Если `img_aspect == pano_aspect` (с допуском) → рамка на весь экран, движений нет.

Сейчас все 4 направления активны всегда.

**Решение:** Перед циклом обработки клавиш вычислить флаги блокировки:

```python
# Оси перемещения
move_h = (crop_w < img_w)  # можно двигать влево-вправо
move_v = (crop_h < img_h)  # можно двигать вверх-вниз
```

В обработчиках клавиш проверять эти флаги:

```python
elif (key == 81 or key == 97 or key == ord('a')) and move_h:
    crop_x = max(0, crop_x - step)
elif (key == 83 or key == 100 or key == ord('d')) and move_h:
    crop_x = min(img_w - crop_w, crop_x + step)
elif (key == 82 or key == 119 or key == ord('w')) and move_v:
    crop_y = max(0, crop_y - step)
elif (key == 84 or key == 115 or key == ord('s')) and move_v:
    crop_y = min(img_h - crop_h, crop_y + step)
```

То же самое для блока `elif key == 0` со стрелками.

При изменении размера рамки (`+`, `-`, `r`) флаги `move_h`/`move_v` пересчитываются (но вообще после zoom рамка уже не прижата к краю, так что можно и не пересчитывать — пусть остаются от начального соотношения сторон; это проще).

---

### 2. Масштабирование окна OpenCV

**Проблема:** Изображение открывается в 100% масштабе. Для больших картинок (например 8000×2700) окно не влезает в монитор. Кнопки зума в тулбаре OpenCV не работают на Linux.

**Решение:** Автоматическое масштабирование отображения.

Алгоритм:
1. Вычислить максимальный размер для отображения:
   - `MAX_DISPLAY_W = 1920` (можно поставить из cv2, но проще захардкодить)
   - `MAX_DISPLAY_H = 1080`

2. Вычислить `display_scale`:
   ```python
   display_scale = min(
       1.0,
       MAX_DISPLAY_W / img_w,
       MAX_DISPLAY_H / img_h,
   )
   ```

3. В цикле отрисовки:
   - Масштабировать изображение: `display = cv2.resize(img, None, fx=display_scale, fy=display_scale, interpolation=cv2.INTER_AREA)`
   - Масштабировать координаты рамки:
     ```python
     dx, dy = int(crop_x * display_scale), int(crop_y * display_scale)
     dw, dh = int(crop_w * display_scale), int(crop_h * display_scale)
     cv2.rectangle(display, (dx, dy), (dx + dw, dy + dh), ...)
     ```
   - Весь оверлей (затемнение) тоже рисуется на масштабированном изображении

4. Создать окно с `cv2.WINDOW_NORMAL` и установить размер:
   ```python
   cv2.namedWindow("Crop", cv2.WINDOW_NORMAL)
   cv2.resizeWindow("Crop", int(img_w * display_scale), int(img_h * display_scale))
   ```

---

### 3. Параметр `--dir`

**Проблема:** Имя рабочей директории всегда берётся из имени файла. Хочется иметь возможность задать его явно.

**Решение:** Добавить аргумент `--dir`:

```python
parser.add_argument(
    "--dir",
    default=None,
    help="Output directory name (default: image filename without extension)",
)
```

При сохранении:

```python
if args.dir:
    output_dir = args.dir
else:
    output_dir = os.path.splitext(os.path.basename(args.image))[0]
```

---

## Полный diff изменений в crop.py

### А. Добавить `--dir` в argparse (после `--scene`)

```python
parser.add_argument(
    "--dir",
    default=None,
    help="Output directory name (default: image filename without extension)",
)
```

### Б. После вычисления начальной рамки добавить флаги блокировки

После строк 83-84 (`crop_x`, `crop_y`):

```python
# Оси перемещения
move_h = (crop_w < img_w)
move_v = (crop_h < img_h)
```

### В. В `cv2.namedWindow` и `cv2.imshow` — добавить масштабирование

Перед циклом `while True`:

```python
MAX_DISPLAY_W = 1920
MAX_DISPLAY_H = 1080
display_scale = min(1.0, MAX_DISPLAY_W / img_w, MAX_DISPLAY_H / img_h)
cv2.namedWindow("Crop", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Crop", int(img_w * display_scale), int(img_h * display_scale))
```

В начале цикла:

```python
# Масштабированное отображение
display = cv2.resize(img, None, fx=display_scale, fy=display_scale, interpolation=cv2.INTER_AREA)
overlay = display.copy()
dx, dy = int(crop_x * display_scale), int(crop_y * display_scale)
dw, dh = int(crop_w * display_scale), int(crop_h * display_scale)
cv2.rectangle(overlay, (dx, dy), (dx + dw, dy + dh), (0, 0, 0), -1)
display = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
cv2.rectangle(display, (dx, dy), (dx + dw, dy + dh), (0, 255, 0), 2)
cv2.imshow("Crop", display)
```

### Г. В обработчиках клавиш — добавить проверку `move_h`/`move_v`

```python
elif (key == 82 or key == 119 or key == ord('w')) and move_v:
    ...
elif (key == 84 or key == 115 or key == ord('s')) and move_v:
    ...
elif (key == 81 or key == 97 or key == ord('a')) and move_h:
    ...
elif (key == 83 or key == 100 or key == ord('d')) and move_h:
    ...
```

То же для блока стрелок `elif key == 0`.

### Д. В `r` (reset) — пересчитать флаги

После пересчёта crop_x, crop_y, crop_w, crop_h при `r`:

```python
move_h = (crop_w < img_w)
move_v = (crop_h < img_h)
```

### Е. В сохранении — использовать `--dir`

Заменить строки 148-149:

```python
image_name = os.path.splitext(os.path.basename(args.image))[0]
output_dir = image_name
```

На:

```python
if args.dir:
    output_dir = args.dir
else:
    output_dir = os.path.splitext(os.path.basename(args.image))[0]
```

---

## Файлы для модификации
- `crop.py`

## Файлы для создания
- нет

## Тестирование
- `python3 -c "import ast; ast.parse(open('crop.py').read())"` — синтаксис
- визуально проверить работу клавиш и масштабирование окна
