# widgets/uptime_widget.py

from textual.reactive import reactive
from textual.widgets import Static


class UptimeWidget(Static):
    """시스템 가동 시간 표시 위젯"""

    uptime_str: reactive[str] = reactive("가동 시간 정보 없음")
    BORDER_TITLE: str = "⏱️ 시스템 가동 시간"

    def render(self) -> str:
        """위젯의 내용을 렌더링합니다."""
        return str(self.uptime_str)
