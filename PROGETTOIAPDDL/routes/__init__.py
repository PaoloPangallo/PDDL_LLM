# routes/__init__.py

import pkgutil
import importlib
from flask import Blueprint, Flask

def register_routes(app: Flask) -> None:
    """
    Scansiona i moduli in routes/ (non pkg) e registra ogni Blueprint
    trovato come <nome_attr>_bp. Se nel modulo c'è URL_PREFIX, lo usa.
    """
    package_name = __name__  # "routes"
    for _finder, module_name, is_pkg in pkgutil.iter_modules(__path__):
        if is_pkg:
            continue
        full_name = f"{package_name}.{module_name}"
        module = importlib.import_module(full_name)
        for attr in dir(module):
            if not attr.endswith("_bp"):
                continue
            bp = getattr(module, attr)
            if isinstance(bp, Blueprint):
                prefix = getattr(module, "URL_PREFIX", None)
                if prefix:
                    app.register_blueprint(bp, url_prefix=prefix)
                else:
                    app.register_blueprint(bp)
