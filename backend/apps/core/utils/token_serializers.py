from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from apps.core.utils.tokens import DailyExpiryRefreshToken


class DailyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """TokenObtainPair serializer using tokens that expire at 23:00 Bangkok time."""

    token_class = DailyExpiryRefreshToken


class DailyTokenRefreshSerializer(TokenRefreshSerializer):
    """TokenRefresh serializer using tokens that expire at 23:00 Bangkok time.

    When ROTATE_REFRESH_TOKENS is True the replacement refresh token is also
    issued with the daily expiry rule.
    """

    token_class = DailyExpiryRefreshToken
