import asyncio
import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.css.query import NoMatches
from textual.widgets import Footer, Header

import globals
from collectors.base import collector_registry
from collectors.top_processes import TopProcessCollector
from utils.log_writer import LogWriter
from utils.memory_cache import MetricCache
from widgets import (
    CurrentTimeWidget,
    DmesgErrorsWidget,
    DockerStatsWidget,
    SystemInfoWidget,
    TopProcessesWidget,
    UptimeWidget,
)

COLLECTION_INTERVAL_SECONDS: int = 2
METRIC_CACHE_TTL_SECONDS: int = 300
LOG_DIR_NAME: str = "logs"


class MonitoringDashboardApp(App[None]):
    CSS_PATH = (
        "dashboard.tcss"  # Assuming dashboard.tcss is in the same directory or accessible path
    )
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
        instantiated_collectors = globals.get_instantiated_collectors()
        if not instantiated_collectors:
            collectors_to_init = []
            for collector_cls in collector_registry:
                try:
                    collectors_to_init.append(collector_cls())
                except Exception as e:
                    msg = f"컬렉터 {collector_cls.__name__} 인스턴스화 실패: {e}"
                    # Use self.log if available (after app init), otherwise print
                    if hasattr(self, "log"):
                        self.log.error(msg)
                    else:
                        print(f"ERROR: {msg}")  # Early error
            globals.set_instantiated_collectors(collectors_to_init)

        current_collectors = globals.get_instantiated_collectors()
        if not current_collectors:
            msg = "인스턴스화된 컬렉터 없음. 메트릭 수집 불가."
            if hasattr(self, "log"):
                self.log.error(msg)
            else:
                print(f"ERROR: {msg}")

        log_writer = globals.get_log_writer_instance()
        if log_writer is None:
            try:
                base_dir_for_logs = Path(__file__).resolve().parent
                main_log_path = base_dir_for_logs / LOG_DIR_NAME
                log_writer = LogWriter(log_dir=main_log_path)
                globals.set_log_writer_instance(log_writer)
                msg = f"LogWriter 인스턴스 생성됨. 로그 위치: {log_writer.log_dir}"
                if hasattr(self, "log"):
                    self.log.info(msg)
                else:
                    print(f"INFO: {msg}")
            except Exception as e:
                msg = f"LogWriter 초기화 실패: {e}"
                if hasattr(self, "log"):
                    self.log.error(msg)
                else:
                    print(f"ERROR: {msg}")

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
        yield CurrentTimeWidget(id="custom_clock")  # Renamed from CurrentTime to CurrentTimeWidget

    async def on_mount(self) -> None:
        """앱 마운트 시 비동기 작업을 시작합니다."""
        log_writer = globals.get_log_writer_instance()
        if log_writer:
            try:
                # LogWriter.start might not be async, ensure it's called correctly
                if asyncio.iscoroutinefunction(log_writer.start):
                    await log_writer.start()
                else:
                    log_writer.start()  # Assuming start creates a task
                self.log.info("LogWriter 백그라운드 작업 시작됨.")
            except (
                RuntimeError
            ) as e:  # Catch specific error if loop is already running for the task
                self.log.error(
                    f"LogWriter 시작 중 오류: {e}. 이미 루프가 있거나 다른 문제일 수 있습니다."
                )
            except Exception as e:  # Catch other potential errors
                self.log.error(f"LogWriter 시작 중 예기치 않은 오류: {e}")
        else:
            self.log.warning("LogWriter가 초기화되지 않았습니다. 파일 로깅이 비활성화됩니다.")

        if not globals.get_instantiated_collectors():
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
        all_top_processes_data: List[Dict[str, Any]] = []  # Explicitly for TopProcessCollector
        self.docker_metrics_buffer.clear()  # For DockerStatsCollector

        log_writer = globals.get_log_writer_instance()
        instantiated_collectors = globals.get_instantiated_collectors()

        for collector_instance in instantiated_collectors:
            collector_name = collector_instance.__class__.__name__
            try:
                loop = asyncio.get_running_loop()
                # The collected_data can be List[Tuple[str, Any]] or List[Dict[str, Any]]
                collected_data: Union[List[Tuple[str, Any]], List[Dict[str, Any]], List[Any]]
                collected_data = await loop.run_in_executor(None, collector_instance.collect)

                if not collected_data:
                    continue

                # Handle data based on collector type or data structure
                if isinstance(collector_instance, TopProcessCollector):
                    # This data is List[Dict[str, Any]]
                    all_top_processes_data = collected_data  # type: ignore [assignment]
                    if log_writer:
                        for proc_info in all_top_processes_data:  # proc_info is a Dict
                            pid = proc_info.get("pid", "unknown")
                            name = str(proc_info.get("name", "unknown_proc"))
                            # Sanitize name for URI if necessary
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
                    # Skip to next collector as TopProcessCollector data is handled
                    continue

                # For other collectors, assume List[Tuple[str, Any]]
                # This needs to be safe if collected_data is not a list of tuples
                metrics_tuples = collected_data  # type: ignore [assignment]

                for item in metrics_tuples:  # item is Tuple[str, Any]
                    if not (isinstance(item, tuple) and len(item) == 2):
                        self.log.warning(
                            f"컬렉터 {collector_name}에서 잘못된 형식의 메트릭 데이터 수신: {item}"
                        )
                        continue  # Skip malformed item

                    uri, value = item

                    await self.metric_cache.update(uri, value, current_time_utc)
                    if log_writer:
                        log_entry: Dict[str, Any] = {
                            "ts": current_time_utc.isoformat(),
                            "uri": uri,
                            "value": value,
                            "source": collector_name,
                        }
                        await log_writer.append(log_entry)

                    # Update widgets based on URI
                    self.update_widget_data(uri, value, temp_per_core_cpu)

                    # Aggregate CPU and Docker data
                    if isinstance(value, (int, float)):  # Ensure value is numeric for these calcs
                        if uri.startswith("system.cpu.core"):
                            total_cpu_sum += float(value)
                            total_cpu_cores += 1
                        elif uri.startswith("docker.container."):
                            parts = uri.split(".")
                            if len(parts) > 3:  # e.g., docker.container.NAME.metric_type
                                container_name = parts[2]
                                metric_type = parts[
                                    3
                                ]  # e.g., cpu_percent, mem_percent, mem_usage_mb
                                if container_name not in self.docker_metrics_buffer:
                                    self.docker_metrics_buffer[container_name] = {
                                        "name": container_name
                                    }
                                self.docker_metrics_buffer[container_name][metric_type] = value
            except Exception as e:
                self.log.error(f"컬렉터 {collector_name} 처리 중 오류: {e}")

        # Update SystemInfoWidget with aggregated CPU data
        try:
            sys_info_widget = self.query_one(SystemInfoWidget)
            if total_cpu_cores > 0:
                sys_info_widget.cpu_usage_overall = total_cpu_sum / total_cpu_cores
            else:
                sys_info_widget.cpu_usage_overall = 0.0  # Avoid division by zero
            sys_info_widget.cpu_usage_per_core = temp_per_core_cpu
        except NoMatches:
            self.log.warning(
                "SystemInfoWidget을 찾을 수 없어 CPU 데이터를 업데이트하지 못했습니다."
            )

        # Update TopProcessesWidget
        if all_top_processes_data:  # Check if data was collected
            try:
                top_procs_widget = self.query_one(TopProcessesWidget)
                top_procs_widget.update_processes(all_top_processes_data)
            except NoMatches:
                self.log.warning("TopProcessesWidget을 찾을 수 없어 업데이트하지 못했습니다.")

        # Update DockerStatsWidget
        current_docker_stats_list = list(self.docker_metrics_buffer.values())
        if current_docker_stats_list:  # Check if there's any docker data
            try:
                docker_stats_widget = self.query_one(DockerStatsWidget)
                docker_stats_widget.update_docker_stats(current_docker_stats_list)
            except NoMatches:
                self.log.warning("DockerStatsWidget을 찾을 수 없어 업데이트하지 못했습니다.")

    def update_widget_data(self, uri: str, value: Any, temp_per_core_cpu: Dict[str, float]) -> None:
        """수집된 메트릭을 기반으로 해당 위젯의 데이터를 업데이트합니다."""
        try:
            if uri.startswith("system.cpu.core") and isinstance(value, (int, float)):
                temp_per_core_cpu[uri] = float(value)  # Aggregated later
            elif uri == "system.memory.used_percent" and isinstance(value, (int, float)):
                self.query_one(SystemInfoWidget).mem_usage_percent = float(value)
            elif uri == "system.uptime.description":  # UptimeCollector now returns this
                self.query_one(UptimeWidget).uptime_str = str(value)
            elif uri == "kernel.dmesg.errors":
                if isinstance(value, (int, float)):
                    self.query_one(DmesgErrorsWidget).error_count = int(value)
            # Docker metrics are handled by populating self.docker_metrics_buffer
            # and then updating the DockerStatsWidget in run_metric_collection_background
        except NoMatches:
            # This can happen if a widget is not found, e.g. during app startup/shutdown
            self.log.warning(
                f"'{uri}'에 대한 위젯을 찾을 수 없습니다. UI가 아직 준비되지 않았을 수 있습니다."
            )
        except Exception as e:
            self.log.error(f"위젯 데이터 업데이트 중 오류 ({uri}: {value}): {e}")

    async def on_shutdown_request(self, _event: Any) -> None:
        """애플리케이션 종료 요청 시 호출됩니다."""
        self.log.info("애플리케이션 종료 요청 수신...")
        log_writer = globals.get_log_writer_instance()
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

                # Ensure queue processing is complete
                if hasattr(log_writer, "queue") and hasattr(log_writer.queue, "join"):
                    self.log.info("log_writer.queue.join() 대기 중...")
                    try:
                        # Allow some time for the queue to be processed
                        await asyncio.wait_for(log_writer.queue.join(), timeout=5.0)
                        self.log.info("Log writer queue 처리가 완료되었습니다.")
                    except asyncio.TimeoutError:
                        self.log.warning("log_writer.queue.join() 대기 시간 초과.")
                    except Exception as e_join:
                        self.log.error(f"log_writer.queue.join() 중 오류 발생: {e_join}")

                # Cancel the background task
                if hasattr(log_writer, "task") and log_writer.task and not log_writer.task.done():
                    self.log.info("LogWriter 백그라운드 작업 취소 중...")
                    log_writer.task.cancel()
                    try:
                        await log_writer.task  # Wait for the task to acknowledge cancellation
                    except asyncio.CancelledError:
                        self.log.info("LogWriter 백그라운드 작업이 성공적으로 취소되었습니다.")
                    except Exception as e_task_cancel:
                        # Log any other errors that might occur during task cancellation
                        self.log.error(f"취소된 LogWriter 작업 대기 중 오류 발생: {e_task_cancel}")
            except Exception as e:  # Catch-all for other issues during shutdown logic
                self.log.error(f"LogWriter 종료 처리 중 예기치 않은 오류 발생: {e}")
        self.log.info("종료 완료.")
