"""Tests for the user accounts in logic.py.  Run:  python3 test_users.py"""
import unittest
import logic


class UserTests(unittest.TestCase):
    def setUp(self):
        self.root = logic.new_store()  # shaped like the old data file

    def register(self, name="alice", pw="password1"):
        return logic.register_user(self.root, name, pw, pw)

    def test_register_and_login(self):
        user = self.register()
        self.assertNotEqual(user["password_hash"], "password1")  # never plain text
        self.assertEqual(logic.authenticate(self.root, "alice", "password1")["id"], user["id"])

    def test_login_is_case_insensitive_for_username(self):
        self.register("Alice")
        self.assertTrue(logic.authenticate(self.root, "ALICE", "password1"))

    def test_wrong_password_and_unknown_user_same_message(self):
        self.register()
        with self.assertRaises(logic.ValidationError) as a:
            logic.authenticate(self.root, "alice", "wrongpass")
        with self.assertRaises(logic.ValidationError) as b:
            logic.authenticate(self.root, "nobody", "password1")
        self.assertEqual(str(a.exception), str(b.exception))

    def test_duplicate_username_any_case(self):
        self.register("alice")
        with self.assertRaises(logic.ValidationError):
            self.register("ALICE")

    def test_bad_usernames(self):
        for bad in ("", "ab", "has space", "x" * 21, "bad!name"):
            with self.assertRaises(logic.ValidationError):
                self.register(bad)

    def test_bad_passwords(self):
        with self.assertRaises(logic.ValidationError):
            logic.register_user(self.root, "alice", "short", "short")
        with self.assertRaises(logic.ValidationError):
            logic.register_user(self.root, "alice", "password1", "password2")

    def test_data_is_separate_per_user(self):
        a, b = self.register("alice"), self.register("bob")
        logic.add_note(logic.user_store(self.root, a["id"]), "alice's note")
        self.assertEqual(logic.user_store(self.root, b["id"])["notes"], [])

    def test_first_user_inherits_old_data_second_does_not(self):
        logic.add_note(self.root, "old note")  # data from before accounts
        a, b = self.register("alice"), self.register("bob")
        self.assertEqual(len(logic.user_store(self.root, a["id"])["notes"]), 1)
        self.assertEqual(logic.user_store(self.root, b["id"])["notes"], [])
        self.assertNotIn("notes", self.root)  # moved, not copied


if __name__ == "__main__":
    unittest.main()
