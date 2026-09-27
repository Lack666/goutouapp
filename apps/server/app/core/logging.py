"""Minimal server logging that never records requests, headers or bodies."""

import logging

LOGGER_NAME = "goutoujunshi.server"


def configure_logging(*, debug: bool = False) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    logging.getLogger("uvicorn.access").disabled = True
    if not any(getattr(handler, "_goutoujunshi_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        handler._goutoujunshi_handler = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    return logger
