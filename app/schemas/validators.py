from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, Field, StringConstraints

STRONG_PASSWORD_PATTERN = (
    r"^(?:"
    r"[ -~]*[a-z][ -~]*[A-Z][ -~]*[0-9]"
    r"|[ -~]*[a-z][ -~]*[0-9][ -~]*[A-Z]"
    r"|[ -~]*[A-Z][ -~]*[a-z][ -~]*[0-9]"
    r"|[ -~]*[A-Z][ -~]*[0-9][ -~]*[a-z]"
    r"|[ -~]*[0-9][ -~]*[a-z][ -~]*[A-Z]"
    r"|[ -~]*[0-9][ -~]*[A-Z][ -~]*[a-z]"
    r")[ -~]*$"
)


def validate_password_complexity(value: str) -> str:
    if not value.isascii() or not all(character.isprintable() for character in value):
        raise ValueError("Password must contain only printable ASCII characters.")
    if not any(character.isupper() for character in value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(character.islower() for character in value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(character.isdigit() for character in value):
        raise ValueError("Password must contain at least one number.")
    return value


StrongPassword = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=128,
        pattern=STRONG_PASSWORD_PATTERN,
    ),
    Field(
        description=(
            "Minimum 8 and maximum 128 printable ASCII characters, with at least "
            "one uppercase letter, one lowercase letter, and one number."
        ),
    ),
    AfterValidator(validate_password_complexity),
]
