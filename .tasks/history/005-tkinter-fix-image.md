# 005 — Crop: tkinter-окно обрезает картинку по высоте

## Описание
Интерактивное окно `crop.py` показывает только верхнюю часть
изображения (небо). Нижняя часть обрезана из-за того, что
`root.geometry(f"{disp_w}x{disp_h}")` задаёт внешний размер окна,
а клиентская область меньше на высоту заголовка (~30-40px).

## История исправлений

### Итерация 1 — Geometry
Удалён `root.geometry()` и `root.resizable(False, False)`,
добавлено центрирование окна через `root.geometry(f"+{x}+{y}")`.

### Итерация 2 — Resize в update()
Добавлен `pil_img.resize()` перед передачей в tkinter, иначе окно
растягивалось на три монитора под full-res изображение.

### Итерация 3 — Resize до рисования прямоугольника
Double-scaling: прямоугольник рисовался в display-координатах на
full-res кадре, затем кадр ресайзился. Решение: `cv2.resize()` ДО
рисования, PIL resize удалён.

### Итерация 4 — Crop persistence
Положение crop сохраняется в `crop.json` между запусками.
При старте скрипт ищет `crop.json` в выходной директории
и загружает координаты, если они валидны.

### Итерация 5 — label.pack() после установки изображения (текущая)

**Проблема:** `label.pack()` вызывался на пустой `Label` (без
изображения). Окно фиксировало размер 1×1. Когда `update()`
позже устанавливал изображение через `label.config(image=...)`,
окно не расширялось — tkinter уже «закоммитил» геометрию.

**Решение:** Вызывать `label.pack()` и `label.focus_set()` **после**
первого вызова `update()`, когда изображение уже установлено.

## Файл
`crop.py`

## Изменения (итерация 5)

### Перенести label.pack() после первого update()

**Было:**
```python
    label = tk.Label(root)
    label.pack()
    label.focus_set()

    centered = False

    def update():
        nonlocal centered
        if exit_flag:
            return
        display = cv2.resize(img, (disp_w, disp_h), ...)
        ...
        label.config(image=tk_img)
        label.image = tk_img
        if not centered:
            centered = True
            x = (root.winfo_screenwidth() - disp_w) // 2
            y = (root.winfo_screenheight() - disp_h) // 2
            root.geometry(f"+{x}+{y}")
        root.after(30, update)

    update()
    root.after(30, update)
    root.mainloop()
```

**Стало:**
```python
    label = tk.Label(root)

    centered = False

    def update():
        nonlocal centered
        if exit_flag:
            return
        display = cv2.resize(img, (disp_w, disp_h), ...)
        ...
        label.config(image=tk_img)
        label.image = tk_img
        if not centered:
            centered = True
            x = (root.winfo_screenwidth() - disp_w) // 2
            y = (root.winfo_screenheight() - disp_h) // 2
            root.geometry(f"+{x}+{y}")
        root.after(30, update)

    update()
    label.pack()
    label.focus_set()
    root.mainloop()
```

### Убрать дублирующийся root.after(30, update) снаружи
(уже сделано — в текущем коде его нет, только внутри update)

## Проверка
1. Запустить `python crop.py panorama.jpg` — окно нормального размера
2. Для 25000×3848: disp_w=1919, disp_h≈295 — не полоска
3. Стрелки/WASD, +/-, Enter/Esc, крестик, Ctrl-C
4. Enter → crop.json + source.jpg
5. Повторный запуск → crop из crop.json

### Итерация 6 (cleanup) — центрирование и финальная отладка

- Раскомментирован блок `if not centered:` в `update()` — центрирование работает
- Порядок: `update()` (установить изображение) → `label.pack()` → `label.focus_set()` → `mainloop()`
- Centered флаг предотвращает повторное центрирование на каждом кадре
- Убран дублирующийся `root.after(30, update)` (только внутри `update()`)

## Текущее состояние

- Окно открывается с правильным размером (display_scale по aspect ratio)
- Центрируется на экране
- Crop rectangle рисуется корректно (resize ДО overlay)
- Crop позиция сохраняется в crop.json между запусками
- WASD/стрелки, +/-, Enter/Esc, крестик, Ctrl-C — работают
