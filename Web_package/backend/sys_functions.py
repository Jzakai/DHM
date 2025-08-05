import numpy as np
from skimage.draw import disk, rectangle
import os
import numpy as np
import matplotlib
matplotlib.use('TkAgg')  # or 'Qt5Agg' if you have PyQt installed
import matplotlib.pyplot as plt
from skimage.draw import disk, rectangle
from tkinter import Tk, filedialog, Label, Entry, Button, StringVar, OptionMenu
from PIL import Image
import tkinter as tk
from matplotlib.widgets import RectangleSelector
from skimage.draw import line
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pypylon import pylon
import cv2

# Global config variables (initialized with None or default values)
_pixel_size_var = 2
_magnification_var = 40
_delta_ri_var = 0.4
_dc_remove_var = 20
_filter_type_var = 'circle'
_filter_size_var = 100
_wavelength_var = 0.65  # Added wavelength variable
_beam_type_var = '1 beam'
_threshold_var = 1.0

# Setters
def set_pixel_size_var(value):
    global _pixel_size_var
    _pixel_size_var = value

def set_magnification_var(value):
    global _magnification_var
    _magnification_var = value

def set_delta_ri_var(value):
    global _delta_ri_var
    _delta_ri_var = value

def set_dc_remove_var(value):
    global _dc_remove_var
    _dc_remove_var = value

def set_filter_type_var(value):
    global _filter_type_var
    _filter_type_var = value

def set_filter_size_var(value):
    global _filter_size_var
    _filter_size_var = value


def set_wavelength_var(value):
    global _wavelength_var
    _wavelength_var = value

def set_beam_type_var(value):
    global _beam_type_var
    _beam_type_var = value

def set_threshold_var(value):
    global _threshold_var
    _threshold_var = value

# Getters
def get_pixel_size_var():
    return _pixel_size_var

def get_magnification_var():
    return _magnification_var

def get_delta_ri_var():
    return _delta_ri_var

def get_dc_remove_var():
    return _dc_remove_var

def get_filter_type_var():
    return _filter_type_var

def get_filter_size_var():
    return _filter_size_var

def get_wavelength_var():
    return _wavelength_var

def get_beam_type_var():
    return _beam_type_var

def get_threshold_var():
    return _threshold_var


def FFT_calc(A):
    A = A.astype(float)
    return np.fft.fftshift(np.fft.fft2(A))


def create_mask(imageArray, max_coords):
    Ny, Nx = imageArray.shape
    max_y, max_x = max_coords
    center = (max_y, max_x)
    kind = get_filter_type_var()
    filter_size = get_filter_size_var()

    mask = np.zeros((Ny, Nx), dtype=bool)
    if kind == 'square':
        top_left = (center[0] - filter_size // 2, center[1] - filter_size // 2)
        rr, cc = rectangle(start=top_left, extent=(filter_size, filter_size), shape=(Ny, Nx))
    elif kind == 'circle':
        rr, cc = disk(center, radius=filter_size // 2, shape=(Ny, Nx))
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


def check_spectrum(imageArray):
    dc_remove = get_dc_remove_var()
    filter_type = get_filter_type_var()
    filter_size = get_filter_size_var()

    if isinstance(imageArray, np.ndarray):
        Ny, Nx = imageArray.shape
        imageArray_shiftft = FFT_calc(imageArray)

        center_y, center_x = Ny // 2, Nx // 2
        temp = np.abs(imageArray_shiftft.copy())
        dc_out = int(dc_remove)

        temp[center_y - dc_out:center_y + dc_out, center_x - dc_out:center_x + dc_out] = 0
        max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)

        mask_bool = create_mask(imageArray, (max_y, max_x))
        spectrum_global = np.log(1 + np.abs(imageArray_shiftft))
        return imageArray_shiftft, mask_bool, max_y, max_x


#make it take 3 params, image & red & params(json file)
#make run phase difference use local vars of params,
#make a helper function to split the json string, converty types, and save to variables

import json

##can be deleted
def get_params(params:dict):
    # Extract and convert values
    set_wavelength_var(float(params.get("wavelength", 0.65)))
    set_pixel_size_var(float(params.get("pixel_size", 1.0)))
    set_magnification_var(float(params.get("magnification", 10)))
    set_delta_ri_var(float(params.get("delta_ri", 1)))
    set_dc_remove_var (int(params.get("dc_remove", 20)))
    set_filter_type_var (params.get("filter_type", "circle"))
    set_filter_size_var(int(params.get("filter_size", 101)))
    set_beam_type_var (params.get("beam_type", "1 Beam"))
    set_threshold_var (float(params.get("threshold_strength", 1.0)))

def run_phase_difference(imageArray,reference):
    """
    Compute unwrapped phase difference between object image and reference.
    Returns:
    np.ndarray
        Unwrapped phase map.
    """

    Ny, Nx = imageArray.shape
    A1_shiftft = FFT_calc(imageArray)

    center_y, center_x = Ny // 2, Nx // 2
    temp = np.abs(A1_shiftft.copy())
    temp[center_y - get_dc_remove_var():center_y + get_dc_remove_var(), center_x - get_dc_remove_var():center_x + get_dc_remove_var()] = 0
    max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)
    mask_bool = create_mask((imageArray), (max_y, max_x))

    filt_spec = A1_shiftft * mask_bool
    cy, cx = np.array(mask_bool.shape) // 2
    shift_y = cy - max_y
    shift_x = cx - max_x
    filt_spec = np.roll(np.roll(filt_spec, shift_y, axis=0), shift_x, axis=1)
    obj_image = np.fft.ifft2(filt_spec)

    A2_shiftft = FFT_calc(reference)
    ref_filt_spec = A2_shiftft * mask_bool
    ref_filt_spec = np.roll(np.roll(ref_filt_spec, shift_y, axis=0), shift_x, axis=1)
    ref_image = np.fft.ifft2(ref_filt_spec)

    o1 = obj_image / ref_image
    phase1 = np.angle(o1)
    phase1[phase1 < 0] += 2 * np.pi

    Fs_x = 1 / get_pixel_size_var()
    Fs_y = 1 / get_pixel_size_var()
    dFx = Fs_x / Nx
    dFy = Fs_y / Ny
    Fx = np.linspace(-Fs_x / 2, Fs_x / 2 - dFx, Nx)
    Fy = np.linspace(-Fs_y / 2, Fs_y / 2 - dFy, Ny)

    unwrapped_psi = Fast_Unwrap(Fx, Fy, phase1)
    unwrapped_psi -= np.min(unwrapped_psi)

    # Optional cleaning based on threshold_strength
    mean = np.mean(unwrapped_psi)
    psi_inverted = 2 * mean - unwrapped_psi
    clean_psi = np.copy(unwrapped_psi)
    clean_psi[unwrapped_psi < mean] = mean
    clean_psi_inverted = np.copy(psi_inverted)
    clean_psi_inverted[psi_inverted < mean] = mean
    combined_clean = np.maximum(clean_psi, clean_psi_inverted)

    if get_beam_type_var() == "1 Beam":
        return combined_clean
    else:
        return unwrapped_psi
    

