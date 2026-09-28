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

    if BaseConfig.SECRET_KEY == "dev_only_change_me":
        raise RuntimeError(
            "FLASK_SECRET_KEY must be set to a strong value in production."
        )


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
