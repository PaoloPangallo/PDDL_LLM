# routes/app_factory.py

import os
import logging
from flask import Flask, request
from db.db import init_db
from . import register_routes
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf

csrf = CSRFProtect()

class QuestMasterApp:
    """
    Factory per la nostra app Flask:
    - punta ai template e static folder nel root del progetto
    - carica config
    - prepara uploads
    - inizializza DB
    - configura logging e hook request/response
    - registra dinamicamente tutti i blueprint
    - definisce error handler 404/500
    """

    def __init__(self, config_object=None):
        # 1) Calcola il root del progetto (una cartella sopra routes/)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        # 2) Crea l'app con TEMPLATE e STATIC assoluti
        tmpl_folder = os.path.join(project_root, "templates")
        stat_folder = os.path.join(project_root, "static")
        self.app = Flask(
            __name__,
            template_folder=tmpl_folder,
            static_folder=stat_folder
        )

        # 3) Carica la configurazione, se passata
        if config_object:
            self.app.config.from_object(config_object)

        # 4) Prepara uploads dir
        uploads_dir = os.path.join(project_root, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        self.app.config["UPLOAD_FOLDER"] = uploads_dir

        # 5) Inizializza il DB
        init_db()

        # 6) Logging e hook
        self._configure_logging()
        self._register_request_hooks()

        # 7) Registra tutti i blueprint
        register_routes(self.app)

        # 8) Error handler centralizzati
        self._register_error_handlers()
        self.app.context_processor(lambda: {"csrf_token": generate_csrf})


    def _configure_logging(self):
        """Stream e File handler con formatter unificato."""
        self.app.logger.handlers.clear()
        self.app.logger.setLevel(logging.DEBUG)

        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        sh  = logging.StreamHandler()
        fh  = logging.FileHandler("questmaster.log", encoding="utf-8")
        sh.setFormatter(fmt)
        fh.setFormatter(fmt)

        self.app.logger.addHandler(sh)
        self.app.logger.addHandler(fh)

    def _register_request_hooks(self):
        """Logga request / response per debugging."""
        @self.app.before_request
        def _before():
            self.app.logger.debug(
                "→ REQUEST %s %s args=%s form=%s",
                request.method,
                request.path,
                dict(request.args),
                list(request.form.keys())
            )

        @self.app.after_request
        def _after(response):
            self.app.logger.debug(
                "← RESPONSE %s %s status=%s",
                request.method,
                request.path,
                response.status_code
            )
            return response

    def _register_error_handlers(self):
        """404 e 500 handler."""
        @self.app.errorhandler(404)
        def _not_found(_error):
            return "Pagina non trovata", 404

        @self.app.errorhandler(500)
        def _server_error(_error):
            self.app.logger.error("Errore interno: %s", _error)
            return "Errore interno del server", 500

    @classmethod
    def create(cls, config_object=None):
        """
        Metodo comodo:
            from config import DevConfig
            app = QuestMasterApp.create(DevConfig)
        """
        return cls(config_object).app
