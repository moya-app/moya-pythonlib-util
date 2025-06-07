import asyncio
import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger("url-checker")


async def check_forbidden_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs are supported")

    if parsed.port in {22, 23, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995}:
        logger.warning(f"Forbidden URL: {url} uses a forbidden port: {parsed.port}")
        raise ValueError("Forbidden URL")

    host = parsed.hostname
    # This can be extended - basic checks without DNS
    if host is None or host in ("localhost", "") or host.endswith(".local") or host.endswith(".localdomain"):
        logger.warning(f"Invalid Hostname in URL: {url}")
        raise ValueError("Invalid Hostname")

    # Try a DNS lookup and ensure that all possible connections are to global
    # IP addresses. Not a fail-safe method but pretty good at catching obvious
    # abuse.
    try:
        items = await asyncio.get_running_loop().getaddrinfo(host, 80)
    except socket.gaierror as e:
        logger.warning(f"Forbidden URL: {url} could not be resolved for checking: {e}")
        return

    for family, type, proto, canonname, sockaddr in items:
        address = sockaddr[0]
        if not ipaddress.ip_address(address).is_global:
            logger.warning(f"Forbidden URL: {url} resolves to a non-global IP address: {address}")
            raise ValueError("Forbidden URL")
