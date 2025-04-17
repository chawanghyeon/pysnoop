# tests/test_uri_tree.py
from server.fs.tree import URITree


def test_uri_insertion():
    tree = URITree()
    assert not tree.exists("/user/agent1/metric1")
    tree.insert_uri("/user/agent1/metric1")
    assert tree.exists("/user/agent1/metric1")
    assert tree.exists("/user/agent1")
    assert tree.exists("/user")


test_uri_insertion()
