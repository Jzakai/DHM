
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


app = FastAPI()


# Calculate absolute path to frontend folder
frontend_path = os.path.join(os.path.dirname(__file__), "..", "Frontend", "src")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

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

import cv2
import base64

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

##debug
    


