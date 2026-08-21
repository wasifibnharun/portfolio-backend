from rest_framework.throttling import ScopedRateThrottle


class IPScopedRateThrottle(ScopedRateThrottle):
    """
    Always identify clients by IP, including authenticated users.
    """

    def get_cache_key(self, request, view):
        if not self.scope:
            return None

        ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }