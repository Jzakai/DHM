from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
import numpy as np
from package.backend.sys_functions import run_phase_difference, compute_2d_thickness, compute_3d_thickness

import cv2
import io
from PIL import Image
import json

app = FastAPI()

def read_imagefile(file) -> np.ndarray:
    image = Image.open(io.BytesIO(file))
    return np.array(image.convert("L"))

from fastapi import FastAPI
from pydantic import BaseModel
from sys_functions import run_phase_difference_backend

app = FastAPI()

class PhaseParams(BaseModel):
    wavelength: float
    pixel_size: float
    magnification: float
    delta_ri: float
    dc_remove: int
    filter_type: str
    filter_size: int
    beam_type: str
    threshold_strength: float

@app.post("/run_phase_difference")
async def run_phase_difference(params: PhaseParams):
    # Assuming images have already been sent via SCP and saved at fixed paths
    image_path = "server_storage/image.bmp"
    reference_path = "server_storage/reference.bmp"

    phase_result = run_phase_difference_backend(image_path, reference_path, params.dict())
    
    # Convert numpy array to list (for JSON transport)
    return {"phase_map": phase_result.tolist()}

@app.post("/compute_2d_thickness")
async def thickness_2d(image: UploadFile = Form(...)):
    img = read_imagefile(await image.read())
    result = compute_2d_thickness(img)
    return JSONResponse(content={"thickness_2d": result.tolist()})

@app.post("/compute_3d_thickness")
async def thickness_3d(image: UploadFile = Form(...)):
    img = read_imagefile(await image.read())
    X, Y, Z = compute_3d_thickness(img)
    return JSONResponse(content={
        "X": X.tolist(),
        "Y": Y.tolist(),
        "Z": Z.tolist()
    })
