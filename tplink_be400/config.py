"""Config file management for tplink-be400 CLI."""
import os
from typing import Any

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "tplink-be400")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.toml")

EXAMPLE_CONFIG = """\
# tplink-be400 CLI configuration
# Define your routers and credentials here.

[auth]
password = "YourRouterPasswordHere"

[routers.r1]
host = "http://192.168.0.1"
label = "Router 1"

# Add more routers as needed:
# [routers.r2]
# host = "http://192.168.0.202"
# label = "Router 2 (AP)"
"""


def _parse_toml(path):
    """Minimal TOML parser for the flat config we use.
    Avoids requiring tomllib (3.11+) or tomli for broader compat."""
    config = {}
    current_section = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1].strip()
                parts = current_section.split(".")
                d = config
                for p in parts:
                    d = d.setdefault(p, {})
                continue
            if "=" in line and current_section:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                parts = current_section.split(".")
                d = config
                for p in parts:
                    d = d.setdefault(p, {})
                d[key] = val
    return config


def load_config():
    """Load config from file. Returns (password, routers_dict)."""
    if not os.path.exists(CONFIG_FILE):
        return None, {}
    cfg = _parse_toml(CONFIG_FILE)
    password = cfg.get("auth", {}).get("password")
    routers = {}
    for name, rdata in cfg.get("routers", {}).items():
        if isinstance(rdata, dict) and "host" in rdata:
            host = rdata["host"]
            if not host.startswith("http"):
                host = f"http://{host}"
            routers[name] = (host, rdata.get("label", name))
    return password, routers


def create_default_config():
    """Create the config directory and example config file."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(EXAMPLE_CONFIG)
    return CONFIG_FILE


def _normalize_host_url(url: str) -> str:
    u = (url or "").strip().rstrip("/")
    if not u.startswith("http"):
        u = f"http://{u}"
    return u.lower()


def _next_router_key(existing: dict) -> str:
    nums = []
    for k in existing:
        if k.startswith("r") and len(k) > 1 and k[1:].isdigit():
            nums.append(int(k[1:]))
    n = max(nums, default=0) + 1
    return f"r{n}"


def _toml_escape_label(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def persist_discovered_routers(found: list[dict[str, Any]]) -> dict[str, Any]:
    """Append [routers.*] entries for newly discovered devices that authenticated.

    Skips hosts already present in config. Only adds items with auth_ok and a
    usable URL or IP.

    Returns a dict with ``added``, ``skipped``, ``persisted`` (bool), and
    optional ``reason`` when nothing was written.
    """
    result: dict[str, Any] = {
        "persisted": False,
        "added": [],
        "skipped": [],
        "reason": None,
    }
    if not os.path.exists(CONFIG_FILE):
        result["reason"] = "config file missing — run tplink-be400 --setup"
        return result

    password, routers = load_config()
    if not password:
        result["reason"] = "no [auth] password in config"
        return result

    existing_hosts: set[str] = set()
    for _name, (host, _label) in routers.items():
        existing_hosts.add(_normalize_host_url(host))

    routers_mut = dict(routers)

    for item in found:
        if not item.get("auth_ok"):
            result["skipped"].append(
                {"ip": item.get("ip"), "reason": "auth not verified — not persisted"}
            )
            continue
        url = item.get("url") or ""
        ip = item.get("ip") or ""
        if not url and ip:
            url = f"http://{ip}/"
        host_norm = _normalize_host_url(url)
        if not host_norm or host_norm == "http://":
            result["skipped"].append({"ip": ip, "reason": "no URL"})
            continue
        if host_norm in existing_hosts:
            result["skipped"].append({"host": host_norm, "reason": "already in config"})
            continue

        key = _next_router_key(routers_mut)

        model = (item.get("model") or "TP-Link").strip()
        label = f"{model} ({ip})" if ip else model
        label = label[:120]

        block = (
            f'\n[routers.{key}]\n'
            f'host = "{host_norm}"\n'
            f'label = "{_toml_escape_label(label)}"\n'
        )
        try:
            with open(CONFIG_FILE, "a", encoding="utf-8") as f:
                f.write(block)
        except OSError as e:
            result["reason"] = str(e)[:200]
            return result

        routers_mut[key] = (host_norm, label)
        existing_hosts.add(host_norm)
        result["added"].append({"key": key, "host": host_norm, "label": label})

    result["persisted"] = bool(result["added"])
    if not result["added"] and not result["reason"]:
        result["reason"] = "no new authenticated routers to add"
    return result
