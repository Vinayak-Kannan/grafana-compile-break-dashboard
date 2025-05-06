import pickle
import shutil
import os

# Delete the Hugging Face cache directory if it exists
cache_dir = os.path.expanduser("~/.cache/huggingface")
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)




from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
model_name = "MoritzLaurer/DeBERTa-v3-base-mnli"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)
premise = "I first thought that I liked the movie, but upon second thought it was actually disappointing."
hypothesis = "The movie was good."
inputs = tokenizer(premise, hypothesis, truncation=True, return_tensors="pt")

with open("inputs.pkl", "wb") as f:
    pickle.dump(inputs, f)
