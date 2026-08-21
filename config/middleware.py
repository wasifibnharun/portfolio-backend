import logging
import time

request_logger = logging.getLogger("request_timing")


class RequestTimingMiddleware:
    """
    Log every request and expose its processing time in a response
    header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.perf_counter()

        response = self.get_response(request)

        elapsed_ms = (
            time.perf_counter() - started_at
        ) * 1000

        formatted_time = f"{elapsed_ms:.2f} ms"

        response["X-Response-Time"] = formatted_time

        request_logger.info(
            "%s %s -> %s (%s)",
            request.method,
            request.path,
            response.status_code,
            formatted_time,
        )

        return response