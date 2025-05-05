from huggingface_hub import HfApi, ModelInfo, ModelCard
import re
import io
import sys
import ast
import json


def get_model_sample_code(model_id: str):
        """
        Fetches the sample code for a model from Hugging Face Hub.

        Returns:
        A dictionary containing the model ID and its sample code.
        """
#     try:
        card = ModelCard.load(model_id)
        model_card_str = card.content
        parse_text(model_card_str)
#     except Exception as e:
#         print(f"Error fetching sample code for {model_id}: {e}")
#         return None


def parse_text(card_text: str):
        # Find all Python code blocks
        code_blocks = re.findall(r'```python(.*?)```', card_text, re.DOTALL | re.IGNORECASE)
        # Search each block for a line containing 'input'
        for block in code_blocks:
            lines = block.strip().split('\n')
            for i, line in enumerate(lines):
                # Match the line containing 'input'
                if "encoded_input" in line:
                    # Only keep lines up to and including the 'input' assignment
                    output_lines = lines[:i + 1]
                    # Insert print statement for the variable assigned in the 'input' line
                    match = re.match(r'\s*(\w+)\s*=', line)
                    if match:
                        var_name = match.group(1)
                        # Add print statement
                        output_lines.append(f'print({var_name})')
                    else:
                        output_lines.append('# print statement could not be generated')
                    # Print the final code
                    print('\n'.join(output_lines))
                    # Capture the output of print statements
                    old_stdout = sys.stdout
                    sys.stdout = mystdout = io.StringIO()
                    try:
                            exec('\n'.join(output_lines), {})
                    except Exception as e:
                        print(f"Error during execution: {e}")
                    sys.stdout = old_stdout

                    # Save the captured output to temp.txt
                    with open('temp.txt', 'w') as f:
                        f.write(mystdout.getvalue())
                    return
        else:
            raise ValueError("No code block with an 'input' assignment found.")
