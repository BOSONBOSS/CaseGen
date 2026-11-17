"""Automated Unit Tests for Module 1: Authentication & Access Control.

Mapped to Course Evaluation Test Cases:
- TC01: Valid User Authentication
- TC02: Invalid Password Handling
- TC03: Empty Credentials Validation
- TC04: Unknown / Unregistered User Lookup
"""

import unittest
import sqlite3
from pipeline.persistence.auth import (
    init_users_table,
    verify_login,
    register_user,
    DB_PATH,
)


class TestAuthenticationModule(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Ensure users table is initialized and demo accounts are seeded."""
        init_users_table()

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
                    f"Valid login failed for {username}",
                )

    def test_tc02_invalid_password(self):
        """TC02: Verify that an incorrect password for an existing user is rejected."""
        self.assertFalse(
            verify_login("ananshi", "WrongPassword!"),
            "Invalid password was incorrectly accepted",
        )
        self.assertFalse(
            verify_login("ananshi", "casegen@2026"),  # test case-sensitivity of password
            "Password should be case-sensitive",
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
            verify_login("ghost_unregistered_user", "AnyPassword123"),
            "Unregistered user was incorrectly authenticated",
        )

    def test_registration_flow(self):
        """Verify new user registration and duplicate user detection."""
        test_user = "eval_student_auto"
        test_pass = "SecurePass@2026"

        # Register
        res = register_user(test_user, test_pass, "Auto Tester", "240888")
        self.assertTrue(res, f"Registration failed: {res}")

        # Login with newly registered user
        self.assertTrue(
            verify_login(test_user, test_pass),
            "Login failed for newly registered user",
        )

        # Duplicate username attempt
        dup_res = register_user(test_user, "AnotherPass123", "Dup Person", "240889")
        self.assertIsInstance(dup_res, str, "Duplicate username was not rejected")
        self.assertIn("already", dup_res.lower())


if __name__ == "__main__":
    unittest.main()