#removed threshold param from this function
def reduce_noise(imageArray):
    pixel_size = float(get_pixel_size_var())
    magnification = float(get_magnification_var())

    noise_red_phase = imageArray.copy()
    noise_red_phase[noise_red_phase < get_threshold_var() * np.mean(noise_red_phase)] = get_threshold_var() * np.mean(noise_red_phase)

    rows2, cols2 = noise_red_phase.shape
    delta_x = np.arange(1, cols2 + 1) * pixel_size / magnification
    delta_y = np.arange(1, rows2 + 1) * pixel_size / magnification

    return noise_red_phase, delta_x, delta_y


def compute_2d_thickness(imageArray):
    pixel_size = float(get_pixel_size_var())
    magnification = float(get_magnification_var())
    delta_ri = float(get_delta_ri_var())
    lambda_ = float(get_wavelength_var())

    thickness = imageArray * lambda_ / (2 * np.pi * delta_ri)
    thickness -= np.min(thickness)
    return thickness


def compute_3d_thickness(imageArray):
    thickness_2d = compute_2d_thickness(imageArray)
    pixel_size = float(get_pixel_size_var())
    magnification = float(get_magnification_var())

    pixel_size_micron = pixel_size / magnification
    rows2, cols2 = thickness_2d.shape
    delta_x = np.arange(0, cols2) * pixel_size_micron
    delta_y = np.arange(0, rows2) * pixel_size_micron
    X, Y = np.meshgrid(delta_x, delta_y)

    return X, Y, thickness_2d



def compute_1d_thickness(imageArray):

    thickness_1d = compute_2d_thickness(imageArray)
    thickness_1d = thickness_1d - thickness_1d.min()

    cam_pix_size = float(get_pixel_size_var())
    magnification = float(get_magnification_var())
    pixel_size_micron = cam_pix_size / magnification

    fig, ax = plt.subplots()
    ax.imshow(thickness_1d, cmap='jet')
    ax.set_title("Click two points to extract 1D profile", fontsize=14)
    pts = plt.ginput(2)

    if len(pts) != 2:
        plt.close(fig)
        messagebox.showerror("Error", "Please select exactly two points.")
        return

    (x1, y1), (x2, y2) = pts
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    rr, cc = line(y1, x1, y2, x2)

    rr = np.clip(rr, 0, thickness_1d.shape[0] - 1)
    cc = np.clip(cc, 0, thickness_1d.shape[1] - 1)

    ax.plot([x1, x2], [y1, y2], 'w-', linewidth=2)
    ax.set_title("Selected Line for 1D Profile", fontsize=14)
    plt.close( )
    thickness_values = thickness_1d[rr, cc]

    distances = np.linspace(0, len(thickness_values) * pixel_size_micron, len(thickness_values))
    return (distances, thickness_values)