import os
from rembg import remove
from PIL import Image


base_dir = os.path.dirname(os.path.abspath(__file__))

input_folder = os.path.join(base_dir, "hair_mapper/HairMapper/test_data/mapper_res")
output_folder = os.path.join(base_dir, "DECA/TestSamples/examples")


for file in os.listdir(input_folder):
    if file.lower().endswith((".png", ".jpg", ".jpeg")):
        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, os.path.splitext(file)[0] + ".png")

        with Image.open(input_path) as img:
            output = remove(img)
            output.save(output_path)
            print(f"Saved: {output_path}")
