from __future__ import annotations

import string

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from app.schemas.validators import validate_password_complexity
from app.schemas.workspace import WorkspaceCreateRequest

printable_ascii = st.text(
    alphabet=string.ascii_letters + string.digits + string.punctuation + " ",
    min_size=8,
    max_size=128,
)
uppercase_only_passwords = st.builds(
    lambda upper, rest: f"{upper}{rest}",
    st.sampled_from(string.ascii_uppercase),
    st.text(
        alphabet=string.ascii_uppercase + string.digits + string.punctuation + " ",
        min_size=7,
        max_size=127,
    ),
)
letters_without_digits_passwords = st.builds(
    lambda upper, lower, rest: f"{upper}{lower}{rest}",
    st.sampled_from(string.ascii_uppercase),
    st.sampled_from(string.ascii_lowercase),
    st.text(
        alphabet=string.ascii_letters + string.punctuation + " ",
        min_size=6,
        max_size=126,
    ),
)
strong_passwords = st.builds(
    lambda prefix, upper, lower, digit, suffix: (
        f"{prefix}{upper}{lower}{digit}{suffix}"
    ),
    st.text(alphabet=string.printable.strip(), max_size=20),
    st.sampled_from(string.ascii_uppercase),
    st.sampled_from(string.ascii_lowercase),
    st.sampled_from(string.digits),
    st.text(alphabet=string.printable.strip(), max_size=20),
).filter(lambda value: 8 <= len(value) <= 128)


@given(password=strong_passwords)
def test_strong_printable_ascii_passwords_are_accepted(password: str) -> None:
    assert validate_password_complexity(password) == password
    request = WorkspaceCreateRequest(
        name="Acme Workspace",
        admin_email="admin@example.com",
        admin_password=password,
    )
    assert request.admin_password == password


@given(
    password=printable_ascii.filter(lambda value: not any(ch.isupper() for ch in value))
)
def test_passwords_without_uppercase_are_rejected(password: str) -> None:
    with pytest.raises(ValueError, match="uppercase"):
        validate_password_complexity(password)


@given(password=uppercase_only_passwords)
def test_passwords_without_lowercase_are_rejected(password: str) -> None:
    with pytest.raises(ValueError, match="lowercase"):
        validate_password_complexity(password)


@given(password=letters_without_digits_passwords)
def test_passwords_without_digits_are_rejected(password: str) -> None:
    with pytest.raises(ValueError, match="number"):
        validate_password_complexity(password)


@given(password=st.text(min_size=1).filter(lambda value: not value.isascii()))
def test_non_ascii_passwords_are_rejected(password: str) -> None:
    with pytest.raises(ValueError, match="printable ASCII"):
        validate_password_complexity(password)


@given(name=st.text(max_size=2), password=strong_passwords)
def test_workspace_names_shorter_than_three_characters_are_rejected(
    name: str, password: str
) -> None:
    with pytest.raises(ValidationError):
        WorkspaceCreateRequest(
            name=name,
            admin_email="admin@example.com",
            admin_password=password,
        )
