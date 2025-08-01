from fastapi import FastAPI, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import numpy as np
from package.backend.sys_functions import get_params,run_phase_difference, compute_2d_thickness, compute_3d_thickness

import cv2
import io
from PIL import Image
import json

app = FastAPI()

def read_imagefile(file) -> np.ndarray:
    image = Image.open(io.BytesIO(file))
    return np.array(image.convert("L"))


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

@app.post("/set_params")
async def set_params(params: PhaseParams):
    try:
        params_dict = params.model_dump()
        print("Received params:", params_dict)  # Debug log
        get_params(params_dict)
        return {"status": "ok", "received": params_dict}
    except Exception as e:
        import traceback
        print("Error in set_params:", str(e))
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.post("/run_phase_difference")
async def run_phase_difference(params: PhaseParams):
    # Assuming images have already been sent via SCP and saved at fixed paths
    image_path = "server_storage/image.bmp"
    reference_path = "server_storage/reference.bmp"

    phase_result = run_phase_difference(image_path, reference_path, params.dict())
    
    # Convert numpy array to list (for JSON transport)
    return {"phase_map": phase_result.tolist()}
    

   
    