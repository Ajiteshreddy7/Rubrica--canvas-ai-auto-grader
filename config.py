"""
Centralized configuration management with validation.
"""

import json
import sys
from pathlib import Path
from typing import List, Optional, Union
from pydantic import BaseModel, field_validator

CONFIG_FILE = Path(__file__).parent / "config.json"


class CanvasConfig(BaseModel):
    base_url: str
    api_token: str
    course_id: str

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v):
        if not v or v == "https://your-institution.instructure.com/":
            raise ValueError("canvas.base_url must be set to your institution's Canvas URL")
        return v.rstrip("/")

    @field_validator("api_token")
    @classmethod
    def validate_api_token(cls, v):
        if not v or v == "YOUR_CANVAS_API_TOKEN_HERE":
            raise ValueError("canvas.api_token must be set. Generate one in Canvas > Account > Settings > New Access Token")
        return v

    @field_validator("course_id")
    @classmethod
    def validate_course_id(cls, v):
        if not v or v == "YOUR_COURSE_ID":
            raise ValueError("canvas.course_id must be set to your Canvas course ID")
        return v


class GradingConfig(BaseModel):
    clone_path: str = "assignments"
    cleanup_days: int = 7
    assignment_filter: Union[str, List[str]] = ""
    post_to_canvas: bool = False

    @field_validator("assignment_filter", mode="before")
    @classmethod
    def normalize_filter(cls, v):
        """Accept both a single string and a list of strings."""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [v] if v else []
        return []


class DaemonConfig(BaseModel):
    poll_interval_seconds: int = 300


class AppConfig(BaseModel):
    canvas: CanvasConfig
    grading: GradingConfig = GradingConfig()
    daemon: DaemonConfig = DaemonConfig()


_config: Optional[AppConfig] = None


def load_config() -> AppConfig:
    """Load and validate configuration from config.json."""
    global _config
    if _config is not None:
        return _config

    if not CONFIG_FILE.exists():
        print(f"ERROR: {CONFIG_FILE} not found.")
        print("Copy config.example.json to config.json and fill in your values.")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {CONFIG_FILE}: {e}")
        sys.exit(1)

    try:
        _config = AppConfig(**raw)
    except Exception as e:
        print(f"ERROR: Invalid configuration: {e}")
        sys.exit(1)

    return _config


def get_config_dict() -> dict:
    """Get config as a plain dict (for backward compatibility)."""
    config = load_config()
    return config.model_dump()
