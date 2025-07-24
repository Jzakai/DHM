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


#get image and system params
#return numpy array
def create_mask(imageArray, filter_size, kind='square'):
    Ny, Nx = imageArray.shape
    shape = (Ny,Nx)
    imageArray_shiftft = FFT_calc(imageArray)
    temp = np.abs(imageArray_shiftft.copy())
    max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)
    
    center = (max_y, max_x)

    mask = np.zeros(shape, dtype=bool)
    if kind == 'square':
        top_left = (center[0] - filter_size // 2, center[1] - filter_size // 2)
        rr, cc = rectangle(start=top_left, extent=(filter_size, filter_size), shape=shape)
    elif kind == 'circle':
        rr, cc = disk(center, radius=filter_size // 2, shape=shape)
    mask[rr, cc] = True
    return mask



#not used by user
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


#not used by user
def FFT_calc(A):
    A = A.astype(float)
    return np.fft.fftshift(np.fft.fft2(A))



#get image and system params
#return 4 numpy arrays
def check_spectrum(imageArray, dc_remove, filter_type, filter_size):

    #added error handling
    if type(imageArray) == np.ndarray:
        Ny, Nx = imageArray.shape
        imageArray_shiftft = FFT_calc(imageArray)

        center_y, center_x = Ny // 2, Nx // 2
        temp = np.abs(imageArray_shiftft.copy())
        dc_out = int(dc_remove)

        temp[center_y-dc_out:center_y+dc_out, center_x-dc_out:center_x+dc_out] = 0
        max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)
        mask_bool = create_mask((Ny, Nx), (max_y, max_x), filter_size, kind=filter_type)
        spectrum_global = np.log(1 + np.abs(imageArray_shiftft))
        return(imageArray_shiftft, mask_bool, max_y, max_x)



def run_phase_difference(wavelengthrushhold, magnaification, delta_ri, dc_remove, filter_type, filter_size, imageArray, reference):

    lambda_ = float(wavelengthrushhold)
    cam_pix_filter_size = float(filter_size)
    magnification = float(magnaification)
    delta_RI = float(delta_ri)
    dc_out = int(dc_remove)
    filter_type = filter_type
    filter_filter_size = int(filter_size)

    imageArray = imageArray
    print(np.mean(imageArray))

    Ny, Nx = imageArray.shape
    imageArray_shiftft = FFT_calc(imageArray)

    center_y, center_x = Ny // 2, Nx // 2
    temp = np.abs(imageArray_shiftft.copy())
    temp[center_y - dc_out:center_y + dc_out, center_x - dc_out:center_x + dc_out] = 0
    max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)
    mask_bool = create_mask((Ny, Nx), (max_y, max_x), filter_filter_size, kind=filter_type)

    filt_spec = imageArray_shiftft * mask_bool
    cy, cx = np.array(mask_bool.shape) // 2
    shift_y = cy - max_y
    shift_x = cx - max_x
    filt_spec = np.roll(np.roll(filt_spec, shift_y, axis=0), shift_x, axis=1)
    obj_image = np.fft.ifft2(filt_spec)

    A2 = reference
    A2_shiftft = FFT_calc(A2)
    ref_filt_spec = A2_shiftft * mask_bool
    ref_filt_spec = np.roll(np.roll(ref_filt_spec, shift_y, axis=0), shift_x, axis=1)
    ref_image = np.fft.ifft2(ref_filt_spec)

    o1 = obj_image / ref_image
    phase1 = np.angle(o1)
    phase1[phase1 < 0] += 2 * np.pi

    obj_img = np.fft.fft2(np.fft.fftshift(filt_spec))
    int_obj = np.abs(obj_img) ** 2
    int_obj = (int_obj - np.min(int_obj)) / np.max(int_obj)

    Fs_x = 1 / cam_pix_filter_size
    Fs_y = 1 / cam_pix_filter_size
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

    vmin = min(np.min(unwrapped_psi), np.min(psi_inverted), np.min(combined_clean))
    vmax = max(np.max(unwrapped_psi), np.max(psi_inverted), np.max(combined_clean))

    if filter_type == "1 Beam":
        unwrapped_psi = combined_clean
    return unwrapped_psi







def reduce_noise(thrushhold, imageArray, pixel_size, magnification):
    in_phase = imageArray
    noise_red_phase = in_phase.copy()
    noise_red_phase[noise_red_phase<thrushhold*np.mean(noise_red_phase)] = thrushhold*np.mean(noise_red_phase)

    cam_pix_size = float(pixel_size)
    magnification = float(magnification)

    rows2, cols2 = noise_red_phase.shape
    delta_x = np.arange(1, cols2 + 1) * cam_pix_size / magnification
    delta_y = np.arange(1, rows2 + 1) * cam_pix_size / magnification

    return noise_red_phase, delta_x, delta_y





def compute_2d_thickness(imageArray, wavelength_var, pixel_size, magnification, delta_ri):

    in_phase = imageArray
    lambda_ = float(wavelength_var)
    cam_pix_size = float(pixel_size)
    magnification = float(magnification)
    delta_RI = float(delta_ri)

    rows2, cols2 = in_phase.shape
    delta_x = np.arange(1, cols2 + 1) * cam_pix_size / magnification
    delta_y = np.arange(1, rows2 + 1) * cam_pix_size / magnification

    thickness = in_phase * lambda_ / (2 * np.pi * delta_RI)
    thickness -= np.min(thickness)
    return thickness


def compute_3d_thickness(imageArray, wavelength_var, pixel_size, magnification, delta_ri):

    thickness_3d = compute_2d_thickness(imageArray, wavelength_var, pixel_size, magnification, delta_ri)
    thickness_3d -= np.min(thickness_3d)

    cam_pix_size = float(pixel_size)
    magnification = float(magnification)
    pixel_size_micron = cam_pix_size / magnification

    rows2, cols2 = thickness_3d.shape
    delta_x = np.arange(0, cols2) * cam_pix_size / magnification
    delta_y = np.arange(0, rows2) * cam_pix_size / magnification
    X, Y = np.meshgrid(delta_x, delta_y)

    return (X,Y,thickness_3d)


