import pandas as pd
from collections import defaultdict
import os

def generate_rasa_data(file_path):
    df = pd.read_excel(file_path)
    intent_examples = defaultdict(list)
    responses = {}

    # Lấy tên file gốc không đuôi .xlsx
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    responses_file_path = f"domain/responses/{file_name}_responses.yml"
    intents_file_path = f"domain/intents/{file_name}_intents.yml"
    nlu_file_path = f"data/nlu/{file_name}_nlu.yml"

    # Tạo mapping câu trả lời -> intent
    intent_mapping = {}
    intent_counter = 1

    for _, row in df.iterrows():
        question = str(row["Question"]).strip()
        answer = str(row["Answer"]).strip()

        if answer not in intent_mapping:
            intent_mapping[answer] = f"{file_name}/intent_{intent_counter}"
            intent_counter += 1

        intent_name = intent_mapping[answer]
        utter_name = f"utter_{intent_name}"  # tương ứng retrieval intent

        intent_examples[intent_name].append(question)
        responses[utter_name] = answer

    # Tạo NLU file
    os.makedirs(os.path.dirname(nlu_file_path), exist_ok=True)
    with open(nlu_file_path, "w", encoding="utf-8") as f:
        f.write("version: \"3.1\"\nnlu:\n")
        for intent, examples in intent_examples.items():
            f.write(f"- intent: {intent}\n  examples: |\n")
            for ex in examples:
                f.write(f"    - {ex}\n")

    # Tạo responses file
    os.makedirs(os.path.dirname(responses_file_path), exist_ok=True)
    with open(responses_file_path, "w", encoding="utf-8") as f:
        f.write("version: \"3.1\"\nresponses:\n")
        for utter_name, text in responses.items():
            f.write(f"  {utter_name}:\n")
            f.write(f"  - text: \"{text}\"\n")

    # Tạo intents file
    os.makedirs(os.path.dirname(intents_file_path), exist_ok=True)
    with open(intents_file_path, "w", encoding="utf-8") as f:
        f.write("version: \"3.1\"\nintents:\n")
        f.write(f"  - {file_name}\n")  # retrieval intent chính

    print(f"✅ Đã tạo: {nlu_file_path}, {responses_file_path} và {intents_file_path}")

# Gọi hàm
generate_rasa_data("input_file/stocks_qna.xlsx")
