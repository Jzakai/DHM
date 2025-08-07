
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
from sys_functions import get_params, get_points, run_phase_difference
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


# Calculate absolute path to frontend folder
frontend_path = os.path.join(os.path.dirname(__file__), "..", "Frontend", "src")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")


