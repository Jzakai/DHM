# -*- coding: utf-8 -*-
"""Noise2Void.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1hS12SUizi-Nu5Pzo8YR9vZS0cBTK26Rt
"""

import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import matplotlib.pyplot as plt
from tqdm import tqdm
import random

# Dataset Loader for Noisy Images Only
class NoisyOnlyDataset(Dataset):
    def __init__(self, noisy_dir, transform=None):
        self.noisy_dir = noisy_dir
        self.filenames = sorted(os.listdir(noisy_dir))
        self.transform = transform if transform else transforms.ToTensor()

    def __len__(self):
        return len(self.filenames)

    def __getitem__(self, idx):
        path = os.path.join(self.noisy_dir, self.filenames[idx])
        img = Image.open(path).convert('RGB')
        return self.transform(img)

# Random Masking Function
def random_mask(img, mask_prob=0.05):
    mask = (torch.rand_like(img) < mask_prob).float()
    masked_img = img * (1 - mask)  # set masked pixels to 0
    return masked_img, mask


# Masked Loss Function
def masked_mse_loss(pred, target, mask):
    masked_diff = (pred - target) * mask
    return (masked_diff ** 2).sum() / mask.sum()

# U-Net Definition (Grayscale Input)
class UNet(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(UNet, self).__init__()

        def block(in_c, out_c):
            return nn.Sequential(
                nn.Conv2d(in_c, out_c, 3, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True),
                nn.Conv2d(out_c, out_c, 3, padding=1),
                nn.BatchNorm2d(out_c),
                nn.ReLU(inplace=True)
            )

        self.enc1 = block(in_channels, 64)
        self.enc2 = block(64, 128)
        self.enc3 = block(128, 256)
        self.enc4 = block(256, 512)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = block(512, 1024)
        self.up4 = nn.ConvTranspose2d(1024, 512, 2, stride=2)
        self.dec4 = block(1024, 512)
        self.up3 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec3 = block(512, 256)
        self.up2 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec2 = block(256, 128)
        self.up1 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec1 = block(128, 64)
        self.final = nn.Conv2d(64, out_channels, kernel_size=1)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))
        d4 = self.up4(b)
        d4 = self.dec4(torch.cat([d4, e4], dim=1))
        d3 = self.up3(d4)
        d3 = self.dec3(torch.cat([d3, e3], dim=1))
        d2 = self.up2(d3)
        d2 = self.dec2(torch.cat([d2, e2], dim=1))
        d1 = self.up1(d2)
        d1 = self.dec1(torch.cat([d1, e1], dim=1))
        return self.final(d1)

# Training Setup
# Settings
noisy_data_path = 'your_dataset/noisy/'  # CHANGE THIS TO FOLDER
batch_size = 8
num_epochs = 20
learning_rate = 1e-3

transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.ToTensor()
])

dataset = NoisyOnlyDataset(noisy_data_path, transform=transform)
dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = UNet(in_channels=3, out_channels=3).to(device) # if grey scale change to 1
criterion = masked_mse_loss
optimizer = optim.Adam(model.parameters(), lr=learning_rate)

# Training Loop
for epoch in range(num_epochs):
    model.train()
    epoch_loss = 0

    for imgs in tqdm(dataloader):
        imgs = imgs.to(device)
        masked_imgs, masks = random_mask(imgs)
        masked_imgs, masks = masked_imgs.to(device), masks.to(device)

        outputs = model(masked_imgs)
        loss = criterion(outputs, imgs, masks)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        epoch_loss += loss.item()

    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss/len(dataloader):.4f}")

# Save Model
torch.save(model.state_dict(), "unet_selfsupervised_denoiser.pth")

# Inference & Visualization
model.eval()
sample = dataset[0].unsqueeze(0).to(device)
with torch.no_grad():
    output = model(sample)

output = output.squeeze(0).cpu().clamp(0, 1)
input_image = sample.squeeze(0).cpu().clamp(0, 1)

plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.imshow(input_image.permute(1, 2, 0))
plt.title("Noisy Input")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.imshow(output.permute(1, 2, 0))
plt.title("Denoised Output")
plt.axis("off")
plt.show()