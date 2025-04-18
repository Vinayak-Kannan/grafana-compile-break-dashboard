import torch
from torch import nn
from torchview import draw_graph

class GraphBreakModule(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = nn.Linear(10, 20)
        self.linear2 = nn.Linear(20, 5)

    def forward(self, x):
        x = self.linear1(x)

        print("break")

        return self.linear2(x)

# Usage
module = GraphBreakModule()
inputs = torch.randn(1, 10)
model_graph = draw_graph(module, input_size=inputs.shape, device='cpu')
model_graph.visual_graph