"""
MCP Server for TP-Link Archer BE400 router.

Exposes nine purpose-built tools over stdio with persistent session
management and built-in rate limiting to prevent router overload.
"""
import asyncio
import json
import logging
import platform
import re
import subprocess
import time
from typing import Annotated

from mcp.server.fastmcp import FastMCP

from .config import load_config, CONFIG_FILE
from .discovery import discover_tplink_routers
from .endpoints import ENDPOINTS

log = logging.getLogger("tplink-be400")

# Optional router key from ~/.config/tplink-be400/config.toml (e.g. r1, r2)
RouterKey = Annotated[
    str | None,
    "Optional router key from config (e.g. r1, r2). Omit to use the active router (defaults to first entry).",
]

mcp = FastMCP(
    "tplink-be400",
    instructions=(
        "TP-Link Archer BE400 router management. Use discover_routers to find "
        "TP-Link units on the LAN (optionally filter by model e.g. BE400). Use "
        "router_overview for a dashboard; pass router='r2' etc. when multiple "
        "routers are in config. get_setting / change_setting for reads and writes. "
        "A persistent session with rate limiting protects the router."
    ),
)

# ---------------------------------------------------------------------------
# Session manager -- single persistent connection with rate limiting
# ---------------------------------------------------------------------------

_session = {
    "router": None,
    "host": None,
    "password": None,
    "label": None,
    "router_key": None,
    "last_request": 0.0,
}

MIN_REQUEST_GAP = 1.5


def _resolve_router_key(router: str | None) -> str:
    password, routers = load_config()
    if not routers:
        raise RuntimeError(
            f"No routers configured. Edit {CONFIG_FILE} and add a [routers.r1] section."
        )
    if router is not None:
        if router not in routers:
            raise ValueError(
                f"Unknown router '{router}'. Configured keys: {list(routers.keys())}"
            )
        return router
    if _session.get("router_key") and _session["router_key"] in routers:
        return _session["router_key"]
    return next(iter(routers))


def _ensure_session(router: str | None = None):
    """Lazy-connect using config file credentials. Reuses session when the same router key is active."""
    password, routers = load_config()
    if not password:
        raise RuntimeError(
            f"No password configured. Edit {CONFIG_FILE} or run: tplink-be400 --setup"
        )
    if not routers:
        raise RuntimeError(
            f"No routers configured. Edit {CONFIG_FILE} and add a [routers.r1] section."
        )

    key = _resolve_router_key(router)
    host, label = routers[key]

    if _session["router"] is not None and _session.get("router_key") == key:
        return _session["router"]

    if _session.get("router"):
        try:
            _session["router"].logout()
        except Exception:
            pass

    _session["router"] = None
    _session["router_key"] = key
    _session["host"] = host
    _session["password"] = password
    _session["label"] = label

    from tplinkrouterc6u import TplinkRouterProvider

    log.info("Connecting to %s (%s)", host, label)
    r = TplinkRouterProvider.get_client(host, password)
    log.info("Auto-detected client: %s", type(r).__name__)
    r.authorize()
    _session["router"] = r
    log.info("Session established")
    return r


def _reconnect():
    """Force a fresh session (e.g. after timeout)."""
    old = _session.get("router")
    if old:
        try:
            old.logout()
        except Exception as e:
            log.debug("Logout during reconnect failed: %s", e)
    _session["router"] = None
    log.info("Reconnecting...")
    return _ensure_session()


async def _rate_limit():
    """Enforce minimum gap between API calls."""
    elapsed = time.monotonic() - _session["last_request"]
    if elapsed < MIN_REQUEST_GAP:
        wait = MIN_REQUEST_GAP - elapsed
        log.debug("Rate limit: sleeping %.2fs", wait)
        await asyncio.sleep(wait)


def _build_path(path: str, op: str) -> str:
    """Append operation to URL path (required by newer firmware)."""
    return f"{path}&operation={op}" if "?" in path else f"{path}?operation={op}"


def _request(path: str, op: str):
    """Rate-limited request with auto-reconnect on session expiry."""
    _session["last_request"] = time.monotonic()
    r = _ensure_session()
    full_path = _build_path(path, op)
    try:
        return r.request(full_path, f"operation={op}")
    except Exception as first_err:
        log.warning("Request failed (%s %s): %s — reconnecting", path, op, first_err)
        try:
            r = _reconnect()
            _session["last_request"] = time.monotonic()
            return r.request(full_path, f"operation={op}")
        except Exception:
            raise first_err


