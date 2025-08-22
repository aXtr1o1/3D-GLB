import torch
import torchvision.models as models

# Load base model
model = models.resnet50(pretrained=False)  # or resnet18, resnet101 — match what you used

# Modify the final layer for 2 classes
model.fc = torch.nn.Linear(model.fc.in_features, 2)

# Load weights
model.load_state_dict(torch.load('C:\\Users\\sanje\\OneDrive\\Desktop\\hair_mapper\\HairMapper\\classifier\\gender_classification\\classification_model.pth', map_location='cpu'))

model.eval()




from torchvision import transforms
from PIL import Image

# Preprocess
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

image = Image.open('C:\\Users\\sanje\\OneDrive\\Desktop\\hair_mapper\\HairMapper\\test_data\\origin\\vineesh_01.png').convert('RGB')
input_tensor = transform(image).unsqueeze(0)  # Add batch dim

# Predict
with torch.no_grad():
    output = model(input_tensor)
    predicted_class = torch.argmax(output, dim=1).item()
    print("Predicted:", "Male" if predicted_class == 0 else "Female")
