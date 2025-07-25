from typing import Any, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import EventType
import logging

from .doc_retriever import smart_retrieve, retrieve_answer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_ANSWER_CHARS = 500  # Giảm xuống vì thông tin đã được trích xuất chính xác hơn


class ActionSearchDoc(Action):
    _call_count = 0  # đếm số lần action được gọi

    def name(self) -> str:
        return "action_search_doc"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any],
    ) -> List[EventType]:
        # Đếm số lần action được gọi
        ActionSearchDoc._call_count += 1
        logger.info(f"ActionSearchDoc called {ActionSearchDoc._call_count} times")

        user_msg = tracker.latest_message.get("text", "").strip()
        logger.info(f"User message: {user_msg}")

        if not user_msg:
            dispatcher.utter_message(text="Bạn vui lòng nhập câu hỏi.")
            return []

        try:
            # Sử dụng smart_retrieve để có kết quả tốt nhất
            results = smart_retrieve(user_msg, top_k=3, score_threshold=0.30)
            logger.info(f"Smart search results: {len(results)} chunks")

            if not results:
                # Thử với ngưỡng thấp hơn nếu không tìm thấy
                results = smart_retrieve(user_msg, top_k=3, score_threshold=0.20)
                logger.info(f"Fallback search results: {len(results)} chunks")

            if not results:
                dispatcher.utter_message(
                    text="Xin lỗi, mình không tìm được thông tin liên quan trong tài liệu. "
                         "Bạn có thể thử diễn đạt câu hỏi khác không?"
                )
                return []

            # Lấy kết quả tốt nhất
            score, extracted_text, meta = results[0]
            source_file = meta.get('filename', meta.get('file', 'tài liệu'))
            extraction_method = meta.get('extraction_method', 'unknown')
            
            logger.info(f"Best score: {score:.4f}, Source: {source_file}, Method: {extraction_method}")

            # Xử lý câu trả lời
            answer = self._format_answer(extracted_text, score)
            
            # Tạo thông tin nguồn
            source_info = self._format_source_info(source_file, score, extraction_method)
            
            # Kiểm tra xem có kết quả khác có thể hữu ích không
            additional_info = self._get_additional_info(results[1:] if len(results) > 1 else [])

            # Gửi câu trả lời
            final_response = f"{answer}\n\n{source_info}"
            if additional_info:
                final_response += f"\n\n{additional_info}"

            dispatcher.utter_message(text=final_response)

        except Exception as e:
            logger.error(f"Error in ActionSearchDoc: {e}")
            dispatcher.utter_message(
                text="Xin lỗi, đã có lỗi xảy ra khi tìm kiếm thông tin. "
                     "Vui lòng thử lại sau."
            )

        return []

    def _format_answer(self, text: str, score: float) -> str:
        """
        Format câu trả lời, cắt gọn nếu cần và thêm độ tin cậy.
        """
        # Cắt gọn nếu quá dài
        if len(text) > MAX_ANSWER_CHARS:
            # Tìm điểm cắt tự nhiên (cuối câu)
            truncated = text[:MAX_ANSWER_CHARS]
            last_sentence_end = max(
                truncated.rfind('.'),
                truncated.rfind('!'),
                truncated.rfind('?')
            )
            
            if last_sentence_end > MAX_ANSWER_CHARS * 0.7:  # Nếu tìm được điểm cắt tốt
                text = truncated[:last_sentence_end + 1]
            else:
                text = truncated.rstrip() + "..."

        # Thêm độ tin cậy nếu thấp
        if score < 0.4:
            confidence_note = " (Thông tin có thể không hoàn toàn chính xác)"
            text += confidence_note

        return text.strip()

    def _format_source_info(self, source_file: str, score: float, method: str) -> str:
        """
        Tạo thông tin nguồn với độ tin cậy.
        """
        # Làm sạch tên file
        if '/' in source_file or '\\' in source_file:
            source_file = source_file.split('/')[-1].split('\\')[-1]

        # Thêm thông tin độ tin cậy
        if score >= 0.7:
            confidence = "Rất tin cậy"
        elif score >= 0.5:
            confidence = "Tin cậy"
        elif score >= 0.3:
            confidence = "Khá tin cậy"
        else:
            confidence = "Độ tin cậy thấp"

        return f"📄 *Nguồn: {source_file}* | *Độ tin cậy: {confidence}*"

    def _get_additional_info(self, other_results: List) -> str:
        """
        Tạo thông tin bổ sung từ các kết quả khác nếu có.
        """
        if not other_results or len(other_results) == 0:
            return ""

        # Kiểm tra xem có kết quả nào khác có điểm cao không
        high_score_results = [r for r in other_results if r[0] >= 0.4]
        
        if not high_score_results:
            return ""

        # Lấy thông tin từ kết quả tốt nhất thứ 2
        score, text, meta = high_score_results[0]
        source_file = meta.get('filename', meta.get('file', 'tài liệu khác'))
        
        if '/' in source_file or '\\' in source_file:
            source_file = source_file.split('/')[-1].split('\\')[-1]

        # Rút gọn thông tin bổ sung
        additional_text = text[:150].strip()
        if len(text) > 150:
            additional_text += "..."

        return f"💡 *Thông tin bổ sung từ {source_file}:*\n{additional_text}"


