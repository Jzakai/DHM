import cv2
import tkinter as tk
from tkinter import ttk
from threading import Thread
from pypylon import pylon

# --- Global Zoom Level ---
zoom_level = 1.0  # 1.0 = no zoom

# --- Setup Basler Camera ---
camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()
camera.ExposureAuto.SetValue('Off')
camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

converter = pylon.ImageFormatConverter()
converter.OutputPixelFormat = pylon.PixelType_Mono8
converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

# --- Zoom Logic ---
def apply_zoom(frame, zoom_factor):
    if zoom_factor == 1.0:
        return frame

    h, w = frame.shape[:2]
    center_x, center_y = w // 2, h // 2
    new_w, new_h = int(w / zoom_factor), int(h / zoom_factor)

    x1 = max(center_x - new_w // 2, 0)
    y1 = max(center_y - new_h // 2, 0)
    x2 = min(center_x + new_w // 2, w)
    y2 = min(center_y + new_h // 2, h)

    cropped = frame[y1:y2, x1:x2]
    resized = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    return resized

# --- Update Exposure ---
def update_exposure(val):
    try:
        val = float(val)
        camera.ExposureTime.SetValue(val)
    except Exception as e:
        print("Exposure update error:", e)

def on_exposure_enter(event):
    update_exposure(exposure_entry.get())
    exposure_slider.set(float(exposure_entry.get()))

# --- Zoom Buttons ---
def zoom_in():
    global zoom_level
    zoom_level = min(zoom_level + 0.1, 3.0)
    zoom_label.config(text=f"{zoom_level:.1f}x")

def zoom_out():
    global zoom_level
    zoom_level = max(zoom_level - 0.1, 1.0)
    zoom_label.config(text=f"{zoom_level:.1f}x")

# --- GUI Setup ---
root = tk.Tk()
root.title("Camera Controls")
root.geometry("400x160")

toolbar = tk.Frame(root)
toolbar.pack(side="top", fill="x", padx=10, pady=5)

# Exposure control
tk.Label(toolbar, text="Exposure (µs):").pack(side="left")
exposure_slider = tk.Scale(toolbar, from_=camera.ExposureTime.GetMin(), to=camera.ExposureTime.GetMax(),
                           orient=tk.HORIZONTAL, length=150, resolution=1, command=update_exposure)
exposure_slider.set(camera.ExposureTime.GetValue())
exposure_slider.pack(side="left")

exposure_entry = ttk.Entry(toolbar, width=8)
exposure_entry.insert(0, str(int(camera.ExposureTime.GetValue())))
exposure_entry.bind("<Return>", on_exposure_enter)
exposure_entry.pack(side="left", padx=5)

# Zoom buttons
zoom_out_btn = ttk.Button(toolbar, text="-", command=zoom_out)
zoom_out_btn.pack(side="left", padx=5)
zoom_in_btn = ttk.Button(toolbar, text="+", command=zoom_in)
zoom_in_btn.pack(side="left")
zoom_label = tk.Label(toolbar, text="1.0x")
zoom_label.pack(side="left", padx=5)

# --- OpenCV Camera Thread ---
def show_camera():
    cv2.namedWindow("Live Camera", cv2.WINDOW_NORMAL)
    while camera.IsGrabbing():
        grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded():
            image = converter.Convert(grab_result)
            frame = image.GetArray()
            frame = apply_zoom(frame, zoom_level)

            cv2.imshow("Live Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q') or cv2.getWindowProperty("Live Camera", cv2.WND_PROP_VISIBLE) < 1:
                break
        grab_result.Release()

    camera.StopGrabbing()
    camera.Close()
    cv2.destroyAllWindows()
    root.quit()

# --- Start Everything ---
Thread(target=show_camera, daemon=True).start()
root.mainloop()
