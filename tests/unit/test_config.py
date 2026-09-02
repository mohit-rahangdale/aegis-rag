"""Unit tests for configuration and settings management."""

from app.config.settings import Settings, get_settings


def test_default_settings():
    """Verify default settings values."""
    settings = Settings()
    assert settings.app_name == "aegisrag"
    assert settings.app_version == "0.1.0"
    assert settings.port == 8000
    assert settings.host == "0.0.0.0"
    assert settings.log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def test_custom_settings():
    """Verify custom environment values are respected."""
    custom = Settings(
        app_name="custom-aegis",
        app_env="production",
        debug=False,
        port=9000,
        log_level="ERROR",
    )
    assert custom.app_name == "custom-aegis"
    assert custom.is_production is True
    assert custom.is_testing is False
    assert custom.debug is False
    assert custom.port == 9000
    assert custom.log_level == "ERROR"


def test_testing_environment_flag():
    """Verify is_testing property."""
    test_settings = Settings(app_env="testing")
    assert test_settings.is_testing is True
    assert test_settings.is_production is False


def test_cached_get_settings():
    """Verify get_settings returns a singleton instance."""
    instance_one = get_settings()
    instance_two = get_settings()
    assert instance_one is instance_two
