from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict
from rasa_sdk.events import EventType
from rasa_sdk.events import SlotSet,FollowupAction


import os
import pathlib 


class ActionProcessStockOrder(Action):
    def name(self) -> Text:
        return "action_process_stock_order"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        action = tracker.get_slot("action")
        stock_symbol = (tracker.get_slot("stock_symbol") or "").upper()
        quantity = tracker.get_slot("quantity")
        
        if action and stock_symbol and quantity:
            message = f"Đã xử lý lệnh {action} {quantity} cổ phiếu {stock_symbol.upper()}"
            dispatcher.utter_message(text=message)
        else:
            dispatcher.utter_message(text="Thông tin lệnh không đầy đủ. Vui lòng cung cấp đầy đủ: hành động (mua/bán), mã chứng khoán và số lượng.")
        
        return []
    
class ValidateLoginForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_stock_trading_form"
    def validate_action(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        action = str(slot_value).lower().strip()

        valid_actions = ["mua", "bán", "ban"]  # chấp nhận lỗi chính tả "ban" thay cho "bán"

        if action in valid_actions:
            # Chuẩn hóa lại về "mua" hoặc "bán"
            normalized = "bán" if action == "ban" else action
            return {"action": normalized}
        else:
            dispatcher.utter_message(text=f"⚠️ Bạn vừa nhập '{slot_value}' không rõ là mua hay bán. Vui lòng chọn lại.")
            return {"action": None}
    def validate_stock_symbol(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        lookup_path = "data/lookup_table/stock_symbol.txt"
        valid_symbols = pathlib.Path(lookup_path).read_text().split("\n")
        if slot_value.upper() in valid_symbols:
            return {"stock_symbol": slot_value}
        else:
            dispatcher.utter_message(text=f"Mã cổ phiếu '{slot_value}' không hợp lệ. Vui lòng nhập lại.")
            return {"stock_symbol": None}
    def validate_quantity(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        try:
            quantity = int(slot_value)
            if quantity > 0:
                return {"quantity": quantity}
            else:
                dispatcher.utter_message(text="Số lượng phải lớn hơn 0. Vui lòng nhập lại.")
                return {"quantity": None}
        except ValueError:
            dispatcher.utter_message(text="Số lượng không hợp lệ. Vui lòng nhập lại bằng số.")
            return {"quantity": None}
    def validate_confirm_inf(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if tracker.get_intent_of_latest_message() == "affirm":
            dispatcher.utter_message(text="Thông tin đã được xác nhận. Cảm ơn bạn!")
            return {"confirm_inf": True}
        if tracker.get_intent_of_latest_message() == "deny":
            dispatcher.utter_message(text="Thông tin không chính xác. Vui lòng nhập lại thông tin.")
            return {"confirm_inf": None, "stock_symbol": None, "action": None, "quantity": None}
        dispatcher.utter_message(text="Xin lỗi, tôi không hiểu. Vui lòng xác nhận 'có' hoặc 'không'.")
        return {"confirm_details": None}
    
        
class AskConfirmInfAction(Action):
    def name(self) -> Text:
        return "action_ask_confirm_inf"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        action = tracker.get_slot("action")
        stock_symbol = (tracker.get_slot("stock_symbol") or "").upper()
        quantity = tracker.get_slot("quantity")
        dispatcher.utter_message(
            text=f"Xác nhận lệnh: {action} {quantity} cổ phiếu {stock_symbol}. Bạn có muốn thực hiện không?",
            buttons=[
                {"title": "Đồng ý", "payload": "/affirm"},
                {"title": "Từ chối", "payload": "/deny"},
            ],
        )
        return []
    
class AskConfirmAction(Action):
    def name(self) -> Text:
        return "action_ask_action"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[EventType]:
        dispatcher.utter_message(
            text=f"Bạn muốn mua hay bán cổ phiếu?",
            buttons=[
                {"title": "Mua", "payload": "mua"},
                {"title": "Bán", "payload": "bán"},
            ],
        )
        return []
    
class ActionAskSurveyType(Action):
    def name(self) -> Text:
        return "action_ask_survey_type"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        buttons = [
            {"title": "Đánh giá dịch vụ", "payload": "service"},
            {"title": "Phản hồi sản phẩm", "payload": "product"}
        ]

        dispatcher.utter_message(text="Bạn muốn làm khảo sát nào?", buttons=buttons)
        return []
    
class ValidateFBForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_feedback_form"
    def validate_survey_type(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> Dict[Text, Any]:
        valid_types = ["service", "product"]
        if slot_value in valid_types:
            return {"survey_type": slot_value}
        else:
            dispatcher.utter_message(text=f"⚠️ Bạn vừa nhập '{slot_value}' không hợp lệ. Vui lòng chọn lại.")
            return {"survey_type": None}
        
    async def required_slots(
        self,
        domain_slots: List[Text],       # Danh sách slot mặc định trong domain.yml
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Text]:
        survey_type = tracker.get_slot("survey_type")
        service_rating = tracker.get_slot("service_rating")
        product_feedback = tracker.get_slot("product_feedback")
        
        # Debug: In ra giá trị survey_type để kiểm tra
        print(f"DEBUG: survey_type = '{survey_type}'")
        print(f"DEBUG: domain_slots = {domain_slots}")
        
        required = domain_slots.copy()
        
        if survey_type == "product":
            # Bỏ các slot không liên quan đến product
            slots_to_remove = ["service_target", "service_rating","service_location"]
            for s in slots_to_remove:
                if s in required:
                    required.remove(s)
                    print(f"DEBUG: Removed {s} for product survey")
        
        elif survey_type == "service":
            # Bỏ các slot không liên quan đến service
            slots_to_remove = ["product_target", "product_feedback", "product_location"]
            for s in slots_to_remove:
                if s in required:
                    required.remove(s)
                    print(f"DEBUG: Removed {s} for service survey")
        
        else:
            print(f"DEBUG: survey_type is not 'product' or 'service', it's: '{survey_type}'")

        if service_rating is not None:
            rating_value = float(service_rating)
            if rating_value < 3:
                required.remove("service_location")
                print("DEBUG: Removed service_location due to low service_rating")
        if product_feedback is not None:
            if product_feedback !="good" and product_feedback !="excellent": #hardcode các giá trị tốt, có thế thêm lại ở phần nlu
                required.remove("product_location")
                print("DEBUG: Removed product_location due to bad product_feedback")
        
        print(f"DEBUG: Final required slots = {required}")
        return required


class ActionThanks(Action):
    """Action để cảm ơn người dùng và reset tất cả slots về None"""

    def name(self) -> Text:
        return "action_thanks"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(
            text="Cảm ơn bạn đã phản hồi!"
        )
        
        # Reset tất cả các slots về None
        return [
            SlotSet("survey_type", None),
            SlotSet("service_target", None),
            SlotSet("product_target", None),
            SlotSet("service_rating", None),
            SlotSet("product_feedback", None),
            SlotSet("service_location", None),
            SlotSet("product_location", None)
        ]
class ValidateFormSurveyTypebot(FormValidationAction):
    def name(self) -> Text:
        return "validate_form_survey_typebot"
    
    def validate_ready(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Xử lý khi người dùng từ chối tiếp tục"""
        if slot_value is False:
            # Tạm dừng form và lưu trạng thái
            dispatcher.utter_message(response="utter_form_paused")
            return {
                "ready": None,  # Reset slot ready
                "form_paused": True,  # Đánh dấu form đã tạm dừng
                "requested_slot": None  # Dừng form
            }
        return {"ready": slot_value}
    def validate_question1(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question1"""
        if slot_value and slot_value.startswith("question1_"):
            option_number = slot_value.replace("question1_", "")
            response_key = f"utter_confirm_q1_{option_number}"

            if response_key in domain.get("responses", {}):
                dispatcher.utter_message(response=response_key)
            else:
                dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")

            return {"question1": slot_value}

        # Trường hợp slot_value không đúng định dạng
        dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
        return {"question1": None}
    
    def validate_question2(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question2"""
        if slot_value and slot_value.startswith("question2_"):
            option_number = slot_value.replace("question2_", "")
            response_key = f"utter_confirm_q2_{option_number}"

            if response_key in domain.get("responses", {}):
                dispatcher.utter_message(response=response_key)
            else:
                dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")

            return {"question2": slot_value}

        # Trường hợp slot_value không đúng định dạng
        dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
        return {"question2": None}
    
class ActionCustomFormSubmit(Action):
    def name(self) -> Text:
        return "action_submit_form_survey_typebot"
    
    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        """Xử lý khi form hoàn thành"""
        
        # Lấy tất cả thông tin đã thu thập
        industry = tracker.get_slot("industry")
        seniority = tracker.get_slot("seniority")
        budget = tracker.get_slot("budget")
        question1 = tracker.get_slot("question1")
        question2 = tracker.get_slot("question2")
        ready= tracker.get_slot("ready")

        if(ready is None or ready is False):
            return []
        else:
            dispatcher.utter_message(
            text=f"Cảm ơn bạn đã hoàn thành khảo sát!\n"
                f"Lĩnh vực: {industry}\n"
                f"Vị trí: {seniority}\n"
                f"Ngân sách: {budget}\n"
                f"Câu trả lời 1: {question1}\n"
                f"Câu trả lời 2: {question2}"
            )
            
            return [
                SlotSet("industry", None),
                SlotSet("seniority", None),
                SlotSet("budget", None),
                SlotSet("ready", None),
                SlotSet("question1", None),
                SlotSet("question2", None),
                SlotSet("form_paused", False),
            ]
    class ActionHandleReadyToContinue(Action):
        def name(self) -> Text:
            return "action_handle_ready_to_continue"
        
        def run(
            self, 
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]
        ) -> List[Dict[Text, Any]]:
            """Xử lý khi người dùng sẵn sàng tiếp tục"""
            
            # Kiểm tra xem có phải form đang tạm dừng không
            form_paused = tracker.get_slot("form_paused")
            
            if form_paused is True:
                dispatcher.utter_message(response="utter_form_resumed")
                return [
                    SlotSet("ready", True),
                    SlotSet("form_paused", False),
                    FollowupAction("form_survey_typebot")
                ]
            else:
                dispatcher.utter_message(text="Bạn chưa bắt đầu khảo sát nào cả!")
                return []
class ActionFormPaused(Action):
    def name(self) -> Text:
        return "action_form_paused"
    
    def run(self, 
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(response="utter_form_paused")
        return []
    
class ActionAskQuestion1(Action):
    def name(self) -> Text:
        return "action_ask_question1"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        buttons = [
            {"title": "a. Trên 50%", "payload": '/choose_q1{"question1": "question1_1"}'},
            {"title": "b. 25-<50%", "payload": '/choose_q1{"question1": "question1_2"}'},
            {"title": "c. 10–<25%", "payload": '/choose_q1{"question1": "question1_3"}'},
            {"title": "d. 0–<10%", "payload": '/choose_q1{"question1": "question1_4"}'},
        ]
        dispatcher.utter_message(
            text="Tỷ lệ nợ trên tổng tài sản của anh/chị là bao nhiêu? (Tổng tài sản bao gồm: tiền mặt và các loại hình đầu tư khác)",
            buttons=buttons,
        )
        return []
class ActionAskQuestion2(Action):
    def name(self) -> Text:
        return "action_ask_question2"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        buttons = [
            {"title": "a. Trên 50%", "payload": '/choose_q2{"question2": "question2_1"}'},
            {"title": "b. 25-<50%", "payload": '/choose_q2{"question2": "question2_2"}'},
            {"title": "c. 10–<25%", "payload": '/choose_q2{"question2": "question2_3"}'},
            {"title": "d. 0 – <10%", "payload": '/choose_q2{"question2": "question2_4"}'},
        ]
        dispatcher.utter_message(
            text="Giá trị ròng tài khoản chứng khoán chiếm bao nhiêu % tổng tài sản?",
            buttons=buttons,
        )
        return []
class ActionAskReady(Action):
    def name(self) -> Text:
        return "action_ask_ready"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        buttons = [
            {"title": "Bắt đầu", "payload": '/affirm{"ready": "true"}'},
            {"title": "Chưa sẵn sàng", "payload": '/deny{"ready": "false"}'},
        ]
        dispatcher.utter_message(
            text=(
                "Để có thể tư vấn bạn tốt hơn, vui lòng trả lời một số câu hỏi sau đây.\n"
                "Sẵn sàng chưa nào?"
            ),
            buttons=buttons,
        )
        return []

