import torch
import torch._dynamo as dynamo
from transformers import AutoModel
import numpy as np
import umap

model = AutoModel.from_pretrained("prajjwal1/bert-tiny")
inputs = {"input_ids": torch.ones(1, 10, dtype=torch.long)}

# explanation = dynamo.explain(model.forward)(**inputs)

# # Save to a text file
# with open("dynamo_explanation.txt", "w") as f:
#     f.write(str(explanation))


# Option 1: Modify your forward_refined function to accept keyword argumentsimport umap

def forward_refined(**kwargs):
    # Get the input_ids tensor
    input_ids = kwargs["input_ids"]
    
    # Get the second value in the shape (which is the sequence length)
    seq_length = input_ids.shape[1]
    
    # Create a copy of the input_ids to avoid modifying the original
    modified_input_ids = input_ids.clone()
    
    # Add the sequence length to the first element of input_ids
    # The first element is at position [0, 0]
    modified_input_ids[0, 0] += seq_length
    
    # Print for debugging
    print(f"Original first element: {input_ids[0, 0]}")
    print(f"Modified first element: {modified_input_ids[0, 0]}")
    print(f"Sequence length added: {seq_length}")
    
    # Apply UMAP transformation (arbitrary example)
    # Convert input_ids to a NumPy array for UMAP
    input_ids_np = input_ids.cpu().numpy()
    reducer = umap.UMAP(n_neighbors=2, n_components=2, random_state=42)
    umap_embedding = reducer.fit_transform(input_ids_np)

    # Print UMAP embedding for debugging
    print(f"UMAP embedding: {umap_embedding}")

    # Convert the UMAP embedding value to a PyTorch tensor
    umap_value = torch.tensor(umap_embedding[0, 0], dtype=modified_input_ids.dtype, device=modified_input_ids.device)

    # Add the UMAP value to the first element of modified_input_ids
    modified_input_ids[0, 0] += umap_value

    # Update the kwargs with the modified input_ids
    kwargs["input_ids"] = modified_input_ids
    
    # Call the original forward method with the modified inputs
    return model.original_forward(**kwargs)


# Not broken: tlparse logs/dedicated_log_torch_trace_v3ixwcdv.log -o tl_out/ --overwrite

# Save the original forward method
model.original_forward = model.forward
# Replace with your custom method
model.forward = forward_refined
# Compile the model
model = torch.compile(model)
# Call the model
model.forward(**inputs)
