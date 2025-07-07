# run.py o main.py (entrypoint)

from optimize_app import optimize_before_launch
from routes.app_factory import QuestMasterApp
from config import DevConfig

# 🛠️ Ottimizzazione leggera prima di creare l'app Flask
optimize_before_launch()

# 🚀 Crea e avvia l'app
app = QuestMasterApp.create(DevConfig)

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))
# Note: In a production environment, you would typically use a WSGI server like Gunicorn or uWSGI to run the app.
# This script is intended for development purposes and may not be suitable for production use as is.