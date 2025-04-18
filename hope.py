import torch
import torch.nn as nn
import torch._dynamo as dynamo
from torch.fx import passes, symbolic_trace
import re
from graphviz import Digraph, Source


"""
import torch
from torch.fx import symbolic_trace, Tracer

# Define your model
class MyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(10, 5)

    def forward(self, x):
        return self.linear(x)

# Instantiate the model
model = MyModel()

# Create a custom tracer with stack trace recording enabled
class CustomTracer(Tracer):
    def __init__(self):
        super().__init__()
        self.record_stack_traces = True  # Enable stack trace recording

# Use the custom tracer for symbolic tracing
tracer = CustomTracer()
graph = tracer.trace(model)

# Wrap the graph into a GraphModule
graph_module = torch.fx.GraphModule(model, graph)

# Access a node's stack trace
for node in graph.nodes:
    print(f"Node: {node.name}, Stack Trace: {node.stack_trace}")
"""

class GraphBreakVisualizer:
    def __init__(self, module, inputs):
        self.module = module
        self.inputs = inputs

        # Get dynamo explanation
        self.dynamo_explanation = dynamo.explain(module.forward)(inputs)

        # Get FX graph
        self.traced_module = symbolic_trace(module)
        self.graph_drawer = passes.graph_drawer.FxGraphDrawer(
            self.traced_module, module.__class__.__name__)

    def create_visualization(self, output_path="enhanced_graph.svg"):
        # Get the original dot graph
        dot_graph = self.graph_drawer.get_dot_graph()
        # Different ways to access the source depending on the graphviz implementation
        try:
            # For Python graphviz package
            if hasattr(dot_graph, 'source'):
                dot_source = dot_graph.source
            # For pydot implementation
            elif hasattr(dot_graph, 'to_string'):
                dot_source = dot_graph.to_string()
            # Try string representation
            else:
                dot_source = str(dot_graph)
        except AttributeError:
            # Fall back to getting raw representation
            dot_source = repr(dot_graph)

        # Create a new graph with the same properties
        enhanced_dot = Digraph(comment='Enhanced Graph with Break Points')
        enhanced_dot.attr(rankdir='TB')

        # Extract break information
        # Extract break locations
        break_locations = set()
        for reason in self.dynamo_explanation.break_reasons:
            if hasattr(reason, 'user_stack'):
                for frame in reason.user_stack:
                    break_locations.add((frame.filename, frame.lineno))

        print(f"Break locations: {break_locations}")
        # Map FX nodes to break locations
        break_nodes = set()
        for node in self.traced_module.graph.nodes:
            print(dir(node))
            print(node.stack_trace)
            if node.stack_trace:
                for frame in node.stack_trace:
                    print(frame)
                    loc = (frame.filename, frame.lineno)
                    if loc in break_locations:
                        break_nodes.add(node.name)

        print(f"Break nodes: {break_nodes}")

        # Parse the original dot source to extract nodes and edges
        node_pattern = re.compile(r'(\w+)\s+\[([^\]]+)\]')
        edge_pattern = re.compile(r'(\w+)\s+->\s+(\w+)')

        # Find nodes with potential breaks
        break_nodes = []
        for reason in break_reasons:
            if hasattr(reason, 'user_stack'):
                for frame in reason.user_stack:
                    # Look for code location information in the frame
                    if hasattr(frame, 'line_no') and hasattr(frame, 'code'):
                        # Match this with node information
                        break_nodes.append((frame.line_no, frame.code))

        # Modify nodes in the dot source to highlight breaks
        lines = dot_source.split('\n')
        print(lines)
        for i, line in enumerate(lines):
            node_match = node_pattern.search(line)
            if node_match:
                node_name = node_match.group(1)
                attrs = node_match.group(2)

                # Check if this node corresponds to a break point
                is_break_node = False
                for line_no, code in break_nodes:
                    if str(line_no) in line or code in line:
                        is_break_node = True
                        break

                if is_break_node:
                    # Highlight break nodes in red
                    lines[i] = f'{node_name} [{attrs}, fillcolor=red, style=filled]'

        # Create a new dot source with the modifications
        modified_source = '\n'.join(lines)

        # Render the enhanced graph
        src = Source(modified_source)
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

# Usage
module = GraphBreakModule()
inputs = torch.randn(1, 10)
visualizer = GraphBreakVisualizer(module, inputs)
enhanced_graph_path = visualizer.create_visualization()
print(f"Enhanced graph created at: {enhanced_graph_path}")
