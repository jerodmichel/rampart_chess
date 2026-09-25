"""Players page: ranking, presence, privacy settings, challenge policy.
Run from server/:  python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

import fake_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402


class PlayersTests(unittest.TestCase):
    def setUp(self):
        self.fake = fake_db.install()
        import blocks, challenges, players  # noqa
        self.p = players; self.c = challenges; self.blocks = blocks
        players._last_seen.clear()
        for uid, name, rating in (("uA", "alice", 1300), ("uB", "bob", 1450), ("uC", "carol", 1200)):
            self.fake.reference(f"users/{uid}").set({"username": name.title(), "rating": rating, "games_played": 3})
            self.fake.reference(f"usernames/{name}").set(uid)
        self.fake.reference("friends/uA/uB").set({"since": 1})
        self.fake.reference("friends/uB/uA").set({"since": 1})
        self.fake.reference("badges/uB/adept").set({"unlocked_at": 5})

    def names(self, rows):
        return [r["username"] for r in rows]

    def test_ranked_by_rating_with_badges(self):
        rows = self.p.list_players()
        self.assertEqual(self.names(rows), ["Bob", "Alice", "Carol"])
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3])
        self.assertEqual(rows[0]["badges"], {"adept": {"unlocked_at": 5}})

    def test_never_played_accounts_are_unranked_and_listed_last(self):
        self.fake.reference("users/uD").set({"username": "Dave", "rating": 1200, "games_played": 0})
        self.fake.reference("users/uE").set({"username": "Eve", "rating": 1100, "games_played": 9})
        rows = self.p.list_players()
        self.assertEqual(self.names(rows), ["Bob", "Alice", "Carol", "Eve", "Dave"])
        self.assertEqual([r["rank"] for r in rows], [1, 2, 3, 4, None])
        import ratings
        self.assertEqual(ratings.get_rank("uE")["rank"], 4)
        self.assertIsNone(ratings.get_rank("uD")["rank"])
        self.assertEqual(ratings.get_rank("uD")["total"], 4)

    def test_anonymous_viewer_can_challenge_nobody(self):
        self.assertFalse(any(r["can_challenge"] for r in self.p.list_players()))

    def test_signed_in_viewer_can_challenge_others_not_self(self):
        rows = {r["username"]: r for r in self.p.list_players("uA")}
        self.assertFalse(rows["Alice"]["can_challenge"])
        self.assertTrue(rows["Alice"]["is_me"])
        self.assertTrue(rows["Bob"]["can_challenge"])
        self.assertTrue(rows["Carol"]["can_challenge"])

    def test_presence_window_and_show_online(self):
        self.p.ping("uB")
        rows = {r["username"]: r for r in self.p.list_players()}
        self.assertTrue(rows["Bob"]["online"])
        self.assertFalse(rows["Carol"]["online"])
        self.p._last_seen["uB"] -= self.p.ONLINE_WINDOW_MS + 1
        self.assertFalse({r["username"]: r for r in self.p.list_players()}["Bob"]["online"])
        self.p.ping("uB")
        self.p.update_privacy("uB", show_online=False)
        self.assertFalse({r["username"]: r for r in self.p.list_players()}["Bob"]["online"])
        self.p.ping("uB")  # still hidden even while pinging
        self.assertFalse({r["username"]: r for r in self.p.list_players()}["Bob"]["online"])

    def test_friends_only_policy(self):
        self.p.update_privacy("uB", challenge_policy="friends")
        self.assertTrue({r["username"]: r for r in self.p.list_players("uA")}["Bob"]["can_challenge"])
        self.assertFalse({r["username"]: r for r in self.p.list_players("uC")}["Bob"]["can_challenge"])
        self.c.create_challenge("uA", "Alice", "bob")  # friend: allowed
        with self.assertRaises(HTTPException) as ctx:
            self.c.create_challenge("uC", "Carol", "bob")
        self.assertEqual(ctx.exception.status_code, 403)
        self.p.update_privacy("uB", challenge_policy="everyone")
        self.c.create_challenge("uC", "Carol", "bob")

    def test_invalid_policy_rejected(self):
        with self.assertRaises(HTTPException):
            self.p.update_privacy("uA", challenge_policy="nobody")

    def test_blocks_hide_and_disable(self):
        self.blocks.block("uA", "carol")
        rows_a = self.p.list_players("uA")
        self.assertNotIn("Carol", self.names(rows_a))
        self.assertEqual({r["username"]: r["rank"] for r in rows_a}, {"Bob": 1, "Alice": 2})
        rows_c = {r["username"]: r for r in self.p.list_players("uC")}
        self.assertFalse(rows_c["Alice"]["can_challenge"])  # blocked by Alice: no button, no reveal
        self.assertTrue(rows_c["Bob"]["can_challenge"])


if __name__ == "__main__":
    unittest.main()
