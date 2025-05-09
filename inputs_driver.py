import pickle
import shutil
import os

# Delete the Hugging Face cache directory if it exists
cache_dir = os.path.expanduser("~/.cache/huggingface")
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)

###### INSERT USAGE HERE ######
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from datasets import load_dataset

# load model and processor
model_id = "litus-ai/whisper-small-ita"
processor = WhisperProcessor.from_pretrained(model_id)
model = WhisperForConditionalGeneration.from_pretrained(model_id)

# load Meta voxpopuli in italian
ds = load_dataset("facebook/voxpopuli", "it", split="test")
sample = ds[171]["audio"]  # sample having an "[UNINT]" token

inputs = processor(
  sample["array"],
  sampling_rate=sample["sampling_rate"],
  return_tensors="pt",
).input_features

#################################

with open("inputs.pkl", "wb") as f:
    pickle.dump(inputs, f)
