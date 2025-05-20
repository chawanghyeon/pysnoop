# widgets/top_processes_widget.py

from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.widgets import DataTable


class TopProcessesWidget(Container):
    """상위 프로세스 정보를 표시하는 DataTable 위젯"""

    BORDER_TITLE: str = "📈 상위 프로세스 (CPU 기준)"
    _columns: List[str] = ["PID", "이름", "CPU %", "MEM %"]

    def compose(self) -> ComposeResult:
        """위젯의 하위 구성요소를 정의합니다."""
        yield DataTable(id="top_procs_table")

    def on_mount(self) -> None:
        """위젯 마운트 시 호출됩니다."""
        try:
            table = self.query_one(DataTable)
            table.add_columns(*self._columns)
        except NoMatches:
            # Assuming self.app.log is available if this widget is part of an App
            # If not, you might need to pass a logger or handle logging differently
            if hasattr(self, "app") and hasattr(self.app, "log"):
                self.app.log.warning("TopProcessesWidget: DataTable 초기화 중 찾을 수 없습니다.")
            else:
                print("TopProcessesWidget: WARNING - DataTable 초기화 중 찾을 수 없습니다.")

    def update_processes(self, processes_data: List[Dict[str, Any]]) -> None:
        """프로세스 데이터로 테이블을 업데이트합니다."""
        try:
            table = self.query_one("#top_procs_table", DataTable)
            table.clear()
            if not table.columns:  # Ensure columns are added if table was cleared/recreated
                table.add_columns(*self._columns)

            for p_info in processes_data[:10]:  # 상위 10개
                pid = p_info.get("pid", "N/A")
                name = str(p_info.get("name", "N/A"))[:25]  # 이름 길이 제한
                cpu = p_info.get("cpu_percent", 0.0)
                mem = p_info.get("memory_percent", 0.0)
                table.add_row(str(pid), name, f"{cpu:.2f}", f"{mem:.2f}")
        except NoMatches:
            if hasattr(self, "app") and hasattr(self.app, "log"):
                self.app.log.warning(
                    "TopProcessesWidget: DataTable을 찾을 수 없습니다 (업데이트 시도 중)."
                )
            else:
                print(
                    "TopProcessesWidget: WARNING - DataTable을 찾을 수 없습니다 (업데이트 시도 중)."
                )
