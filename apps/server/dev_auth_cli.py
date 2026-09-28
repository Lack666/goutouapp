"""Development-only user bootstrap and short-lived signed token issuer."""

import argparse
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings
from app.db.repositories import records
from app.db.session import Database


def main() -> None:
    parser = argparse.ArgumentParser(description="Development-only auth setup")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("bootstrap", help="Create one local development User and Conversation")
    issue = commands.add_parser("token", help="Issue a short-lived local development JWT")
    issue.add_argument("--user-id", required=True, type=UUID)
    args = parser.parse_args()
    settings = Settings()
    if settings.app_env != "development":
        raise RuntimeError("This CLI runs only with APP_ENV=development")
    secret = settings.auth_jwt_secret
    if secret is None or len(secret.get_secret_value().encode("utf-8")) < 32:
        raise RuntimeError("Set a private AUTH_JWT_SECRET of at least 32 bytes")
    database = Database(settings)
    try:
        if args.command == "bootstrap":
            with database.session() as db, db.begin():
                user = records.create_user(db)
                conversation = records.create_conversation(db, user.id)
                print(f"user_id={user.id}\nconversation_id={conversation.id}")
        else:
            with database.session() as db:
                if records.get_user(db, args.user_id) is None:
                    raise RuntimeError("The user does not exist")
            token = jwt.encode(
                {
                    "sub": str(args.user_id),
                    "exp": datetime.now(UTC) + timedelta(minutes=15),
                    "iss": settings.auth_jwt_issuer,
                    "aud": settings.auth_jwt_audience,
                },
                secret.get_secret_value(),
                algorithm="HS256",
            )
            print(token)
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
