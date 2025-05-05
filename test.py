import torch
import torch._dynamo as dynamo
from transformers import AutoModel

model = AutoModel.from_pretrained("prajjwal1/bert-tiny")
inputs = {"input_ids": torch.ones(1, 10, dtype=torch.long)}

# Modify the forward method to include data-dependent control flow
original_forward = model.forward
def forward_with_break(*args, **kwargs):
    output = original_forward(*args, **kwargs)
    # Data-dependent control flow will cause a graph break
    if output.last_hidden_state.sum() > 0:
        return output
    return output


def forward_with_multiple_breaks(*args, **kwargs):
    # First traceable section
    partial_output = original_forward(*args, **kwargs)

    # Break 1: data-dependent control flow
    if partial_output.last_hidden_state.sum() > 0:
        x = partial_output.last_hidden_state + 1
    else:
        x = partial_output.last_hidden_state - 1

    # Second traceable section
    y = x * 2

    # Break 2: tensor.item() operation
    value = y[0, 0, 0].item()

    # Third traceable section
    result = y + value
    return result


model.forward = forward_with_multiple_breaks

# # Get explanation of graph breaks
# explanation = dynamo.explain(model.forward)(**inputs)
def toy_example(a, b):
    # First traceable section
    x = a / (torch.abs(a) + 1)

    # Break 1: print statement
    print("This will cause a break")

    # Second traceable section
    if b.sum() < 0:
        b = b * -1

    return x * b


a = torch.randn(10)
b = torch.randn(10)
explanation = dynamo.explain(toy_example)(a, b)
print(explanation)