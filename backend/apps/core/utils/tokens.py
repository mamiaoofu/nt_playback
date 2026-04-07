from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

_BANGKOK_TZ = ZoneInfo('Asia/Bangkok')
_EXPIRE_HOUR = 23  # 23:00 Bangkok time


def _get_daily_expiry() -> datetime:
    """Return the next 23:00 Bangkok time as a timezone-aware datetime.

    If the current time is already at or past 23:00, returns 23:00 tomorrow.
    """
    now = datetime.now(_BANGKOK_TZ)
    target = now.replace(hour=_EXPIRE_HOUR, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return target


class DailyExpiryAccessToken(AccessToken):
    """Access token that always expires at 23:00 Bangkok time."""

    def set_exp(self, claim='exp', from_time=None, lifetime=None):
        self.payload[claim] = int(_get_daily_expiry().timestamp())


class DailyExpiryRefreshToken(RefreshToken):
    """Refresh token that always expires at 23:00 Bangkok time.

    Also produces a DailyExpiryAccessToken when .access_token is accessed,
    ensuring that token rotation and cookie-based refresh both honour the
    daily expiry rule.
    """

    access_token_class = DailyExpiryAccessToken

    def set_exp(self, claim='exp', from_time=None, lifetime=None):
        self.payload[claim] = int(_get_daily_expiry().timestamp())
