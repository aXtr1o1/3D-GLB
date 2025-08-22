

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os

# Set base directory relative to script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

# Dynamically find the image in input folder (e.g., first .png or .jpg file)
def find_input_image(folder, extensions=("png", "jpg", "jpeg")):
    for fname in os.listdir(folder):
        if fname.lower().endswith(extensions):
            return os.path.join(folder, fname)
    raise FileNotFoundError(f"No image found in {folder} with extensions {extensions}")



def extract_region_hsv(uv_texture_path, region_coords):

    image = cv2.imread(uv_texture_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    x, y, w, h = region_coords
    region_rgb = image_rgb[y:y+h, x:x+w]
    region_hsv = cv2.cvtColor(region_rgb, cv2.COLOR_RGB2HSV)

    avg_hsv = region_hsv.mean(axis=(0, 1)).astype(int)

    # Visualize the region and a patch with the average HSV color converted back to RGB for display
    avg_hsv_color = np.uint8([[avg_hsv]])  # Shape (1,1,3)
    avg_rgb_color = cv2.cvtColor(avg_hsv_color, cv2.COLOR_HSV2RGB)[0][0]

    plt.figure(figsize=(4, 2))
    plt.subplot(1, 2, 1)
    plt.imshow(region_rgb)
    plt.title("Sampled Region")
    plt.axis("off")

    plt.subplot(1, 2, 2)
    plt.imshow(np.ones((100, 100, 3), dtype=np.uint8) * avg_rgb_color)
    plt.title(f"Avg HSV: {tuple(avg_hsv)}")
    plt.axis("off")

    return tuple(avg_hsv)

# Example usage
uv_texture_path = find_input_image(INPUT_DIR)
region_coords = (70, 110, 130, 20)  # x, y, width, height
avg_hsv = extract_region_hsv(uv_texture_path, region_coords)
print("Average skin color (HSV):", avg_hsv)



# Load image
texture_path = os.path.join(BASE_DIR, "default_texture.jpg")
image = cv2.imread(texture_path)
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Convert to HSV
image_hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)

# Calculate current average HSV of the whole image (or a region if you prefer)
avg_hsv_current = image_hsv.mean(axis=(0, 1)).astype(np.int32)

# Target HSV value to shift toward (replace this with your extracted value)
target_hsv = np.array(list(avg_hsv), dtype=np.int32)

# Compute difference between target and current HSV
hsv_shift = target_hsv - avg_hsv_current

# Apply the shift to the entire image (with wraparound for hue)
image_hsv_shifted = image_hsv.astype(np.int32)
image_hsv_shifted[:, :, 0] = (image_hsv_shifted[:, :, 0] + hsv_shift[0]) % 180  # Hue
image_hsv_shifted[:, :, 1] = np.clip(image_hsv_shifted[:, :, 1] + hsv_shift[1], 0, 255)
image_hsv_shifted[:, :, 2] = np.clip(image_hsv_shifted[:, :, 2] + hsv_shift[2], 0, 255)
image_hsv_shifted = image_hsv_shifted.astype(np.uint8)

# Convert back to RGB
recolored_rgb = cv2.cvtColor(image_hsv_shifted, cv2.COLOR_HSV2RGB)

# Show results
plt.figure(figsize=(6, 3))
plt.subplot(1, 2, 1)
plt.imshow(image_rgb)
plt.title("Original Texture")
plt.axis("off")

plt.subplot(1, 2, 2)
plt.imshow(recolored_rgb)
plt.title(f"Tone Shifted (HSV→{tuple(target_hsv)})")
plt.axis("off")
plt.tight_layout()
# Save the recolored image
cv2.imwrite(os.path.join(OUTPUT_DIR,"toned_texture.jpg"), cv2.cvtColor(recolored_rgb, cv2.COLOR_RGB2BGR))

cv2.imwrite(os.path.join(OUTPUT_DIR,"toned_texture.jpg"), cv2.cvtColor(recolored_rgb, cv2.COLOR_RGB2BGR))



