import logging
import sys
from contextvars import ContextVar
from pathlib import Path

# Context variables for request-scoped logging
query_id_var = ContextVar("query_id", default="N/A")
latency_var = ContextVar("latency_ms", default="N/A")

class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.query_id = query_id_var.get()
        record.latency_ms = latency_var.get()
        return True

def setup_logger():
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("research_assistant")
    logger.setLevel(logging.INFO)
    
    # Prevent adding handlers multiple times if imported multiple times
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | QueryID: %(query_id)s | Latency: %(latency_ms)s | %(message)s'
        )
        
        # Console output
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(formatter)
        
        # File output
        fh = logging.FileHandler(log_dir / "app.log")
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        logger.addFilter(RequestContextFilter())
        
    return logger

logger = setup_logger()