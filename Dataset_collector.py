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


#fixed problem with functionss & variables assigment / now able to use run all many times without problems
#did some refactoring
#fixed roi selection by making all windows top level

#global variables initialization
root = tk.Tk()

#users imported images
images_dict = {}
reference_dict = {}

#variables to hold images for functions
spectrum_image = unwrapped_psi_image = roi_image = cleaned_roi_image = thickness_2d_image = thickness_3d_image = thickness_1d_image = None

vmin = vmax = None

#Ui buttons
check_spectrum_button = run_phase_button = select_roi_button = noise_reduction_button = thickness_2d_button = thickness_3d_button = thickness_1d_button = run_all_button = None

dropdown_var = reference_label_var = image_label_var = None

dropdown_widget = None

#System parameters
pixel_size_var = magnification_var = delta_ri_var = dc_remove_var = filter_type_var = filter_size_var = type_var = None


#for roi selection
roi_coords = None
roi_selected_flag = False


list_of_windows = []

######################################################################################################################
#function for UI/UX
def show_figure_in_new_window(fig, title="Figure"):
    win = tk.Toplevel()
    win.title(title)
    canvas = FigureCanvasTkAgg(fig, master=win)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


#function used to ensure order of operations by user / enabling program features only after images are loaded
def enable_phase_computation():
    global run_phase_button
    if (len(images_dict.keys()) > 0) and (len(reference_dict.keys()) > 0):
        run_phase_button.config(state='normal')

######################################################################################################################
#Back-End

def load_image(dest, dropdown_var=None, dropdown_widget=None, label_var=None):
    file_paths = filedialog.askopenfilenames(
        title="Select Image(s)",
        filetypes=[
            ("Bitmap files", "*.bmp"),
            ("TIFF files", "*.tif"),
            ("All files", "*.*")
        ]
    )

    if not file_paths:
        print("No file(s) selected.")
        return

    try:
        for file_path in file_paths:
            img = Image.open(file_path).convert("L")
            title = os.path.basename(file_path)
            dest[title] = np.array(img)

        first_title = os.path.basename(file_paths[0])

        # Update dropdown menu if provided
        if dropdown_var and dropdown_widget:
            menu = dropdown_widget["menu"]
            menu.delete(0, "end")
            for item in dest:
                menu.add_command(label=item, command=tk._setit(dropdown_var, item))
            dropdown_var.set(first_title)

        # Update label_var if provided (to show first loaded image name)
        if label_var:
            label_var.set(first_title)

        enable_phase_computation()

        global image_label_var
        print(image_label_var.get())

    except Exception as e:
        print("Image loading failed:", e)






