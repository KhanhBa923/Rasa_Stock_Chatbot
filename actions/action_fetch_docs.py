from typing import Any, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import EventType

from .doc_retriever import semantic_search


MAX_ANSWER_CHARS = 600  # tránh trả lời quá dài; cắt gọn


class ActionSearchDoc(Action):
    def name(self) -> str:
        return "action_search_doc"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any],
    ) -> List[EventType]:
        user_msg = tracker.latest_message.get("text", "").strip()
        if not user_msg:
            dispatcher.utter_message(text="Bạn vui lòng nhập câu hỏi.")
            return []

        results = semantic_search(user_msg, top_k=5, score_threshold=0.35)

        if not results:
            # không tìm thấy gì đủ giống -> utter_default hoặc fallback
            dispatcher.utter_message(text="Xin lỗi, mình không tìm được thông tin trong tài liệu.")
            return []

        # lấy top 1
        score, chunk_text, meta = results[0]

        # cắt gọn cho gọn UI
        answer = chunk_text[:MAX_ANSWER_CHARS].strip()
        if len(chunk_text) > MAX_ANSWER_CHARS:
            answer += " ..."

        # thêm nguồn (file + chunk)
        src = meta.get("source", "tài liệu")
        dispatcher.utter_message(text=f"{answer}\n\n(Nguồn: {src})")
        return []
