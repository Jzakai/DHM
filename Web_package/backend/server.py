
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

app = FastAPI()

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
    # Parse images to NumPy
    image_np = read_imagefile(await image.read())
    reference_np = read_imagefile(await reference.read())

    # Set parameters
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

    print(params_dict)

    # Run computation
    phase_result = run_phase_difference(image_np, reference_np)
    print(type(phase_result))
    return {"phase_map": phase_result.tolist()}

##debug
    


from fastapi.staticfiles import StaticFiles
import os

# Calculate absolute path to frontend folder
frontend_path = os.path.join(os.path.dirname(__file__), "..", "Frontend", "src")

app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")