def create_mask(shape, center, size, kind='square'):
    mask = np.zeros(shape, dtype=bool)
    if kind == 'square':
        top_left = (center[0] - size // 2, center[1] - size // 2)
        rr, cc = rectangle(start=top_left, extent=(size, size), shape=shape)
    elif kind == 'circle':
        rr, cc = disk(center, radius=size // 2, shape=shape)
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

def FFT_calc(A):
    A = A.astype(float)
    return np.fft.fftshift(np.fft.fft2(A))

def check_spectrum(calledFromFunction=False):
    global mask_bool, shift_y, shift_x, obj_image, image_label_var, dc_remove_var, filter_type_var, filter_size_var
    global images_dict

    A1 = images_dict.get(image_label_var.get())

    #added error handling
    if type(A1) == np.ndarray:
        Ny, Nx = A1.shape
        A1_shiftft = FFT_calc(A1)

        center_y, center_x = Ny // 2, Nx // 2
        temp = np.abs(A1_shiftft.copy())
        dc_out = int(dc_remove_var.get())
        filter_type = filter_type_var.get()
        filter_size = int(filter_size_var.get())

        temp[center_y-dc_out:center_y+dc_out, center_x-dc_out:center_x+dc_out] = 0
        max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)
        mask_bool = create_mask((Ny, Nx), (max_y, max_x), filter_size, kind=filter_type)
        spectrum_global = np.log(1 + np.abs(A1_shiftft))
        if not calledFromFunction:
            fig, ax = plt.subplots()
            ax.imshow(np.log(1 + np.abs(A1_shiftft)), cmap='gray')
            ax.contour(mask_bool, colors='red', linewidths=1)
            ax.set_title('Filter and Position')
            ax.axis('off')
            fig.tight_layout()

            show_figure_in_new_window(fig, title="Filter and Position")

            filt_spec = A1_shiftft * mask_bool
            cy, cx = np.array(mask_bool.shape) // 2
            shift_y = cy - max_y
            shift_x = cx - max_x
            filt_spec = np.roll(np.roll(filt_spec, shift_y, axis=0), shift_x, axis=1)
            obj_image = np.fft.ifft2(filt_spec)
        else:

            return(A1_shiftft, mask_bool, max_y, max_x)


def run_phase_difference(calledFromFunction=False):
    global unwrapped_psi_image
    global wavelength_var, pixel_size_var, magnification_var, delta_ri_var
    global dc_remove_var, filter_type_var, filter_size_var
    global image_label_var, reference_label_var
    global images_dict, reference_dict
    global vmin, vmax

    lambda_ = float(wavelength_var.get())
    cam_pix_size = float(pixel_size_var.get())
    magnification = float(magnification_var.get())
    delta_RI = float(delta_ri_var.get())
    dc_out = int(dc_remove_var.get())
    filter_type = filter_type_var.get()
    filter_size = int(filter_size_var.get())

    for img_name, A1 in images_dict.items():
        for ref_name, A2 in reference_dict.items():
            print(f"Processing: Image = {img_name}, Reference = {ref_name}")
            print("Image mean:", np.mean(A1))
            print("Reference mean:", np.mean(A2))

            Ny, Nx = A1.shape
            A1_shiftft = FFT_calc(A1)

            center_y, center_x = Ny // 2, Nx // 2
            temp = np.abs(A1_shiftft.copy())
            temp[center_y - dc_out:center_y + dc_out, center_x - dc_out:center_x + dc_out] = 0
            max_y, max_x = np.unravel_index(np.argmax(temp), temp.shape)
            mask_bool = create_mask((Ny, Nx), (max_y, max_x), filter_size, kind=filter_type)

            filt_spec = A1_shiftft * mask_bool
            cy, cx = np.array(mask_bool.shape) // 2
            shift_y = cy - max_y
            shift_x = cx - max_x
            filt_spec = np.roll(np.roll(filt_spec, shift_y, axis=0), shift_x, axis=1)
            obj_image = np.fft.ifft2(filt_spec)

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

            Fs_x = 1 / cam_pix_size
            Fs_y = 1 / cam_pix_size
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

            normalized = (unwrapped_psi - np.min(unwrapped_psi)) / (np.max(unwrapped_psi) - np.min(unwrapped_psi))
            img_uint8 = (normalized * 255).astype(np.uint8)

            img_pil = Image.fromarray(img_uint8)
            img_pil.save(f"phase_{img_name}_vs_{ref_name}.png")


root.title("Image Plane DHM")
root.geometry("480x500")
root.resizable(False, False)

param_panel = tk.LabelFrame(root, text="Parameters", padx=10, pady=10, font=('Arial', 10, 'bold'))
param_panel.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

Label(param_panel, text="Wavelength (μm)").grid(row=0, column=0, sticky='e')
wavelength_var = Entry(param_panel, width=10)
wavelength_var.insert(0, "0.650")
wavelength_var.grid(row=0, column=1)

Label(param_panel, text="Camera Pixel Size (μm)").grid(row=0, column=2, sticky='e')
pixel_size_var = Entry(param_panel, width=10)
pixel_size_var.insert(0, "1.0")
pixel_size_var.grid(row=0, column=3)

Label(param_panel, text="Magnification").grid(row=1, column=0, sticky='e')
magnification_var = Entry(param_panel, width=10)
magnification_var.insert(0, "10")
magnification_var.grid(row=1, column=1)

Label(param_panel, text="RI Difference").grid(row=1, column=2, sticky='e')
delta_ri_var = Entry(param_panel, width=10)
delta_ri_var.insert(0, "1")
delta_ri_var.grid(row=1, column=3)

Label(param_panel, text="Pixels not be used in scanning").grid(row=2, column=0, sticky='e')
dc_remove_var = Entry(param_panel, width=10)
dc_remove_var.insert(0, "20")
dc_remove_var.grid(row=2, column=1)

Label(param_panel, text="Filter Size (pixels)").grid(row=2, column=2, sticky='e')
filter_size_var = Entry(param_panel, width=10)
filter_size_var.insert(0, "101")
filter_size_var.grid(row=2, column=3)

Label(param_panel, text="Filter Type").grid(row=3, column=0, sticky='e')
filter_type_var = StringVar(root)
filter_type_var.set("circle")
OptionMenu(param_panel, filter_type_var, "circle", "square").grid(row=3, column=1)

Label(param_panel, text="Number of beams").grid(row=3, column=2, sticky='e')
type_var = StringVar(root)
type_var.set("1 Beam")
OptionMenu(param_panel, type_var, "2 Beams", "1 Beam").grid(row=3, column=3)


button_panel = tk.LabelFrame(root, text="Phase computation", padx=10, pady=10, font=('Arial', 10, 'bold'))
button_panel.grid(row=4, column=0, columnspan=4, pady=20)

reference_label_var = tk.StringVar(value="No Reference Selected")

images_panel = tk.LabelFrame(root, text="Images", padx=10, pady=10, font=('Arial', 10, 'bold'))
images_panel.grid(row=3, column=0, columnspan=4, pady=10)


# Define label vars
image_label_var = tk.StringVar(value="None Selected")
reference_label_var = tk.StringVar(value="None Selected")

# Dropdowns
image_dropdown = tk.OptionMenu(images_panel, image_label_var, "None Available")
image_dropdown.grid(row=4, column=1, pady=(0, 2))

reference_dropdown = tk.OptionMenu(images_panel, reference_label_var, "None Available")
reference_dropdown.grid(row=4, column=2, pady=(0, 2))

# Buttons
Button(images_panel, text="Load Image",
       command=lambda: load_image(images_dict, image_label_var, image_dropdown),
       width=15).grid(row=3, column=1, padx=10, pady=5)

Button(images_panel, text="Load Reference",
       command=lambda: load_image(reference_dict, reference_label_var, reference_dropdown),
       width=15).grid(row=3, column=2, padx=10, pady=5)


Label(images_panel, textvariable=image_label_var).grid(row=4, column=1, pady=(0, 2))
Label(images_panel, textvariable=reference_label_var).grid(row=4, column=2, pady=(0, 5))

run_phase_button  = Button(button_panel, state='disabled', text="Phase Difference", command=run_phase_difference, width=15)
run_phase_button.grid(row=0, column=1, padx=10, pady=5)


root.mainloop()


