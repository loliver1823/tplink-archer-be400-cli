"""Config file management for tplink-be400 CLI."""
import os
import sys

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
