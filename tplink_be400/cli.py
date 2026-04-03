"""CLI entry point for tplink-be400."""
import argparse
import sys

from .endpoints import ENDPOINTS
from .config import load_config, create_default_config, CONFIG_FILE
from .connection import connect
from . import commands


HELP_TEXT = f"""
tplink-be400 -- TP-Link Archer BE400 Router CLI ({len(ENDPOINTS)} endpoints)

Usage:
  tplink-be400 <router> <command> [args...]
  tplink-be400 --host <ip> --password <pw> <command> [args...]

Commands:
  status                  Full router status overview
  devices                 List all connected devices
  wifi                    WiFi settings (all bands + OFDMA/TWT/WPS)
  dhcp                    DHCP config + lease table
  wan                     WAN/internet status + detection
  lan                     LAN IP, subnet, aggregation, flow control
  firewall                SPI firewall + IoT security + access control
  access                  Access control (whitelist / blacklist)
  nat                     NAT boost, port forwarding, DMZ, ALG
  qos                     QoS / bandwidth control / device priority
  ddns                    Dynamic DNS settings
  upnp                    UPnP status + active services
  imb                     IP-MAC binding + ARP table
  ports                   Physical port status (speed/duplex)
  iptv                    IPTV / IGMP / port assignments
  guest                   Guest network + portal settings
  mesh                    EasyMesh status + topology
  cloud                   TP-Link cloud account + firmware check
  disk                    USB disk info + Time Machine
  speedtest               Speed test results + live WAN speed
  rebootsched             Scheduled reboot settings
  sharing                 USB / folder / media sharing
  logs [TYPE]             System logs (NETWORK, NAT, FIREWALL, etc.)
  mode                    Operation mode (router/ap/repeater)
  firmware                Firmware version + auto-upgrade settings
  vpn                     VPN configs (OpenVPN, PPTP, WireGuard)
  admin                   Administration (remote mgmt, HTTPS, recovery)
  eco                     Eco mode / power settings
  led                     LED control + night mode
  time                    Time/NTP + DST settings
  diag                    Diagnostics
  ipv6                    IPv6 configuration
  routes                  Routing table (system + static)

  read <endpoint>         Read a raw endpoint
  write <endpoint> k=v    Write to an endpoint
  reboot                  Reboot the router (with confirmation)
  endpoints               List all known API endpoints
  dump                    Dump every readable setting to JSON file
  monitor                 Continuous network health monitoring

  discover                Scan LAN for TP-Link routers (see --subnet, --match-model)

Examples:
  tplink-be400 r1 status
  tplink-be400 r1 firewall
  tplink-be400 r1 write security/firewall wan_ping=on
  tplink-be400 r1 write nat/dmz enable=on ipaddr=192.168.0.100
  tplink-be400 --host 192.168.0.1 --password secret status
  tplink-be400 r1 monitor
  tplink-be400 discover --match-model BE400

Config: {CONFIG_FILE}
"""


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP_TEXT)
        return

    # Parse --host/--password flags
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--subnet", default=None, help="CIDR for discover (default: auto /24)")
    parser.add_argument("--match-model", default=None, dest="match_model", help="Filter discover by model substring")
    parser.add_argument("--no-auth-discovery", action="store_true", help="Fingerprint only; do not log in per host")
    parser.add_argument("positional", nargs="*")
    parsed = parser.parse_args()

    if parsed.setup:
        path = create_default_config()
        print(f"  Config created at: {path}")
        print(f"  Edit it to add your router IP and password.")
        return

    if parsed.positional and parsed.positional[0] == "discover":
        password_cfg, _ = load_config()
        commands.cmd_discover(
            subnet=parsed.subnet,
            password=password_cfg,
            match_model=parsed.match_model,
            no_auth=parsed.no_auth_discovery,
        )
        return

    password_cfg, routers = load_config()

    if parsed.host:
        host = parsed.host if parsed.host.startswith("http") else f"http://{parsed.host}"
        password = parsed.password or password_cfg
        label = host
        router_key = "direct"
        if not password:
            print("  Error: --password required when using --host")
            print(f"  Or set password in config: {CONFIG_FILE}")
            sys.exit(1)
        if len(parsed.positional) < 1:
            print("  Error: missing command")
            sys.exit(1)
        cmd = parsed.positional[0]
        args = parsed.positional[1:]
    else:
        if len(parsed.positional) < 2:
            if not routers and not password_cfg:
                print("  No config found. Run: tplink-be400 --setup")
                print(f"  Then edit: {CONFIG_FILE}")
                return
            print(HELP_TEXT)
            return
        router_key = parsed.positional[0]
        cmd = parsed.positional[1]
        args = parsed.positional[2:]
        if router_key not in routers:
            print(f"  Unknown router: {router_key}")
            print(f"  Available: {', '.join(routers.keys())}")
            sys.exit(1)
        host, label = routers[router_key]
        password = password_cfg
        if not password:
            print(f"  Error: no password in config: {CONFIG_FILE}")
            sys.exit(1)

    r = connect(host, password)

    try:
        command_map = {
            "status": lambda: commands.cmd_status(r, label),
            "devices": lambda: commands.cmd_devices(r, label),
            "wifi": lambda: commands.cmd_wifi(r, label),
            "dhcp": lambda: commands.cmd_dhcp(r, label),
            "wan": lambda: commands.cmd_wan(r, label),
            "lan": lambda: commands.cmd_lan(r, label),
            "firewall": lambda: commands.cmd_firewall(r, label),
            "security": lambda: commands.cmd_firewall(r, label),
            "access": lambda: commands.cmd_access(r, label),
            "nat": lambda: commands.cmd_nat(r, label),
            "qos": lambda: commands.cmd_qos(r, label),
            "ddns": lambda: commands.cmd_ddns(r, label),
            "upnp": lambda: commands.cmd_upnp(r, label),
            "imb": lambda: commands.cmd_imb(r, label),
            "ports": lambda: commands.cmd_ports(r, label),
            "iptv": lambda: commands.cmd_iptv(r, label),
            "guest": lambda: commands.cmd_guest(r, label),
            "mesh": lambda: commands.cmd_mesh(r, label),
            "cloud": lambda: commands.cmd_cloud(r, label),
            "disk": lambda: commands.cmd_disk(r, label),
            "speedtest": lambda: commands.cmd_speedtest(r, label),
            "rebootsched": lambda: commands.cmd_rebootsched(r, label),
            "logs": lambda: commands.cmd_logs(r, label, args[0] if args else "ALL"),
            "mode": lambda: commands.cmd_mode(r, label),
            "firmware": lambda: commands.cmd_firmware(r, label),
            "vpn": lambda: commands.cmd_vpn(r, label),
            "admin": lambda: commands.cmd_admin(r, label),
            "eco": lambda: commands.cmd_eco(r, label),
            "led": lambda: commands.cmd_led(r, label),
            "time": lambda: commands.cmd_time(r, label),
            "diag": lambda: commands.cmd_diag(r, label),
            "ipv6": lambda: commands.cmd_ipv6(r, label),
            "routes": lambda: commands.cmd_routes(r, label),
            "sharing": lambda: commands.cmd_sharing(r, label),
            "monitor": lambda: commands.cmd_monitor(r, label, host, password),
            "endpoints": lambda: commands.cmd_endpoints(r, label),
            "dump": lambda: commands.cmd_dump(r, label, router_key),
            "read": lambda: commands.cmd_read(r, label, args[0] if args else "status/all"),
            "write": lambda: commands.cmd_write(r, label, args[0], args[1:]) if len(args) >= 2 else print("  Usage: write <endpoint> key=value ..."),
            "load": lambda: commands.cmd_read(r, label, args[0] if args else "syslog/log"),
            "reboot": lambda: commands.cmd_reboot(r, label),
        }
        if cmd in command_map:
            command_map[cmd]()
        else:
            print(f"  Unknown command: {cmd}")
            print(f"  Available: {', '.join(sorted(command_map.keys()))}")
    finally:
        try:
            r.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()