def _request_raw(path: str, payload: str):
    """Send a pre-built payload string (used for writes). Auto-reconnects."""
    _session["last_request"] = time.monotonic()
    r = _ensure_session()
    # Extract operation from payload and append to path for newer firmware
    op_match = re.search(r"operation=(\w+)", payload)
    if op_match:
        full_path = _build_path(path, op_match.group(1))
    else:
        full_path = path
    try:
        return r.request(full_path, payload)
    except Exception as first_err:
        log.warning("Raw request failed (%s): %s — reconnecting", path, first_err)
        try:
            r = _reconnect()
            _session["last_request"] = time.monotonic()
            return r.request(full_path, payload)
        except Exception:
            raise first_err


def _safe(path: str, op: str):
    """Like _request but returns None on failure."""
    try:
        return _request(path, op)
    except Exception as e:
        log.debug("Safe request returned None for %s [%s]: %s", path, op, e)
        return None


async def _read(path: str, op: str):
    """Async wrapper: rate-limit then read."""
    await _rate_limit()
    return _safe(path, op)


async def _read_must(path: str, op: str):
    """Async wrapper: rate-limit then read, raising on failure."""
    await _rate_limit()
    return _request(path, op)


# ---------------------------------------------------------------------------
# Topic aggregation maps for get_setting
# ---------------------------------------------------------------------------

TOPIC_MAP = {
    "wifi": [
        "wireless/wireless_2g", "wireless/wireless_5g", "wireless/wireless_5g_2",
        "wireless/smart_connect", "wireless/ofdma", "wireless/ofdma_mimo",
        "wireless/twt", "wireless/wps", "wireless/wps_pin",
        "wireless/region", "wireless/advanced", "wireless/statistics",
    ],
    "guest": [
        "wireless/guest", "guest/portal", "guest/background", "guest/logo",
    ],
    "wan": [
        "network/status_ipv4", "network/wan_status", "status/internet",
        "network/wan_fc", "network/wan_detect", "network/port_speed",
        "network/wan_protos", "status/wan_dual_nat",
    ],
    "lan": [
        "network/lan_ipv4", "network/lan_agg", "network/lan_fc",
    ],
    "dhcp": [
        "dhcps/setting", "dhcps/client", "dhcps/reservation",
    ],
    "firewall": [
        "security/firewall", "security/iot",
        "access/enable", "access/mode",
        "access/white_list", "access/black_list",
    ],
    "nat": [
        "nat/setting", "nat/dmz", "nat/alg",
        "nat/virtual_servers", "nat/port_triggering", "nat/clients",
    ],
    "qos": [
        "qos/setting", "qos/device_priority", "qos/accelerator",
    ],
    "vpn": [
        "openvpn/config", "pptpd/config", "pptpd/accounts",
        "wireguard/config", "wireguard/account",
    ],
    "admin": [
        "admin/account", "admin/mode", "admin/remote",
        "admin/https", "admin/recovery", "admin/local",
    ],
    "mesh": [
        "easymesh/enable", "easymesh/topo",
    ],
    "ipv6": [
        "network/lan_ipv6", "network/wan_ipv6_status",
        "network/wan_ipv6_dynamic", "network/wan_ipv6_static",
        "network/wan_ipv6_pppoe", "network/wan_ipv6_pass",
        "network/wan_ipv6_tunnel",
    ],
    "ddns": [
        "ddns/provider", "ddns/tplink", "ddns/dyndns", "ddns/noip",
    ],
    "upnp": [
        "upnp/enable", "upnp/service",
    ],
    "led": [
        "ledgeneral/setting", "ledpm/setting",
    ],
    "eco": [
        "eco_mode/settings",
    ],
    "time": [
        "time/settings", "time/dst",
    ],
    "firmware": [
        "firmware/upgrade", "firmware/auto_upgrade", "firmware/config",
    ],
    "disk": [
        "disk/metadata", "disk/scan", "time_machine/settings",
    ],
    "sharing": [
        "folder_sharing/settings", "folder_sharing/server",
        "folder_sharing/auth", "folder_sharing/media", "folder_sharing/mode",
    ],
    "iptv": [
        "iptv/setting", "iptv/udp_proxy",
    ],
    "imb": [
        "imb/setting", "imb/arp_list", "imb/bind_list",
    ],
    "cloud": [
        "cloud/device_info", "cloud/bind_status", "cloud/upgrade", "cloud/remind",
    ],
    "logs": [
        "syslog/log", "syslog/filter", "syslog/types",
    ],
    "ports": [
        "status/router", "network/port_names", "network/wan_port",
        "network/port_speed", "network/port_speed_supported",
    ],
    "routes": [
        "network/routes_system", "network/routes_static",
    ],
}


