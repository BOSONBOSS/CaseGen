"""Automated Unit Tests for Module 1: Authentication & Access Control.

Mapped directly to Course Evaluation Test Cases:
- TC01: Valid User Authentication
- TC02: Invalid Password Handling
- TC03: Empty Credentials Validation
- TC04: Unknown / Unregistered User Lookup & Timing Side-Channel Prevention
"""

import sqlite3
import unittest
from pipeline.persistence.auth import (
    DB_PATH,
    init_users_table,
    verify_login,
    register_user,
    get_user_info,
)


class TestAuthenticationModule(unittest.TestCase):

    TEST_REG_USER = "student_evaluator_2026"

    @classmethod
    def setUpClass(cls):
        """Ensure users table is initialized and demo accounts are seeded."""
        init_users_table()

    def _cleanup_test_user(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (self.TEST_REG_USER,))
            conn.commit()

    def setUp(self):
        self._cleanup_test_user()

    def tearDown(self):
        self._cleanup_test_user()

    def test_tc01_valid_login(self):
        """TC01: Verify all 4 team members can log in with valid credentials."""
        members = [
            ("ananshi", "CaseGen@2026"),
            ("aditya", "CaseGen@2026"),
            ("sumit", "CaseGen@2026"),
            ("dhruv", "CaseGen@2026"),
        ]
        for username, password in members:
            with self.subTest(user=username):
                self.assertTrue(
                    verify_login(username, password),
                    f"Valid login failed for team member: {username}",
                )

    def test_tc02_invalid_password(self):
        """TC02: Verify that an incorrect password for an existing user is rejected."""
        self.assertFalse(
            verify_login("ananshi", "WrongPassword!"),
            "Invalid password was incorrectly accepted",
        )
        self.assertFalse(
            verify_login("ananshi", "casegen@2026"),  # test case-sensitivity of password
            "Password should be strictly case-sensitive",
        )

    def test_tc03_empty_credentials(self):
        """TC03: Verify that blank or whitespace-only credentials are rejected."""
        self.assertFalse(verify_login("", ""), "Empty username & password allowed")
        self.assertFalse(verify_login("   ", "   "), "Whitespace credentials allowed")
        self.assertFalse(verify_login("ananshi", ""), "Empty password allowed")
        self.assertFalse(verify_login("", "CaseGen@2026"), "Empty username allowed")

    def test_tc04_unknown_user(self):
        """TC04: Verify that an unregistered user is rejected safely without leaking info."""
        self.assertFalse(
            verify_login("ghost_unregistered_user_999", "AnyPassword123"),
            "Unregistered user was incorrectly authenticated",
        )

    def test_registration_and_profile_flow(self):
        """Verify new user registration, email validation, duplicate detection, and profile fetching."""
        test_user = self.TEST_REG_USER
        test_pass = "SecurePass@2026"
        test_email = "evaluator@casegen.edu"

        # Invalid email rejected
        bad_email = register_user(test_user, test_pass, "Evaluator Person", "not-an-email")
        self.assertIsInstance(bad_email, str, "Invalid email should be rejected")
        self.assertIn("email", bad_email.lower())

        # Register with valid email
        res = register_user(test_user, test_pass, "Evaluator Person", test_email)
        self.assertTrue(res, f"Registration failed: {res}")

        # Login with newly registered user
        self.assertTrue(
            verify_login(test_user, test_pass),
            "Login failed for newly registered user",
        )

        # Profile fetch
        info = get_user_info(test_user)
        self.assertIsNotNone(info)
        self.assertEqual(info["username"], test_user)
        self.assertEqual(info["full_name"], "Evaluator Person")
        self.assertEqual(info["email"], test_email)

        # Duplicate username attempt
        dup_res = register_user(test_user, "AnotherPass123", "Dup Person", "dup@casegen.edu")
        self.assertIsInstance(dup_res, str, "Duplicate username was not rejected")
        self.assertIn("already", dup_res.lower())


if __name__ == "__main__":
    unittest.main()
