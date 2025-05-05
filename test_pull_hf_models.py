import json
import os
import pytest

tmp_dir = None

import pull_hf_models
from dynamo_explain_parser import BreakReason, DynamoExplainData

@pytest.fixture(autouse=True)
def isolate_filesystem(tmp_path, monkeypatch):
    # Redirect state and output files to tmp_path
    monkeypatch.setattr(pull_hf_models, 'STATE_FILE', str(tmp_path / 'state.json'))
    monkeypatch.setattr(pull_hf_models, 'OUTPUT_FILE', str(tmp_path / 'out.json'))
    # Ensure pull_hf_models writes into tmp_path
    # Change cwd during test
    monkeypatch.chdir(tmp_path)
    return tmp_path

@pytest.fixture
def patch_pipeline(monkeypatch):
    # Provide dummy model list
    monkeypatch.setattr(pull_hf_models, 'fetch_top_models', lambda n: ['model1', 'model2'])
    # Dummy commits
    monkeypatch.setattr(pull_hf_models, 'get_latest_commit', lambda mid: f'sha-{mid}')
    # Dummy analyze outputs: one break reason per model
    def fake_analyze(mid):
        br = BreakReason(number=1, reason=f'reason-{mid}', user_stack=[f'frame-{mid}'])
        data = DynamoExplainData(
            graph_count=1,
            graph_break_count=1,
            op_count=5,
            break_reasons=[br],
            compile_times=None,
            additional_data={},
            graphs=[]
        )
        return data
    monkeypatch.setattr(pull_hf_models, 'analyze_model_raw', fake_analyze)
    # Capture record and flush calls
    record_calls = []
    def fake_record(model, commit, reason):
        record_calls.append((model, commit, reason))
    monkeypatch.setattr(pull_hf_models, 'record', fake_record)
    flush_calls = []
    def fake_flush(grouping_key=None):
        flush_calls.append(grouping_key)
    monkeypatch.setattr(pull_hf_models, 'flush', fake_flush)
    return record_calls, flush_calls

def test_scheduled_scan_writes_state_and_output(isolate_filesystem, patch_pipeline):
    record_calls, flush_calls = patch_pipeline
    # Run scheduled scan on top-2 models
    pull_hf_models.scheduled_scan(2)
    # Check state file
    assert os.path.exists('state.json')
    state = json.load(open('state.json'))
    assert state == {'model1': 'sha-model1', 'model2': 'sha-model2'}
    # Check output file
    assert os.path.exists('out.json')
    out = json.load(open('out.json'))
    # Should contain entries for both models
    assert set(out.keys()) == {'model1', 'model2'}
    # Verify JSON structure matches DynamoExplainData dataclass
    for mid, entry in out.items():
        assert entry['graph_count'] == 1
        assert entry['break_reasons'][0]['reason'] == f'reason-{mid}'
    # Verify record and flush called correctly
    assert record_calls == [('model1', 'sha-model1', 'reason-model1'),
                              ('model2', 'sha-model2', 'reason-model2')]
    # flush called once per model with grouping_key
    assert flush_calls == [ {'model': 'model1', 'commit': 'sha-model1'},
                             {'model': 'model2', 'commit': 'sha-model2'} ]

def test_single_scan_prints_models(capsys, isolate_filesystem):
    # Patch fetch_top_models to known list
    pull_hf_models.fetch_top_models = lambda n: ['A', 'B', 'C']
    pull_hf_models.single_scan(3)
    captured = capsys.readouterr()
    # Expect lines ' 1. A', ' 2. B', ' 3. C'
    assert ' 1. A' in captured.out
    assert ' 2. B' in captured.out
    assert ' 3. C' in captured.out

@pytest.mark.watch
def test_watch_loop_once(monkeypatch, isolate_filesystem, patch_pipeline):
    # Run watch_loop but break after first iteration
    calls = []
    def fake_sleep(seconds):
        raise KeyboardInterrupt
    monkeypatch.setattr(pull_hf_models, 'fetch_top_models', lambda n: ['X'])
    monkeypatch.setattr(pull_hf_models, 'get_latest_commit', lambda mid: 'sha-X')
    def fake_analyze(mid):
        # record call to show it was invoked
        calls.append(mid)
        return patch_pipeline[0][0]  # not used
    monkeypatch.setattr(pull_hf_models, 'analyze_model_raw', fake_analyze)
    monkeypatch.setattr(pull_hf_models, 'record', lambda *args, **kwargs: None)
    monkeypatch.setattr(pull_hf_models, 'flush', lambda *args, **kwargs: None)
    monkeypatch.setattr(pull_hf_models, 'time', type('t',(),{'sleep': fake_sleep}))
    with pytest.raises(KeyboardInterrupt):
        pull_hf_models.watch_loop(1, interval=1)
    # Ensure analyze_model_raw was called for 'X'
    assert 'X' in calls