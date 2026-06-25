import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "process": record.process,
            "thread": record.thread,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        for key in ("status_code", "request", "path", "method", "user_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = str(value)

        return json.dumps(payload, default=str, ensure_ascii=False)
