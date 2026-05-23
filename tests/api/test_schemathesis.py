from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-test-secret-key-1234567890")

import schemathesis
from hypothesis import HealthCheck, assume, settings
from schemathesis.specs.openapi.checks import unsupported_method

from main import app

schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@schema.parametrize()
@settings(
    max_examples=20,
    deadline=None,
    # Schemathesis generates multiple examples per pytest case. Reusing the
    # TestClient fixture across those examples is intentional for this contract test.
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_api_schema(case, client):
    if case.method == "POST" and case.path == "/api/v1/workspaces/":
        admin_email = (
            case.body.get("admin_email") if isinstance(case.body, dict) else None
        )
        assume(not (isinstance(admin_email, str) and "xn--" in admin_email))

    response = case.call(session=client)
    case.validate_response(response, excluded_checks=[unsupported_method])
