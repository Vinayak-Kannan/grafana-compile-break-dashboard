from dynamo_explain_parser import DynamoExplainParser
from dynamo_explain_viewer import DynamoExplainViewer
import torch
import torch._dynamo as dynamo

def main():
    # Example 1: Parse directly from ExplainOutput object
    def example_model(x):
        return torch.nn.functional.relu(x)
    
    x = torch.randn(10, 10)
    
    explanation = dynamo.explain(example_model)(x)
    
    data = DynamoExplainParser.parse_explain_output(explanation)
    
    # Example 2: Add custom data (demonstrating extensibility)
    DynamoExplainParser.add_custom_data(data, 'analysis_timestamp', '2024-04-04')
    DynamoExplainParser.add_custom_data(data, 'model_name', 'example_model')
    
    # Generate and view the HTML report
    DynamoExplainViewer.view_explain_output(data)
    
    # Example 3: Legacy method - parse from a file (if you have saved the output)
    # data_from_file = DynamoExplainParser.parse_from_file('dynamo_explanation.txt')
    # DynamoExplainViewer.view_explain_output(data_from_file, "dynamo_explain_view_from_file.html")

if __name__ == "__main__":
    main() 