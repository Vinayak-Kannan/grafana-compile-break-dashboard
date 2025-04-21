from inspect import FrameInfo
from traceback import FrameSummary
import torch
import torch.nn as nn
import torch._dynamo as dynamo
from torch._dynamo.output_graph import GraphCompileReason
from torch.fx import passes, symbolic_trace
from optimum.utils import DummyInputGenerator
from graphviz import Digraph, Source
from transformers import AutoImageProcessor, AutoModel
from PIL import Image
import requests

class GraphBreakVisualizer:
    def __init__(self, module, inputs):
        self.module = module
        self.inputs = inputs

        # Get dynamo explanation
        self.dynamo_explanation = dynamo.explain(module.forward)(**inputs)

        # Get FX graph
        self.traced_module = symbolic_trace(module)
        self.graph_drawer = passes.graph_drawer.FxGraphDrawer(self.traced_module, module.__class__.__name__, parse_stack_trace=True)


    def modify_node_style(self, node, tooltip: str):
        node['attributes']['fontcolor'] = '#880808'
        node['attributes']['tooltip'] = tooltip
        return node

    def format_break_reason(self, break_reason: GraphCompileReason):
        # Format the break reason string
        formatted_reason = break_reason.reason
        if "builtin: print" in formatted_reason:
            formatted_reason = f"Unsupported print statement. {formatted_reason}"

        if break_reason.user_stack:
            formatted_reason += "\n\nUser Stack:\n"
            for frame in break_reason.user_stack:
                formatted_reason += f"{frame.filename}:{frame.lineno}\n"
        return formatted_reason

    def align_graph_break_to_node(self, break_frame: list[FrameSummary], nodes: dict):
        target_file = break_frame[0].filename
        target_line = break_frame[0].lineno

        best_node_name = None
        best_dist = float('inf')
        best_node = None

        for node_name, node in nodes.items():
            if 'Stack Trace DEPRECATED' not in node[0]:
                continue

            stack_frames: list[FrameInfo] = node[0]['Stack Trace DEPRECATED']

            for stack_frame in stack_frames:
                if stack_frame.filename == target_file:
                    dist = abs(stack_frame.lineno - target_line)
                    if dist < best_dist:
                        best_dist = dist
                        best_node_name = node_name
                        best_node = node

        return best_node_name, best_node

    def create_visualization(self, output_path="enhanced_graph.svg"):
        # Get the original dot graph
        dot_graph = self.graph_drawer.get_dot_graph()

        # Create a new graph with the same properties
        enhanced_dot = Digraph(comment='Enhanced Graph with Break Points')
        enhanced_dot.attr(rankdir='TB')

        for break_reason in self.dynamo_explanation.break_reasons:
            user_stack = break_reason.user_stack
            best_node_name, _ = self.align_graph_break_to_node(user_stack, dot_graph.obj_dict['nodes'])
            tooltip_str = self.format_break_reason(break_reason)
            updated_node = self.modify_node_style(dot_graph.obj_dict['nodes'][best_node_name][0], tooltip_str)
            dot_graph.obj_dict['nodes'][best_node_name][0] = updated_node


        # Render the enhanced graph
        src = Source(str(dot_graph))
        src.render(output_path, format='svg', cleanup=True)

        return output_path


class GraphBreakModule(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear1 = nn.Linear(10, 20)
        self.linear2 = nn.Linear(20, 5)

    def forward(self, x):
        x = self.linear1(x)
        print("break")
        return self.linear2(x)

# HOPE
device = "cuda" if torch.cuda.is_available() else "cpu"

url = 'http://images.cocodataset.org/val2017/000000039769.jpg'
image = Image.open(requests.get(url, stream=True).raw)

processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
module = AutoModel.from_pretrained('facebook/dinov2-small')

inputs_model = processor(images=image, return_tensors="pt")
outputs = module(**inputs_model)
print(outputs)

# Usage
# module = GraphBreakModule()
# inputs = torch.randn(1, 10)
visualizer = GraphBreakVisualizer(module, inputs_model)
enhanced_graph_path = visualizer.create_visualization("actually_useful")
print(f"Enhanced graph created at: {enhanced_graph_path}")
