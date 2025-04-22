# server/fs/tree.py


class URINode:
    def __init__(self, name):
        self.name = name
        self.children = {}  # key: str, value: URINode

    def add_child(self, name):
        if name not in self.children:
            self.children[name] = URINode(name)
        return self.children[name]

    def get_child(self, name):
        return self.children.get(name)


class URITree:
    def __init__(self):
        self.root = URINode("/")

    def insert_uri(self, uri: str):
        parts = [p for p in uri.strip("/").split("/") if p]
        node = self.root
        for part in parts:
            node = node.add_child(part)

    def exists(self, uri: str) -> bool:
        parts = [p for p in uri.strip("/").split("/") if p]
        node = self.root
        for part in parts:
            node = node.get_child(part)
            if node is None:
                return False
        return True
