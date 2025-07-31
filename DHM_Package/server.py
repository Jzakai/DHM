from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
import numpy as np
from backend.sys_functions import run_phase_difference, compute_2d_thickness, compute_3d_thickness

import cv2
import io
from PIL import Image
import json

app = FastAPI()

def read_imagefile(file) -> np.ndarray:
    image = Image.open(io.BytesIO(file))
    return np.array(image.convert("L"))

@app.post("/run_phase_difference")
async def phase_difference(
    params: str = Form(...),
    object_image: UploadFile = Form(...),
    reference_image: UploadFile = Form(...)
):
    try:
        # --- Parse parameters ---
        params_dict = json.loads(params)

        # --- Read Images ---
        obj_img = read_imagefile(await object_image.read())
        ref_img = read_imagefile(await reference_image.read())

        # --- Run backend function ---
        result = run_phase_difference(obj_img, ref_img)

        # Convert NumPy to list
        result_list = result.tolist()
        return JSONResponse(content={"status": "success", "phase_map": result_list})

    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)})

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
    