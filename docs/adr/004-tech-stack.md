# ADR-004: Technology stack

**Context:** The pipeline needs: image read/write, geometric transformations
(perspective, remap), GUI display, and pixel array manipulation.

**Decision:**
- OpenCV (cv2) — core image I/O, resize, warpPerspective, remap
- NumPy — pixel arrays, math
- Pillow (PIL) — bridge between OpenCV (numpy array) and tkinter (PhotoImage)
- tkinter — GUI for crop.py (see ADR-001)

**Consequences:** Three dependencies instead of one (e.g. Pillow alone),
but OpenCV provides better performance for geometric transformations,
and Pillow is the only reliable way to pass images to tkinter.
