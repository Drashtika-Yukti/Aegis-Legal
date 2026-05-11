import logging
import json
import os
from datetime import datetime
from typing import Any, Dict

class JsonFormatter(logging.Formatter):
    """
    Structured JSON Formatter for Aegis Intelligence.
    Mimics professional Go/ZeroLog output.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
        }
        
        # Capture extra context if provided
        if hasattr(record, "context"):
            log_data["context"] = record.context
            
        # Capture exceptions
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)

def get_logger(name: str):
    logger = logging.getLogger(name)
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    
    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        
    return logger
