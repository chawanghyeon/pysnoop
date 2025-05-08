# core/textml/extractor.py
import re
from typing import List, Tuple

NumberMatch = Tuple[str, float]


def extract_numbers_from_text(text: str) -> List[NumberMatch]:
    """
    텍스트에서 숫자(float)를 추출하여 (문맥, 값) 형태로 반환
    """
    # 숫자: 정수, 소수, - 부호 포함
    number_pattern = re.compile(r"(?P<context>\b[\w\-\/\.]+)?[=:]?\s*(?P<value>[-+]?\d+(\.\d+)?)")
    matches = []

    for match in number_pattern.finditer(text):
        raw_value = match.group("value")
        context = match.group("context") or ""
        try:
            num = float(raw_value)
            matches.append((context.strip(), num))
        except ValueError:
            continue

    return matches
