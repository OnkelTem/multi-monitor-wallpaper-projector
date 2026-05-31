# 004 — Переход crop.py на tkinter вместо OpenCV окна

## Мотивация

OpenCV-окно (`cv2.imshow`) на Linux с GTK-бэкендом не умеет детектить закрытие окна (крестик). `getWindowProperty`, `getWindowImageRect` и другие методы не срабатывают — окно визуально закрывается, но `cv2.waitKey()` продолжает возвращать `-1`, и на следующей итерации цикла создаётся новое окно. Ctrl-C тоже не прерывает процесс.

**Решение:** заменить `cv2.imshow`/`cv2.waitKey` на полноценное окно tkinter.

## Что меняется

tkinter встроен в Python (никаких новых зависимостей), корректно обрабатывает:
- Закрытие окна (через `protocol("WM_DELETE_WINDOW")`)
- Клавиатуру (через `bind("<Key>")`)
- Ctrl-C (между тиками `after()`)

## Алгоритм нового цикла отрисовки

1. Загрузить изображение через OpenCV (`cv2.imread`) как сейчас — BGR numpy array.
2. Конвертировать BGR → RGB (`cv2.cvtColor(img, cv2.COLOR_BGR2RGB)`).
3. Для каждого кадра:
   - Скопировать RGB-массив
   - Нарисовать зелёную рамку и затемнение средствами PIL/Pillow (или numpy + cv2, затем конвертировать)
   - Конвертировать в `PIL.Image` → `PIL.ImageTk.PhotoImage`
   - Показать через `tk.Label.configure(image=...)`
4. Клавиатура: `root.bind("<Key>", on_key)`.
5. Закрытие: `root.protocol("WM_DELETE_WINDOW", on_close)` → установить флаг выхода.
6. Таймер: `root.after(30, update)` вместо `cv2.waitKey(30)`.
7. При Enter — сохранить, закрыть окно.
8. При Esc — закрыть без сохранения.
9. При крестике — закрыть без сохранения.

## Детали реализации

### Импорты (добавить в начало)

```python
import tkinter as tk
from PIL import Image, ImageTk
```

PIL уже установлен в проекте (`.venv`).

### Конвертация изображения

После `cv2.imread`:

```python
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
pil_base = Image.fromarray(img_rgb)
```

Каждый кадр: копируем `pil_base`, рисуем на копии прямоугольник через `PIL.ImageDraw`.

Или быстрее: рисуем на numpy-массиве через OpenCV (как сейчас с `display` и `overlay`), потом конвертируем:

```python
display_rgb = cv2.cvtColor(display_bgr, cv2.COLOR_BGR2RGB)
pil_display = Image.fromarray(display_rgb)
tk_img = ImageTk.PhotoImage(pil_display)
```

### Масштабирование

Оставляем `display_scale` как сейчас — масштабируем изображение через OpenCV или PIL перед конвертацией.

### Главный цикл

```python
def update():
    if exit_flag:
        return
    
    # Создаём display с рамкой на numpy
    display = img.copy()
    overlay = display.copy()
    dx, dy = int(crop_x * display_scale), int(crop_y * display_scale)
    dw, dh = int(crop_w * display_scale), int(crop_h * display_scale)
    cv2.rectangle(overlay, (dx, dy), (dx + dw, dy + dh), (0, 0, 0), -1)
    display = cv2.addWeighted(display, 0.7, overlay, 0.3, 0)
    cv2.rectangle(display, (dx, dy), (dx + dw, dy + dh), (0, 255, 0), 2)
    
    # Конвертируем в tkinter
    display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(display_rgb)
    tk_img = ImageTk.PhotoImage(pil_img)
    label.config(image=tk_img)
    label.image = tk_img  # держим ссылку
    
    root.after(30, update)
```

### Обработка клавиш

```python
def on_key(event):
    nonlocal crop_x, crop_y, crop_w, crop_h, move_h, move_v
    
    if event.keysym == "Escape":
        root.destroy()
        sys.exit(0)
    elif event.keysym == "Return":
        root.destroy()
        # ... сохранение ...
    elif event.keysym in ("w", "W", "Up") and move_v:
        crop_y = max(0, crop_y - step)
    elif event.keysym in ("s", "S", "Down") and move_v:
        crop_y = min(img_h - crop_h, crop_y + step)
    elif event.keysym in ("a", "A", "Left") and move_h:
        crop_x = max(0, crop_x - step)
    elif event.keysym in ("d", "D", "Right") and move_h:
        crop_x = min(img_w - crop_w, crop_x + step)
    elif event.keysym in ("plus", "equal"):
        # zoom out
        ...
    elif event.keysym in ("minus", "underscore"):
        # zoom in
        ...
    elif event.keysym in ("r", "R"):
        # reset
        ...
```

### Закрытие окна

```python
exit_flag = False

def on_close():
    global exit_flag
    exit_flag = True
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)
```

### Запуск

```python
root = tk.Tk()
root.title("Crop")
root.geometry(f"{int(img_w * display_scale)}x{int(img_h * display_scale)}")

label = tk.Label(root)
label.pack()

root.bind("<Key>", on_key)
root.protocol("WM_DELETE_WINDOW", on_close)
root.after(30, update)
root.mainloop()
```

## Что удалить из crop.py

- `cv2.namedWindow()`, `cv2.resizeWindow()`, `cv2.imshow()`, `cv2.waitKey()` — полностью убрать
- Весь цикл `while True:` заменить на tkinter-цикл с `root.after()` и `root.mainloop()`
- `cv2.destroyAllWindows()` убрать (tkinter сам уничтожает окно)

## Что остаётся без изменений

- Вся логика расчёта `crop_x`, `crop_y`, `crop_w`, `crop_h`
- `move_h`/`move_v` блокировка осей
- `--scene`, `--dir` аргументы
- Сохранение `crop.json` и `source.jpg`
- `vertices_to_quad`, `get_quad_size`
- Загрузка `scene.json`

## Файлы для модификации
- `crop.py`

## Зависимости
- `tkinter` — встроен в Python
- `Pillow` (PIL) — уже установлен в `.venv`
- `opencv-python` (cv2) — остаётся для чтения изображения и манипуляций с numpy

## Тестирование
- `python3 -c "import ast; ast.parse(open('crop.py').read())"` — синтаксис
- Запустить `python crop.py scene.jpg test.jpg`, проверить:
  - Стрелки/WASD двигают рамку
  - +/- меняют размер
  - Enter сохраняет
  - Esc выходит
  - Крестик выходит
  - Ctrl-C прерывает
