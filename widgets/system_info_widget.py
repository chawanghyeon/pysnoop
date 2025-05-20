# widgets/system_info_widget.py

from typing import Dict, List

from textual.app import ComposeResult
from textual.containers import VerticalScroll  # 스크롤 가능한 컨테이너
from textual.reactive import reactive
from textual.widget import Widget  # 기본 Widget으로 변경
from textual.widgets import Static  # 개별 정보 표시에 사용


class SystemInfoWidget(Widget):  # Static 대신 Widget을 상속받도록 변경
    """시스템 CPU 및 메모리 정보를 표시하는 스크롤 가능한 위젯"""

    DEFAULT_CSS = """
    SystemInfoWidget {
        height: auto; /* 위젯의 높이를 자동으로 설정 */
        max-height: 10; /* 위젯의 최대 높이 (10줄로 예시, 필요에 따라 조절) */
        /* border: round green; */ /* 디버깅 또는 디자인용 테두리 */
    }
    VerticalScroll {
        /* VerticalScroll 내부의 스크롤바 스타일링 (선택 사항) */
        scrollbar-background: $primary-background-darken-2;
        scrollbar-background-hover: $primary-background-darken-1;
        scrollbar-color: $primary;
        scrollbar-color-hover: $secondary;
    }
    """

    cpu_usage_overall: reactive[float] = reactive(0.0)
    cpu_usage_per_core: reactive[Dict[str, float]] = reactive({})
    mem_usage_percent: reactive[float] = reactive(0.0)
    BORDER_TITLE: str = "📊 시스템 정보"  # 테두리 제목은 유지 (app.py에서 스타일링)

    # 위젯의 내용을 동적으로 생성하기 위해 render 대신 compose와 watch 메소드 활용

    def compose(self) -> ComposeResult:
        # 스크롤 가능한 컨테이너를 생성합니다.
        with VerticalScroll(id="system_info_scroll_area"):
            yield Static(id="cpu_overall_static")
            yield Static(id="cpu_per_core_static")
            yield Static(id="mem_usage_static")

    # cpu_usage_overall 값이 변경될 때 호출됩니다.
    def watch_cpu_usage_overall(self, new_value: float) -> None:
        try:
            cpu_overall_widget = self.query_one("#cpu_overall_static", Static)
            cpu_overall_widget.update(f"💻 CPU 전체: {new_value:.2f}%")
        except Exception:
            # 위젯이 아직 완전히 마운트되지 않았을 수 있습니다.
            pass  # 또는 self.app.log.error(...) 등으로 로깅

    # cpu_usage_per_core 값이 변경될 때 호출됩니다.
    def watch_cpu_usage_per_core(self, new_value: Dict[str, float]) -> None:
        try:
            cpu_per_core_widget = self.query_one("#cpu_per_core_static", Static)
            core_lines: List[str] = []
            if new_value:
                # 코어 이름(예: core0, core10)을 기준으로 정렬하여 표시
                sorted_cores = sorted(
                    new_value.items(),
                    key=lambda item: int(item[0].replace("system.cpu.core", "")),
                )
                for core_uri_key, usage in sorted_cores:
                    display_core_name = core_uri_key.replace("system.cpu.", "")  # 예: "core0"
                    core_lines.append(f"   - {display_core_name}: {usage:.2f}%")
            cpu_per_core_widget.update("\n".join(core_lines))
        except Exception:
            pass

    # mem_usage_percent 값이 변경될 때 호출됩니다.
    def watch_mem_usage_percent(self, new_value: float) -> None:
        try:
            mem_usage_widget = self.query_one("#mem_usage_static", Static)
            mem_usage_widget.update(f"💾 메모리: {new_value:.2f}%")
        except Exception:
            pass

    # 초기 마운트 시 또는 데이터가 처음 설정될 때 모든 내용을 한 번 업데이트합니다.
    # 또는 app.py에서 초기 데이터를 설정할 때 각 reactive 변수를 업데이트하면 자동으로 watch 메소드가 호출됩니다.
    def on_mount(self) -> None:
        # 초기 값으로 위젯 업데이트 (app.py에서 reactive 변수에 값을 할당하면 자동으로 호출됨)
        self.watch_cpu_usage_overall(self.cpu_usage_overall)
        self.watch_cpu_usage_per_core(self.cpu_usage_per_core)
        self.watch_mem_usage_percent(self.mem_usage_percent)
