import re

from django.core.cache import cache
from django.test import TestCase


class RequestTimingMiddlewareTests(TestCase):
    def setUp(self):
        cache.clear()

    def assert_valid_timing_header(self, response):
        self.assertIn("X-Response-Time", response)

        header_value = response["X-Response-Time"]

        self.assertIsNotNone(
            re.fullmatch(
                r"\d+\.\d{2} ms",
                header_value,
            )
        )

    def test_successful_request_is_timed_and_logged(self):
        with self.assertLogs(
            "request_timing",
            level="INFO",
        ) as captured_logs:
            response = self.client.get("/api/skills/")

        self.assertEqual(response.status_code, 200)
        self.assert_valid_timing_header(response)

        self.assertTrue(
            any(
                "GET /api/skills/ -> 200 ("
                in message
                for message in captured_logs.output
            )
        )

    def test_404_request_is_also_timed_and_logged(self):
        with self.assertLogs(
            "request_timing",
            level="INFO",
        ) as captured_logs:
            response = self.client.get(
                "/api/definitely-not-a-real-endpoint/"
            )

        self.assertEqual(response.status_code, 404)
        self.assert_valid_timing_header(response)

        self.assertTrue(
            any(
                (
                    "GET /api/definitely-not-a-real-endpoint/ "
                    "-> 404 ("
                )
                in message
                for message in captured_logs.output
            )
        )