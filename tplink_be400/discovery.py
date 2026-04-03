"""Scan the LAN for TP-Link web admin interfaces and optionally identify models via API."""
from __future__ import annotations

import ipaddress
import logging
import re
import socket
import ssl
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

log = logging.getLogger("tplink-be400.discovery")

# HTML / header fingerprints for TP-Link admin (Archer and Omada-style vary)
_TPLINK_MARKERS = (
    "tp-link",
    "tplink",
    "tp link",
    "tp_link",
    "/webpages/",
    "tplinkwifi.net",
    "router login",
)

def guess_local_ipv4() -> str | None:
    """Best-effort primary IPv4 without sending real traffic."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


def subnets_to_scan(explicit_cidr: str | None) -> list[str]:
    """Return one or more /24 CIDRs to scan."""
    if explicit_cidr:
        return [explicit_cidr.strip()]
    ip = guess_local_ipv4()
    if ip:
        parts = ip.split(".")
        return [f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"]
    return ["192.168.0.0/24", "192.168.1.0/24"]


def _hosts_in_network(cidr: str) -> list[str]:
    net = ipaddress.ip_network(cidr, strict=False)
    if net.version != 4:
        return []
    # Cap scan size to avoid accidental huge ranges
    if net.num_addresses > 512:
        log.warning("Subnet %s too large; scanning first /24 only", cidr)
        base = str(net.network_address).split(".")
        return [str(ipaddress.IPv4Address((int(net.network_address) + i))) for i in range(1, 255)]
    return [str(h) for h in net.hosts()]


def _looks_like_tplink_html(body: str) -> bool:
    b = body.lower()
    return any(m in b for m in _TPLINK_MARKERS) or bool(
        re.search(r"tp[\s_-]?link", b, re.I)
    )


def _fetch_landing(ip: str, scheme: str, timeout: float) -> tuple[bool, str]:
    """Return (is_tplink_like, snippet_or_error)."""
    url = f"{scheme}://{ip}/"
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "tplink-be400-cli/discovery"},
        method="GET",
    )
    try:
        if scheme == "https":
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                raw = resp.read(12000)
        else:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(12000)
        text = raw.decode("utf-8", errors="ignore")
        return _looks_like_tplink_html(text), text[:500]
    except urllib.error.HTTPError as e:
        try:
            raw = e.read(8000)
            text = raw.decode("utf-8", errors="ignore")
            if _looks_like_tplink_html(text):
                return True, text[:500]
        except Exception:
            pass
        return False, str(e)[:200]
    except Exception as e:
        return False, str(e)[:200]


def probe_tplink_lan_ip(ip: str, timeout: float = 0.6) -> dict[str, Any] | None:
    """Return a dict if this IP looks like a TP-Link admin UI, else None."""
    for scheme in ("http", "https"):
        ok, info = _fetch_landing(ip, scheme, timeout)
        if ok:
            return {
                "ip": ip,
                "url": f"{scheme}://{ip}/",
                "scheme": scheme,
                "detection": "http-fingerprint",
            }
    return None


def enrich_with_auth(host_url: str, password: str) -> dict[str, Any]:
    """Connect with tplinkrouterc6u and read firmware identity. host_url must include scheme."""
    out: dict[str, Any] = {"auth_ok": False}
    try:
        from .connection import connect, safe_request

        r = connect(host_url, password)
        try:
            fw = safe_request(r, "admin/firmware?form=upgrade", "read") or {}
            out["auth_ok"] = True
            out["model"] = fw.get("model")
            out["hardware_version"] = fw.get("hardware_version")
            out["firmware_version"] = fw.get("firmware_version")
        finally:
            try:
                r.logout()
            except Exception:
                pass
    except Exception as e:
        out["auth_error"] = str(e)[:300]
    return out


def discover_tplink_routers(
    subnet: str | None = None,
    password: str | None = None,
    *,
    probe_timeout: float = 0.55,
    match_model_substring: str | None = None,
    try_auth: bool = True,
    max_workers: int = 48,
    persist_to_config: bool = True,
) -> dict[str, Any]:
    """
    Scan subnet(s) for TP-Link web admin pages, optionally authenticate and read model.

    Returns a dict with ``subnets_scanned``, ``found`` (list), and ``summary``.
    """
    cidrs = subnets_to_scan(subnet)
    seen: set[str] = set()
    hosts: list[str] = []
    for cidr in cidrs:
        for h in _hosts_in_network(cidr):
            if h not in seen:
                seen.add(h)
                hosts.append(h)

    found: list[dict[str, Any]] = []

    def job(ip: str) -> dict[str, Any] | None:
        return probe_tplink_lan_ip(ip, timeout=probe_timeout)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(job, ip): ip for ip in hosts}
        for fut in as_completed(futures):
            try:
                r = fut.result()
                if r:
                    found.append(r)
            except Exception as e:
                log.debug("probe failed: %s", e)

    # Stable sort by IP
    found.sort(key=lambda x: tuple(map(int, x["ip"].split("."))))

    if try_auth and password:
        for item in found:
            url = item.get("url")
            if not url:
                continue
            extra = enrich_with_auth(url, password)
            item.update(extra)

    if match_model_substring:
        m = match_model_substring.lower()
        found = [
            item
            for item in found
            if m in (item.get("model") or "").lower()
        ]

    summary = {
        "count": len(found),
        "with_model": sum(1 for x in found if x.get("model")),
        "auth_failed": sum(1 for x in found if try_auth and password and not x.get("auth_ok")),
    }

    out: dict[str, Any] = {
        "subnets_scanned": cidrs,
        "hosts_probed": len(hosts),
        "found": found,
        "summary": summary,
    }

    if persist_to_config:
        from .config import persist_discovered_routers

        out["persist"] = persist_discovered_routers(found)
    else:
        out["persist"] = {"persisted": False, "skipped": [], "reason": "skipped (--skip-persist / skip_persist)"}

    return out
