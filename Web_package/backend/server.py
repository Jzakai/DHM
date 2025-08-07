
import cv2
import io
from PIL import Image
import json

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import numpy as np
from PIL import Image
import io
from sys_functions import get_params, run_phase_difference
from fastapi.staticfiles import StaticFiles
import os

import cv2
import base64
from pydantic import BaseModel

import plotly.graph_objs as go
import plotly.io as pio
from sys_functions import (compute_3d_thickness, get_phase_difference, reduce_noise, compute_1d_thickness)


app = FastAPI()

#globals
roi_phase = None
roi_coords = None



# Enable CORS (for frontend fetch calls)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def read_imagefile(file) -> np.ndarray:
    image = Image.open(io.BytesIO(file))
    return np.array(image.convert("L"))


@app.post("/run_phase_difference")
async def run_phase_difference_endpoint(
    wavelength: float = Form(...),
    pixel_size: float = Form(...),
    magnification: float = Form(...),
    delta_ri: float = Form(...),
    dc_remove: int = Form(...),
    filter_type: str = Form(...),
    filter_size: int = Form(...),
    beam_type: str = Form(...),
    threshold_strength: float = Form(...),
    image: UploadFile = File(...),
    reference: UploadFile = File(...)
):
    # Convert uploaded images to numpy arrays
    image_np = read_imagefile(await image.read())
    reference_np = read_imagefile(await reference.read())

    # Set parameters globally
    params_dict = {
        "wavelength": wavelength,
        "pixel_size": pixel_size,
        "magnification": magnification,
        "delta_ri": delta_ri,
        "dc_remove": dc_remove,
        "filter_type": filter_type,
        "filter_size": filter_size,
        "beam_type": beam_type,
        "threshold_strength": threshold_strength,
    }

    get_params(params_dict)
    # Run computation (numeric phase result)
    phase_result = run_phase_difference(image_np, reference_np)

    # Normalize and apply colormap
    norm_phase = cv2.normalize(phase_result, None, 0, 255, cv2.NORM_MINMAX)
    norm_phase = norm_phase.astype(np.uint8)
    colored_phase = cv2.applyColorMap(norm_phase, cv2.COLORMAP_JET)

    # Encode image as Base64
    _, buffer = cv2.imencode(".png", colored_phase)
    phase_base64 = base64.b64encode(buffer).decode("utf-8")

    return {
        "phase_image": phase_base64,
        "shape": phase_result.shape,
        "min": float(phase_result.min()),
        "max": float(phase_result.max())
    }



@app.get("/compute_3d")
async def compute_3d_endpoint():
    phase_result = roi_phase if roi_phase is not None else get_phase_difference()
    print(phase_result)
    if phase_result is None:
        return {"error": "No phase difference computed yet."}

    X, Y, Z = compute_3d_thickness(phase_result)

    return {
        "x": X.tolist(),
        "y": Y.tolist(),
        "z": Z.tolist()
    }




@app.post("/compute_1d")
async def compute_1d(data: dict):
    try:
        phase_result = roi_phase if roi_phase is not None else get_phase_difference()
        print(phase_result)
        
        x1, y1, x2, y2 = data["x1"], data["y1"], data["x2"], data["y2"]
        x_vals, thickness_vals = compute_1d_thickness(x1, y1, x2, y2, phase_result)
        return {
            "x": x_vals.tolist(),
            "y": thickness_vals.tolist()
        }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)



@app.post("/select_roi")
async def select_roi_endpoint(coords: dict):
    global roi_phase, roi_coords
    phase = get_phase_difference()
    if phase is None:
        return {"error": "No phase difference computed yet."}

    x1, y1, x2, y2 = coords["x1"], coords["y1"], coords["x2"], coords["y2"]
    roi = phase[y1:y2, x1:x2]
    roi_phase, _, _ = reduce_noise(roi)
    roi_coords = (x1, y1, x2, y2)

    # Normalize and convert to 8-bit image
    norm_roi = (roi_phase - np.min(roi_phase)) / (np.max(roi_phase) - np.min(roi_phase) + 1e-8)
    roi_uint8 = (norm_roi * 255).astype(np.uint8)

    norm_roi = cv2.normalize(roi_phase, None, 0, 255, cv2.NORM_MINMAX)
    norm_roi = norm_roi.astype(np.uint8)
    colored_roi = cv2.applyColorMap(norm_roi, cv2.COLORMAP_JET)

    _, buffer = cv2.imencode(".png", colored_roi)
    roi_base64 = base64.b64encode(buffer).decode("utf-8")

    
    return {
        "status": "ROI selected and noise reduced",
        "shape": roi_phase.shape,
        "roi_image": roi_base64
    }

from fastapi.responses import StreamingResponse
import cv2
import numpy as np
from pypylon import pylon

camera = None
converter = None

@app.get("/start_camera")
async def start_camera():
    global camera, converter
    try:
        camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
        camera.Open()
        camera.ExposureAuto.SetValue('Off')
        camera.ExposureTime.SetValue(150.0)
        camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)

        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_Mono8
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        return {"status": "Camera started"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/camera_feed")
def video_feed():
    def generate():
        while camera and camera.IsGrabbing():
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
            if grab_result.GrabSucceeded():
                image = converter.Convert(grab_result)
                frame = image.GetArray()
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    continue
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            grab_result.Release()

    return StreamingResponse(generate(), media_type='multipart/x-mixed-replace; boundary=frame')


@app.post("/set_exposure")
def set_exposure(exposure: dict):
    global camera
    try:
        value = exposure["exposure"]
        if camera and camera.IsOpen():
            camera.ExposureTime.SetValue(float(value))
            return {"success": True}
        else:
            return {"error": "Camera not open"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/capture_image")
def capture_image(data: dict):
    global camera, converter, last_frame, reference, image_np
    try:
        if not camera.IsGrabbing():
            return {"error": "Camera not running"}
        grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded():
            img = converter.Convert(grab_result)
            frame = img.GetArray()
            last_frame = frame
            if data["type"] == "reference":
                reference = frame
            elif data["type"] == "object":
                image_np = frame
            else:
                return {"error": "Invalid type"}
            return {"success": True}
        else:
            return {"error": "Failed to grab image"}
    except Exception as e:
        return {"error": str(e)}

# Calculate absolute path to frontend folder
frontend_path = os.path.join(os.path.dirname(__file__), "..", "Frontend", "src")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


