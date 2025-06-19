from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict
from rasa_sdk.events import EventType

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