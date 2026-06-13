"""Avira parental-control (per-device URL/domain blocking) API for the BE400.

The BE400's Parental Controls are Avira-based ("Owner" profiles), reached at
``admin/avira_parental_control?form=avira_pactrl``. The wire format was
reverse-engineered from firmware v1.11.0 and verified live:

  * ``operation`` AND all params go in the URL QUERY, URL-encoded, using the
    web UI's JS model field names; array/object values are JSON strings.
  * the POST body carries only ``operation=<op>`` (AES-encrypted as usual).
  * success responses come back as a *bare* (unwrapped) encrypted blob, so we
    decrypt manually and tolerate both the wrapped ``{"data":...}`` and bare
    shapes.

A profile binds one or more device MACs (``allDeviceMac``) to a blocked-domain
list (``filterWebsiteList``, max 64 entries, <=64 chars each). Blocking is
enforced at the gateway via DNS manipulation, so it also drops HTTPS to those
domains. Set ``internetBlocked`` false so the device keeps general internet.
"""
import json
import hashlib
from urllib.parse import quote
from requests import post

FORM = "admin/avira_parental_control?form=avira_pactrl"


def avira_call(r, operation: str, params: dict | None = None) -> dict:
    """Low-level Avira request via an authenticated TplinkRouterSG session `r`."""
    query = f"operation={operation}"
    for k, v in (params or {}).items():
        query += f"&{k}={quote(str(v))}"
    enc = r._aes_encrypt(f"operation={operation}")
    r._hash = hashlib.sha256(enc.encode()).hexdigest()
    sign = r._build_request_signature(len(enc))
    url = f"{r.host}/cgi-bin/luci/;stok={r._stok}/{FORM}&{query}"
    resp = post(
        url, data=f"sign={sign}&data={quote(enc)}",
        headers=r._headers_request, cookies={"sysauth": r._sysauth},
        timeout=r.timeout, verify=r._verify_ssl,
    )
    try:
        dec = r._aes_decrypt(json.loads(resp.text)["data"])
    except Exception:
        dec = r._aes_decrypt(resp.text)
    try:
        return json.loads(dec)
    except Exception:
        return {"_raw": dec}


def owner_params(name, macs, block_domains, owner_id="-1", age="30",
                 internet_blocked=False) -> dict:
    """Build the addOwnerInList / profile param dict from simple inputs."""
    return {
        "ownerId": str(owner_id),
        "name": name,
        "age": str(age),
        "internetBlocked": "true" if internet_blocked else "false",
        "allDeviceMac": json.dumps(list(macs), separators=(",", ":")),
        "filterCategoriesList": "[]",
        "filterWebsiteList": json.dumps(list(block_domains), separators=(",", ":")),
        "bedtime": json.dumps(
            {"enable": False, "everyday": {"bedtimeBegin": "1260", "bedtimeEnd": "1380"}},
            separators=(",", ":")),
        "filterFreeWebsiteList": "[]",
    }


def as_list(value) -> list:
    """Accept a comma-separated string or a list; return a clean list."""
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return [str(x).strip() for x in value if str(x).strip()]
