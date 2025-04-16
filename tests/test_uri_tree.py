# tests/test_uri_tree.py
import sys
import os
import pytest

# 프로젝트 루트 기준 상대 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.fs.tree import URITree


def test_uri_insertion():
    tree = URITree()
    assert not tree.exists("/user/agent1/metric1")
    tree.insert_uri("/user/agent1/metric1")
    assert tree.exists("/user/agent1/metric1")
    assert tree.exists("/user/agent1")
    assert tree.exists("/user")


test_uri_insertion()
