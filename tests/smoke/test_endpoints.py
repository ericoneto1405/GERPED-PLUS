import pytest


@pytest.mark.smoke
@pytest.mark.parametrize(
    ("path", "expected_status"),
    [
        ("/healthz", 200),
        ("/readiness", 200),
        ("/metrics", 200),
        ("/docs", 200),
        ("/login", 200),
        ("/", 302),
    ],
)
def test_smoke_endpoints(client, path, expected_status):
    response = client.get(path)
    assert response.status_code == expected_status