# ---------------------------------------------------------------------------
# Tool 1: router_overview
# ---------------------------------------------------------------------------

@mcp.tool()
async def router_overview(router: RouterKey = None) -> dict:
    """One-call dashboard of the TP-Link Archer BE400 router.

    Returns firmware info, CPU/memory usage, WAN status (IP, uptime,
    gateway, DNS), LAN IP, operation mode, time, internet connectivity,
    connected device counts, and WiFi SSID summary. Use this as the
    starting point before drilling into specific settings.
    """
    _ensure_session(router)
    result = {}

    fw = await _read("admin/firmware?form=upgrade", "read") or {}
    result["firmware"] = {
        "model": fw.get("model"),
        "hardware": fw.get("hardware_version"),
        "version": fw.get("firmware_version"),
    }

    s = await _read("admin/status?form=all", "read") or {}
    result["performance"] = {
        "cpu_percent": round(float(s.get("cpu_usage", 0)) * 100, 1),
        "memory_percent": round(float(s.get("mem_usage", 0)) * 100, 1),
    }

    wired = s.get("access_devices_wired", [])
    wireless = s.get("access_devices_wireless_host", [])
    result["clients"] = {
        "wired": len(wired),
        "wireless": len(wireless),
        "total": len(wired) + len(wireless),
    }

    net = await _read("admin/network?form=status_ipv4", "read") or {}
    wan_up = int(net.get("wan_ipv4_uptime", 0) or 0)
    result["wan"] = {
        "ip": net.get("wan_ipv4_ipaddr"),
        "gateway": net.get("wan_ipv4_gateway"),
        "dns": [net.get("wan_ipv4_pridns"), net.get("wan_ipv4_snddns")],
        "uptime_seconds": wan_up,
        "uptime_human": f"{wan_up // 3600}h {(wan_up % 3600) // 60}m {wan_up % 60}s",
    }
    result["lan_ip"] = net.get("lan_ipv4_ipaddr")

    inet = await _read("admin/status?form=internet", "read") or {}
    result["internet_status"] = inet.get("internet_status")

    mode = await _read("admin/system?form=sysmode", "read") or {}
    result["operation_mode"] = mode.get("mode")

    t = await _read("admin/time?form=settings", "read") or {}
    result["time"] = f"{t.get('date', '?')} {t.get('time', '?')}"

    ssids = []
    for band, form in [("2.4GHz", "wireless_2g"), ("5GHz", "wireless_5g"), ("5GHz-2", "wireless_5g_2")]:
        w = await _read(f"admin/wireless?form={form}", "read")
        if w and w.get("ssid"):
            ssids.append({
                "band": band,
                "ssid": w.get("ssid"),
                "enabled": w.get("enable"),
                "channel": w.get("current_channel"),
            })
    result["wifi_summary"] = ssids

    result["router_label"] = _session.get("label", "?")
    return result


# ---------------------------------------------------------------------------
# Tool 2: list_devices
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_devices(router: RouterKey = None) -> dict:
    """List every device currently connected to the router.

    Returns all wired and wireless clients with hostname, IP address,
    MAC address, and connection type (Wired / WiFi band).
    """
    _ensure_session(router)
    await _rate_limit()
    s = _request("admin/status?form=all", "read")
    devices = []
    for d in s.get("access_devices_wired", []):
        devices.append({
            "hostname": d.get("hostname", "?"),
            "ip": d.get("ipaddr"),
            "mac": d.get("macaddr"),
            "connection": "Wired",
        })
    for d in s.get("access_devices_wireless_host", []):
        devices.append({
            "hostname": d.get("hostname", "?"),
            "ip": d.get("ipaddr"),
            "mac": d.get("macaddr"),
            "connection": d.get("wire_type", "WiFi"),
        })
    return {"device_count": len(devices), "devices": devices}


