import torch
import torch._dynamo as dynamo
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import os

# Hugging Face access token
hf_token = os.environ.get("HUGGING_FACE_TOKEN")

# Load the model and tokenizer.
model_name = "meta-llama/Llama-3.2-1B"
model = AutoModelForSequenceClassification.from_pretrained(model_name, token=hf_token)
tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)

# Set model to evaluation mode and disable gradients.
model.eval()
dummy_text = "This is a dummy input for TorchDynamo."
dummy_input = tokenizer(dummy_text, return_tensors="pt")

def forward_fn(inputs):
    return model(**inputs)

# Optionally, run in no_grad() context.
with torch.no_grad():
    explanation = dynamo.explain(forward_fn, dummy_input)
    # Write explanation to file
    with open("dynamo_explanation.txt", "w") as f:
        f.write(str(explanation))
    