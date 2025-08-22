import bpy
import os
import time
import bmesh
import math
import glob
import argparse

# Get the directory where the current script is located
BASE_DIR = os.path.dirname(__file__)

def abs_path(rel_path):
    """Helper to build an absolute path from a relative one."""
    return os.path.join(BASE_DIR, rel_path)

# Helper to delete all objects
def delete_all_objects():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

def import_obj(filepath):
    bpy.ops.wm.obj_import(filepath=filepath)
    return bpy.context.selected_objects


# Parse command-line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--g", type=str, required=True, help="Specify gender: 'male' or 'female'")
args, unknown = parser.parse_known_args()
gender = args.g.lower()

if gender not in ["male", "female"]:
    raise ValueError("Invalid gender. Use 'male' or 'female'.")


# Reset scene
delete_all_objects()

head_folder = abs_path("ready to use model/head")

# Find the first .obj file in the folder
obj_files = glob.glob(os.path.join(head_folder, "*.obj"))

if not obj_files:
    raise FileNotFoundError("❌ No .obj file found in the head folder.")

# Pick the first .obj file
obj1_path = obj_files[0]

# Extract just the file name (without folder and extension)
obj1_filename = os.path.basename(obj1_path)
obj1_name_wo_ext = os.path.splitext(obj1_filename)[0]  # e.g., 'output2'

# === Import first OBJ ===
imported_objs1 = import_obj(obj1_path)
obj1 = imported_objs1[0]
bpy.context.view_layer.objects.active = obj1

texture_path = abs_path("ready to use model/head/final_texture.jpeg")
img = bpy.data.images.load(texture_path)

# Get the first material from obj1
mat = obj1.active_material

if mat and mat.use_nodes:
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    # Create Image Texture node
    image_node = nodes.new('ShaderNodeTexImage')
    image_node.image = img
    image_node.location = (-300, 300)

    # Link it to the Principled BSDF node
    bsdf_node = nodes.get("Principled BSDF")
    if bsdf_node:
        links.new(image_node.outputs["Color"], bsdf_node.inputs["Base Color"])
    else:
        print("❌ 'Principled BSDF' not found in head material.")
else:
    print("❌ No material or material not using nodes on obj1.")


# Convert tris to quads
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.tris_convert_to_quads()
bpy.ops.object.mode_set(mode='OBJECT')

# Apply transformations
if gender == "male":
    obj1.location = (0.0166, 0.069, 8.712)
    obj1.rotation_euler[0] = math.radians(72)
    obj1.scale = (5.5, 5.5, 5.5)


    # === Import second OBJ ===
    obj2_path = abs_path("ready to use model/male/male body.obj")
    imported_objs2 = import_obj(obj2_path)


    # Texture image file paths
    body_textures = {
        "untitled:lambert1SG.001": "Std_Skin_Body_Diffuse.png",
        "untitled:lambert2SG.001": "Std_Skin_Arm_Diffuse.png",
        "untitled:lambert3SG.001": "Std_Skin_Leg_Diffuse.png"
    }

    for mat_name, img_filename in body_textures.items():
        texture_path = abs_path(f"Texture_body/output/{img_filename}")
        mat = bpy.data.materials.get(mat_name)
        if not mat or not mat.use_nodes:
            print(f"❌ Material {mat_name} not found or doesn't use nodes.")
            continue

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Load image
        img = bpy.data.images.load(texture_path)

        # Create texture node
        image_node = nodes.new('ShaderNodeTexImage')
        image_node.image = img
        image_node.location = (-300, 300)

        # Link to Base Color
        bsdf_node = nodes.get("Principled BSDF")
        if bsdf_node:
            links.new(image_node.outputs["Color"], bsdf_node.inputs["Base Color"])
            bsdf_node.inputs["Roughness"].default_value = 0.535
            bsdf_node.inputs["Metallic"].default_value = 0.173
            bsdf_node.inputs["IOR"].default_value = 0.100 
            print(f"✅ Added texture for {mat_name}")
        else:
            print(f"❌ 'Principled BSDF' not found in {mat_name}")

else:
    obj1.location = (0.0321, -0.06828, 8.5042)
    obj1.rotation_euler[0] = math.radians(84)
    obj1.rotation_euler[2] = math.radians(4.63)
    obj1.scale = (4.7, 4.7, 4.7)
    obj2_path = abs_path("ready to use model/female/famale_pubg.obj")
    imported_objs2 = import_obj(obj2_path)


    # Set shading to MATERIAL in 3D Viewport
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'MATERIAL'

    # Find the material
    material_name = "famale_pubg:Material__45.002"
    material = bpy.data.materials.get(material_name)

    if material and material.use_nodes:
        # Load image
        image_path = abs_path("Texture_body/output/female.png")
        image = bpy.data.images.load(image_path)

        # Create Image Texture node
        node_tree = material.node_tree
        nodes = node_tree.nodes
        links = node_tree.links

        tex_image = nodes.new('ShaderNodeTexImage')
        tex_image.image = image
        tex_image.location = (-300, 300)

        # Find Principled BSDF
        bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)

        if bsdf:
            # Link image color to base color
            links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
            bsdf_node.inputs["Roughness"].default_value = 0.8  # Set roughness to 0.8

    else:
        print(f"Material '{material_name}' not found or doesn't use nodes.")


# Join objects
for obj in imported_objs2:
    obj.select_set(True)
obj1.select_set(True)
bpy.context.view_layer.objects.active = obj1
bpy.ops.object.join()

bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

obj = bpy.context.object
bpy.ops.object.mode_set(mode='EDIT')
bm = bmesh.from_edit_mesh(obj.data)
bm.normal_update()

# Deselect all geometry
for v in bm.verts:
    v.select = False
for e in bm.edges:
    e.select = False

# Define z-range for neck seam
z_min = 7.0
z_max = 8.0

selected_edge_count = 0
bm.verts.ensure_lookup_table()

for e in bm.edges:
    if len(e.link_faces) == 1:
        v1, v2 = e.verts
        if z_min <= v1.co.z <= z_max and z_min <= v2.co.z <= z_max:
            e.select = True
            v1.select = True
            v2.select = True
            selected_edge_count += 1
bmesh.update_edit_mesh(obj.data)

sample_zs = [v.co.z for v in bm.verts[:10]]
print(f"✅ Selected {selected_edge_count} neck seam edges.")

bpy.ops.mesh.remove_doubles(threshold=0.075)
bpy.ops.object.mode_set(mode='OBJECT')




output_path = abs_path(f"output/{obj1_name_wo_ext}_model.glb")
os.makedirs(os.path.dirname(output_path), exist_ok=True)

# Create a temporary collection for export
temp_col = bpy.data.collections.new("TempExportCollection")
bpy.context.scene.collection.children.link(temp_col)

# Move the object to the new collection
obj_to_export = bpy.context.object
for col in obj_to_export.users_collection:
    col.objects.unlink(obj_to_export)
temp_col.objects.link(obj_to_export)

# Set the collection as active and export
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    use_selection=True  # Exports selected objects
)

print(f"✅ Exported GLB to {output_path}")
