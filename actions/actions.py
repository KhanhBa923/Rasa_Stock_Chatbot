from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict
from rasa_sdk.events import EventType
from rasa_sdk.events import SlotSet,FollowupAction
from abc import ABC, abstractmethod
from typing import Optional

import re
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
    async def required_slots(
        self,
        domain_slots: List[Text],       # Danh sách slot mặc định trong domain.yml
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict
    ) -> List[Text]:
        question5 = tracker.get_slot("question5")
        #print(f"DEBUG: question5 = '{question5}'")
        required = domain_slots.copy()
        
        if question5 == "question5_1":
            required.remove("question5_1")
            #print("DEBUG: Removed question5_1 because question5 is 1")

        return required
    def validate_question1(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question1"""
        match = re.match(r"question1_(\d+)", str(slot_value))
        if match:
            option_number = match.group(1)
            response_key = f"utter_confirm_q1_{option_number}"

            if response_key in domain.get("responses", {}):
                dispatcher.utter_message(response=response_key)
                return {"question1": slot_value}
            else:
                dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                return {"question1": None}
        
        dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
        return {"question1": None}
    def validate_question3(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question3"""
        try:
            if slot_value and slot_value.startswith("question3_"):
                option_number = slot_value.replace("question3_", "") # Lấy số thứ tự từ slot_value
                option_q1 = get_question_option_number_from_tracker(tracker, "question1")
                if option_q1 is None:
                    dispatcher.utter_message(text="Bạn chưa trả lời câu hỏi 1, vui lòng trả lời trước khi tiếp tục.")
                    return {"question3": None}
                if option_number == "1":
                    if(option_q1 == "1"):
                        dispatcher.utter_message(response="utter_confirm_q3_1")
                    else:
                        dispatcher.utter_message(response="utter_confirm_q3_2")
                elif option_number == "2":
                    if(option_q1 == "1"):
                        dispatcher.utter_message(response="utter_confirm_q3_3")
                    else:
                        dispatcher.utter_message(response="utter_confirm_q3_4")
                elif option_number == "3":
                    dispatcher.utter_message(response="utter_confirm_q3_5")
                elif option_number == "4":
                    dispatcher.utter_message(response="utter_confirm_q3_6")
                else:
                    dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                    return {"question3": None}
                return {"question3": slot_value}
            else:
                dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
                return {"question3": None}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question3: {e}")
            return {"question3": None}
    def validate_question4(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question4"""
        try:
            if slot_value and slot_value.startswith("question4_"):
                option_number = slot_value.replace("question4_", "") # Lấy số thứ tự từ slot_value
                option_q1 = get_question_option_number_from_tracker(tracker, "question1")
                if option_q1 is None:
                    dispatcher.utter_message(text="Bạn chưa trả lời câu hỏi 1, vui lòng trả lời trước khi tiếp tục.")
                    return {"question4": None}
                if option_number == "1":
                    if(option_q1 == "1"):
                        dispatcher.utter_message(response="utter_confirm_q4_1")
                    else:
                        dispatcher.utter_message(response="utter_confirm_q4_2")
                elif option_number == "2":
                    if(option_q1 == "1"):
                        dispatcher.utter_message(response="utter_confirm_q4_3")
                    else:
                        dispatcher.utter_message(response="utter_confirm_q4_4")
                elif option_number == "3":
                    dispatcher.utter_message(response="utter_confirm_q4_0")
                    return {"question4": None}
                else:
                    dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                    return {"question4": None}
                return {"question4": slot_value}
            else:
                dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
                return {"question4": None}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question4: {e}")
            return {"question4": None}
    def validate_question5(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question5"""
        try:
            if slot_value and slot_value.startswith("question5_"):
                option_number = slot_value.replace("question5_", "") # Lấy số thứ tự từ slot_value
                if option_number == "1" or option_number == "2":
                    return {"question5": slot_value}
                else:
                    dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                    return {"question5": None}
            else:
                dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
                return {"question4": None}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question5: {e}")
            return {"question5": None}
    def validate_question6(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question6"""
        try:
            # Valid choices for question6
            valid_choices = [
                "question6_1",  # Tham gia vào các nhóm tư vấn
                "question6_2",  # Tham gia các khóa học
                "question6_3",  # Tìm kiếm dịch vụ tư vấn chuyên sâu
                "question6_4"   # Tiếp tục đầu tư, rút kinh nghiệm
            ]
            
            # Handle case where slot_value is None or empty
            if not slot_value:
                dispatcher.utter_message(text="Vui lòng chọn ít nhất một phương án.")
                return {"question6": None}
            
            # Convert single value to list for consistent processing
            if isinstance(slot_value, str):
                selected_values = [slot_value]
            elif isinstance(slot_value, list):
                selected_values = slot_value
            else:
                # Handle unexpected data types
                dispatcher.utter_message(text="Dữ liệu không hợp lệ. Vui lòng chọn lại.")
                return {"question6": None}
            
            # Validate each selected value
            validated_values = []
            for value in selected_values:
                if value in valid_choices:
                    validated_values.append(value)
                else:
                    dispatcher.utter_message(text=f"Lựa chọn '{value}' không hợp lệ.")
                    return {"question6": None}
            
            # Check if at least one option is selected
            if not validated_values:
                dispatcher.utter_message(text="Vui lòng chọn ít nhất một phương án.")
                return {"question6": None}
            
            # Success case - return validated values
            # Convert back to single value if only one item selected
            if len(validated_values) == 1:
                return {"question6": validated_values[0]}
            else:
                return {"question6": validated_values}
                
        except Exception as e:
            print(f"Error in validate_question6: {str(e)}")
            dispatcher.utter_message(text="Đã xảy ra lỗi. Vui lòng thử lại.")
            return {"question6": None}
    def validate_question7(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question7"""

        try:
            if slot_value and slot_value.startswith("question7_"):
                option_number = slot_value.replace("question7_", "")  # Lấy số thứ tự từ slot_value

                valid_options = ["1", "2", "3","4", "5"]
                if option_number in valid_options:
                    return {"question7": slot_value}
                else:
                    dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                    return {"question7": None}
            else:
                dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
                return {"question7": None}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question7: {e}")
            return {"question7": None}
    def validate_question8(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question8"""
        try:
            numbers = [int(item.split('_')[1]) for item in slot_value] #3,4
            count = len(numbers)
            if not numbers:
                dispatcher.utter_message(text="Vui lòng chọn ít nhất một phương án.")
                return {"question8": None}
            if count > 3:
                dispatcher.utter_message(response="utter_confirm_q8_1")
                dispatcher.utter_message(response="utter_confirm_q8_2")
                return {"question8": slot_value}
            else:
                if contains_all_numbers(numbers, [1, 6, 7]):
                    dispatcher.utter_message(response="utter_confirm_q8_2")
                    return {"question8": slot_value}
                elif contains_all_numbers(numbers, [1, 7]):
                    dispatcher.utter_message(response="utter_confirm_q8_3")
                    return {"question8": slot_value}
                elif contains_all_numbers(numbers, [1, 5]): 
                    dispatcher.utter_message(response="utter_confirm_q8_4")
                    return {"question8": slot_value}
                elif contains_all_numbers(numbers, [1, 4]):
                    dispatcher.utter_message(response="utter_confirm_q8_5")
                    return {"question8": slot_value}
                elif contains_all_numbers(numbers, [1, 2]):
                    dispatcher.utter_message(response="utter_confirm_q8_6")
                    return {"question8": slot_value}
                elif contains_all_numbers(numbers, [1, 3]):
                    dispatcher.utter_message(response="utter_confirm_q8_6")
                    return {"question8": slot_value}
                else:
                    return {"question8": slot_value}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question8: {e}")
            return {"question8": None}
    def validate_question9(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question9"""
        try:
            if slot_value and slot_value.startswith("question9_"):
                option_number = slot_value.replace("question9_", "")  # Lấy số thứ tự từ slot_value

                valid_options = ["1", "2", "3"]
                if option_number in valid_options:
                    return {"question9": slot_value}
                else:
                    dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                    return {"question9": None}
            else:
                dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
                return {"question9": None}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question9: {e}")
            return {"question9": None}
    def validate_question10(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        """Hiển thị lại câu trả lời question10"""
        try:
            if slot_value and slot_value.startswith("question10_"):
                option_number = slot_value.replace("question10_", "")  # Lấy số thứ tự từ slot_value

                valid_options = ["1", "2", "3","4"]
                if option_number in valid_options:
                    return {"question10": slot_value}
                else:
                    dispatcher.utter_message(text="Lựa chọn không hợp lệ, vui lòng chọn lại.")
                    return {"question10": None}
            else:
                dispatcher.utter_message(text="Dữ liệu không hợp lệ.")
                return {"question10": None}
        except Exception as e:
            dispatcher.utter_message(text="Đã xảy ra lỗi khi xử lý lựa chọn. Vui lòng thử lại.")
            print(f"[ERROR] validate_question10: {e}")
            return {"question10": None}
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
        question3 = tracker.get_slot("question3")
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
                f"Câu trả lời 2: {question3}"
            )
            
            return [
                SlotSet("industry", None),
                SlotSet("seniority", None),
                SlotSet("budget", None),
                SlotSet("ready", None),
                SlotSet("question1", None),
                SlotSet("question3", None),
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

def get_question_option_number_from_tracker(tracker: Tracker, slot_name: str) -> Optional[str]:
    """
    Trích số thứ tự từ giá trị của slot (ví dụ: slot 'question1' có giá trị 'question1_2' → trả về '2')
    """
    slot_value = tracker.get_slot(slot_name)
    if not slot_value:
        return None

    match = re.match(fr"{slot_name}_(\d+)", slot_value)
    if match:
        return match.group(1)
    return None
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

class ActionAskQuestionBase(Action, ABC):
    @abstractmethod
    def name(self) -> Text:
        """Abstract method that must be implemented by subclasses"""
        pass
     
    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        action_name = self.name()  # Ví dụ: action_ask_question5_1
        question_slot = action_name.replace("action_ask_", "")  # Ví dụ: question5_1
        print(f"DEBUG: Running action {action_name} for slot {question_slot}")
        # Lấy response chứa buttons: utter_res_questionX hoặc utter_res_questionX_Y
        response_key = f"utter_res_{question_slot}"
        response_data = domain.get("responses", {}).get(response_key, [])
         
        # Kiểm tra xem có buttons hay không
        if not response_data or not response_data[0].get("buttons", []):
            # Nếu không có buttons, chỉ hiển thị câu hỏi
            dispatcher.utter_message(response=f"utter_ask_{question_slot}")
            return []
         
        domain_buttons = response_data[0].get("buttons", [])
        buttons = []
         
        # Xử lý intent name cho cả question1 và question5_1
        if "_" in question_slot:
            # Trường hợp question5_1 -> choose_q5_1
            question_number = question_slot.replace("question", "")
            intent_name = f"choose_q{question_number}"
        else:
            # Trường hợp question1 -> choose_q1
            intent_name = f"choose_q{question_slot[8:]}"
         
        for idx, button in enumerate(domain_buttons):
            question_value = f"{question_slot}_{idx + 1}"
            buttons.append({
                "title": button["title"],
                "payload": f'/{intent_name}{{"{question_slot}": "{question_value}"}}'
            })
         
        # utter_ask_questionX hoặc utter_ask_questionX_Y
        dispatcher.utter_message(
            response=f"utter_ask_{question_slot}",
            buttons=buttons,
        )
        return []
    
class ActionAskQuestionBaseMultiChoice(Action, ABC):
    @abstractmethod
    def name(self) -> Text:
        """Abstract method that must be implemented by subclasses"""
        pass
     
    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        try:
            action_name = self.name()  # Ví dụ: action_ask_question5_1
            question_slot = action_name.replace("action_ask_", "")  # Ví dụ: question5_1
            print(f"DEBUG: Running action {action_name} for slot {question_slot}")
            # Lấy response chứa buttons: utter_res_questionX hoặc utter_res_questionX_Y
            response_key = f"utter_res_{question_slot}"
            response_data = domain.get("responses", {}).get(response_key, [])
            
            # Kiểm tra xem có buttons hay không
            if not response_data or not response_data[0].get("buttons", []):
                # Nếu không có buttons, chỉ hiển thị câu hỏi
                dispatcher.utter_message(response=f"utter_ask_{question_slot}")
                print(f"DEBUG: No buttons found for {response_key}, only showing question.")
                return []
            
            domain_buttons = response_data[0].get("buttons", [])
            buttons = []
            for idx, button in enumerate(domain_buttons):
                question_value = f"{question_slot}_{idx + 1}"
                buttons.append({
                    "text": button["title"],
                    "value": question_value 
                })
            
            # utter_ask_questionX hoặc utter_ask_questionX_Y
            custom_payload = build_multi_select_response(question_slot, buttons)            
            dispatcher.utter_message(
                response=f"utter_ask_{question_slot}",
                custom=custom_payload
            )
            return []
        except Exception as e:
            print(f"Error in ActionAskQuestionBaseMultiChoice: {str(e)}")
            dispatcher.utter_message(text="Đã xảy ra lỗi khi hiển thị câu hỏi. Vui lòng thử lại.")
            return []

def build_multi_select_response(question_id: str, choices: list) -> dict:
    return {
        "multi_select": True,
        "question_id": question_id,
        "choices": [
            {"text": c["text"], "value": c["value"]}
            for c in choices
        ]
    }
def contains_all_numbers(numbers, check_nums):
    return all(num in numbers for num in check_nums)


class ActionAskQuestion1(ActionAskQuestionBase):
    def name(self) -> Text:
        return "action_ask_question1"
    
class ActionAskquestion3(Action):
    def name(self) -> Text:
        return "action_ask_question3"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        response_data = domain["responses"]["utter_res_question3"][0]
        domain_buttons = response_data.get("buttons", [])
        
        buttons = []
        for idx, button in enumerate(domain_buttons):
            question_value = f"question3_{idx + 1}"
            buttons.append({
                "title": button["title"],
                "payload": f'/choose_q2{{"question3": "{question_value}"}}'
            })

        dispatcher.utter_message(
            response="utter_ask_question3",
            buttons=buttons,
        )
        return []
        
class ActionAskQuestion4(ActionAskQuestionBase):
    def name(self) -> Text:
        return "action_ask_question4"
    
class ActionAskQuestion5(ActionAskQuestionBase):
    def name(self) -> Text:
        return "action_ask_question5"
    
class ActionAskQuestion5_1(ActionAskQuestionBase):
    def name(self) -> Text:
        return "action_ask_question5_1"

class ActionShowQuestion6(ActionAskQuestionBaseMultiChoice):
    def name(self) -> str:
        return "action_ask_question6"

class ActionAskQuestion7(ActionAskQuestionBase):
    def name(self) -> Text:
        return "action_ask_question7"
    
class ActionShowQuestion8(ActionAskQuestionBaseMultiChoice):
    def name(self) -> str:
        return "action_ask_question8"
    
class ActionShowQuestion9(ActionAskQuestionBase):
    def name(self) -> str:
        return "action_ask_question9"
    
class ActionShowQuestion10(ActionAskQuestionBase):
    def name(self) -> str:
        return "action_ask_question10"
