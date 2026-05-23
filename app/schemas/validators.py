from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints


def validate_password_complexity(value: str) -> str:
    if not any(character.isupper() for character in value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(character.islower() for character in value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must contain at least one number.")
    return value


StrongPassword = Annotated[
    str,
    StringConstraints(min_length=8, max_length=128),
    Field(
        description=(
            "Minimum 8 characters, with at least one uppercase letter, "
            "one lowercase letter, and one number."
        ),
        json_schema_extra={"pattern": r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).+$"},
    ),
    AfterValidator(validate_password_complexity),
]
