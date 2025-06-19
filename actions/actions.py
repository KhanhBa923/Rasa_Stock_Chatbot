from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import FormValidationAction
from rasa_sdk.types import DomainDict

import os

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

    def validate_stock_symbol(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        lookup_path = "data/lookup_tables/stock_symbol.yml"
        valid_symbols = set()

        if os.path.exists(lookup_path):
            with open(lookup_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip("- \n")
                    if line and not line.startswith("version") and not line.startswith("nlu:") and "lookup" not in line:
                        valid_symbols.add(line.upper())

        if slot_value in valid_symbols:
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