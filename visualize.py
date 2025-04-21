import torch
from PIL import Image
import torchlens as tl
import requests 
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import requests

device = "cuda" if torch.cuda.is_available() else "cpu"

url = 'http://images.cocodataset.org/val2017/000000039769.jpg'
image = Image.open(requests.get(url, stream=True).raw)

processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
module = AutoModel.from_pretrained('facebook/dinov2-small')

inputs_model = processor(images=image, return_tensors="pt")
model_history = tl.log_forward_pass(module, inputs_model['pixel_values'], layers_to_save='all', vis_opt='unrolled', vis_save_only=True)
