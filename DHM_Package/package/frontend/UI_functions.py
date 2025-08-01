# main_gui.py
import json
from fastapi import requests
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import os
import numpy as np
from PIL import Image,ImageTk
import tkinter as tk
from tkinter import Label, Entry, Button, StringVar, OptionMenu, filedialog, messagebox
import paramiko
from pathlib import Path
from pypylon import pylon
import requests
import json





from package.backend.sys_functions import (
    check_spectrum, run_phase_difference, reduce_noise,
    compute_2d_thickness, compute_3d_thickness, compute_1d_thickness)
class DHMGUI:
    def __init__(self, root):
        self.root = root
        root.title("Image Plane DHM")
        root.geometry("480x850")
        root.resizable(False, False)

        self.ip = "192.168.1.121"
        self.port = "8000"
        self.username = "dhm"
        self.password = "123"
        self.image_name = "x.jpg"
        self.images_path = r"./images/input"
        self.src = f"./images/input/{self.image_name}" # full path to your local file
        self.dest = r"/home/dhm/Desktop/x.bmp"  # remote target full path (adjust if Windows!)

        # Storage
        self.images_dict = {}
        self.reference = None
        self.image_label_var = tk.StringVar(value="None Selected")
        self.reference_label_var = tk.StringVar(value="No Reference Selected")
        self.unwrapped_psi_image = None

        
        self.param_panel = tk.LabelFrame(root, text="Parameters", padx=10, pady=10, font=('Arial', 10, 'bold'))
        self.param_panel.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

        # Row 0
        tk.Label(self.param_panel, text="Wavelength (μm)").grid(row=0, column=0, sticky='e')
        self.wavelength_var = tk.Entry(self.param_panel, width=10)
        self.wavelength_var.insert(0, "0.650")
        self.wavelength_var.grid(row=0, column=1)

        tk.Label(self.param_panel, text="Camera Pixel Size (μm)").grid(row=0, column=2, sticky='e')
        self.pixel_size_var = tk.Entry(self.param_panel, width=10)
        self.pixel_size_var.insert(0, "1.0")
        self.pixel_size_var.grid(row=0, column=3)

        # Row 1
        tk.Label(self.param_panel, text="Magnification").grid(row=1, column=0, sticky='e')
        self.magnification_var = tk.Entry(self.param_panel, width=10)
        self.magnification_var.insert(0, "10")
        self.magnification_var.grid(row=1, column=1)

        tk.Label(self.param_panel, text="RI Difference").grid(row=1, column=2, sticky='e')
        self.delta_ri_var = tk.Entry(self.param_panel, width=10)
        self.delta_ri_var.insert(0, "1")
        self.delta_ri_var.grid(row=1, column=3)

        # Row 2
        tk.Label(self.param_panel, text="Pixels not be used in scanning").grid(row=2, column=0, sticky='e')
        self.dc_remove_var = tk.Entry(self.param_panel, width=10)
        self.dc_remove_var.insert(0, "20")
        self.dc_remove_var.grid(row=2, column=1)

        tk.Label(self.param_panel, text="Filter Size (pixels)").grid(row=2, column=2, sticky='e')
        self.filter_size_var = tk.Entry(self.param_panel, width=10)
        self.filter_size_var.insert(0, "101")
        self.filter_size_var.grid(row=2, column=3)

        # Row 3
        tk.Label(self.param_panel, text="Filter Type").grid(row=3, column=0, sticky='e')
        self.filter_type_var = tk.StringVar(root)
        self.filter_type_var.set("circle")
        tk.OptionMenu(self.param_panel, self.filter_type_var, "circle", "square").grid(row=3, column=1)

        tk.Label(self.param_panel, text="Number of beams").grid(row=3, column=2, sticky='e')
        self.type_var = tk.StringVar(root)
        self.type_var.set("1 Beam")
        tk.OptionMenu(self.param_panel, self.type_var, "2 Beams", "1 Beam").grid(row=3, column=3)

        tk.Label(self.param_panel, text="Threshold strengh").grid(row=3, column=4, sticky='e')
        self.noise_th = Entry(self.param_panel, width=10)
        self.noise_th.insert(0, "1")
        self.noise_th.grid(row=3, column=4)

        # --- Camera Panel ---
        camera_panel = tk.LabelFrame(root, text="Camera", padx=10, pady=10, font=('Arial', 10, 'bold'))
        camera_panel.grid(row=2, column=0, columnspan=4, pady=10)
        Button(camera_panel, text="Open Camera", command=self.open_camera_window, width=15).grid(row=3, column=1, padx=10, pady=5)

        # --- Images Panel ---
        images_panel = tk.LabelFrame(root, text="Images", padx=10, pady=10, font=('Arial', 10, 'bold'))
        images_panel.grid(row=3, column=0, columnspan=4, pady=10)

        Button(images_panel, text="Load Image", command=self.load_images_to_dict, width=15).grid(row=3, column=1, padx=10, pady=5)
        Button(images_panel, text="Load Reference", command=self.load_reference_image, width=15).grid(row=3, column=2, padx=10, pady=5)

        # Dropdown for images
        self.image_dropdown = OptionMenu(images_panel, self.image_label_var, "None Available")
        self.image_dropdown.grid(row=4, column=1, pady=(0, 2))

        Label(images_panel, textvariable=self.reference_label_var).grid(row=4, column=2, pady=(0, 5))

        # --- Phase Computation Panel ---
        button_panel = tk.LabelFrame(root, text="Phase computation", padx=10, pady=10, font=('Arial', 10, 'bold'))
        button_panel.grid(row=4, column=0, columnspan=4, pady=20)
        self.check_spectrum_button = Button(button_panel, text="Check Spectrum", command=self.display_spectrum, width=15)
        self.check_spectrum_button.grid(row=0, column=0, padx=10, pady=5)
        self.run_phase_button = Button(button_panel, text="Phase Difference", command=self.display_phase_difference, width=15)
        self.run_phase_button.grid(row=0, column=1, padx=10, pady=5)

        # --- ROI and Noise Panel ---
        button_panel2 = tk.LabelFrame(root, text="ROI and Noise Reduction", padx=10, pady=10, font=('Arial', 10, 'bold'))
        button_panel2.grid(row=5, column=0, columnspan=4, pady=20)
        Button(button_panel2, text="Select ROI", command=self.select_roi, width=15).grid(row=0, column=0, padx=10)
        #Button(button_panel2, text="Noise Reduction", command=reduce_noise, width=15).grid(row=0, column=4, padx=10)

        # --- Thickness Panel ---
        button_panel3 = tk.LabelFrame(root, text="Thickness Distribution", padx=10, pady=10, font=('Arial', 10, 'bold'))
        button_panel3.grid(row=6, column=0, columnspan=4, pady=20)
        Button(button_panel3, text="2D profile", command=self.display_2d_thickness, width=15).grid(row=0, column=0, padx=10)
        Button(button_panel3, text="3D profile", command=self.display_3d_thickness, width=15).grid(row=0, column=1, padx=10)
        Button(button_panel3, text="1D profile", command=self.display_1d_thickness, width=15).grid(row=0, column=3, padx=10)

        # --- Other Panel ---
        button_panel4 = tk.LabelFrame(root, text="Other", padx=10, pady=10, font=('Arial', 10, 'bold'))
        button_panel4.grid(row=7, column=0, columnspan=4, pady=20)
        Button(button_panel4, text="Run All", command=self.run_all, width=15).grid(row=0, column=1, padx=10)




    def send_images_to_backend(self, ip, username, password, image_title,src, dest):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            print(f"Connecting to {ip} as {username}...")
            client.connect(ip, username=username, password=password)

            with client.open_sftp() as sftp:
                print(f"Uploading {src} to {dest}...")
                sftp.put(src, dest)
                print("Upload complete!")

        except Exception as e:
            print("Error during upload:", e)

        finally:
            client.close()


    def open_camera_window(self):
        new_win = tk.Toplevel(self.root)
        new_win.title("Camera View")
        new_win.geometry("960x600")

        top_bar = tk.Frame(new_win, padx=10, pady=5)
        top_bar.pack(fill='x')

        capture_btn = tk.Button(top_bar, text="Capture", state='disabled')
        capture_btn.pack(side='left', padx=5)

        set_reference_btn = tk.Button(top_bar, text="Set as Reference", state='disabled')
        set_reference_btn.pack(side='left', padx=5)

        add_image_btn = tk.Button(top_bar, text="Add as Image", state='disabled')
        add_image_btn.pack(side='left', padx=5)

        tk.Label(top_bar, text="Exposure (µs):").pack(side='left')
        exposure_var = tk.StringVar(value="150")
        exposure_entry = tk.Entry(top_bar, textvariable=exposure_var, width=10)
        exposure_entry.pack(side='left', padx=5)

        canvas = tk.Canvas(new_win, width=960, height=540)
        canvas.pack()

        upButton = tk.Button(top_bar, text="↑ Up", width=10, command=None)
        upButton.pack(side='left', padx=5)

        leftButton = tk.Button(top_bar, text="← Left", width=10, command=lambda: move_motor("left"))
        leftButton.pack(side='left', padx=5)

        rightButton = tk.Button(top_bar, text="→ Right", width=10, command=lambda: move_motor("right"))
        rightButton.pack(side='left', padx=5)

        downButton = tk.Button(top_bar, text="↓ Down", width=10, command=lambda: move_motor("down"))
        downButton.pack(side='left', padx=5)

        def move_motor(direction):
            print(f"Moving motor: {direction}")
            # TODO: Replace with motor control code

        # Create a separate frame for motor buttons
        motor_bar = tk.Frame(new_win, padx=10, pady=5)
        motor_bar.pack(fill='x')
        try:
            camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
            camera.Open()
            camera.ExposureAuto.SetValue('Off')  # Disable auto exposure
            camera.ExposureTime.SetValue(150.0)  # Default exposure
            camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
        except Exception as e:
            tk.messagebox.showerror("Camera Error", f"Failed to open Basler camera.\n{e}")
            new_win.destroy()
            return

        converter = pylon.ImageFormatConverter()
        converter.OutputPixelFormat = pylon.PixelType_Mono8
        converter.OutputBitAlignment = pylon.OutputBitAlignment_MsbAligned

        current_img = [None]
        tk_img = [None]

        def update_frame():
            if camera.IsGrabbing():
                grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if grab_result.GrabSucceeded():
                    image = converter.Convert(grab_result)
                    frame = image.GetArray()

                    img = Image.fromarray(frame)
                    img = img.resize((960, 540), Image.Resampling.LANCZOS)
                    current_img[0] = frame
                    tk_img[0] = ImageTk.PhotoImage(img)
                    canvas.create_image(0, 0, anchor='nw', image=tk_img[0])

                    capture_btn.config(state='normal')
                grab_result.Release()
            if camera.IsGrabbing():
                new_win.after(30, update_frame)

        def capture_image():
            capture_btn.config(state='disabled')
            set_reference_btn.config(state='normal')
            add_image_btn.config(state='normal')

        def set_as_reference():
            global reference, reference_label_var
            reference = current_img[0]
            reference_label_var.set("Captured Reference")
            set_reference_btn.config(state='disabled')
            add_image_btn.config(state='disabled')
            self.enable_phase_computation()

        def add_as_image():
            global images_dict, image_label_var, image_dropdown
            index = 1
            while f"Captured_Image_{index}" in images_dict:
                index += 1
            key = f"Captured_Image_{index}"
            images_dict[key] = current_img[0]

            menu = image_dropdown["menu"]
            menu.delete(0, "end")
            for item in images_dict:
                menu.add_command(label=item, command=tk._setit(image_label_var, item))
            image_label_var.set(key)

            set_reference_btn.config(state='disabled')
            add_image_btn.config(state='disabled')
            self.enable_phase_computation()

        def on_exposure_change(*args):
            try:
                val = float(exposure_var.get())
                if camera.IsOpen():
                    camera.ExposureTime.SetValue(val)
            except Exception as e:
                print(f"Exposure update failed: {e}")

        exposure_var.trace_add("write", on_exposure_change)

        def on_close():
            try:
                if camera.IsGrabbing():
                    camera.StopGrabbing()
                camera.Close()
            except Exception as e:
                print(f"Camera close failed: {e}")
            new_win.destroy()

        new_win.protocol("WM_DELETE_WINDOW", on_close)

        capture_btn.config(command=capture_image)
        set_reference_btn.config(command=set_as_reference)
        add_image_btn.config(command=add_as_image)

        update_frame()

    #function used to ensure order of operations by user / enabling program features only after images are loaded
    def enable_phase_computation():
        global check_spectrum_button
        global run_phase_button
        global run_all_button


        if (len(images_dict.keys()) > 0) and reference is not None:

            check_spectrum_button.config(state='normal')
            run_phase_button.config(state='normal')
            run_all_button.config(state='normal')
            
    def display_spectrum(self):

        # --- Get selected image from GUI ---
        image_key = self.image_label_var.get()
        if not image_key or image_key not in self.images_dict:
            print("No image selected.")
            return

        imageArray = self.images_dict[image_key]
        if imageArray is None or not isinstance(imageArray, np.ndarray):
            print("Invalid image data.")
            return

        # --- Call backend function ---
        imageArray_shiftft, mask_bool, max_y, max_x = check_spectrum(imageArray)

        fig, ax = plt.subplots()
        ax.imshow(np.log(1 + np.abs(imageArray_shiftft)), cmap='gray')
        ax.contour(mask_bool, colors='red', linewidths=1)
        ax.set_title('Filter and Position')
        ax.axis('off')
        fig.tight_layout()
        plt.show()

    def display_phase_difference(self):

        # --- Collect parameters into a dictionary ---
        params = {
            "wavelength": float(self.wavelength_var.get()),
            "pixel_size": float(self.pixel_size_var.get()),
            "magnification": float(self.magnification_var.get()),
            "delta_ri": float(self.delta_ri_var.get()),
            "dc_remove": int(self.dc_remove_var.get()),
            "filter_type": self.filter_type_var.get(),
            "filter_size": int(self.filter_size_var.get()),
            "beam_type": self.type_var.get(),
            "threshold_strength": float(self.noise_th.get())
        }

        resp = requests.post(f"http://{self.ip}:8000/{"run_phase_difference"}", json.dumps(params))
        print(resp.status_code, resp.text)
    
        #pass parameters as post to server
        # --- Convert to JSON and send POST to server ---
        try:
            response = requests.post(
                "http://127.0.0.1:8000/run_phase_difference_params",
                json=params
            )
            if response.status_code == 200:
                result = response.json()
                print("Server Response:", result)  # or handle returned metadata
            else:
                print("Server Error:", response.status_code, response.text)
        except Exception as e:
            print("Error communicating with server:", e)

        # --- Get the selected object image and reference ---
        image_key = self.image_label_var.get()
        if not image_key or image_key not in self.images_dict:
            print("No image selected.")
            return

        imageArray = self.images_dict[image_key]
        reference = self.reference
        if reference is None:
            print("No reference image set.")
            return

        # --- Call backend computation ---
        unwrapped_psi = run_phase_difference(
        imageArray,
        reference,
        params["wavelength"],
        params["pixel_size"],
        params["magnification"],
        params["delta_ri"],
        params["dc_remove"],
        params["filter_type"],
        params["filter_size"],
        params["beam_type"],
        params["threshold_strength"]
        )
    #send params, image, ref to server
    # reqeust unwraped phase image


    #get the unwrapped phase image

        # --- Store result for later ROI / thickness use ---
        self.unwrapped_psi_image = unwrapped_psi


        mean = np.mean(unwrapped_psi)

        psi_inverted = 2 * mean - unwrapped_psi

        clean_psi = np.copy(unwrapped_psi)
        clean_psi[unwrapped_psi < mean] = mean

        clean_psi_inverted = np.copy(psi_inverted)
        clean_psi_inverted[psi_inverted < mean] = mean

        combined_clean = np.maximum(clean_psi, clean_psi_inverted)

        
        vmin, vmax = np.min(unwrapped_psi), np.max(unwrapped_psi)

        fig, ax = plt.subplots(figsize=(8, 6))

        if self.type_var.get() == "1 Beam":
            im = ax.imshow(combined_clean, cmap='jet', vmin=vmin, vmax=vmax)
            ax.set_title('Combined Unwrapped Phase')
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            unwrapped_psi = combined_clean
        else:
            im = ax.imshow(unwrapped_psi, cmap='jet')
            ax.set_title('Unwrapped Phase')
            ax.axis('off')
            fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        unwrapped_psi_image = unwrapped_psi
        fig.tight_layout()
        plt.show()

    

    def display_2d_thickness(self):
        """
        Display 2D thickness profile using backend compute_2d_thickness.
        Uses ROI if available, otherwise the full phase image.
        """
        # Choose ROI if available, else entire phase image
        if hasattr(self, "roi") and self.roi is not None:
            data = self.roi
        else:
            data = getattr(self, "unwrapped_psi_image", None)
            if data is None:
                print("No phase image computed yet.")
                return

        # Call backend to compute thickness
        thickness = compute_2d_thickness(data)

        # Plot the 2D thickness map
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(thickness, cmap='jet')
        ax.set_title('Thickness 2D Profile', fontsize=16)
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('(μm)', fontsize=14)
        ax.set_xlabel('x (μm)')
        ax.set_ylabel('y (μm)')
        plt.show()
        
    def display_3d_thickness(self):
        """
        Display 3D thickness profile from ROI if selected, else from full image.
        Uses compute_3d_thickness backend.
        """
        # Choose ROI if available, else entire phase image
        if hasattr(self, "roi") and self.roi is not None:
            data = self.roi
        else:
            data = getattr(self, "unwrapped_psi_image", None)
            if data is None:
                print("No phase image computed yet.")
                return

        # --- Call backend computation (only image array is required now) ---
        X, Y, thickness = compute_3d_thickness(data)

        # --- Plot 3D surface ---
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        surf = ax.plot_surface(X, Y, thickness, cmap='jet', linewidth=0, antialiased=True, shade=True)

        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label='(μm)')
        ax.set_title('Thickness 3D rendering')
        ax.set_xlabel('x (μm)')
        ax.set_ylabel('y (μm)')
        ax.set_zlabel('Thickness (μm)')

        plt.show()

    def display_1d_thickness(self):
        """
        Display 1D thickness profile using backend compute_1d_thickness.
        Uses ROI if available, otherwise the full phase image.
        """
        # Choose ROI if available, else full image
        if hasattr(self, "roi") and self.roi is not None:
            data = self.roi
        else:
            data = getattr(self, "unwrapped_psi_image", None)
            if data is None:
                print("No phase image computed yet.")
                return

        # Call backend (backend handles user point selection & computation)
        result = compute_1d_thickness(data)
        if result is None:
            print("1D thickness computation canceled or failed.")
            return

        distances, values = result

        # Plot the thickness profile
        fig, ax = plt.subplots()
        ax.plot(distances, values, 'b-', linewidth=2)
        ax.set_xlabel("Position (μm)")
        ax.set_ylabel("Thickness (μm)")
        ax.set_title("1D Thickness Profile")
        ax.grid(True)
        plt.show()

    #helper function to save image in server
    
    def load_images_to_dict(self):
        """Load one or more sample images into dictionary and update dropdown."""
        file_paths = filedialog.askopenfilenames(
            title="Select Image(s)",
            filetypes=[("Bitmap files", "*.bmp"), ("TIFF files", "*.tif"), ("All files", "*.*")]
        )

        if not file_paths:
            return

        try:
            for file_path in file_paths:
                img = Image.open(file_path).convert("L")
                title = os.path.basename(file_path)
                self.images_dict[title] = np.array(img)
                img.save(f"{self.images_path}/{title}")
                src = os.path.abspath(f"{self.images_path}/{title}")
                self.send_images_to_backend(self.ip, self.username, self.password, title, src,f"/home/dhm/Desktop/{title}")
            # Update dropdown menu
            menu = self.image_dropdown["menu"]
            menu.delete(0, "end")
            for item in self.images_dict:
                menu.add_command(label=item, command=tk._setit(self.image_label_var, item))
            self.image_label_var.set(list(self.images_dict.keys())[0])

        except Exception as e:
            messagebox.showerror("Error", f"Image loading failed: {e}")

    def load_reference_image(self):
        """Load one or more sample images into dictionary and update dropdown."""
        file_paths = filedialog.askopenfilenames(
            title="Select Image(s)",
            filetypes=[("Bitmap files", "*.bmp"), ("TIFF files", "*.tif"), ("All files", "*.*")]
        )

        img = Image.open(file_paths[0]).convert("L")
        title = os.path.basename(file_paths[0])

        img.save(f"{self.images_path}/{title}")
        src = os.path.abspath(f"{self.images_path}/{title}")
        self.send_images_to_backend(self.ip, self.username, self.password, title, src,f"/home/dhm/Desktop/{title}")
        
        img_array = np.array(img)
        self.reference_label_var.set(title)
        self.reference = img_array


    def select_roi(self, calledFromFunction=False):
        """Interactive ROI selection on unwrapped_psi_image."""
        if self.unwrapped_psi_image is None:
            messagebox.showerror("Error", "No image data available for ROI selection.")
            return

        # Reset ROI state
        self.roi_coords = None
        self.roi_selected_flag = False

        def onselect(eclick, erelease):
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)
            self.roi_coords = (min(y1, y2), max(y1, y2), min(x1, x2), max(x1, x2))
            self.roi_selected_flag = True
            plt.close()

        fig, ax = plt.subplots()
        ax.imshow(self.unwrapped_psi_image, cmap='jet')
        ax.set_title("Draw ROI: Click-drag-release")

        # Keep a reference to RectangleSelector
        self.rectangle_selector = RectangleSelector(
            ax, onselect,
            useblit=True,
            interactive=True,
            button=[1],
            minspanx=5,
            minspany=5,
            props=dict(facecolor='none', edgecolor='red', linestyle='--', linewidth=2)
        )

        plt.show(block=True)

        # If user did not select ROI
        if not self.roi_selected_flag or self.roi_coords is None:
            print("ROI selection not done.")
            return

        r1, r2, c1, c2 = self.roi_coords
        self.roi = self.unwrapped_psi_image[r1:r2, c1:c2]

        if not calledFromFunction:
            fig, ax = plt.subplots()
            im = ax.imshow(self.roi, cmap='jet')
            ax.set_title("Selected ROI")
            ax.axis('off')
            fig.colorbar(im, ax=ax)
            fig.tight_layout()
            plt.show()
    
            return reduce_noise(self.roi,2)

    def run_all(self):
        """Run full DHM pipeline and display results in a multi-panel figure."""
        # --- Validate images ---
        image_key = self.image_label_var.get()
        if not image_key or image_key not in self.images_dict:
            messagebox.showerror("Error", "No image selected.")
            return
        if self.reference is None:
            messagebox.showerror("Error", "No reference image selected.")
            return

        image = self.images_dict[image_key]
        reference = self.reference

        # --- Step 1: Spectrum check ---
        A1_shiftft, mask_bool, max_y, max_x = check_spectrum(image)
        spectrum_display = np.log(1 + np.abs(A1_shiftft))

        # --- Step 2: Phase difference ---
        unwrapped_psi_image = run_phase_difference(image, reference)
        self.unwrapped_psi_image = unwrapped_psi_image

        # --- Step 3: ROI ---
        roi = self.select_roi(calledFromFunction=True)
        self.roi = roi if roi is not None else unwrapped_psi_image

        # --- Step 4: Noise reduction on ROI ---
        noise_red_phase, delta_x, delta_y = reduce_noise(self.roi, threshold=1.0)

        # --- Step 5: Thickness profiles ---
        X, Y, thickness_3d = compute_3d_thickness(self.roi)
        distances, thickness_values = compute_1d_thickness(self.roi)

        # --- Plotting results ---
        fig, axs = plt.subplots(3, 2, figsize=(16, 18))
        fig.suptitle("DHM Output Overview", fontsize=22)
        axs = axs.ravel()

        # 1. Original Image
        im0 = axs[0].imshow(image, cmap='gray')
        axs[0].set_title('Original Image'); axs[0].axis('off')
        fig.colorbar(im0, ax=axs[0], fraction=0.046)

        # 2. FFT Spectrum + Mask
        im1 = axs[1].imshow(spectrum_display, cmap='gray')
        axs[1].contour(mask_bool, colors='red', linewidths=1)
        axs[1].set_title('Filter and Position'); axs[1].axis('off')
        fig.colorbar(im1, ax=axs[1], fraction=0.046)

        # 3. Unwrapped Phase
        im2 = axs[2].imshow(unwrapped_psi_image, cmap='jet')
        axs[2].set_title('Unwrapped Phase'); axs[2].axis('off')
        fig.colorbar(im2, ax=axs[2], fraction=0.046)

        # 4. ROI
        im3 = axs[3].imshow(self.roi, cmap='jet')
        axs[3].set_title("Selected ROI"); axs[3].axis('off')
        fig.colorbar(im3, ax=axs[3], fraction=0.046)

        # 5. 1D Thickness Profile
        axs[4].plot(distances, thickness_values, 'b-', linewidth=2)
        axs[4].set_title("1D Thickness Profile")
        axs[4].set_xlabel("Position (μm)"); axs[4].set_ylabel("Thickness (μm)")
        axs[4].grid(True)

        # 6. Noise Reduced Phase
        im5 = axs[5].imshow(noise_red_phase,
                            extent=(delta_x.min(), delta_x.max(), delta_y.min(), delta_y.max()),
                            cmap='jet')
        axs[5].set_title('Noise Reduced Phase')
        axs[5].set_xlabel('x (μm)'); axs[5].set_ylabel('y (μm)')
        fig.colorbar(im5, ax=axs[5], fraction=0.046).set_label('(μm)')

        plt.tight_layout(rect=[0, 0, 1, 0.97])
        plt.show()


    def run():
        root = tk.Tk()
        app = DHMGUI(root)
        root.mainloop()
  