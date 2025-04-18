import torch
import torch.nn as nn
import torch._dynamo as dynamo
from torch.fx import passes, symbolic_trace


class GraphBreakModule(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = nn.Linear(10, 20)
        self.linear2 = nn.Linear(20, 5)

    def forward(self, x):
        x = self.linear1(x)

        print("break")

        return self.linear2(x)

# Create an instance of the module
module = GraphBreakModule()
inputs = torch.randn(1, 10)
# dynamo_explanation = dynamo.explain(module.forward)(inputs)
# Print attributes for dynamo_explanation
# print("Dynamo Explanation:")
# for attr in dir(dynamo_explanation.graphs[0]):
#     if not attr.startswith('__'):
#         print(f"{attr}: {getattr(dynamo_explanation.graphs[0], attr)}")

traced_module = symbolic_trace(module)

graph_drawer = passes.graph_drawer.FxGraphDrawer(traced_module, 'GraphBreakModule')
with open("graph.svg", "wb") as f:
    f.write(graph_drawer.get_dot_graph().create_svg())