# ---------------------------------------------------------------------------
# Tool 3: get_setting
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_setting(
    topic: Annotated[str, (
        "What to read. Use a high-level category like 'wifi', 'wan', 'lan', "
        "'dhcp', 'firewall', 'nat', 'qos', 'vpn', 'admin', 'mesh', 'ipv6', "
        "'ddns', 'upnp', 'led', 'eco', 'time', 'firmware', 'disk', 'sharing', "
        "'iptv', 'imb', 'cloud', 'logs', 'ports', 'routes', 'guest' to read "
        "multiple related endpoints at once. Or use any endpoint shortname from "
        "the 130-endpoint catalog (e.g. 'wireless/ofdma', 'nat/dmz') for a "
        "single raw read. Use find_endpoints to discover available endpoints."
    )],
    router: RouterKey = None,
) -> dict:
    """Read router settings by topic or specific endpoint.

    High-level topics aggregate multiple endpoints into one response.
    Endpoint shortnames return raw JSON from a single API call.
    """
    _ensure_session(router)
    if topic in TOPIC_MAP:
        result = {}
        for ep_name in TOPIC_MAP[topic]:
            path, op = ENDPOINTS[ep_name]
            data = await _read(path, op)
            if data is not None:
                result[ep_name] = data
        return {"topic": topic, "endpoints_read": len(result), "data": result}

    if topic in ENDPOINTS:
        path, op = ENDPOINTS[topic]
        data = await _read_must(path, op)
        return {"endpoint": topic, "path": path, "operation": op, "data": data}

    close = [k for k in ENDPOINTS if topic.lower() in k.lower()]
    if close:
        return {
            "error": f"Unknown topic '{topic}'",
            "did_you_mean": close[:10],
            "hint": "Use find_endpoints to search the full catalog.",
        }
    return {
        "error": f"Unknown topic '{topic}'",
        "available_topics": sorted(TOPIC_MAP.keys()),
        "hint": "Or use an endpoint shortname like 'wireless/ofdma'.",
    }


# ---------------------------------------------------------------------------
# Tool 4: change_setting
# ---------------------------------------------------------------------------

@mcp.tool()
async def change_setting(
    endpoint: Annotated[str, (
        "The endpoint shortname to write to (e.g. 'security/firewall', "
        "'nat/dmz', 'wireless/ofdma'). Use find_endpoints to discover names."
    )],
    settings: Annotated[dict, (
        "Key-value pairs to change. Example: {'enable': 'on'} or "
        "{'wan_ping': 'on', 'lan_ping': 'off'}. Keys must match the "
        "field names returned by get_setting for that endpoint."
    )],
    router: RouterKey = None,
) -> dict:
    """Change a router setting. Reads current values, applies your changes,
    writes back, then re-reads to confirm persistence.

    WARNING: This modifies the router configuration. Double-check endpoint
    and field names using get_setting first.
    """
    _ensure_session(router)
    if endpoint not in ENDPOINTS:
        close = [k for k in ENDPOINTS if endpoint.lower() in k.lower()]
        return {"error": f"Unknown endpoint '{endpoint}'", "did_you_mean": close[:10]}

    path, default_op = ENDPOINTS[endpoint]

    # Step 1: Read current state
    before = await _read(path, default_op)
    if before is None:
        before = await _read(path, "load")
    if before is None:
        return {"error": f"Could not read current values from {path}"}

    if not isinstance(before, dict):
        return {
            "error": "Endpoint returns a list, not a dict. Direct key=value writes not supported for list endpoints.",
            "current_data": before,
        }

    # Validate requested keys exist in the current data
    unknown_keys = [k for k in settings if k not in before]
    if unknown_keys:
        log.warning("Writing unknown keys %s to %s (may be valid)", unknown_keys, endpoint)

    # Step 2: Merge changes into current state and build payload
    merged = dict(before)
    merged.update(settings)

    parts = ["operation=write"]
    for k, v in merged.items():
        parts.append(f"{k}={json.dumps(v) if isinstance(v, (dict, list)) else v}")
    payload = "&".join(parts)

    # Step 3: Write
    await _rate_limit()
    try:
        _request_raw(path, payload)
    except Exception as e:
        log.error("Write to %s failed: %s", path, e)
        return {"error": f"Write failed: {str(e)[:300]}", "payload_sent": payload[:500]}

    # Step 4: Re-read to verify persistence
    after = await _read(path, default_op)

    changed = {}
    for k, v in settings.items():
        old_val = str(before.get(k, ""))
        new_val = str((after or {}).get(k, ""))
        persisted = new_val == str(v)
        changed[k] = {
            "before": old_val,
            "after": new_val,
            "requested": str(v),
            "persisted": persisted,
        }

    all_persisted = all(c["persisted"] for c in changed.values())
    return {
        "success": True,
        "all_persisted": all_persisted,
        "endpoint": endpoint,
        "path": path,
        "changes": changed,
    }


