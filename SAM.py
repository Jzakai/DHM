
from segment_anything import SamPredictor, sam_model_registry
import torch
import cv2
import numpy as np

# Load model
model_type = "vit_h"
checkpoint = "sam_vit_h.pth"
sam = sam_model_registry[model_type](checkpoint=checkpoint)
sam.to(device="cuda" if torch.cuda.is_available() else "cpu")

# Load image
image = cv2.imread("your_image.jpg")
image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Predict
predictor = SamPredictor(sam)
predictor.set_image(image)

# Define a point or bounding box
input_point = np.array([[300, 400]])
input_label = np.array([1])  # 1 = foreground
masks, scores, logits = predictor.predict(
    point_coords=input_point,
    point_labels=input_label,
    multimask_output=True,
)

# Show mask
import matplotlib.pyplot as plt
plt.imshow(masks[0])
plt.axis('off')
plt.show()
