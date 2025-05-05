from dynamo_explain_parser import DynamoExplainData
import json
from pathlib import Path
import webbrowser
import os
from jinja2 import Environment, FileSystemLoader

class DynamoExplainViewer:
    @staticmethod
    def generate_html(data: DynamoExplainData, output_path: str = "dynamo_explain_view.html") -> str:
        """Generate an HTML page with the parsed data"""
        
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("dynamo_explain_template.html")
        
        # Generate break reasons rows
        break_reasons_rows = ""
        for br in data.break_reasons:
            stack_html = "<div class='stack-trace'>" + "<br>".join(br.user_stack) + "</div>"
            break_reasons_rows += f"""
                <tr>
                    <td>{br.number}</td>
                    <td>{br.reason}</td>
                    <td>{stack_html}</td>
                </tr>
            """
        
        # Generate compile times HTML if available
        compile_times_html = ""
        if data.compile_times:
            compile_times_html = f"""
                <div class="summary-item">Total Compile Time: {data.compile_times.total_time}s</div>
                <div class="summary-item">Compile Time Details:</div>
                <ul>
            """
            for name, times in data.compile_times.details.items():
                compile_times_html += f"<li>{name}: {', '.join([f'{t}' for t in times])}s</li>"
            compile_times_html += "</ul>"
        
        # Generate ops per graph HTML if available
        ops_per_graph_html = ""
        if 'ops_per_graph' in data.additional_data and data.additional_data['ops_per_graph']:
            ops_per_graph = data.additional_data['ops_per_graph']
            for i, ops in enumerate(ops_per_graph):
                ops_per_graph_html += f"<h3>Ops {i+1}</h3>"
                ops_per_graph_html += "<div class='stack-trace'>"
                for op in ops:
                    ops_per_graph_html += f"<div>{op}</div>"
                ops_per_graph_html += "</div>"
        else:
            ops_per_graph_html = "<p>No operations per graph data available.</p>"
        
        # Generate out guards HTML if available
        out_guards_html = ""
        if 'out_guards' in data.additional_data and data.additional_data['out_guards']:
            out_guards = data.additional_data['out_guards']
            out_guards_html += "<table>"
            out_guards_html += "<thead><tr><th>#</th><th>Guard</th></tr></thead><tbody>"
            for i, guard in enumerate(out_guards):
                out_guards_html += f"<tr><td>Guard {i+1}</td><td>{guard}</td></tr>"
            out_guards_html += "</tbody></table>"
        else:
            out_guards_html = "<p>No out guards data available.</p>"
        
        # Generate additional data HTML
        additional_data_html = ""
        if data.additional_data:
            additional_data_html += "<table>"
            additional_data_html += "<thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>"
            for key, value in data.additional_data.items():
                if key not in ['ops_per_graph', 'out_guards']:  # Skip these as they're handled separately
                    additional_data_html += f"<tr><td>{key}</td><td>{value}</td></tr>"
            additional_data_html += "</tbody></table>"
        else:
            additional_data_html = "<p>No additional data available.</p>"
        
        # Generate graphs HTML if available
        graphs_html = ""
        if data.graphs and len(data.graphs) > 0:
            graphs_html = "<div class='graphs-container'>"
            for i, graph in enumerate(data.graphs):
                graphs_html += f"""
                    <div class="graph-item">
                        <h3>Graph {i+1}</h3>
                        <pre class="graph-content">{graph}</pre>
                    </div>
                """
            graphs_html += "</div>"
        else:
            graphs_html = "<p>No graph data available.</p>"
        
        # Render the template with Jinja2
        html_content = template.render(
            graph_count=data.graph_count,
            graph_break_count=data.graph_break_count,
            op_count=data.op_count,
            break_reasons_rows=break_reasons_rows,
            compile_times_html=compile_times_html,
            ops_per_graph_html=ops_per_graph_html,
            out_guards_html=out_guards_html,
            additional_data_html=additional_data_html,
            graphs_html=graphs_html
        )
        
        # Write to file
        output_path = os.path.join(os.path.dirname(__file__), "templates", output_path)
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        return output_path
    
    @staticmethod
    def view_explain_output(data: DynamoExplainData, output_path: str = "dynamo_explain_view.html", auto_open: bool = True) -> str:
        """Generate and optionally open the HTML view"""
        output_path = DynamoExplainViewer.generate_html(data, output_path)
        if auto_open:
            webbrowser.open('file://' + str(Path(output_path).absolute()))
        return output_path