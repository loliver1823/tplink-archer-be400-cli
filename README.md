# tplink-archer-be400-cli

Full CLI for the **TP-Link Archer BE400** router — 130 reverse-engineered API endpoints, 36 commands.

> **BE400-only.** This tool was built by reverse-engineering the Archer BE400's web UI JavaScript bundles (firmware v1.0.4, build 2024-09-04). It may partially work on other TP-Link routers that share the same firmware platform, but full compatibility is only guaranteed for the BE400.

## Installation

```bash
pip install git+https://github.com/loliver1823/tplink-archer-be400-cli.git
```

Or clone and install locally:

```bash
git clone https://github.com/loliver1823/tplink-archer-be400-cli.git
cd tplink-archer-be400-cli
pip install .
```

## First-Time Setup

```bash
tplink-be400 --setup
```

This creates a config file at `~/.config/tplink-be400/config.toml`. Edit it with your router's IP and password:

```toml
[auth]
password = "YourRouterPasswordHere"

[routers.r1]
host = "http://192.168.0.1"
label = "Main Router"

# Multiple routers supported:
# [routers.r2]
# host = "http://192.168.0.202"
# label = "AP Mode Router"
```

You can also skip the config file entirely and pass credentials directly:

```bash
tplink-be400 --host 192.168.0.1 --password YourPassword status
```

## Usage

```
tplink-be400 <router> <command> [args...]
```

Where `<router>` is a key from your config (e.g. `r1`).

### All Commands

| Command | Description |
|---------|-------------|
| `status` | Full router overview (CPU, memory, WAN, clients, firmware) |
| `devices` | List all connected devices (wired + wireless) |
| `wifi` | WiFi settings for all bands + OFDMA, TWT, WPS, Smart Connect |
| `dhcp` | DHCP config, lease table, and reservations |
| `wan` | WAN/internet status, protocols, flow control, double NAT detection |
| `lan` | LAN IP, subnet, link aggregation, flow control |
| `firewall` | SPI firewall, IoT security, access control overview |
| `access` | Access control details (whitelist/blacklist) |
| `nat` | NAT boost, virtual servers, port triggering, DMZ, ALG |
| `qos` | QoS bandwidth control, device priority list, game accelerator |
| `ddns` | Dynamic DNS (TP-Link, DynDNS, No-IP) |
| `upnp` | UPnP status and active service mappings |
| `imb` | IP-MAC binding settings and ARP table |
| `ports` | Physical port status (speed, duplex, WAN/LAN) |
| `iptv` | IPTV, IGMP snooping, port assignments |
| `guest` | Guest network and captive portal settings |
| `mesh` | EasyMesh status and topology |
| `cloud` | TP-Link cloud account, firmware update check |
| `disk` | USB disk info and Time Machine settings |
| `speedtest` | Speed test results and live WAN throughput |
| `rebootsched` | Scheduled reboot settings |
| `sharing` | USB/folder/media sharing configuration |
| `logs [TYPE]` | System logs (filter: NETWORK, NAT, FIREWALL, DHCP, etc.) |
| `mode` | Operation mode (router/AP/repeater) |
| `firmware` | Firmware version, auto-upgrade settings, config backup |
| `vpn` | VPN configs (OpenVPN, PPTP, WireGuard) |
| `admin` | Administration (remote mgmt, HTTPS, recovery, email alerts) |
| `eco` | Eco mode / power-saving settings |
| `led` | LED control and night mode schedule |
| `time` | Time/NTP and DST settings |
| `diag` | Router diagnostics |
| `ipv6` | Full IPv6 configuration |
| `routes` | Routing table (system + static routes) |

### Advanced Commands

| Command | Description |
|---------|-------------|
| `read <endpoint>` | Read raw data from any endpoint |
| `write <endpoint> key=value ...` | Write settings to any endpoint |
| `reboot` | Reboot the router (requires confirmation) |
| `endpoints` | List all 130 known API endpoints |
| `dump` | Export every readable setting to a JSON file |
| `monitor` | Continuous network health check (ping + WAN uptime) |

### Examples

```bash
# Full status overview
tplink-be400 r1 status

# List connected devices
tplink-be400 r1 devices

# Check WiFi settings
tplink-be400 r1 wifi

# View firewall rules
tplink-be400 r1 firewall

# Enable WAN ping
tplink-be400 r1 write security/firewall wan_ping=on

# Set up DMZ host
tplink-be400 r1 write nat/dmz enable=on ipaddr=192.168.0.100

# Read a raw endpoint
tplink-be400 r1 read wireless/statistics

# Dump everything to JSON
tplink-be400 r1 dump

# Monitor network stability
tplink-be400 r1 monitor
```

## Rate Limiting / Router Stability

The BE400's web server is an embedded system with limited resources. **Rapid-fire API calls can crash the router**, causing a watchdog reboot with no crash logs.

Guidelines for safe usage:

- **Single commands are always safe.** Normal CLI usage (one command at a time) will never cause issues.
- **Scripting**: Add at least a 2-second delay between commands. Avoid running `dump` repeatedly.
- **Session churn**: Each CLI invocation creates a new authenticated session (RSA key exchange + AES encryption). Running many commands in rapid succession creates heavy CPU load on the router.
- **The `dump` command** reads all 130 endpoints sequentially and takes ~60 seconds. Don't run it more than once every few minutes.
- **The `monitor` command** uses a 25-second polling interval by design.

If the router becomes unresponsive after heavy API usage, wait 60-90 seconds for it to reboot automatically.

## How It Works

This tool communicates with the router's internal web API — the same API that the browser-based admin panel uses. All endpoints were discovered by reverse-engineering the router's JavaScript bundles.

Authentication uses RSA + AES encryption (handled by the `tplinkrouterc6u` library). Every request goes through the same encrypted channel as the web UI.

## Dependencies

- [tplinkrouterc6u](https://github.com/AlexandrEroworker/TP-Link-Archer-C6U) — TP-Link router API library
- [pycryptodome](https://github.com/Legrandin/pycryptodome) — RSA/AES encryption

## Compatibility

| Router | Firmware | Status |
|--------|----------|--------|
| Archer BE400 v1.0 | 1.0.4 Build 20240904 | Fully tested |
| Other TP-Link routers | — | May partially work |

## License

MIT
