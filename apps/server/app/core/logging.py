"""Minimal server logging that never records requests, headers or bodies."""

import logging

LOGGER_NAME = "goutoujunshi.server"
SAFE_MESSAGES = frozenset(
    {
        "Unhandled server error",
        "Import artifact cleanup deferred; maintenance retry required",
    }
)


_LOG_FIELDS = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class _SafeApplicationFilter(logging.Filter):
    """Only fixed, reviewed event descriptions reach application handlers."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, str) or record.msg not in SAFE_MESSAGES or record.args:
            record.msg = "Server event details suppressed"
        record.args = ()
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        for key in set(record.__dict__) - _LOG_FIELDS:
            del record.__dict__[key]
        return True


class _PrivateExceptionFilter(logging.Filter):
    """Uvicorn re-logs exceptions after Starlette's safe 500 handler returns."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info or record.exc_text or record.stack_info:
            record.msg = "Server operation failed; exception details suppressed"
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


def configure_logging(*, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    if not any(isinstance(item, _SafeApplicationFilter) for item in logger.filters):
        logger.addFilter(_SafeApplicationFilter())
    logging.getLogger("uvicorn.access").disabled = True
    server_errors = logging.getLogger("uvicorn.error")
    if not any(isinstance(item, _PrivateExceptionFilter) for item in server_errors.filters):
        server_errors.addFilter(_PrivateExceptionFilter())
    if not any(getattr(handler, "_goutoujunshi_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        handler._goutoujunshi_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger
