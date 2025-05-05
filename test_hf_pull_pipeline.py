import os
import torch
import pytest

# Stub out Dynamo viewer and parser globally to avoid UI in tests
from dynamo_explain_viewer import DynamoExplainViewer
DynamoExplainViewer.view_explain_output = lambda data: None

from dynamo_explain_parser import DynamoExplainParser
DynamoExplainParser.parse_explain_output = lambda explanation: {'parsed': True, 'raw': explanation}

# Import the function to test
from analyze_model import analyze_model

@pytest.fixture
def patch_dependencies(monkeypatch):
    """
    Monkey-patch external dependencies to make analyze_model fast and testable:
    - Transformers AutoModel.from_pretrained
    - torch._dynamo.explain
    """
    # Dummy model that stores calls
    class DummyModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.forward_called = False
        def forward(self, **kwargs):
            self.forward_called = True
            # Return a simple tensor
            return torch.tensor([[42.0]])

    dummy_model = DummyModel()

    # Monkey-patch AutoModel.from_pretrained to return the dummy model
    import pull_model_run_dynamo_explain
    monkeypatch.setattr(
        'pull_model_run_dynamo_explain.AutoModel.from_pretrained',
        lambda model_id: dummy_model
    )

    # Monkey-patch torch._dynamo.explain to wrap the function normally
    import torch._dynamo as dynamo
    monkeypatch.setattr(
        'torch._dynamo.explain',
        lambda fn: (lambda **kwargs: fn(**kwargs))
    )

    yield

@pytest.mark.usefixtures("patch_dependencies")
def test_analyze_model_creates_file_and_parses(tmp_path):
    """
    Test that analyze_model:
      - Creates the explanation text file in the provided directory
    """
    model_id = 'dummy-model'
    inputs = {'input_ids': torch.ones(1, 3, dtype=torch.long)}
    analyze_model(model_id, inputs=inputs, output_dir=str(tmp_path))

    expected_file = tmp_path / f"{model_id.replace('/', '_')}_dynamo_explanation.txt"
    assert expected_file.exists()
    content = expected_file.read_text()
    assert 'tensor' in content.lower()

@pytest.mark.usefixtures("patch_dependencies")
def test_analyze_model_output_metrics(tmp_path):
    """
    Test that analyze_model runs without error and writes output file.
    """
    model_id = 'dummy-model'
    inputs = {'input_ids': torch.ones(1, 2, dtype=torch.long)}
    analyze_model(model_id, inputs=inputs, output_dir=str(tmp_path))
    file = tmp_path / f"{model_id.replace('/', '_')}_dynamo_explanation.txt"
    assert file.exists()

@pytest.mark.integration
def test_analyze_model_integration(tmp_path):
    """
    Integration test: run analyze_model on a real but small HF model to produce an explanation file.
    """
    model_id = 'prajjwal1/bert-tiny'
    # Use minimal dummy inputs for the real model
    inputs = {'input_ids': torch.ones(1, 10, dtype=torch.long)}
    analyze_model(model_id, inputs=inputs, output_dir=str(tmp_path))

    expected_file = tmp_path / f"{model_id.replace('/', '_')}_dynamo_explanation.txt"
    assert expected_file.exists(), f"Expected file {expected_file} for real model"


