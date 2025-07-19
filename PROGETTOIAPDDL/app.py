from optimize_app import optimize_before_launch
from routes.app_factory import QuestMasterApp
from config import DevConfig
from urllib.parse import unquote
from werkzeug.serving import WSGIRequestHandler
import logging

app = QuestMasterApp.create(DevConfig)

class PercentStripFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = record.msg.replace("%", "")
        return True

logging.getLogger().addFilter(PercentStripFilter())

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", False))