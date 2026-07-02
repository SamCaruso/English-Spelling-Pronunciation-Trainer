import logging
import sys
import json


class CloudRunFormatter(logging.Formatter):
    """Formats logs as JSON so Google Cloud Logging can natively parse them."""

    def format(self, record):
        log_entry = {
            'severity': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
        }
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CloudRunFormatter())

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
)
