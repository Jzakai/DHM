# main_gui.py
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
import os
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import Label, Entry, Button, StringVar, OptionMenu, filedialog, messagebox
from package.backend.sys_functions import (
    check_spectrum, run_phase_difference, reduce_noise,
    compute_2d_thickness, compute_3d_thickness, compute_1d_thickness
)

class DHMGUI:
    def __init__(self, root):
        self.root = root
        root.title("Image Plane DHM")
        root.geometry("480x850")
        root.resizable(False, False)

        # Storage
        self.images_dict = {}
        self.references_dict = {}
        self.image_label_var = tk.StringVar(value="None Selected")
        self.reference_label_var = tk.StringVar(value="No Reference Selected")

        # --- Parameters panel ---
        param_panel = tk.LabelFrame(root, text="Parameters", padx=10, pady=10, font=('Arial', 10, 'bold'))
        param_panel.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

        Label(param_panel, text="Wavelength (μm)").grid(row=0, column=0, sticky='e')
        self.wavelength_var = Entry(param_panel, width=10)
        self.wavelength_var.insert(0, "0.650")
        self.wavelength_var.grid(row=0, column=1)

        # --- Camera Panel ---
        camera_panel = tk.LabelFrame(root, text="Camera", padx=10, pady=10, font=('Arial', 10, 'bold'))
        camera_panel.grid(row=2, column=0, columnspan=4, pady=10)
        #Button(camera_panel, text="Open Camera", command=open_camera_window, width=15).grid(row=3, column=1, padx=10, pady=5)

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
        Button(button_panel2, text="Noise Reduction", command=reduce_noise, width=15).grid(row=0, column=4, padx=10)

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

        # --- Create figure ---
        fig, axs = plt.subplots(1, 2, figsize=(10, 5))

        # Display log spectrum
        spectrum_display = np.log(1 + np.abs(imageArray_shiftft))
        axs[0].imshow(spectrum_display, cmap='gray')
        axs[0].set_title('Spectrum (Log Scale)')
        axs[0].plot(max_x, max_y, 'r+', markersize=12)  # mark max frequency
        axs[0].axis('off')

        # Display mask
        axs[1].imshow(mask_bool, cmap='gray')
        axs[1].set_title('Frequency Mask')
        axs[1].axis('off')

        plt.suptitle("Fourier Spectrum & Mask", fontsize=14)
        plt.tight_layout()
        plt.show()

    def display_phase_difference(self):
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
        unwrapped_psi = run_phase_difference(imageArray, reference)

        # --- Store result for later ROI / thickness use ---
        self.unwrapped_psi_image = unwrapped_psi

        # --- Display using Matplotlib ---
        vmin, vmax = unwrapped_psi.min(), unwrapped_psi.max()
        fig, ax = plt.subplots(figsize=(8, 6))
        im = ax.imshow(unwrapped_psi, cmap="jet", vmin=vmin, vmax=vmax)
        ax.set_title("Unwrapped Phase Difference")
        ax.axis("off")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
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

            # Update dropdown menu
            menu = self.image_dropdown["menu"]
            menu.delete(0, "end")
            for item in self.images_dict:
                menu.add_command(label=item, command=tk._setit(self.image_label_var, item))
            self.image_label_var.set(list(self.images_dict.keys())[0])

            messagebox.showinfo("Success", f"Loaded {len(file_paths)} image(s).")
        except Exception as e:
            messagebox.showerror("Error", f"Image loading failed: {e}")

    def load_reference_image(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Reference Image(s)",
            filetypes=[
                ("Bitmap files", "*.bmp"),
                ("TIFF files", "*.tif"),
                ("All files", "*.*")
            ]
        )
        if not file_paths:
            print("No reference file(s) selected.")
            return

        try:
            for file_path in file_paths:
                img = Image.open(file_path).convert("L")
                title = os.path.basename(file_path)
                self.references_dict[title] = np.array(img)

            # Update dropdown for references
            menu = self.reference_dropdown["menu"]
            menu.delete(0, "end")
            for item in self.references_dict:
                menu.add_command(label=item, command=tk._setit(self.reference_label_var, item))

            self.reference_label_var.set(list(self.references_dict.keys())[0])  # Set first loaded reference as default
            print("Reference images loaded:", list(self.references_dict.keys()))
        except Exception as e:
            print("Reference loading failed:", e)

    def select_roi(self, calledFromFunction=False):
        """Interactive ROI selection on unwrapped_psi_image."""
        if self.unwrapped_psi_image is None:
            messagebox.showerror("Error", "No image data available for ROI selection.")
            return

        # Reset ROI state
        self.roi_coords = None
        self.roi_selected_flag = False
        plt.close('all')

        def onselect(eclick, erelease):
            x1, y1 = int(eclick.xdata), int(eclick.ydata)
            x2, y2 = int(erelease.xdata), int(erelease.ydata)
            self.roi_coords = (min(y1, y2), max(y1, y2), min(x1, x2), max(x1, x2))
            self.roi_selected_flag = True
            plt.close()

        fig, ax = plt.subplots()
        ax.imshow(self.unwrapped_psi_image, cmap='jet')
        ax.set_title("Draw ROI: Click-drag-release")

        RectangleSelector(
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
        else:
            return reduce_noise(self.roi)

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
  