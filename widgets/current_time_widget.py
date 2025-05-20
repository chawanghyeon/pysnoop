# widgets/current_time_widget.py

import datetime

from textual.widgets import Static


class CurrentTimeWidget(Static):
    """현재 시간을 표시하는 위젯"""

    def on_mount(self) -> None:
        """위젯 마운트 시 호출됩니다."""
        self.update_time()
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        """현재 시간으로 위젯을 업데이트합니다."""
        self.update(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
