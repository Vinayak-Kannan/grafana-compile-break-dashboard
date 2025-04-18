import torch
import torchvision.models as models
from torch.fx import passes, symbolic_trace

model = models.resnet18()
model = symbolic_trace(model)

g = passes.graph_drawer.FxGraphDrawer(model, 'resnet50')
with open("a.svg", "wb") as f:
    f.write(g.get_dot_graph().create_svg())