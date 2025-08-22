

import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

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



texture_filenames = [
    "Std_Skin_Leg_Diffuse.png",
    "Std_Skin_Arm_Diffuse.png",
    "Std_Skin_Body_Diffuse.png",
    "female.png"
]

for texture_file in texture_filenames:
    texture_path = os.path.join(BASE_DIR, texture_file)
    image = cv2.imread(texture_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # Convert to HSV
    image_hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)

    # Calculate current average HSV
    avg_hsv_current = image_hsv.mean(axis=(0, 1)).astype(np.int32)

    # Target HSV (already computed above)
    target_hsv = np.array(list(avg_hsv), dtype=np.int32)

    # Compute difference and apply shift
    hsv_shift = target_hsv - avg_hsv_current
    image_hsv_shifted = image_hsv.astype(np.int32)
    image_hsv_shifted[:, :, 0] = (image_hsv_shifted[:, :, 0] + hsv_shift[0]) % 180
    image_hsv_shifted[:, :, 1] = np.clip(image_hsv_shifted[:, :, 1] + hsv_shift[1], 0, 255)
    image_hsv_shifted[:, :, 2] = np.clip(image_hsv_shifted[:, :, 2] + hsv_shift[2], 0, 255)
    image_hsv_shifted = image_hsv_shifted.astype(np.uint8)

    # Convert back to RGB
    recolored_rgb = cv2.cvtColor(image_hsv_shifted, cv2.COLOR_HSV2RGB)

    # Save the result with the same name in OUTPUT_DIR
    output_path = os.path.join(OUTPUT_DIR, texture_file)
    cv2.imwrite(output_path, cv2.cvtColor(recolored_rgb, cv2.COLOR_RGB2BGR))

    print(f"Saved recolored texture: {output_path}")