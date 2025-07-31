import numpy as np
from skimage.draw import disk, rectangle, line
import matplotlib
matplotlib.use('TkAgg')  # Or 'Qt5Agg' if PyQt installed
import matplotlib.pyplot as plt
from PIL import Image
from tkinter import messagebox

# Dummy JSON config for parameters (update or pass your own)
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

def load_image_as_array(image_path):
    img = Image.open(image_path).convert("L")
    return np.array(img)

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

def run_phase_difference(image_path, reference_path, json_params):
    # Load images inside function
    get_parameters(json_params)
    
    image_numpy_array = load_image_as_array(image_path)
    reference_numpy_array = load_image_as_array(reference_path)
    
    magnification = system_params["magnification"]
    delta_ri = system_params["delta_ri"]
    dc_remove = system_params["dc_remove"]
    filter_type = system_params["filter_type"]
    filter_size = system_params["filter_size"]
    pixel_size = system_params["pixel_size"]
    lambda_ = system_params["wavelength"]

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


def reduce_noise(image_numpy_array, json_params):
    get_parameters(json_params)
    
    threshold = 1
    pixel_size = system_params["pixel_size"]
    magnification = system_params["magnification"]

    noise_red_phase = image_numpy_array.copy()
    noise_red_phase[noise_red_phase < threshold * np.mean(noise_red_phase)] = threshold * np.mean(noise_red_phase)

    rows2, cols2 = noise_red_phase.shape
    delta_x = np.arange(1, cols2 + 1) * pixel_size / magnification
    delta_y = np.arange(1, rows2 + 1) * pixel_size / magnification

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(noise_red_phase, extent=(delta_x.min(), delta_x.max(), delta_y.min(), delta_y.max()), cmap='jet')
    ax.set_title('Noise Reduced Phase', fontsize=16, fontname='Times New Roman')
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('(μm)', fontsize=20)
    ax.axis('image')
    ax.tick_params(labelsize=20)
    ax.set_xlabel('x (μm)', fontsize=20, fontname='Times New Roman')
    ax.set_ylabel('y (μm)', fontsize=20, fontname='Times New Roman')

    return noise_red_phase, delta_x, delta_y


def compute_2d_thickness(image_numpy_array, json_params):
    get_parameters(json_params)
    
    pixel_size = system_params["pixel_size"]
    magnification = system_params["magnification"]
    delta_ri = system_params["delta_ri"]
    lambda_ = system_params["wavelength"]

    thickness = image_numpy_array * lambda_ / (2 * np.pi * delta_ri)
    thickness -= np.min(thickness)
    return thickness


def compute_3d_thickness(image_numpy_array, json_params):
    get_parameters(json_params)
    
    thickness_2d = compute_2d_thickness(image_numpy_array, json_params)
    pixel_size = system_params["pixel_size"]
    magnification = system_params["magnification"]

    pixel_size_micron = pixel_size / magnification
    rows2, cols2 = thickness_2d.shape
    delta_x = np.arange(0, cols2) * pixel_size_micron
    delta_y = np.arange(0, rows2) * pixel_size_micron
    X, Y = np.meshgrid(delta_x, delta_y)

    return X, Y, thickness_2d


def compute_1d_thickness(image_numpy_array, json_params):
    get_parameters(json_params)
    
    thickness_1d = compute_2d_thickness(image_numpy_array, json_params)
    thickness_1d = thickness_1d - thickness_1d.min()

    cam_pix_size = system_params["pixel_size"]
    magnification = system_params["magnification"]
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
    plt.close()

    thickness_values = thickness_1d[rr, cc]
    distances = np.linspace(0, len(thickness_values) * pixel_size_micron, len(thickness_values))

    return (distances, thickness_values)
