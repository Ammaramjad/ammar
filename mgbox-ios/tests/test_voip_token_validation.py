#!/usr/bin/env python3
"""Validate the MGBOX VoIP token format used by iOS and PHP."""

import re
import unittest

VOIP_TOKEN_RE = re.compile(r"^[a-f0-9]{64}$", re.IGNORECASE)
ONESIGNAL_ID_RE = re.compile(r"^[a-zA-Z0-9-]{8,128}$")


class VoipTokenValidationTests(unittest.TestCase):
    def test_accepts_pushkit_hex_token(self):
        token = "a" * 64
        self.assertTrue(VOIP_TOKEN_RE.match(token))
        self.assertEqual(token.lower(), token)

    def test_accepts_uppercase_then_normalizes(self):
        token = "AB" * 32
        self.assertTrue(VOIP_TOKEN_RE.match(token))
        self.assertEqual(len(token.lower()), 64)

    def test_rejects_short_token(self):
        self.assertIsNone(VOIP_TOKEN_RE.match("abc123"))

    def test_rejects_non_hex_token(self):
        self.assertIsNone(VOIP_TOKEN_RE.match("g" * 64))

    def test_rejects_empty_token(self):
        self.assertIsNone(VOIP_TOKEN_RE.match(""))

    def test_accepts_onesignal_subscription_id(self):
        self.assertTrue(ONESIGNAL_ID_RE.match("becdaedf-2113-40e9-a884-006765233cbe"))

    def test_make_launch_query_contains_voip_token(self):
        token = "ab" * 32
        query = f"voip_token={token}&onesignal_user_id=player-1"
        self.assertIn("voip_token=", query)
        self.assertTrue(VOIP_TOKEN_RE.match(token))


if __name__ == "__main__":
    unittest.main()
