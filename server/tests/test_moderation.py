"""Block + report behaviour against an in-memory fake DB.
Run from server/:  python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import fake_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402


def make_world():
    fake = fake_db.install()
    import accounts, account_deletion, blocks, challenges, chat, friends, messages, reports  # noqa
    for uid, name in (("uA", "alice"), ("uB", "bob"), ("uC", "carol")):
        fake.reference(f"users/{uid}").set({"username": name.title(), "bio": f"hi from {name}"})
        fake.reference(f"usernames/{name}").set(uid)
    return fake, dict(accounts=accounts, account_deletion=account_deletion, blocks=blocks,
                      challenges=challenges, chat=chat, friends=friends, messages=messages, reports=reports)


def befriend(m, fake, a="uA", an="Alice", b="uB", bn="Bob"):
    fake.reference(f"friends/{a}/{b}").set({"username": bn, "since": 1})
    fake.reference(f"friends/{b}/{a}").set({"username": an, "since": 1})


class BlockTests(unittest.TestCase):
    def setUp(self):
        self.fake, self.m = make_world()

    def status(self, fn, *a, **k):
        try:
            fn(*a, **k)
            return 200
        except HTTPException as e:
            return e.status_code, e.detail

    def test_block_ends_friendship_and_records_both_indexes(self):
        befriend(self.m, self.fake)
        self.m["blocks"].block("uA", "bob")
        self.assertIsNone(self.fake.reference("friends/uA/uB").get())
        self.assertIsNone(self.fake.reference("friends/uB/uA").get())
        self.assertIsNotNone(self.fake.reference("blocks/uA/uB").get())
        self.assertTrue(self.fake.reference("blocked_by/uB/uA").get())
        self.assertEqual([b["username"] for b in self.m["blocks"].list_blocked("uA")], ["Bob"])

    def test_cannot_block_self_or_unknown(self):
        self.assertEqual(self.status(self.m["blocks"].block, "uA", "alice")[0], 400)
        self.assertEqual(self.status(self.m["blocks"].block, "uA", "nobody")[0], 404)

    def test_friend_request_refused_both_directions_with_different_wording(self):
        self.m["blocks"].block("uA", "bob")
        # blocker is told plainly
        code, detail = self.status(self.m["friends"].send_request, "uA", "Alice", "bob")
        self.assertEqual(code, 403); self.assertIn("unblock", detail)
        # blocked player gets a neutral refusal that does NOT say 'blocked'
        code, detail = self.status(self.m["friends"].send_request, "uB", "Bob", "alice")
        self.assertEqual(code, 403); self.assertNotIn("block", detail.lower())

    def test_challenge_and_dm_refused(self):
        self.m["blocks"].block("uA", "bob")
        self.assertEqual(self.status(self.m["challenges"].create_challenge, "uB", "Bob", "alice")[0], 403)
        self.assertEqual(self.status(self.m["challenges"].create_challenge, "uA", "Alice", "bob")[0], 403)
        befriend(self.m, self.fake)   # even if a stale friendship existed
        self.assertEqual(self.status(self.m["messages"].send_message, "uB", "Bob", "alice", "hi")[0], 403)

    def test_unblock_restores_interaction(self):
        self.m["blocks"].block("uA", "bob")
        self.m["blocks"].unblock("uA", "bob")
        self.assertIsNone(self.fake.reference("blocks/uA/uB").get())
        self.assertIsNone(self.fake.reference("blocked_by/uB/uA").get())
        self.assertEqual(self.status(self.m["friends"].send_request, "uB", "Bob", "alice"), 200)

    def test_pending_requests_and_challenges_hidden_from_blocker_only(self):
        self.m["friends"].send_request("uB", "Bob", "alice")
        self.m["challenges"].create_challenge("uB", "Bob", "alice")
        self.assertEqual(len(self.m["friends"].list_incoming("uA")), 1)
        self.assertEqual(len(self.m["challenges"].list_incoming("uA")), 1)
        self.m["blocks"].block("uA", "bob")
        self.assertEqual(self.m["friends"].list_incoming("uA"), [])
        self.assertEqual(self.m["challenges"].list_incoming("uA"), [])

    def test_accept_after_block_refused(self):
        rec = self.m["friends"].send_request("uB", "Bob", "alice")
        ch = self.m["challenges"].create_challenge("uB", "Bob", "alice")
        self.m["blocks"].block("uA", "bob")
        self.assertEqual(self.status(self.m["friends"].accept, rec["request_id"], "uA")[0], 403)
        self.assertEqual(self.status(self.m["challenges"].accept, ch["challenge_id"], "uA")[0], 403)

    def test_game_chat_hidden_from_blocker_but_still_visible_to_others(self):
        self.m["chat"].send_message("g1", "uB", "Bob", "you stink")
        self.m["chat"].send_message("g1", "uA", "Alice", "hello")
        self.m["blocks"].block("uA", "bob")
        self.assertEqual([x["text"] for x in self.m["chat"].list_messages("g1", viewer_uid="uA")], ["hello"])
        self.assertEqual(len(self.m["chat"].list_messages("g1", viewer_uid="uB")), 2)
        self.assertEqual(len(self.m["chat"].list_messages("g1")), 2)

    def test_delete_for_user_removes_blocks_both_ways(self):
        self.m["blocks"].block("uA", "bob")      # A blocked B
        self.m["blocks"].block("uC", "alice")    # C blocked A
        self.m["blocks"].delete_for_user("uA")
        for path in ("blocks/uA", "blocked_by/uB/uA", "blocked_by/uA", "blocks/uC/uA"):
            self.assertIsNone(self.fake.reference(path).get(), path)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.fake, self.m = make_world()

    def test_dm_report_copies_only_reported_players_messages(self):
        befriend(self.m, self.fake)
        self.m["messages"].send_message("uB", "Bob", "alice", "nasty 1")
        self.m["messages"].send_message("uA", "Alice", "bob", "please stop")
        self.m["messages"].send_message("uB", "Bob", "alice", "nasty 2")
        r = self.m["reports"].submit("uA", "Alice", "bob", "dm", "harassment", "  he keeps at it ")
        self.assertEqual([x["text"] for x in r["excerpt"]], ["nasty 1", "nasty 2"])
        self.assertEqual(r["details"], "he keeps at it")
        self.assertEqual((r["reporter_uid"], r["target_uid"], r["status"]), ("uA", "uB", "open"))
        self.assertIsNotNone(self.fake.reference(f"reports/{r['report_id']}").get())

    def test_chat_report_snapshots_chat_and_profile_report_snapshots_bio(self):
        self.m["chat"].send_message("g9", "uB", "Bob", "rude")
        r = self.m["reports"].submit("uA", "Alice", "bob", "chat", "hate", "", verified_game_id="g9")
        self.assertEqual(r["game_id"], "g9"); self.assertEqual(r["excerpt"][0]["text"], "rude")
        p = self.m["reports"].submit("uA", "Alice", "bob", "profile", "inappropriate_image")
        self.assertEqual(p["profile_snapshot"], {"bio": "hi from bob"})

    def test_validation(self):
        R = self.m["reports"].submit
        for args, code in ((("uA", "Alice", "alice", "profile", "spam"), 400),        # self
                           (("uA", "Alice", "bob", "nonsense", "spam"), 400),          # kind
                           (("uA", "Alice", "bob", "profile", "nonsense"), 400),       # reason
                           (("uA", "Alice", "nobody", "profile", "spam"), 404),        # unknown target
                           (("uA", "Alice", "bob", "profile", "spam", "x" * 501), 400)):
            with self.assertRaises(HTTPException) as cm:
                R(*args)
            self.assertEqual(cm.exception.status_code, code, args)

    def test_daily_cap(self):
        for _ in range(self.m["reports"].MAX_REPORTS_PER_DAY):
            self.m["reports"].submit("uA", "Alice", "bob", "other", "spam")
        with self.assertRaises(HTTPException) as cm:
            self.m["reports"].submit("uA", "Alice", "bob", "other", "spam")
        self.assertEqual(cm.exception.status_code, 429)
        # another reporter is unaffected
        self.m["reports"].submit("uC", "Carol", "bob", "other", "spam")

    def test_account_deletion_redacts_reports(self):
        befriend(self.m, self.fake)
        self.m["messages"].send_message("uB", "Bob", "alice", "nasty")
        against_b = self.m["reports"].submit("uA", "Alice", "bob", "dm", "harassment", "details here")
        by_b = self.m["reports"].submit("uB", "Bob", "carol", "profile", "spam", "b's complaint")
        self.m["reports"].anonymize_for_deleted_user("uB")
        a = self.fake.reference(f"reports/{against_b['report_id']}").get()
        self.assertEqual(a["target_username"], "Deleted user"); self.assertNotIn("target_uid", a)
        self.assertNotIn("excerpt", a); self.assertNotIn("details", a)
        self.assertEqual(a["reporter_username"], "Alice")            # the reporter is untouched
        b = self.fake.reference(f"reports/{by_b['report_id']}").get()
        self.assertEqual(b["reporter_username"], "Deleted user"); self.assertNotIn("reporter_uid", b)
        self.assertEqual(b["details"], "b's complaint")              # complaint about someone else stays


if __name__ == "__main__":
    unittest.main()
