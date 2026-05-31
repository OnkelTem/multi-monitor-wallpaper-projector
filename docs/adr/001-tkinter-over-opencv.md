# ADR-001: tkinter for the interactive crop window

**Context:** crop.py needs a window that displays an image, handles keyboard
input, and properly processes window close events (X button, Ctrl-C).

OpenCV (cv2.imshow, cv2.waitKey) on Linux with the GTK backend does not
detect window close events — getWindowProperty and getWindowImageRect fail,
causing the loop to create a new window on every iteration.

**Decision:** Use tkinter with root.protocol("WM_DELETE_WINDOW", ...)
for proper window lifecycle management. Images are passed through
PIL.ImageTk.PhotoImage. Updates are scheduled via root.after().

**Consequences:** An additional dependency (Pillow) and a more complex
conversion pipeline (cv2 → PIL → tkinter), but stable window management.
