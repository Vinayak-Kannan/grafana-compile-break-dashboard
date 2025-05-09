import json
from typing import List, Optional
from dataclasses import dataclass
from dynamo_explain_parser import DynamoExplainData, BreakReason, CompileTime

@dataclass
class MockModelInfo:
    model_family: str
    model_name: str
    model_commit_hash: str

def load_mock_dynamo_explain_data(json_path: str) -> List[DynamoExplainData]:
    with open(json_path, 'r') as f:
        raw_data = json.load(f)

    def to_break_reason(d: dict) -> BreakReason:
        return BreakReason(**d)

    def to_compile_time(d: Optional[dict]) -> Optional[CompileTime]:
        if d is None:
            return None
        return CompileTime(**d)
    
    def to_model_info(d: dict) -> MockModelInfo:
        return MockModelInfo(**d)

    results = []
    model_infos = []
    for item in raw_data:
        model_info = to_model_info(item['model_info'])
        break_reasons = [to_break_reason(b) for b in item['break_reasons']]
        compile_times = to_compile_time(item.get('compile_times'))
        additional_data = item.get('additional_data', {})
        graphs = item.get('graphs', [])

        results.append(DynamoExplainData(
            graph_count=item['graph_count'],
            graph_break_count=item['graph_break_count'],
            op_count=item['op_count'],
            break_reasons=break_reasons,
            compile_times=compile_times,
            additional_data=additional_data,
            graphs=graphs
        ))

        model_infos.append(model_info)

    return results, model_infos