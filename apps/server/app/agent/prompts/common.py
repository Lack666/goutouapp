"""Present supplied context as untrusted data with explicit speaker labels."""

import json

from app.agent.contracts import ConversationMessage


def context_payload(current_message: str, messages: list[ConversationMessage]) -> str:
    return json.dumps(
        {
            "recent_messages": [message.model_dump() for message in messages[-8:]],
            "current_user_message": current_message,
        },
        ensure_ascii=False,
    )
