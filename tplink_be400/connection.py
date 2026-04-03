"""Router connection and shared utilities."""
import json
import logging

log = logging.getLogger("tplink-be400")


def connect(host, password):
    """Authenticate to the router and return the TplinkRouter session."""
    from tplinkrouterc6u import TplinkRouter
    log.info("Connecting to %s", host)
    r = TplinkRouter(host, password)
    r.authorize()
    log.info("Authenticated successfully")
    return r


def safe_request(r, path, op):
    """Make an API request, returning None on any error."""
    try:
        return r.request(path, f"operation={op}")
    except Exception as e:
        log.debug("safe_request failed for %s [%s]: %s", path, op, e)
        return None


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
