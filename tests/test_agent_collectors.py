# tests/test_agent_collectors.py

from datetime import datetime

import pytest

from agents.collectors.base import collector_registry

# 필요한 수집기 모두 import!


def test_all_registered_collectors_collect():
    assert len(collector_registry) > 0, "No collectors registered"

    for CollectorClass in collector_registry:
        collector = CollectorClass()
        metrics = collector.collect()

        assert isinstance(metrics, list), f"{CollectorClass.__name__} did not return a list"

        for uri, value in metrics:
            assert isinstance(uri, str), f"{CollectorClass.__name__} returned invalid URI: {uri}"
            assert isinstance(
                value, float
            ), f"{CollectorClass.__name__} returned invalid value: {value}"


def test_collected_metrics_format():
    # logger_client.py 구조와 맞추기
    user_id = "testagent"
    token = "dummy-token"
    ts = datetime.utcnow().isoformat() + "Z"
    all_metrics = []

    for CollectorClass in collector_registry:
        try:
            collector = CollectorClass()
            metrics = collector.collect()
            for uri, value in metrics:
                full_uri = f"/agent/{user_id}/{uri}"
                all_metrics.append(
                    {
                        "type": "metric",
                        "uri": full_uri,
                        "ts": ts,
                        "value": value,
                        "token": token,
                    }
                )
        except Exception as e:
            pytest.fail(f"Collector {CollectorClass.__name__} failed with exception: {e}")

    assert all_metrics, "No metrics collected"
    for m in all_metrics:
        assert "uri" in m and m["uri"].startswith("/agent/"), "Invalid URI format"
        assert isinstance(m["value"], float), "Value must be float"


def test_all_collectors_work_and_return_data():
    failures = []
    for CollectorClass in collector_registry:
        try:
            collector = CollectorClass()
            results = collector.collect()

            assert isinstance(results, list), f"{CollectorClass.__name__} returned non-list"
            assert all(
                isinstance(x, tuple) and len(x) == 2 for x in results
            ), f"{CollectorClass.__name__} returned invalid format"
            assert all(
                isinstance(uri, str) and isinstance(val, float) for uri, val in results
            ), f"{CollectorClass.__name__} returned bad types"

            if len(results) == 0:
                failures.append(f"{CollectorClass.__name__} returned no data")

        except Exception as e:
            failures.append(f"{CollectorClass.__name__} failed: {e}")

    if failures:
        pytest.fail("Some collectors failed:\n" + "\n".join(failures))
