import asyncio
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static

from collectors.base import BaseCollector, collector_registry
from collectors.top_processes import TopProcessCollector
from utils.log_writer import LogWriter
from utils.memory_cache import MetricCache

# --- 설정 ---
COLLECTION_INTERVAL_SECONDS: int = 2
METRIC_CACHE_TTL_SECONDS: int = 300
LOG_DIR_NAME: str = "logs"


# --- 전역 변수 ---
_instantiated_collectors_cache: List[BaseCollector] = []
_log_writer_instance_cache: Optional[LogWriter] = None


def get_instantiated_collectors() -> List[BaseCollector]:
    """Returns the cached list of instantiated collectors."""
    return _instantiated_collectors_cache


def set_instantiated_collectors(collectors: List[BaseCollector]) -> None:
    """Sets the cached list of instantiated collectors."""
    global _instantiated_collectors_cache
    _instantiated_collectors_cache = collectors


def get_log_writer_instance() -> Optional[LogWriter]:
    """Returns the cached LogWriter instance."""
    return _log_writer_instance_cache


def set_log_writer_instance(log_writer: Optional[LogWriter]) -> None:
    """Sets the cached LogWriter instance."""
    global _log_writer_instance_cache
    _log_writer_instance_cache = log_writer


# --- Textual 위젯 정의 ---
class CurrentTime(Static):
    """현재 시간을 표시하는 위젯"""

    def on_mount(self) -> None:
        """위젯 마운트 시 호출됩니다."""
        self.update_time()
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        """현재 시간으로 위젯을 업데이트합니다."""
        self.update(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class SystemInfoWidget(Static):
    """시스템 CPU 및 메모리 정보를 표시하는 위젯"""

    cpu_usage_overall: reactive[float] = reactive(0.0)
    cpu_usage_per_core: reactive[Dict[str, float]] = reactive({})
    mem_usage_percent: reactive[float] = reactive(0.0)
    BORDER_TITLE: str = "📊 시스템 정보"

    def render(self) -> str:
        """위젯의 내용을 렌더링합니다."""
        content_lines: List[str] = []
        content_lines.append(f"💻 CPU 전체: {self.cpu_usage_overall:.2f}%")
        if self.cpu_usage_per_core:
            for core, usage in self.cpu_usage_per_core.items():
                display_core = core.replace("system.cpu.", "")
                content_lines.append(f"   - {display_core}: {usage:.2f}%")
        content_lines.append(f"💾 메모리: {self.mem_usage_percent:.2f}%")
        return "\n".join(content_lines)


class UptimeWidget(Static):
    """시스템 가동 시간 표시 위젯"""

    uptime_str: reactive[str] = reactive("가동 시간 정보 없음")
    BORDER_TITLE: str = "⏱️ 시스템 가동 시간"

    def render(self) -> str:
        """위젯의 내용을 렌더링합니다."""
        return str(self.uptime_str)


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
            self.app.log.warning("TopProcessesWidget: DataTable 초기화 중 찾을 수 없습니다.")

    def update_processes(self, processes_data: List[Dict[str, Any]]) -> None:
        """프로세스 데이터로 테이블을 업데이트합니다."""
        try:
            table = self.query_one("#top_procs_table", DataTable)
            table.clear()
            if not table.columns:
                table.add_columns(*self._columns)

            for p_info in processes_data[:10]:  # 상위 10개
                pid = p_info.get("pid", "N/A")
                name = str(p_info.get("name", "N/A"))[:25]  # 이름 길이 제한
                cpu = p_info.get("cpu_percent", 0.0)
                mem = p_info.get("memory_percent", 0.0)
                table.add_row(str(pid), name, f"{cpu:.2f}", f"{mem:.2f}")
        except NoMatches:
            self.app.log.warning(
                "TopProcessesWidget: DataTable을 찾을 수 없습니다 (업데이트 시도 중)."
            )


class DmesgErrorsWidget(Static):
    """dmesg 오류 수를 표시하는 위젯"""

    error_count: reactive[int] = reactive(0)
    BORDER_TITLE: str = "⚠️ Dmesg 오류"

    def render(self) -> str:
        """위젯의 내용을 렌더링합니다."""
        return f"발견된 오류 수: {self.error_count}"


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
            self.app.log.warning("DockerStatsWidget: DataTable 초기화 중 찾을 수 없습니다.")

    def update_docker_stats(self, docker_metrics: List[Dict[str, Any]]) -> None:
        """도커 통계 데이터로 테이블을 업데이트합니다."""
        try:
            table = self.query_one("#docker_stats_table", DataTable)
            table.clear()
            if not table.columns:  # Ensure columns exist
                table.add_columns(*self._columns)

            for container_stats in docker_metrics:
                table.add_row(
                    str(container_stats.get("name", "N/A")),
                    f"{container_stats.get('cpu_percent', 0.0):.2f}",
                    f"{container_stats.get('mem_percent', 0.0):.2f}",
                    f"{container_stats.get('mem_usage_mb', 0.0):.2f}",
                )
        except NoMatches:
            self.app.log.warning(
                "DockerStatsWidget: DataTable을 찾을 수 없습니다 (업데이트 시도 중)."
            )


# --- 메인 Textual 앱 클래스 ---
class MonitoringDashboardApp(App[None]):
    CSS_PATH = "dashboard.tcss"
    TITLE = "🚀 실시간 시스템 대시보드"
    BINDINGS = [
        Binding("q", "quit", "종료"),
        Binding("ctrl+c", "quit", "종료"),
        Binding("d", "toggle_dark", "다크 모드 전환"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.metric_cache: MetricCache = MetricCache(ttl_seconds=METRIC_CACHE_TTL_SECONDS)
        self._initialize_collectors_and_logger()
        self.docker_metrics_buffer: Dict[str, Dict[str, Any]] = {}

    def _initialize_collectors_and_logger(self) -> None:
        """컬렉터와 로거를 초기화합니다."""
        instantiated_collectors = get_instantiated_collectors()
        if not instantiated_collectors:
            collectors_to_init: List[BaseCollector] = []
            for collector_cls in collector_registry:
                try:
                    collectors_to_init.append(collector_cls())
                except Exception as e:
                    msg = f"컬렉터 {collector_cls.__name__} 인스턴스화 실패: {e}"
                    if hasattr(self, "log"):
                        self.log.error(msg)
                    else:
                        print(msg)
            set_instantiated_collectors(collectors_to_init)

        current_collectors = get_instantiated_collectors()
        if not current_collectors:
            msg = "인스턴스화된 컬렉터 없음. 메트릭 수집 불가."
            if hasattr(self, "log"):
                self.log.error(msg)
            else:
                print(msg)

        log_writer = get_log_writer_instance()
        if log_writer is None:
            try:
                base_dir_for_logs = Path(__file__).resolve().parent
                main_log_path = base_dir_for_logs / LOG_DIR_NAME
                log_writer = LogWriter(log_dir=main_log_path)
                set_log_writer_instance(log_writer)
                msg = f"LogWriter 인스턴스 생성됨. 로그 위치: {log_writer.log_dir}"
                if hasattr(self, "log"):
                    self.log.info(msg)
                else:
                    print(msg)
            except Exception as e:
                msg = f"LogWriter 초기화 실패: {e}"
                if hasattr(self, "log"):
                    self.log.error(msg)
                else:
                    print(msg)

    def compose(self) -> ComposeResult:
        """앱의 레이아웃을 구성합니다."""
        yield Header(show_clock=False)
        with Container(id="app-grid"):
            with Vertical(id="left-column"):
                yield UptimeWidget(id="uptime")
                yield SystemInfoWidget(id="sys_info")
                yield DmesgErrorsWidget(id="dmesg_errors")
            with Vertical(id="right-column"):
                yield TopProcessesWidget(id="top_procs")
                yield DockerStatsWidget(id="docker_stats")
        yield Footer()
        yield CurrentTime(id="custom_clock")

    async def on_mount(self) -> None:
        """앱 마운트 시 비동기 작업을 시작합니다."""
        log_writer = get_log_writer_instance()
        if log_writer:
            try:
                if asyncio.iscoroutinefunction(log_writer.start):
                    await log_writer.start()
                else:
                    log_writer.start()
                self.log.info("LogWriter 백그라운드 작업 시작됨.")
            except RuntimeError as e:
                self.log.error(
                    f"LogWriter 시작 중 오류: {e}. 이미 루프가 있거나 다른 문제일 수 있습니다."
                )
        else:
            self.log.warning("LogWriter가 초기화되지 않았습니다. 파일 로깅이 비활성화됩니다.")

        if not get_instantiated_collectors():
            self.log.error("사용 가능한 컬렉터가 없어 메트릭 수집을 시작할 수 없습니다.")
            return

        self.set_interval(COLLECTION_INTERVAL_SECONDS, self.run_metric_collection_background)
        self.log.info("대시보드 초기화 완료 및 메트릭 수집 시작.")

    async def run_metric_collection_background(self) -> None:
        """백그라운드에서 주기적으로 메트릭을 수집하고 UI를 업데이트합니다."""
        current_time_utc = datetime.datetime.now(datetime.timezone.utc)
        total_cpu_sum: float = 0.0
        total_cpu_cores: int = 0
        temp_per_core_cpu: Dict[str, float] = {}
        all_top_processes_data: List[Dict[str, Any]] = []
        self.docker_metrics_buffer.clear()

        log_writer = get_log_writer_instance()
        instantiated_collectors = get_instantiated_collectors()

        for collector_instance in instantiated_collectors:
            collector_name = collector_instance.__class__.__name__
            try:
                loop = asyncio.get_running_loop()
                collected_data: Union[List[Tuple[str, Any]], List[Dict[str, Any]], List[Any]]
                collected_data = await loop.run_in_executor(None, collector_instance.collect)

                if not collected_data:
                    continue

                if isinstance(collector_instance, TopProcessCollector):
                    all_top_processes_data = collected_data  # type: ignore [assignment]
                    if log_writer:
                        for proc_info in all_top_processes_data:
                            pid = proc_info.get("pid", "unknown")
                            name = str(proc_info.get("name", "unknown_proc"))
                            clean_name = "".join(
                                c if c.isalnum() or c in ("-", "_", ".") else "_" for c in name
                            ).strip("_")
                            if proc_info.get("cpu_percent") is not None:
                                await log_writer.append(
                                    {
                                        "ts": current_time_utc.isoformat(),
                                        "uri": f"top_cpu.{clean_name}.pid_{pid}.cpu_percent",
                                        "value": proc_info["cpu_percent"],
                                        "source": collector_name,
                                    }
                                )
                            if proc_info.get("memory_percent") is not None:
                                await log_writer.append(
                                    {
                                        "ts": current_time_utc.isoformat(),
                                        "uri": f"top_mem.{clean_name}.pid_{pid}.mem_percent",
                                        "value": proc_info["memory_percent"],
                                        "source": collector_name,
                                    }
                                )
                    continue

                metrics_tuples = collected_data  # type: ignore [assignment]

                for uri, value in metrics_tuples:  # type: ignore [attr-defined]
                    await self.metric_cache.update(uri, value, current_time_utc)
                    if log_writer:
                        log_entry: Dict[str, Any] = {
                            "ts": current_time_utc.isoformat(),
                            "uri": uri,
                            "value": value,
                            "source": collector_name,
                        }
                        await log_writer.append(log_entry)

                    self.update_widget_data(uri, value, temp_per_core_cpu)

                    if isinstance(value, (int, float)):
                        if uri.startswith("system.cpu.core"):
                            total_cpu_sum += float(value)
                            total_cpu_cores += 1
                        elif uri.startswith("docker.container."):
                            parts = uri.split(".")
                            if len(parts) > 3:
                                container_name = parts[2]
                                metric_type = parts[3]
                                if container_name not in self.docker_metrics_buffer:
                                    self.docker_metrics_buffer[container_name] = {
                                        "name": container_name
                                    }
                                self.docker_metrics_buffer[container_name][metric_type] = value
            except Exception as e:
                self.log.error(f"컬렉터 {collector_name} 처리 중 오류: {e}")

        sys_info_widget = self.query_one(SystemInfoWidget)
        if total_cpu_cores > 0:
            sys_info_widget.cpu_usage_overall = total_cpu_sum / total_cpu_cores
        else:
            sys_info_widget.cpu_usage_overall = 0.0
        sys_info_widget.cpu_usage_per_core = temp_per_core_cpu

        if all_top_processes_data:
            try:
                top_procs_widget = self.query_one(TopProcessesWidget)
                top_procs_widget.update_processes(all_top_processes_data)
            except NoMatches:
                self.log.warning("TopProcessesWidget을 찾을 수 없어 업데이트하지 못했습니다.")

        current_docker_stats_list = list(self.docker_metrics_buffer.values())
        if current_docker_stats_list:
            try:
                docker_stats_widget = self.query_one(DockerStatsWidget)
                docker_stats_widget.update_docker_stats(current_docker_stats_list)
            except NoMatches:
                self.log.warning("DockerStatsWidget을 찾을 수 없어 업데이트하지 못했습니다.")

    def update_widget_data(self, uri: str, value: Any, temp_per_core_cpu: Dict[str, float]) -> None:
        """수집된 메트릭을 기반으로 해당 위젯의 데이터를 업데이트합니다."""
        try:
            if uri.startswith("system.cpu.core") and isinstance(value, (int, float)):
                temp_per_core_cpu[uri] = float(value)
            elif uri == "system.memory.used_percent" and isinstance(value, (int, float)):
                self.query_one(SystemInfoWidget).mem_usage_percent = float(value)
            elif uri == "system.uptime.description":
                self.query_one(UptimeWidget).uptime_str = str(value)
            elif uri == "system.uptime.description_length" and isinstance(value, (int, float)):
                self.query_one(UptimeWidget).uptime_str = f"가동시간 정보 길이: {float(value)}"
            elif uri == "kernel.dmesg.errors" and isinstance(value, (int, float)):
                self.query_one(DmesgErrorsWidget).error_count = int(value)
        except NoMatches:
            self.log.warning(
                f"'{uri}'에 대한 위젯을 찾을 수 없습니다. UI가 아직 준비되지 않았을 수 있습니다."
            )
        except Exception as e:
            self.log.error(f"위젯 데이터 업데이트 중 오류 ({uri}: {value}): {e}")

    async def on_shutdown_request(self, _event: Any) -> None:
        """애플리케이션 종료 요청 시 호출됩니다."""
        self.log.info("애플리케이션 종료 요청 수신...")
        log_writer = get_log_writer_instance()
        if log_writer:
            self.log.info("로그 큐 플러시 중...")
            try:
                await log_writer.append(
                    {
                        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "event": "application_shutdown_dashboard",
                        "message": "대시보드 로깅 서비스 중지 시도.",
                    }
                )

                if hasattr(log_writer, "queue") and hasattr(log_writer.queue, "join"):
                    self.log.info("log_writer.queue.join() 대기 중...")
                    try:
                        await asyncio.wait_for(log_writer.queue.join(), timeout=5.0)
                        self.log.info("Log writer queue 처리가 완료되었습니다.")
                    except asyncio.TimeoutError:
                        self.log.warning("log_writer.queue.join() 대기 시간 초과.")
                    except Exception as e_join:
                        self.log.error(f"log_writer.queue.join() 중 오류 발생: {e_join}")

                if hasattr(log_writer, "task") and log_writer.task and not log_writer.task.done():
                    self.log.info("LogWriter 백그라운드 작업 취소 중...")
                    log_writer.task.cancel()
                    try:
                        await log_writer.task
                    except asyncio.CancelledError:
                        self.log.info("LogWriter 백그라운드 작업이 성공적으로 취소되었습니다.")
                    except Exception as e_task_cancel:
                        self.log.error(f"취소된 LogWriter 작업 대기 중 오류 발생: {e_task_cancel}")
            except Exception as e:
                self.log.error(f"LogWriter 종료 처리 중 예기치 않은 오류 발생: {e}")
        self.log.info("종료 완료.")


# --- 애플리케이션 실행 ---
def main_dashboard() -> None:
    """메인 대시보드 애플리케이션을 실행합니다."""
    print("애플리케이션 초기화 중 (대시보드 모드)...")
    app = MonitoringDashboardApp()
    app.run()


if __name__ == "__main__":
    main_dashboard()
