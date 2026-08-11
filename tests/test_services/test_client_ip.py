import pytest
from services.rate_limiter import get_client_ip


def make_request(mocker, remote, **headers):
    return mocker.MagicMock(remote=remote, headers=headers)


CLIENT = "8.8.4.4"


def test_direct_client_without_headers(mocker):
    assert get_client_ip(make_request(mocker, CLIENT)) == CLIENT


@pytest.mark.parametrize("header", ["X-Real-Ip", "X-Forwarded-For"])
def test_direct_client_cannot_forge_headers(mocker, header):
    request = make_request(mocker, CLIENT, **{header: "1.2.3.4"})
    assert get_client_ip(request) == CLIENT


def test_proxy_real_ip(mocker):
    request = make_request(mocker, "172.18.0.5", **{"X-Real-Ip": CLIENT})
    assert get_client_ip(request) == CLIENT


def test_proxy_forwarded_for_takes_rightmost(mocker):
    # The proxy appends the actual peer; anything to its left came from the client.
    request = make_request(mocker, "172.18.0.5", **{"X-Forwarded-For": f"1.2.3.4, {CLIENT}"})
    assert get_client_ip(request) == CLIENT


def test_real_ip_wins_over_forwarded_for(mocker):
    request = make_request(mocker, "172.18.0.5", **{"X-Real-Ip": CLIENT, "X-Forwarded-For": "1.2.3.4"})
    assert get_client_ip(request) == CLIENT


def test_loopback_without_headers_stays_loopback(mocker):
    assert get_client_ip(make_request(mocker, "127.0.0.1")) == "127.0.0.1"


def test_unknown_peer(mocker):
    assert get_client_ip(make_request(mocker, None)) is None
