import pandas as pd
from collections import defaultdict
import os
import glob
import yaml


# ---------- Helpers ----------
def _safe_yaml_load(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def _safe_yaml_dump(path, data):
    dir_path = os.path.dirname(path)
    if dir_path:  # chỉ tạo folder khi dir_path không rỗng
        os.makedirs(dir_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)


def add_retrieval_rule(rule_file_path, retrieval_intent, rule_label=None):
    """
    Ensure a rule exists that maps the retrieval intent -> utter_<retrieval_intent>.

    retrieval_intent: e.g. "stocks_qna"
    resulting action: utter_stocks_qna
    rule_label: human-readable rule name (default: Trả lời Q&A từ <retrieval_intent>)
    """
    if rule_label is None:
        rule_label = f"Trả lời Q&A từ {retrieval_intent}"

    data = _safe_yaml_load(rule_file_path)

    # Normalize schema
    if not isinstance(data, dict):
        data = {}
    data.setdefault("version", "3.1")
    rules = data.get("rules", [])
    if rules is None:
        rules = []
    # Check if already present
    exists = False
    for r in rules:
        steps = r.get("steps", [])
        if (
            len(steps) == 2
            and steps[0].get("intent") == retrieval_intent
            and steps[1].get("action") == f"utter_{retrieval_intent}"
        ):
            exists = True
            # update rule label if user wants a new one
            r["rule"] = rule_label
            break

    if not exists:
        rules.append(
            {
                "rule": rule_label,
                "steps": [
                    {"intent": retrieval_intent},
                    {"action": f"utter_{retrieval_intent}"},
                ],
            }
        )

    data["rules"] = rules
    _safe_yaml_dump(rule_file_path, data)
    print(f"📘 Đã cập nhật rule cho intent '{retrieval_intent}' trong {rule_file_path}.")


# ---------- Main data generation ----------
def generate_rasa_data(file_path):
    """
    Đọc 1 file Excel (cột: Question, Answer) và sinh:
      - data/nlu/<file>_nlu.yml (retrieval NLU examples)
      - domain/responses/<file>_responses.yml (retrieval responses)
      - domain/intents/<file>_intents.yml (khai báo retrieval intent)
    Trả về tên retrieval intent (file_name).
    """
    df = pd.read_excel(file_path)
    intent_examples = defaultdict(list)
    responses = {}

    # Lấy tên file gốc không đuôi .xlsx
    file_name = os.path.splitext(os.path.basename(file_path))[0]

    responses_file_path = f"domain/responses/{file_name}_responses.yml"
    intents_file_path = f"domain/intents/{file_name}_intents.yml"
    nlu_file_path = f"data/nlu/{file_name}_nlu.yml"

    # Tạo mapping câu trả lời -> intent con (sub-intent)
    # retrieval intent chính = file_name (vd: stocks_qna)
    intent_mapping = {}
    intent_counter = 1

    for _, row in df.iterrows():
        question = str(row["Question"]).strip()
        answer = str(row["Answer"]).strip()

        if answer not in intent_mapping:
            intent_mapping[answer] = f"{file_name}/intent_{intent_counter}"
            intent_counter += 1

        intent_name = intent_mapping[answer]  # ví dụ: stocks_qna/intent_1
        utter_name = f"utter_{intent_name}"   # ví dụ: utter_stocks_qna/intent_1

        intent_examples[intent_name].append(question)
        responses[utter_name] = answer

    # ---- Ghi NLU file ----
    os.makedirs(os.path.dirname(nlu_file_path), exist_ok=True)
    with open(nlu_file_path, "w", encoding="utf-8") as f:
        f.write('version: "3.1"\n')
        f.write("nlu:\n")
        for intent, examples in intent_examples.items():
            f.write(f"- intent: {intent}\n  examples: |\n")
            for ex in examples:
                f.write(f"    - {ex}\n")

    # ---- Ghi responses file ----
    os.makedirs(os.path.dirname(responses_file_path), exist_ok=True)
    with open(responses_file_path, "w", encoding="utf-8") as f:
        f.write('version: "3.1"\n')
        f.write("responses:\n")
        for utter_name, text in responses.items():
            f.write(f"  {utter_name}:\n")
            # escape quotes in text
            safe_text = text.replace('"', '\\"')
            f.write(f'  - text: "{safe_text}"\n')

    # ---- Ghi intents file (khai báo retrieval intent chính) ----
    os.makedirs(os.path.dirname(intents_file_path), exist_ok=True)
    with open(intents_file_path, "w", encoding="utf-8") as f:
        f.write('version: "3.1"\n')
        f.write("intents:\n")
        f.write(f"  - {file_name}\n")  # retrieval intent chính

    print(f"✅ Đã tạo: {nlu_file_path}, {responses_file_path} và {intents_file_path}")

    return file_name  # trả về retrieval intent để dùng thêm rule


def process_all_excel_files(folder_path="docs", rule_file_path="rules.yml"):
    """
    Duyệt mọi file .xlsx trong folder, tạo dữ liệu Rasa, và cập nhật rules.yml.
    """
    excel_files = glob.glob(os.path.join(folder_path, "*.xlsx"))
    if not excel_files:
        print("⚠️ Không tìm thấy file Excel nào trong folder.")
        return

    for file_path in excel_files:
        print(f"🔄 Đang xử lý: {file_path}")
        retrieval_intent = generate_rasa_data(file_path)
        # Thêm rule tương ứng
        add_retrieval_rule(rule_file_path, retrieval_intent)

    print("🎉 Hoàn tất xử lý tất cả file Excel và cập nhật rules.")


# ------------ RUN ------------
# Ví dụ chạy
process_all_excel_files("docs", rule_file_path="data/rules.yml")
