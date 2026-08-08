"""URL safety validator enforcing SSRF prevention and IP range restrictions."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "instance-data",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),  # Current network
    ipaddress.ip_network("::1/128"),  # IPv6 Loopback
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-local
    ipaddress.ip_network("fc00::/7"),  # IPv6 Unique local
    ipaddress.ip_network("224.0.0.0/4"),  # IPv4 multicast
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("198.18.0.0/15"),  # Benchmarking networks
    ipaddress.ip_network("ff00::/8"),  # IPv6 multicast
]


def _is_restricted_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return whether an address must never be contacted by the crawler."""
    return any(ip in network for network in BLOCKED_IP_NETWORKS) or any(
        (
            ip.is_loopback,
            ip.is_private,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def resolve_public_ips(hostname: str) -> tuple[bool, str, tuple[str, ...]]:
    """Resolve a host and reject restricted addresses before network I/O.

    DNS failures are returned as an explicit unknown result instead of being
    converted into a public address. The caller may decide whether to defer
    that failure to the HTTP client (fixtures and offline development do so).
    Every redirect calls this function again, preventing a previously trusted
    hostname from being reused without revalidation.
    """
    ip_addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]
    try:
        ip_obj = ipaddress.ip_address(hostname)
        ip_addresses = (ip_obj,)
    except ValueError:
        try:
            resolved_info = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
            ip_addresses = tuple({ipaddress.ip_address(info[4][0]) for info in resolved_info})
        except (OSError, ValueError) as exc:
            return True, f"DNS_UNRESOLVED:{type(exc).__name__}", ()

    for ip in ip_addresses:
        for network in BLOCKED_IP_NETWORKS:
            if ip in network:
                return (
                    False,
                    f"SSRF_BLOCKED: Resolved IP {ip} is in restricted range ({network}).",
                    tuple(str(item) for item in ip_addresses),
                )
        if _is_restricted_ip(ip):
            return (
                False,
                f"SSRF_BLOCKED: Resolved IP {ip} is restricted.",
                tuple(str(item) for item in ip_addresses),
            )
    return True, "SAFE", tuple(str(item) for item in ip_addresses)


def validate_url_safety(url: str, *, allow_unresolved: bool = True) -> tuple[bool, str]:
    """Validate HTTP(S) URL and resolve every host against SSRF restrictions.

    ``allow_unresolved`` is retained for deterministic offline fixtures. A
    production caller should set it to ``False`` when DNS must be fail-closed.
    The fetcher still validates the URL immediately before every request and
    before every redirect.
    """
    if not url:
        return False, "EMPTY_URL: URL string is empty."

    try:
        parsed = urlparse(url.strip())
        hostname = (parsed.hostname or "").lower().rstrip(".")
    except ValueError as exc:
        return False, f"INVALID_URL: {type(exc).__name__}."
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"UNSUPPORTED_SCHEME: Scheme '{scheme}' is not http or https."

    if not hostname:
        return False, "INVALID_HOST: Missing hostname in URL."

    if parsed.username or parsed.password:
        return False, "INVALID_URL: Credentials in URL are not permitted."

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(
        (".local", ".localhost", ".internal", ".test")
    ):
        return False, f"BLOCKED_HOST: Hostname '{hostname}' is restricted."

    is_safe, reason, _addresses = resolve_public_ips(hostname)
    if not is_safe:
        return False, reason
    if reason.startswith("DNS_UNRESOLVED") and not allow_unresolved:
        return False, f"DNS_VALIDATION_FAILED: {reason}"
    return True, reason