class ActionSearchDocDetailed(Action):
    """
    Action trả về thông tin chi tiết hơn với nhiều nguồn.
    """
    
    def name(self) -> str:
        return "action_search_doc_detailed"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[str, Any],
    ) -> List[EventType]:
        user_msg = tracker.latest_message.get("text", "").strip()
        logger.info(f"Detailed search for: {user_msg}")

        if not user_msg:
            dispatcher.utter_message(text="Bạn vui lòng nhập câu hỏi.")
            return []

        try:
            # Lấy nhiều kết quả hơn cho tìm kiếm chi tiết
            results = smart_retrieve(user_msg, top_k=5, score_threshold=0.25)

            if not results:
                dispatcher.utter_message(
                    text="Không tìm thấy thông tin chi tiết. "
                         "Bạn có thể thử với câu hỏi khác không?"
                )
                return []

            # Tạo câu trả lời chi tiết
            response_parts = ["🔍 *Thông tin chi tiết:*\n"]
            
            for i, (score, text, meta) in enumerate(results[:3], 1):
                source_file = meta.get('filename', f'Nguồn {i}')
                if '/' in source_file or '\\' in source_file:
                    source_file = source_file.split('/')[-1].split('\\')[-1]
                
                # Format từng phần
                section = f"**{i}. Từ {source_file}** (Điểm: {score:.2f})\n"
                section += f"{text[:200]}{'...' if len(text) > 200 else ''}\n"
                response_parts.append(section)

            final_response = "\n".join(response_parts)
            
            # Cắt gọn nếu quá dài
            if len(final_response) > 1000:
                final_response = final_response[:1000] + "\n\n*[Đã rút gọn do quá dài]*"

            dispatcher.utter_message(text=final_response)

        except Exception as e:
            logger.error(f"Error in ActionSearchDocDetailed: {e}")
            dispatcher.utter_message(text="Có lỗi xảy ra khi tìm kiếm chi tiết.")

        return []


class ActionSearchDocContext(Action):
    """
    Action tìm kiếm với ngữ cảnh mở rộng.
    """
    
    def name(self) -> str:
        return "action_search_doc_context"

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

        try:
            # Sử dụng context mode
            results = retrieve_answer(user_msg, top_k=3, extract_mode="context")
            
            if not results:
                dispatcher.utter_message(text="Không tìm thấy ngữ cảnh phù hợp.")
                return []

            score, context_text, meta = results[0]
            source_file = meta.get('filename', 'tài liệu')
            
            if '/' in source_file or '\\' in source_file:
                source_file = source_file.split('/')[-1].split('\\')[-1]

            response = f"📖 *Ngữ cảnh từ {source_file}:*\n\n{context_text}"
            
            # Thêm link đến văn bản gốc nếu có
            if meta.get('original_text'):
                response += f"\n\n💭 *Gợi ý: Bạn có thể hỏi chi tiết hơn về nội dung này.*"

            dispatcher.utter_message(text=response)

        except Exception as e:
            logger.error(f"Error in ActionSearchDocContext: {e}")
            dispatcher.utter_message(text="Có lỗi khi tìm kiếm ngữ cảnh.")

        return []