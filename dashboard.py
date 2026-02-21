import panel as pn
import torch
import torchvision.transforms as transforms
from torchvision import models
from PIL import Image
import io
import os

pn.extension()
model_path = ''

# Load model
if os.environ.get('LEGACY_MODEL').lower() == 'true':
    print("Using legacy model (ResNet18 with custom weights)")
    model_path = 'models/best_model.pth'
else:
    model_path = 'model.pth'

if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model not found at {model_path}")

class_names = ['Akara', 'Bread', 'Egusi', 'Moi Moi', 'Rice and Stew', 'Yam']
model = models.resnet18(weights='IMAGENET1K_V1')
model.fc = torch.nn.Linear(model.fc.in_features, len(class_names))
model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
model.eval()

# Transforms
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Save image to correct folder
def save_image(image_obj, predicted_class, image_name="uploaded_image.jpg"):
    save_dir = f"data/train/{predicted_class}"
    os.makedirs(save_dir, exist_ok=True)
    image_path = os.path.join(save_dir, image_name)
    image_obj.save(image_path)

# Panel UI
image_input = pn.widgets.FileInput(accept='image/*')
output = pn.pane.Markdown("Upload an image of food 🍲")
image_preview = pn.pane.Image(width=300, height=300, visible=False)
spinner = pn.indicators.LoadingSpinner(value=False, width=50)

def classify(event=None):
    if image_input.value is None:
        output.object = "⚠️ Please upload an image first."
        image_preview.visible = False
        return
    try:
        image = Image.open(io.BytesIO(image_input.value)).convert('RGB')

        # Update preview
        image_preview.object = image
        image_preview.visible = True


        # Start spinner
        spinner.value = True
        output.object = "🔍 Classifying..."

        # Transform and predict
        img_tensor = transform(image).unsqueeze(0)
        with torch.no_grad():
            outputs = model(img_tensor)
            _, pred = torch.max(outputs, 1)
            predicted_class = class_names[pred.item()]

        # Save image
        save_image(image, predicted_class)
        output.object = f"✅ Identified as **{predicted_class}**. Image saved!"
    except Exception as e:
        output.object = f"❌ Error: {str(e)}"
    finally:
        spinner.value = False

run_button = pn.widgets.Button(name='Classify', button_type='primary')
run_button.on_click(classify)

app = pn.Column(
    "# 🍽️ FlavorSnap",
    "Upload an image and click the button to classify your food!",
    image_input,
    run_button,
    spinner,
    image_preview,
    output,
)

app.servable()
