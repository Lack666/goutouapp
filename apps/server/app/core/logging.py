"""Minimal server logging that never records requests, headers or bodies."""

import logging

LOGGER_NAME = "goutoujunshi.server"


class _PrivateExceptionFilter(logging.Filter):
    """Uvicorn re-logs exceptions after Starlette's safe 500 handler returns."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info or record.exc_text:
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
