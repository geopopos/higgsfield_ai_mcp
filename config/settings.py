"""
Configuration management for AI MV Director Platform
Supports development, testing, and production environments.
"""

import os
from dataclasses import dataclass


@dataclass
class AppConfig:
    env_name: str = "development"
    debug: bool = True
    default_budget_twd: float = 5000.0
    warning_budget_ratio: float = 0.80
    qa_pass_threshold: float = 0.80
    default_duration_sec: float = 8.0
    mock_mode: bool = True
    gemini_api_key: str = ""
    log_dir: str = "logs/director"


class ConfigFactory:
    @staticmethod
    def get_config() -> AppConfig:
        env = os.environ.get("APP_ENV", "development").lower()
        key = os.environ.get("GEMINI_API_KEY", "")
        budget = float(os.environ.get("SESSION_BUDGET_TWD", "5000.0"))

        if env == "production":
            return AppConfig(
                env_name="production",
                debug=False,
                default_budget_twd=budget,
                warning_budget_ratio=0.85,
                qa_pass_threshold=0.85,
                mock_mode=False,
                gemini_api_key=key,
                log_dir="/var/log/ai_mv_director",
            )
        elif env == "testing":
            return AppConfig(
                env_name="testing",
                debug=True,
                default_budget_twd=10000.0,
                warning_budget_ratio=0.90,
                qa_pass_threshold=0.70,
                mock_mode=True,
                gemini_api_key="test-key",
                log_dir="temp/test_logs",
            )
        else:
            return AppConfig(
                env_name="development",
                debug=True,
                default_budget_twd=budget,
                warning_budget_ratio=0.80,
                qa_pass_threshold=0.80,
                mock_mode=bool(not key or os.environ.get("MOCK_MODE", "true").lower() == "true"),
                gemini_api_key=key,
                log_dir="logs/director",
            )
