"""Strict Pydantic validation shared by real and mock providers."""

from pydantic import ValidationError

from app.llm.errors import LLMStructuredOutputError
from app.llm.provider import SchemaT


def validate_structured_output(content: str, schema: type[SchemaT]) -> SchemaT:
    try:
        return schema.model_validate_json(content, strict=True)
    except ValidationError:
        # ValidationError can echo private content; only expose our fixed error.
        raise LLMStructuredOutputError() from None
