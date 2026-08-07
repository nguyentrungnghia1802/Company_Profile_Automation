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
]


def validate_url_safety(url: str) -> tuple[bool, str]:
    """Validate URL for HTTP/HTTPS scheme and SSRF restrictions."""
    if not url:
        return False, "EMPTY_URL: URL string is empty."

    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "").lower()
    if scheme not in ("http", "https"):
        return False, f"UNSUPPORTED_SCHEME: Scheme '{scheme}' is not http or https."

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "INVALID_HOST: Missing hostname in URL."

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith((".local", ".internal")):
        return False, f"BLOCKED_HOST: Hostname '{hostname}' is restricted."

    # Parse direct IP address or resolve DNS
    try:
        ip_obj = ipaddress.ip_address(hostname)
        ip_addresses = [ip_obj]
    except ValueError:
        try:
            # Resolve hostname to IP address
            resolved_info = socket.getaddrinfo(hostname, None)
            ip_addresses = [ipaddress.ip_address(info[4][0]) for info in resolved_info]
        except socket.gaierror:
            # If DNS resolution fails, allow fetcher to handle DNS failure gracefully
            return True, "DNS_UNRESOLVED"

    for ip in ip_addresses:
        for net in BLOCKED_IP_NETWORKS:
            if ip in net:
                return False, f"SSRF_BLOCKED: Resolved IP {ip} is in restricted range ({net})."

    return True, "SAFE"
