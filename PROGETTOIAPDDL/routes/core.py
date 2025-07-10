from flask import Blueprint, render_template
import os

core_bp = Blueprint("core", __name__)

@core_bp.route("/")
def homepage():
    # Carica i file lore anche per l'index (chat)
    lore_files = os.listdir("lore")
    return render_template("index.html", lore_files=lore_files)

@core_bp.route("/pipeline")
def pipeline_page():
    # Stesso loader anche per la pipeline view
    lore_files = os.listdir("lore")
    return render_template("pipeline.html", lore_files=lore_files)
