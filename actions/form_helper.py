from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from typing import Optional, Union

import re

def check_suffix_allowed(items, allowed_values):
    """
    Checks if all items in the list have a suffix that is allowed.

    Args:
        items (list): A list of strings where each string contains a suffix separated by an underscore.
        allowed_values (list): A list of allowed suffix values.

    Returns:
        bool: True if all items have a suffix that is in the allowed_values list, False otherwise.
    """

    for item in items:
        suffix = item.split('_')[-1]
        if suffix not in allowed_values:
            return False
    return True

def contains_value(value: str, target: str | list[str] | None) -> bool:
    """
    Checks if a given value is in a target value or list of values.

    Args:
        value (str): The value to check.
        target (str | list[str] | None): The value or list of values to check against.

    Returns:
        bool: True if the value is in the target, False otherwise.
    """
    
    if isinstance(target, list):
        return value in target
    return False
def get_question_option_number_from_tracker(tracker: Tracker, slot_name: str) -> Optional[Union[str, List[str]]]:
    """
    Trích số thứ tự từ giá trị của slot.
    - Nếu slot là chuỗi: 'question16_2' -> '2'
    - Nếu slot là list: ['question16_1', 'question16_2'] -> ['1', '2']
    """
    slot_value = tracker.get_slot(slot_name)
    if not slot_value:
        return None

    pattern = re.compile(fr"{slot_name}_(\d+)")

    if isinstance(slot_value, list):
        result = []
        for item in slot_value:
            match = pattern.match(item)
            if match:
                result.append(match.group(1))
        return result if result else None
    elif isinstance(slot_value, str):
        match = pattern.match(slot_value)
        if match:
            return match.group(1)

    return None
def contains_all_numbers(numbers, check_nums):
    """Check if a list of numbers contains all elements of another list.

    Args:
        numbers (list): The list of numbers to check in.
        check_nums (list): The list of numbers to check for.

    Returns:
        bool: True if all elements of check_nums are in numbers, False otherwise.
    """
    return all(num in numbers for num in check_nums)