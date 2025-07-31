#from fastapi import FastAPI
#from pydantics import BaseModel

app = FastAPI()

class system_params():
    "pixel_size_var": 2,
    "magnification_var": 40,
    "delta_ri_var": 0.4,
    "dc_remove_var": 20,
    "filter_type_var": "circle",
    "filter_size_var": 100,
    "wavelength_var": 0.65,
    "number_of_beams": "1 Beam"