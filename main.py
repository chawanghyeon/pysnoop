# main.py

"""
Main entry point for the Pysnoop Monitoring Dashboard application.
Initializes and runs the Textual application.
"""


from app import MonitoringDashboardApp  # Import the main app class


def main_dashboard() -> None:
    """메인 대시보드 애플리케이션을 실행합니다."""
    print("애플리케이션 초기화 중 (대시보드 모드)...")
    # Consider any pre-initialization steps if needed here
    # For example, setting up logging for the very start of the app

    # Create an instance of the app
    app = MonitoringDashboardApp()

    # Run the app
    app.run()


if __name__ == "__main__":
    main_dashboard()
