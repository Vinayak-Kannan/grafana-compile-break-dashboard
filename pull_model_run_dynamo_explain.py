import torch
import torch._dynamo as dynamo
from transformers import AutoModel

model = AutoModel.from_pretrained("prajjwal1/bert-tiny")
inputs = {"input_ids": torch.ones(1, 10, dtype=torch.long)}

explanation = dynamo.explain(model.forward)(**inputs)

# Save to a text file
with open("dynamo_explanation.txt", "w") as f:
    f.write(str(explanation))
