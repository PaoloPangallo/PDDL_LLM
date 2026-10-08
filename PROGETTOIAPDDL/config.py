import os


class BaseConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev_only_change_me")
    WTF_CSRF_ENABLED = True


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False

    @classmethod
    def init_app(cls, app):
        # Defer the check until production is actually selected. Importing
        # this module for development/tests must never raise an exception.
        if app.config.get("SECRET_KEY") in (None, "", "dev_only_change_me"):
            raise RuntimeError(
                "FLASK_SECRET_KEY must be set to a strong value in production."
            )


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
