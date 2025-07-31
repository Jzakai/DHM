import numpy as np
from skimage.draw import disk, rectangle, line
import matplotlib
matplotlib.use('TkAgg')  # Or 'Qt5Agg' if PyQt installed
import matplotlib.pyplot as plt
from PIL import Image
from tkinter import messagebox

# Load images as grayscale arrays
img = Image.open("path_to_image")
ref = Image.open("path_to_ref")

json_dummy = {
  "pixel_size_var": 2,
  "magnification_var": 40,
  "delta_ri_var": 0.4,
  "dc_remove_var": 20,
  "filter_type_var": "circle",
  "filter_size_var": 100,
  "wavelength_var": 0.65,
  "number_of_beams": "1 Beam"
}

# system parameters dictionary
system_params = {
    "pixel_size": 0,
    "magnification": 0,
    "delta_ri": 0,
    "dc_remove": 0,
    "filter_type": "",
    "filter_size": 0,
    "wavelength": 0,
    "number_of_beams": ""
}

def get_parameters(json_dummy):
    system_params["pixel_size"] = float(json_dummy["pixel_size_var"])
    system_params["magnification"] = int(json_dummy["magnification_var"])
    system_params["delta_ri"] = float(json_dummy["delta_ri_var"])
    system_params["dc_remove"] = int(json_dummy["dc_remove_var"])
    system_params["filter_type"] = str(json_dummy["filter_type_var"])
    system_params["filter_size"] = int(json_dummy["filter_size_var"])
    system_params["wavelength"] = float(json_dummy["wavelength_var"])
    system_params["number_of_beams"] = str(json_dummy["number_of_beams"])

def FFT_calc(A):
    A = A.astype(float)
    return np.fft.fftshift(np.fft.fft2(A))

def create_mask(shape, center):
    size = system_params["filter_size"]
    kind = system_params["filter_type"]
    mask = np.zeros(shape, dtype=bool)
    if kind == 'square':
        top_left = (center[0] - size // 2, center[1] - size // 2)
        rr, cc = rectangle(start=top_left, extent=(size, size), shape=shape)
    elif kind == 'circle':
        rr, cc = disk(center, radius=size // 2, shape=shape)
    else:
        # Default fallback: no mask (all False)
        return mask
    mask[rr, cc] = True
    return mask

def Fast_Unwrap(Fx, Fy, phase1):
    X, Y = np.meshgrid(Fx, Fy)
    K = X**2 + Y**2 + np.finfo(float).eps
    K = np.fft.fftshift(K)
    estimated_psi = np.fft.ifftn(
        np.fft.fftn(
            (np.cos(phase1) * np.fft.ifftn(K * np.fft.fftn(np.sin(phase1)))) -
            (np.sin(phase1) * np.fft.ifftn(K * np.fft.fftn(np.cos(phase1))))
        ) / K
    )
    Q = np.round((np.real(estimated_psi) - phase1) / (2 * np.pi))
    return phase1 + 2 * np.pi * Q

def run_phase_difference(image_numpy_array, reference_numpy_array):
    magnification = system_params["magnification"]
    delta_ri = system_params["delta_ri"]
    dc_remove = system_params["dc_remove"]
    filter_type = system_params["filter_type"]
    filter_size = system_params["filter_size"]
    pixel_size = system_params["pixel_size"]
    lambda_ = system_params["wavelength"]

    if isinstance(image_numpy_array, np.ndarray):
        Ny, Nx = image_numpy_array.shape
        image_numpy_array_shiftft = FFT_calc(image_numpy_array)

        center_y, center_x = Ny // 2, Nx // 2
        temp = np.abs(image_numpy_array_shiftft.copy())
        temp[center_y - dc_remove:center_y + dc_remove, center_x - dc_remove:center_x + dc_remove] = 0
        max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)

        mask_bool = create_mask(image_numpy_array.shape, (max_y, max_x))
        filt_spec = image_numpy_array_shiftft * mask_bool
        cy, cx = np.array(mask_bool.shape) // 2
        shift_y = cy - max_y
        shift_x = cx - max_x
        filt_spec = np.roll(np.roll(filt_spec, shift_y, axis=0), shift_x, axis=1)
        obj_image = np.fft.ifft2(filt_spec)

        A2_shiftft = FFT_calc(reference_numpy_array)
        ref_filt_spec = A2_shiftft * mask_bool
        ref_filt_spec = np.roll(np.roll(ref_filt_spec, shift_y, axis=0), shift_x, axis=1)
        ref_image = np.fft.ifft2(ref_filt_spec)

        o1 = obj_image / ref_image
        phase1 = np.angle(o1)
        phase1[phase1 < 0] += 2 * np.pi

        Fs_x = 1 / pixel_size
        Fs_y = 1 / pixel_size
        dFx = Fs_x / Nx
        dFy = Fs_y / Ny
        Fx = np.linspace(-Fs_x / 2, Fs_x / 2 - dFx, Nx)
        Fy = np.linspace(-Fs_y / 2, Fs_y / 2 - dFy, Ny)

        unwrapped_psi = Fast_Unwrap(Fx, Fy, phase1)
        unwrapped_psi -= np.min(unwrapped_psi)
        mean = np.mean(unwrapped_psi)
        psi_inverted = 2 * mean - unwrapped_psi

        clean_psi = np.copy(unwrapped_psi)
        clean_psi[unwrapped_psi < mean] = mean

        clean_psi_inverted = np.copy(psi_inverted)
        clean_psi_inverted[psi_inverted < mean] = mean

        combined_clean = np.maximum(clean_psi, clean_psi_inverted)

        if filter_type == "1 Beam":
            unwrapped_psi = combined_clean

        return unwrapped_psi
    else:
        return f"The provided input is not a numpy array, provided:{type(image_numpy_array)}"

# Update parameters once before processing
get_parameters(json_dummy)
