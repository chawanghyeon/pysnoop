# pysnoop 🚀 - 실시간 시스템 모니터링 대시보드

## 📄 프로젝트 소개

**pysnoop**은 Python으로 개발된 터미널 기반의 실시간 시스템 모니터링 대시보드입니다. Textual 프레임워크를 사용하여 다양한 시스템 정보를 인터랙티브하게 시각화하고, 주요 메트릭을 주기적으로 수집하여 로깅합니다.

## ✨ 주요 기능

* **실시간 시스템 정보:**
    * 시스템 가동 시간(Uptime) 표시
    * CPU 전체 및 코어별 사용량 표시
    * 메모리 사용량 표시
    * dmesg 커널 오류 수 표시
* **프로세스 모니터링:** CPU 사용량 기준 상위 프로세스 목록 표시
* **Docker 컨테이너 통계:** 실행 중인 Docker 컨테이너의 CPU, 메모리 사용량 표시
* **데이터 로깅:** 수집된 메트릭 정보를 `logs` 디렉토리에 JSONL 형식으로 저장
* **사용자 인터페이스:**
    * 다크 모드 전환 기능 (`Ctrl+D`)
    * 현재 시간 표시

## 🛠️ 사용 기술

* **언어:** Python 3
* **주요 라이브러리:**
    * Textual: 터미널 사용자 인터페이스(TUI) 개발
    * psutil: 시스템 정보 및 프로세스 관리
* **데이터 수집:** 다양한 `collectors` 모듈을 통해 시스템 메트릭 수집 (dmesg, Docker, psutil 등)

## ⚙️ 설치 및 실행 방법

### 선수 조건

* Python 3.8 이상
* `pip` (Python 패키지 설치 도구)
* `docker` CLI (Docker 통계 수집 시 필요)
* `sudo` 권한 (dmesg 정보 수집 시 필요할 수 있음)

### 설치

1.  프로젝트 저장소를 클론합니다.
    ```bash
    git clone [프로젝트 저장소 URL]
    cd pysnoop
    ```
2.  필요한 Python 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```

### 실행

1.  메인 애플리케이션을 실행합니다.
    ```bash
    python main.py
    ```
2.  터미널에 대시보드가 나타납니다.
    * `q` 또는 `Ctrl+C` 키로 종료할 수 있습니다.
    * `Ctrl+D` 키로 다크 모드를 전환할 수 있습니다.

## 📸 실행 화면
![alt text](<Screenshot 2025-05-22 at 1.03.09 AM.png>)

## 🖥️ 테스트 환경

* **운영체제:** Ubuntu

## 📝 추가 정보

* 수집된 메트릭은 프로젝트 루트의 `logs` 디렉토리 내에 `metrics-YYYYMMDD.jsonl` 형식의 파일로 저장됩니다.
* pre-commit 훅을 사용하여 코드 스타일(black, isort) 및 정적 분석(flake8, mypy)을 관리합니다.

---
