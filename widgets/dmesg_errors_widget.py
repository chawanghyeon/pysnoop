# widgets/dmesg_errors_widget.py
from textual.reactive import reactive
from textual.widgets import Static


class DmesgErrorsWidget(Static):
    """dmesg 오류 수를 표시하는 위젯"""

    error_count: reactive[int] = reactive(0)
    BORDER_TITLE: str = "⚠️ Dmesg 오류"

    def render(self) -> str:
        """위젯의 내용을 렌더링합니다."""
        if self.error_count == -1:
            return "오류: 권한 문제 또는 실행 실패"
        elif self.error_count == -2:
            return "오류: 'dmesg' 명령어 없음"
        elif self.error_count == -3:
            return "오류: 데이터 수집 중 알 수 없는 문제"
        elif self.error_count < 0:
            return "오류: dmesg 데이터 수집 실패"
        else:
            return f"발견된 오류 수: {self.error_count}"
