"""Structured JSON logging with a per-request id."""
import contextvars
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware

request_id = contextvars.ContextVar("request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id.get(),
        }
        entry.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("nela")
    root.handlers = [handler]
    root.setLevel(level)
    root.propagate = False


def log(logger, level, msg, **fields):
    """Log with structured fields: log(logger, logging.INFO, "ocr.done", ms=120)."""
    logger.log(level, msg, extra={"extra_fields": fields})


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        token = request_id.set(rid)
        start = time.perf_counter()
        logger = logging.getLogger("nela.http")
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request.failed", extra={"extra_fields": {"path": request.url.path}})
            raise
        finally:
            request_id.reset(token)
        ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["x-request-id"] = rid
        logger.info("request", extra={"extra_fields": {
            "request_id": rid, "method": request.method, "path": request.url.path,
            "status": response.status_code, "ms": ms}})
        return response