# ---------------------------------------------------------------------------
# Tool 5: get_logs
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_logs(
    log_type: Annotated[str, (
        "Log type filter. Use 'ALL' for everything, or one of: "
        "NETWORK, NAT, FIREWALL, DHCP, UPNP, IGMP, DDNS, IPTV, "
        "VPN, WIRELESS, USB, MESH, CLOUD, OTHER."
    )] = "ALL",
    max_entries: Annotated[int, "Maximum number of log entries to return. Default 50."] = 50,
    router: RouterKey = None,
) -> dict:
    """Retrieve system logs from the router with optional type filtering.

    Returns timestamped log entries with type and severity level.
    """
    _ensure_session(router)
    if log_type != "ALL":
        await _rate_limit()
        try:
            _request("admin/syslog?form=filter", "read")
            await _rate_limit()
            _request_raw("admin/syslog?form=filter", f"operation=write&type={log_type}&level=ALL")
        except Exception as e:
            log.warning("Failed to set log filter to %s: %s", log_type, e)

    logs = await _read("admin/syslog?form=log", "load")

    if log_type != "ALL":
        await _rate_limit()
        try:
            _request_raw("admin/syslog?form=filter", "operation=write&type=ALL&level=ALL")
        except Exception as e:
            log.warning("Failed to reset log filter: %s", e)

    entries = []
    if isinstance(logs, list):
        for entry in logs[:max_entries]:
            if isinstance(entry, dict):
                entries.append({
                    "time": entry.get("time"),
                    "type": entry.get("type"),
                    "level": entry.get("level"),
                    "message": entry.get("content"),
                })

    return {
        "filter": log_type,
        "total_available": len(logs) if isinstance(logs, list) else 0,
        "returned": len(entries),
        "entries": entries,
    }


# ---------------------------------------------------------------------------
# Tool 6: find_endpoints
# ---------------------------------------------------------------------------

@mcp.tool()
async def find_endpoints(
    query: Annotated[str, (
        "Search keyword. Matches against endpoint shortnames and API paths. "
        "Examples: 'firewall', 'wireless', 'vpn', 'ipv6', 'dhcp'."
    )],
) -> dict:
    """Search the 130-endpoint catalog by keyword.

    Returns matching endpoint names, their API paths, and default
    operations. Use the returned shortnames with get_setting or
    change_setting.
    """
    q = query.lower()
    matches = []
    for name, (path, op) in sorted(ENDPOINTS.items()):
        if q in name.lower() or q in path.lower():
            matches.append({"name": name, "path": path, "operation": op})

    topic_matches = [t for t in TOPIC_MAP if q in t]

    return {
        "query": query,
        "endpoint_matches": len(matches),
        "endpoints": matches,
        "matching_topics": topic_matches,
        "hint": "Use endpoint 'name' with get_setting or change_setting.",
    }


# ---------------------------------------------------------------------------
# Tool 7: discover_routers
# ---------------------------------------------------------------------------

