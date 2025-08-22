import cv2
import numpy as np

# Load the image
img = cv2.imread('C:\\Users\\sanje\\OneDrive\\Desktop\\DECA\\TestSamples\\examples\\results\\in_data\\in_data.png')

# Convert to YCrCb
img_ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)

# Define skin color range in YCrCb
lower = np.array([0, 135, 85], dtype=np.uint8)
upper = np.array([255, 180, 135], dtype=np.uint8)

# Create skin mask
skin_mask = cv2.inRange(img_ycrcb, lower, upper)

# Get skin pixels
skin_pixels = img[skin_mask > 0]

# Calculate average color of skin region
avg_color = skin_pixels.mean(axis=0).astype(np.uint8)

# Replace black pixels with average skin color
black_mask = np.all(img == [0, 0, 0], axis=-1)
img[black_mask] = avg_color

# Save the result
cv2.imwrite('C:\\Users\\sanje\\OneDrive\\Desktop\\DECA\\output\\final.jpg', img)
