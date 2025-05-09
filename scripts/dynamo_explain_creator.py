import os
import pickle
import torch
from transformers import AutoModel
from dynamo_explain_parser import DynamoExplainParser, DynamoExplainData

import torch._dynamo as dynamo

INPUTS_DIR = "inputs"
OUTPUT_DIR = "dynamo_explain_output"

os.makedirs(OUTPUT_DIR, exist_ok=True)
subdirs = os.listdir(INPUTS_DIR)

for subdir in subdirs:
        files = os.listdir(os.path.join(INPUTS_DIR, subdir))
        for file in files:
                if file.endswith(".pkl"):
                        input_path = os.path.join(root, file)
                        # Unpickle the inputs
                        with open(input_path, "rb") as f:
                                model_inputs = pickle.load(f)

                        model_name = file.replace(".pkl", "").replace("--", "/")
                        print("Model name:", model_name)
                        if model_name == "HuggingFaceTB/SmolVLM2-256M-Video-Instruct":
                                continue

                        # Load the model
                        try:
                                        model = AutoModel.from_pretrained(model_name, trust_remote_code=True)
                        except Exception:
                                        from transformers import (
                                                        AutoModelForCausalLM,
                                                        AutoModelForSeq2SeqLM,
                                                        AutoModelForMaskedLM,
                                                        AutoModelForTokenClassification,
                                                        AutoModelForSequenceClassification,
                                                        AutoModelForQuestionAnswering,
                                                        AutoModelForImageClassification,
                                                        AutoModelForVision2Seq,
                                                        AutoModelForSpeechSeq2Seq,
                                                        AutoModelForAudioClassification,
                                                        AutoModelForCTC,
                                                        AutoModelForImageTextToText,
                                                        RTDetrForObjectDetection,
                                                        VitPoseForPoseEstimation,
                                                        AutoProcessor,
                                                        AutoImageProcessor,
                                                        Dinov2Model

                                        )
                                        auto_model_classes = [
                                                        AutoModelForCausalLM,
                                                        AutoModelForSeq2SeqLM,
                                                        AutoModelForMaskedLM,
                                                        AutoModelForTokenClassification,
                                                        AutoModelForSequenceClassification,
                                                        AutoModelForQuestionAnswering,
                                                        AutoModelForImageClassification,
                                                        AutoModelForVision2Seq,
                                                        AutoModelForSpeechSeq2Seq,
                                                        AutoModelForAudioClassification,
                                                        AutoModelForCTC,
                                                        AutoModelForImageTextToText,
                                                        RTDetrForObjectDetection,
                                                        VitPoseForPoseEstimation,
                                                        AutoProcessor,
                                                        AutoImageProcessor,
                                                        Dinov2Model
                                        ]
                                        model = None
                                        for AutoModelClass in auto_model_classes:
                                                        try:
                                                                        model = AutoModelClass.from_pretrained(model_name, trust_remote_code=True)
                                                                        break
                                                        except Exception:
                                                                        continue
                                        if model is None:
                                                        raise RuntimeError(f"Could not load any supported AutoModel for {model_name}")
                        model.eval()

                        # Run dynamo.explain
                        try:
                                explain_output = dynamo.explain(model)(**model_inputs)
                        except Exception as e:
                                print("Error occurred while explaining model:", e)
                                continue

                        print("Number of break reasons:", len(explain_output.break_reasons))
                        if len(explain_output.break_reasons) == 0:
                                continue

                        data = DynamoExplainParser.parse_explain_output(explain_output)

                        # Save the explain output
                        output_file = os.path.splitext(file)[0] + "_dynamo_explain.pkl"
                        output_path = os.path.join(OUTPUT_DIR, output_file)
                        with open(output_path, "wb") as f:
                                pickle.dump(data, f)
