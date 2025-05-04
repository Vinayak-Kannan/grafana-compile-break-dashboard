from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
from datetime import datetime
import torch
from torch._dynamo.backends.debugging import ExplainOutput
import html

@dataclass
class BreakReason:
    number: int
    reason: str
    user_stack: List[str]

@dataclass
class CompileTime:
    total_time: float
    details: Dict[str, List[float]]

@dataclass
class DynamoExplainData:
    graph_count: int
    graph_break_count: int
    op_count: int
    break_reasons: List[BreakReason]
    compile_times: Optional[CompileTime] = None
    # Extensible field for additional data
    additional_data: Dict[str, Any] = None
    graphs: List[str] = None

    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}

class DynamoExplainParser:
    @staticmethod
    def parse_explain_output(explain_output: ExplainOutput) -> DynamoExplainData:
        """Parse the ExplainOutput object from torch._dynamo.explain()"""

        graphs = []
        for graph in explain_output.graphs:
            graphs.append(graph.print_readable())
        
        graph_count = explain_output.graph_count
        graph_break_count = explain_output.graph_break_count
        op_count = explain_output.op_count
        
        break_reasons = []
        for idx, break_reason in enumerate(explain_output.break_reasons):
            reason = html.escape(break_reason.reason)
            user_stack = [html.escape(str(frame)) for frame in break_reason.user_stack]
            break_reasons.append(BreakReason(idx+1, reason, user_stack))
        
        compile_times = None
        if explain_output.compile_times is not None:
            compile_time_str = explain_output.compile_times
            total_time = 0.0
            details = {}
            
            # Split into lines and parse each function's runtimes
            lines = compile_time_str.split('\n')
            if len(lines) >= 3:  # Skip header lines
                for line in lines[2:]:
                    parts = line.split(',')
                    if len(parts) > 1:
                        func_name = parts[0].strip()
                        runtimes = [float(t.strip()) for t in parts[1:]]
                        details[func_name] = runtimes
                        total_time += sum(runtimes)
            
            compile_times = CompileTime(total_time, details)
        
        # Create the data object
        data = DynamoExplainData(
            graph_count=graph_count,
            graph_break_count=graph_break_count,
            op_count=op_count,
            break_reasons=break_reasons,
            compile_times=compile_times,
            graphs=graphs
        )
        
        # Add ops_per_graph if available
        if explain_output.ops_per_graph is not None:
            ops_per_graph = []
            for ops in explain_output.ops_per_graph:
                ops_per_graph.append([html.escape(str(op)) for op in ops])
            data.additional_data['ops_per_graph'] = ops_per_graph
        
        # Add out_guards if available
        if explain_output.out_guards is not None:
            out_guards = [html.escape(str(guard)) for guard in explain_output.out_guards]
            data.additional_data['out_guards'] = out_guards
        
        return data
    
    # @staticmethod
    # def parse_from_file(file_path: str) -> DynamoExplainData:
    #     """Parse ExplainOutput from a file (legacy method)"""
    #     with open(file_path, 'r') as f:
    #         return DynamoExplainParser.parse_explain_output_text(f.read())
    
    # @staticmethod
    # def parse_explain_output_text(output_str: str) -> DynamoExplainData:
    #     """Parse the string output from torch._dynamo.explain() (legacy method)"""
        
    #     # Extract basic counts
    #     graph_count = int(re.search(r"Graph Count: (\d+)", output_str).group(1))
    #     graph_break_count = int(re.search(r"Graph Break Count: (\d+)", output_str).group(1))
    #     op_count = int(re.search(r"Op Count: (\d+)", output_str).group(1))
        
    #     # Parse break reasons
    #     break_reasons = []
    #     break_reason_pattern = r"Break Reason (\d+):\n\s+Reason: (.*?)\n\s+User Stack:\n((?:\s+.*\n)*)"
    #     for match in re.finditer(break_reason_pattern, output_str, re.DOTALL):
    #         number = int(match.group(1))
    #         reason = match.group(2).strip()
    #         stack = [line.strip() for line in match.group(3).split('\n') if line.strip()]
    #         break_reasons.append(BreakReason(number, reason, stack))
        
    #     # Parse compile times if available
    #     compile_times = None
    #     if "Compile Times:" in output_str:
    #         compile_time_str = re.search(r"Compile Times: (.*?)(?:\n|$)", output_str).group(1)
    #         # Parse the compile time string into a structured format
    #         total_time = 0.0
    #         details = {}
    #         for line in compile_time_str.split(';'):
    #             if ':' in line:
    #                 name, time = line.split(':')
    #                 time_val = float(time.strip())
    #                 details[name.strip()] = time_val
    #                 total_time += time_val
    #         compile_times = CompileTime(total_time, details)
        
    #     # Create the data object
    #     data = DynamoExplainData(
    #         graph_count=graph_count,
    #         graph_break_count=graph_break_count,
    #         op_count=op_count,
    #         break_reasons=break_reasons,
    #         compile_times=compile_times
    #     )
        
    #     # Parse ops_per_graph if available
    #     if "Ops per Graph:" in output_str:
    #         ops_per_graph = []
    #         ops_pattern = r"Ops (\d+):\n((?:\s+.*\n)*)"
    #         for match in re.finditer(ops_pattern, output_str, re.DOTALL):
    #             ops = [line.strip() for line in match.group(2).split('\n') if line.strip()]
    #             ops_per_graph.append(ops)
    #         if ops_per_graph:
    #             data.additional_data['ops_per_graph'] = ops_per_graph
        
    #     # Parse out_guards if available
    #     if "Out Guards:" in output_str:
    #         out_guards = []
    #         guards_pattern = r"Guard (\d+):\n\s+(.*?)(?=\n\s+Guard|\Z)"
    #         for match in re.finditer(guards_pattern, output_str, re.DOTALL):
    #             guard = match.group(2).strip()
    #             out_guards.append(guard)
    #         if out_guards:
    #             data.additional_data['out_guards'] = out_guards
        
    #     return data
    
    @staticmethod
    def add_custom_data(data: DynamoExplainData, key: str, value: Any) -> None:
        """Add custom data to the parsed output"""
        data.additional_data[key] = value 