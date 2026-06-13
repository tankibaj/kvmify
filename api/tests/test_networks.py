"""Tests for GET /networks."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------

BRIDGE_NET_XML = """
<network>
  <name>public</name>
  <forward mode='bridge'/>
  <bridge name='br0'/>
</network>
"""

NAT_NET_XML = """
<network>
  <name>default</name>
  <forward mode='nat'>
    <nat>
      <port start='1024' end='65535'/>
    </nat>
  </forward>
  <bridge name='virbr0' stp='on' delay='0'/>
  <ip address='192.168.122.1' netmask='255.255.255.0'>
  </ip>
</network>
"""

PRIVATE_NAT_XML = """
<network>
  <name>private</name>
  <forward mode='nat'/>
  <bridge name='virbr1'/>
  <ip address='10.0.0.1' netmask='255.255.255.0'/>
</network>
"""


def _make_net(name: str, xml: str) -> MagicMock:
    net = MagicMock(name=f"virNetwork:{name}")
    net.name.return_value = name
    net.XMLDesc.return_value = xml
    return net


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_list_networks_returns_options(client: TestClient, patch_libvirt, mock_conn):
    """GET /networks returns network options with macvtap appended."""
    public_net = _make_net("public", BRIDGE_NET_XML)
    default_net = _make_net("default", NAT_NET_XML)
    mock_conn.listAllNetworks.return_value = [public_net, default_net]

    resp = client.get("/networks")
    assert resp.status_code == 200
    data = resp.json()

    ids = [o["id"] for o in data]
    assert "public" in ids
    assert "default" in ids
    assert "macvtap" in ids, "Synthetic macvtap option must always be appended"


def test_bridge_network_marked_is_default(client: TestClient, patch_libvirt, mock_conn):
    """The first bridge network must have is_default=True."""
    public_net = _make_net("public", BRIDGE_NET_XML)
    default_net = _make_net("default", NAT_NET_XML)
    mock_conn.listAllNetworks.return_value = [public_net, default_net]

    resp = client.get("/networks")
    data = resp.json()
    bridge_opts = [o for o in data if o["mode"] == "bridge"]
    assert len(bridge_opts) >= 1, "At least one bridge option expected"
    assert bridge_opts[0]["is_default"] is True, "First bridge must be is_default"


def test_nat_network_not_default(client: TestClient, patch_libvirt, mock_conn):
    """NAT networks must NOT be marked as default."""
    default_net = _make_net("default", NAT_NET_XML)
    mock_conn.listAllNetworks.return_value = [default_net]

    resp = client.get("/networks")
    data = resp.json()
    nat_opts = [o for o in data if o["mode"] == "nat"]
    for opt in nat_opts:
        assert opt["is_default"] is False


def test_bridge_network_has_correct_mode_and_source(
    client: TestClient, patch_libvirt, mock_conn
):
    """Bridge network option carries mode='bridge' and source='br0'."""
    public_net = _make_net("public", BRIDGE_NET_XML)
    mock_conn.listAllNetworks.return_value = [public_net]

    resp = client.get("/networks")
    data = resp.json()
    public_opt = next(o for o in data if o["id"] == "public")
    assert public_opt["mode"] == "bridge"
    assert public_opt["source"] == "br0"


def test_macvtap_option_is_direct_mode(client: TestClient, patch_libvirt, mock_conn):
    """Synthetic macvtap option must have mode='direct'."""
    mock_conn.listAllNetworks.return_value = []

    resp = client.get("/networks")
    data = resp.json()
    macvtap = next(o for o in data if o["id"] == "macvtap")
    assert macvtap["mode"] == "direct"
    assert macvtap["is_default"] is False


def test_macvtap_present_even_with_no_networks(
    client: TestClient, patch_libvirt, mock_conn
):
    """Macvtap is appended regardless of the libvirt network list."""
    mock_conn.listAllNetworks.return_value = []

    resp = client.get("/networks")
    data = resp.json()
    assert any(o["id"] == "macvtap" for o in data)


def test_list_networks_503_on_libvirt_error(client: TestClient, monkeypatch):
    """GET /networks returns 503 when libvirt connection fails."""
    import libvirt
    from contextlib import contextmanager

    @contextmanager
    def _boom():
        raise libvirt.libvirtError("cannot connect")
        yield  # noqa: unreachable

    monkeypatch.setattr("api.services.libvirt_service.connection", _boom)

    resp = client.get("/networks")
    assert resp.status_code == 503


def test_three_networks_correct_count(client: TestClient, patch_libvirt, mock_conn):
    """With public+default+private libvirt nets, response has 4 items (+ macvtap)."""
    mock_conn.listAllNetworks.return_value = [
        _make_net("public", BRIDGE_NET_XML),
        _make_net("default", NAT_NET_XML),
        _make_net("private", PRIVATE_NAT_XML),
    ]

    resp = client.get("/networks")
    data = resp.json()
    assert len(data) == 4  # 3 libvirt + 1 macvtap
