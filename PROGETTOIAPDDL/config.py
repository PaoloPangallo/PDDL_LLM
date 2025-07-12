# config.py

class BaseConfig:
    DEBUG = False
    TESTING = False
    SECRET_KEY = "supersegretosegreto"  # ✅ richiesto da Flask-WTF
    WTF_CSRF_ENABLED = True             # ✅ attiva CSRF protection per tutti i form


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False


class TestConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False  # spesso disabilitato nei test