# Load the images (all same size)
facemask = os.path.join(BASE_DIR, "facemask.png")
base_img = cv2.imread(os.path.join(OUTPUT_DIR,"toned_texture.jpg"))
source_img = cv2.imread(uv_texture_path)
mask_img = cv2.imread(facemask, cv2.IMREAD_UNCHANGED)  # Mask image

# Convert mask to grayscale and binary
gray_mask = cv2.cvtColor(mask_img, cv2.COLOR_BGR2GRAY)
_, binary_mask = cv2.threshold(gray_mask, 10, 255, cv2.THRESH_BINARY)

# Extract bounding box around the mask
x, y, w, h = cv2.boundingRect(binary_mask)

# Extract region of interest (ROI)
face_roi = source_img[y:y+h, x:x+w]
mask_roi = binary_mask[y:y+h, x:x+w]

# Determine center point for seamlessClone
center = (x + w // 2, y + h // 2)

# Seamless Cloning
output_normal = cv2.seamlessClone(face_roi, base_img, mask_roi, center, cv2.NORMAL_CLONE)
output_mixed = cv2.seamlessClone(face_roi, base_img, mask_roi, center, cv2.MIXED_CLONE)

# Custom Alpha Blending
output_blended = base_img.copy()
roi = base_img[y:y+h, x:x+w]
mask_3ch = cv2.merge([mask_roi]*3)
alpha = mask_3ch.astype(np.float32) / 255.0
blended = (alpha * face_roi + (1 - alpha) * roi).astype(np.uint8)
output_blended[y:y+h, x:x+w] = blended

# Save result
cv2.imwrite(os.path.join(OUTPUT_DIR,"blend_image.jpg"), output_mixed)

# Display
plt.figure(figsize=(18, 6))
plt.subplot(1, 3, 1)
plt.imshow(cv2.cvtColor(output_normal, cv2.COLOR_BGR2RGB))
plt.title("SeamlessClone: NORMAL")
plt.axis('off')

plt.subplot(1, 3, 2)
plt.imshow(cv2.cvtColor(output_mixed, cv2.COLOR_BGR2RGB))
plt.title("SeamlessClone: MIXED")
plt.axis('off')

plt.subplot(1, 3, 3)
plt.imshow(cv2.cvtColor(output_blended, cv2.COLOR_BGR2RGB))
plt.title("Custom Alpha Blending")
plt.axis('off')

plt.tight_layout()



# Load images
texture_img = cv2.imread(os.path.join(OUTPUT_DIR,"blend_image.jpg"))
eye_mask = os.path.join(BASE_DIR, "maskeye.jpg")   # target texture
uv_img = cv2.imread(uv_texture_path)                 # source UV with eyes
mask_img = cv2.imread(eye_mask, cv2.IMREAD_GRAYSCALE)  # eye mask

# Ensure mask is binary
_, binary_mask = cv2.threshold(mask_img, 10, 255, cv2.THRESH_BINARY)

# Find contours of eye regions
contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# For each eye region
for contour in contours:
    # Get bounding box
    x, y, w, h = cv2.boundingRect(contour)

    # Create individual eye mask
    eye_mask = np.zeros_like(binary_mask)       
    cv2.drawContours(eye_mask, [contour], -1, (255,255,255), -1)

    # Crop eye from UV using mask
    uv_crop = cv2.bitwise_and(uv_img, uv_img, mask=eye_mask)

    # Create exact eye patch
    eye_patch = uv_crop[y:y+h, x:x+w]
    patch_mask = eye_mask[y:y+h, x:x+w]

    # Paste on same position in the texture image
    roi = texture_img[y:y+h, x:x+w]
    inv_mask = cv2.bitwise_not(patch_mask)
    roi_bg = cv2.bitwise_and(roi, roi, mask=inv_mask)
    eye_fg = cv2.bitwise_and(eye_patch, eye_patch, mask=patch_mask)
    combined = cv2.add(roi_bg, eye_fg)

    texture_img[y:y+h, x:x+w] = combined

# Save final result
cv2.imwrite(os.path.join(OUTPUT_DIR,"final_texture.jpeg"), texture_img)
print("✅ Eyes placed accurately using the mask!")