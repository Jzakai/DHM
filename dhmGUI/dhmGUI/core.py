



root.title("Image Plane DHM")
root.geometry("480x850")
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


camera_panel = tk.LabelFrame(root, text="Camera", padx=10, pady=10, font=('Arial', 10, 'bold'))
camera_panel.grid(row=2, column=0, columnspan=4, pady=10)
Button(camera_panel, text="Open Camera", command=open_camera_window, width=15).grid(row=3, column=1, padx=10, pady=5)



Button(images_panel, text="Load Image", command=lambda: load_image(images_dict, image_label_var, image_dropdown), width=15).grid(row=3, column=1, padx=10, pady=5)
Button(images_panel, text="Load Reference", command=lambda: load_image(reference), width=15).grid(row=3, column=2, padx=10, pady=5)

image_label_var = tk.StringVar()
image_label_var.set("None Selected")
image_dropdown = tk.OptionMenu(images_panel, image_label_var, "None Available")
image_dropdown.grid(row=4, column=1, pady=(0, 2))

Label(images_panel, textvariable=image_label_var).grid(row=4, column=1, pady=(0, 2))
Label(images_panel, textvariable=reference_label_var).grid(row=4, column=2, pady=(0, 5))

check_spectrum_button = Button(button_panel, state='disabled', text="Check Spectrum", command=check_spectrum, width=15)
check_spectrum_button.grid(row=0, column=0, padx=10, pady=5)

run_phase_button  = Button(button_panel, state='disabled', text="Phase Difference", command=run_phase_difference, width=15)
run_phase_button.grid(row=0, column=1, padx=10, pady=5)

button_panel2 = tk.LabelFrame(root, text="ROI and backgroundnd noise reduction", padx=10, pady=10, font=('Arial', 10, 'bold'))
button_panel2.grid(row=5, column=0, columnspan=4, pady=20)

select_roi_button = Button(button_panel2, text="Select ROI", state='disabled', command=select_roi, width=15)
select_roi_button.grid(row=0, column=0, padx=10)

Label(button_panel2, text="Threshold strengh").grid(row=0, column=1, sticky='e')

noise_th = Entry(button_panel2, width=10)
noise_th.insert(0, "1")
noise_th.grid(row=0, column=3)

noise_reduction_button = Button(button_panel2, text="Noise Reduction", state='disabled', command=reduce_noise, width=15)
noise_reduction_button.grid(row=0, column=4, padx=10)

button_panel3 = tk.LabelFrame(root, text="Thickness distribution", padx=10, pady=10, font=('Arial', 10, 'bold'))
button_panel3.grid(row=6, column=0, columnspan=4, pady=20)

thickness_2d_button = Button(button_panel3, text="2D profile", state='disabled', command=compute_2d_thickness, width=15)
thickness_2d_button.grid(row=0, column=0, padx=10)

thickness_3d_button = Button(button_panel3, text="3D profile", state='disabled', command=compute_3d_thickness, width=15)
thickness_3d_button.grid(row=0, column=1, padx=10)

thickness_1d_button = Button(button_panel3, text="1D profile", state='disabled', command=compute_1d_thickness, width=15)
thickness_1d_button.grid(row=0, column=3, padx=10)

button_panel4 = tk.LabelFrame(root, text="Other", padx=10, pady=10, font=('Arial', 10, 'bold'))
button_panel4.grid(row=7, column=0, columnspan=4, pady=20)
run_all_button = Button(button_panel4, text="Run All", state='disabled', command=run_all, width=15)
run_all_button.grid(row=0, column=1, padx=10)

root.protocol("WM_DELETE_WINDOW", root.destroy)

root.mainloop()


