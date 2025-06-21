"""Route principali per la homepage, download file e gestione errori dell'app Flask."""

import os
import logging
from flask import Blueprint, render_template, send_file, abort
from werkzeug.utils import secure_filename

core_bp = Blueprint("core", __name__)


@core_bp.route("/", methods=["GET"])
def index():
    """Renderizza la pagina principale dell'applicazione."""
    return render_template("index.html")


@core_bp.route("/uploads/<session>/<filename>")
def download_file(session, filename):
    """Permette il download di un file dalla directory uploads se esiste e il nome è sicuro."""
    if ".." in filename or filename.startswith("/"):
        abort(400, "Nome file non valido.")
    folder = os.path.join(core_bp.root_path, "..", "uploads", session)
    file_path = os.path.join(folder, secure_filename(filename))
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=filename)
    abort(404, f"File non trovato: {filename}")


@core_bp.app_errorhandler(500)
def internal_error(e):
    """Gestisce errori 500 loggando il messaggio e restituendo risposta testuale."""
    logging.getLogger(__name__).error("500 Internal Server Error: %s", e)
    return "❌ Errore interno del server. Controlla i log per maggiori dettagli.", 500
