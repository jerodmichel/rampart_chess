"""Tiny in-memory stand-in for firebase_admin.db - just enough of the
Reference API (get/set/update/delete/push/order_by_child().equal_to().get())
for the modules under test. Resolves {".sv": "timestamp"} to real, strictly increasing
epoch milliseconds. Install with fake_db.install()."""

import copy
import itertools
import time

from firebase_admin import db as real_db

_tick = itertools.count(1)


def _now_ms():
    # Real epoch milliseconds (modules compare against time.time()), made
    # strictly increasing so ordering assertions are deterministic.
    return int(time.time() * 1000) + next(_tick)
_push_ids = itertools.count(1)


def _resolve(value):
    if isinstance(value, dict):
        if value == {".sv": "timestamp"}:
            return _now_ms()
        return {k: _resolve(v) for k, v in value.items()}
    return copy.deepcopy(value)


# Mirrors io_src_dev/database.rules.json: Realtime Database REFUSES
# order_by_child on a path with no .indexOn ("Index not defined"), so the fake
# does too - otherwise a query on an un-indexed path passes every test here
# and only fails against the real database. Keep in sync with that file.
INDEXED = {"challenges": {"from_uid", "to_uid"}, "friend_requests": {"from_uid", "to_uid"}}


class FakeDB:
    def __init__(self):
        self.root = {}

    def reference(self, path=""):
        return Ref(self, [p for p in path.split("/") if p])


class Ref:
    def __init__(self, fake, parts):
        self.fake, self.parts = fake, parts

    @property
    def key(self):
        return self.parts[-1] if self.parts else None

    def _walk(self, create=False):
        node = self.fake.root
        for p in self.parts:
            if not isinstance(node, dict):
                return None
            if p not in node:
                if not create:
                    return None
                node[p] = {}
            node = node[p]
        return node

    def get(self):
        node = self._walk()
        return copy.deepcopy(node) if node is not None else None

    def set(self, value):
        if not self.parts:
            self.fake.root = _resolve(value)
            return
        parent = Ref(self.fake, self.parts[:-1])._walk(create=True)
        parent[self.parts[-1]] = _resolve(value)

    def update(self, changes):
        node = self._walk(create=True)
        for k, v in changes.items():
            if v is None:
                node.pop(k, None)
            else:
                node[k] = _resolve(v)

    def delete(self):
        if not self.parts:
            self.fake.root = {}
            return
        parent = Ref(self.fake, self.parts[:-1])._walk()
        if isinstance(parent, dict):
            parent.pop(self.parts[-1], None)

    def push(self, value):
        key = f"-push{next(_push_ids):05d}"
        child = Ref(self.fake, self.parts + [key])
        child.set(value)
        return child

    def order_by_child(self, field):
        path = "/".join(self.parts)
        if field not in INDEXED.get(path, set()):
            raise RuntimeError(f'Index not defined, add ".indexOn": "{field}", for path "/{path}", to the rules')
        return Query(self, field)


class Query:
    def __init__(self, ref, field):
        self.ref, self.field, self.value = ref, field, None

    def equal_to(self, value):
        self.value = value
        return self

    def get(self):
        node = self.ref.get() or {}
        return {k: v for k, v in node.items() if isinstance(v, dict) and v.get(self.field) == self.value} or None


def install():
    fake = FakeDB()
    real_db.reference = fake.reference
    return fake
