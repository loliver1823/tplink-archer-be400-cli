"""Router connection and shared utilities."""
import json
import logging

log = logging.getLogger("tplink-be400")


def connect(host, password):
    """Authenticate to the router and return an auto-detected session."""
    from tplinkrouterc6u import TplinkRouterProvider
    log.info("Connecting to %s", host)
    r = TplinkRouterProvider.get_client(host, password)
    log.info("Auto-detected client: %s", type(r).__name__)
    r.authorize()
    log.info("Authenticated successfully")
    return r


def safe_request(r, path, op):
    """Make an API request, returning None on any error."""
    try:
        full_path = f"{path}&operation={op}" if "?" in path else f"{path}?operation={op}"
        return r.request(full_path, f"operation={op}")
    except Exception as e:
        log.debug("safe_request failed for %s [%s]: %s", path, op, e)
        return None


def raw_request(r, path, payload, **kwargs):
    """Make a raw request with operation appended to the URL path."""
    import re as _re
    op_match = _re.search(r"operation=(\w+)", payload)
    if op_match:
        op = op_match.group(1)
        full_path = f"{path}&operation={op}" if "?" in path else f"{path}?operation={op}"
    else:
        full_path = path
    return r.request(full_path, payload, **kwargs)


def fmt(data, indent=2):
    """Format data for display."""
    if isinstance(data, (dict, list)):
        return json.dumps(data, indent=indent, default=str)
    return str(data)


def print_table(rows, headers=None):
    """Print a simple aligned table."""
    if not rows:
        print("  (empty)")
        return
    if headers:
        rows = [headers] + rows
    widths = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    for i, row in enumerate(rows):
        line = "  ".join(str(r).ljust(w) for r, w in zip(row, widths))
        print(f"  {line}")
        if i == 0 and headers:
            print(f"  {'  '.join('-' * w for w in widths)}")
