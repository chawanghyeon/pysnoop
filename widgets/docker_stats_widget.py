# widgets/docker_stats_widget.py

from typing import Any, Dict, List

from textual.app import ComposeResult
from textual.containers import Container
from textual.css.query import NoMatches
from textual.widgets import DataTable


class DockerStatsWidget(Container):
    """도커 컨테이너 통계를 표시하는 위젯"""

    BORDER_TITLE: str = "🐳 도커 컨테이너"
    _columns: List[str] = ["컨테이너명", "CPU %", "MEM %", "MEM 사용량(MB)"]

    def compose(self) -> ComposeResult:
        """위젯의 하위 구성요소를 정의합니다."""
        yield DataTable(id="docker_stats_table")

    def on_mount(self) -> None:
        """위젯 마운트 시 호출됩니다."""
        try:
            table = self.query_one(DataTable)
            table.add_columns(*self._columns)
        except NoMatches:
            if hasattr(self, "app") and hasattr(self.app, "log"):
                self.app.log.warning("DockerStatsWidget: DataTable 초기화 중 찾을 수 없습니다.")
            else:
                print("DockerStatsWidget: WARNING - DataTable 초기화 중 찾을 수 없습니다.")

    def update_docker_stats(self, docker_metrics: List[Dict[str, Any]]) -> None:
        """도커 통계 데이터로 테이블을 업데이트합니다."""
        try:
            table = self.query_one("#docker_stats_table", DataTable)
            table.clear()
            if not table.columns:  # Ensure columns are added
                table.add_columns(*self._columns)

            for container_stats in docker_metrics:
                table.add_row(
                    str(container_stats.get("name", "N/A")),
                    f"{container_stats.get('cpu_percent', 0.0):.2f}",
                    f"{container_stats.get('mem_percent', 0.0):.2f}",
                    f"{container_stats.get('mem_usage_mb', 0.0):.2f}",
                )
        except NoMatches:
            if hasattr(self, "app") and hasattr(self.app, "log"):
                self.app.log.warning(
                    "DockerStatsWidget: DataTable을 찾을 수 없습니다 (업데이트 시도 중)."
                )
            else:
                print(
                    "DockerStatsWidget: WARNING - DataTable을 찾을 수 없습니다 (업데이트 시도 중)."
                )
