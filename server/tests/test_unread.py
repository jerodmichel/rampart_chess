"""DM unread flag (drives the header notification bell).
Run from server/:  python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import fake_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402


class UnreadTests(unittest.TestCase):
    def setUp(self):
        self.fake = fake_db.install()
        import accounts, blocks, messages  # noqa
        self.m = messages; self.blocks = blocks
        for uid, name in (("uA", "alice"), ("uB", "bob"), ("uC", "carol")):
            self.fake.reference(f"users/{uid}").set({"username": name.title()})
            self.fake.reference(f"usernames/{name}").set(uid)
        for a, b in (("uA", "uB"), ("uA", "uC")):
            self.fake.reference(f"friends/{a}/{b}").set({"since": 1})
            self.fake.reference(f"friends/{b}/{a}").set({"since": 1})

    def unread(self, uid):
        return sorted(t["other_username"] for t in self.m.list_inbox(uid) if t["unread"])

    def test_new_message_is_unread_for_recipient_only(self):
        self.m.send_message("uB", "Bob", "alice", "hi")
        self.assertEqual(self.unread("uA"), ["Bob"])
        self.assertEqual(self.unread("uB"), [])

    def test_mark_read_clears_and_is_per_thread(self):
        self.m.send_message("uB", "Bob", "alice", "hi")
        self.m.send_message("uC", "Carol", "alice", "yo")
        self.assertEqual(self.unread("uA"), ["Bob", "Carol"])
        self.m.mark_read("uA", "bob")
        self.assertEqual(self.unread("uA"), ["Carol"])

    def test_reply_flips_the_flag(self):
        self.m.send_message("uB", "Bob", "alice", "hi")
        self.m.mark_read("uA", "bob")
        self.m.send_message("uA", "Alice", "bob", "hello")
        self.assertEqual(self.unread("uA"), [])
        self.assertEqual(self.unread("uB"), ["Alice"])

    def test_two_unread_messages_in_one_thread_count_once(self):
        self.m.send_message("uB", "Bob", "alice", "1"); self.m.send_message("uB", "Bob", "alice", "2")
        self.assertEqual(self.unread("uA"), ["Bob"])

    def test_old_threads_without_the_field_are_not_unread(self):
        self.fake.reference("user_threads/uA/uA_uB").set(
            {"other_uid": "uB", "other_username": "Bob", "last_text": "old", "last_timestamp": 5})
        self.assertEqual(self.unread("uA"), [])
        self.assertIs(self.m.list_inbox("uA")[0]["unread"], False)

    def test_blocked_players_thread_never_alerts(self):
        self.m.send_message("uB", "Bob", "alice", "hi")
        self.blocks.block("uA", "bob")
        self.assertEqual(self.unread("uA"), [])

    def test_mark_read_edge_cases(self):
        self.m.mark_read("uA", "bob")                       # never messaged: harmless no-op
        self.assertEqual(self.m.list_inbox("uA"), [])
        with self.assertRaises(HTTPException) as cm:
            self.m.mark_read("uA", "nobody")
        self.assertEqual(cm.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