@mcp.tool()
async def discover_routers(
    subnet: Annotated[str | None, "IPv4 CIDR to scan (e.g. 192.168.0.0/24). Omit to use this host's LAN /24."] = None,
    match_model: Annotated[str | None, "If set, only return entries whose model contains this substring (e.g. BE400). Requires try_auth."] = None,
    try_auth: Annotated[bool, "Use [auth] password from config to log in and read model/firmware per candidate."] = True,
) -> dict:
    """Scan the LAN for TP-Link web admin UIs and optionally authenticate to identify each unit.

    Finds multiple TP-Link devices (including several BE400s) by HTTP fingerprint, then
    optionally uses the same admin password as in config to read the exact model string.
    Add entries under [routers.*] in config only after you know each device's IP.
    """
    password, _routers = load_config()
    pwd = password if try_auth else None
    return await asyncio.to_thread(
        discover_tplink_routers,
        subnet=subnet,
        password=pwd,
        match_model_substring=match_model,
        try_auth=try_auth,
    )


# ---------------------------------------------------------------------------
# Tool 8: run_diagnostic
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_diagnostic(router: RouterKey = None) -> dict:
    """Run a network diagnostic: ping test to 8.8.8.8, physical port
    status, current WAN speed, and WAN uptime. Useful for
    troubleshooting connectivity issues.
    """
    _ensure_session(router)
    result = {}

    try:
        is_windows = platform.system() == "Windows"
        ping_cmd = (
            ["ping", "-n", "4", "-w", "2000", "8.8.8.8"]
            if is_windows
            else ["ping", "-c", "4", "-W", "2", "8.8.8.8"]
        )
        ping = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=15)
        lost = 0
        times = []
        for line in ping.stdout.split("\n"):
            if "Request timed out" in line or "100% packet loss" in line:
                lost += 1
            elif "time=" in line:
                for part in line.split():
                    if part.startswith("time="):
                        ms_str = part.split("=")[1].rstrip("ms")
                        try:
                            times.append(float(ms_str))
                        except ValueError:
                            pass
        result["ping"] = {
            "target": "8.8.8.8",
            "packets_sent": 4,
            "packets_lost": lost,
            "avg_ms": round(sum(times) / len(times), 1) if times else None,
            "times_ms": times,
        }
    except Exception as e:
        log.warning("Ping diagnostic failed: %s", e)
        result["ping"] = {"error": str(e)}

    ports = await _read("admin/status?form=router", "read")
    if isinstance(ports, list):
        result["ports"] = [
            {
                "name": p.get("name"),
                "status": p.get("status"),
                "speed_mbps": p.get("speed"),
                "duplex": p.get("duplex"),
                "is_wan": p.get("is_wan"),
            }
            for p in ports
        ]

    ws = await _read("admin/status?form=wan_speed", "read")
    if ws:
        result["wan_speed"] = {
            "download_bps": ws.get("down_speed"),
            "upload_bps": ws.get("up_speed"),
        }

    net = await _read("admin/network?form=status_ipv4", "read") or {}
    wan_up = int(net.get("wan_ipv4_uptime", 0) or 0)
    result["wan_uptime"] = {
        "seconds": wan_up,
        "human": f"{wan_up // 3600}h {(wan_up % 3600) // 60}m {wan_up % 60}s",
    }

    inet = await _read("admin/status?form=internet", "read") or {}
    result["internet_status"] = inet.get("internet_status")

    return result


# ---------------------------------------------------------------------------
# Tool 9: reboot_router
# ---------------------------------------------------------------------------

@mcp.tool()
async def reboot_router(
    confirm: Annotated[bool, (
        "MUST be set to true to proceed. The router will go offline for "
        "approximately 60-90 seconds during reboot."
    )],
    router: RouterKey = None,
) -> dict:
    """Reboot the TP-Link Archer BE400 router.

    This will disconnect all clients for 60-90 seconds. The confirm
    parameter must be explicitly set to true. After rebooting, the
    MCP session will need to reconnect on next tool call.
    """
    if not confirm:
        return {
            "error": "Reboot not confirmed. Set confirm=true to proceed.",
            "warning": "This will disconnect all devices for 60-90 seconds.",
        }

    await _rate_limit()
    r = _ensure_session(router)
    try:
        r.request(_build_path("admin/system?form=reboot", "write"), "operation=write", ignore_response=True)
        log.info("Reboot command sent successfully")
    except Exception as e:
        log.debug("Expected error after reboot command (router going down): %s", e)

    _session["router"] = None

    return {
        "success": True,
        "message": "Reboot command sent. Router will be offline for ~60-90 seconds.",
        "note": "The session has been cleared. Next tool call will reconnect automatically.",
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
