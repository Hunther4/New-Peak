"""
Rate limiter module alias for core.limiter.
Provides limiter instance and get_rate_limit_str helper.
"""
from core.limiter import get_rate_limit_str, limiter

__all__ = ["limiter", "get_rate_limit_str"]
