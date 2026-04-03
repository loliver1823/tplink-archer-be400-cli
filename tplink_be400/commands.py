"""All high-level CLI commands for the TP-Link Archer BE400."""
import json
import time
import datetime
import subprocess

from .endpoints import ENDPOINTS
from .connection import safe_request, fmt, print_table


def cmd_status(r, label):
    print(f"\n  {label}")
    print(f"  {'=' * 50}")
    fw = safe_request(r, "admin/firmware?form=upgrade", "read") or {}
    print(f"  Model:    {fw.get('model', '?')} ({fw.get('hardware_version', '?')})")
    print(f"  Firmware: {fw.get('firmware_version', '?')}")
    s = safe_request(r, "admin/status?form=all", "read") or {}
    print(f"  CPU:      {float(s.get('cpu_usage', 0)) * 100:.0f}%")
    print(f"  Memory:   {float(s.get('mem_usage', 0)) * 100:.0f}%")
    net = safe_request(r, "admin/network?form=status_ipv4", "read") or {}
    print(f"  LAN IP:   {net.get('lan_ipv4_ipaddr', '?')}")
    wan_up = net.get('wan_ipv4_uptime', '')
    if wan_up:
        h, m, sec = int(wan_up) // 3600, (int(wan_up) % 3600) // 60, int(wan_up) % 60
        print(f"  WAN IP:   {net.get('wan_ipv4_ipaddr', '?')}")
        print(f"  WAN GW:   {net.get('wan_ipv4_gateway', '?')}")
        print(f"  WAN Up:   {wan_up}s ({h}h {m}m {sec}s)")
        print(f"  WAN DNS:  {net.get('wan_ipv4_pridns', '?')} / {net.get('wan_ipv4_snddns', '?')}")
    print(f"  DHCP:     {net.get('lan_ipv4_dhcp_enable', '?')}")
    mode = safe_request(r, "admin/system?form=sysmode", "read") or {}
    print(f"  Mode:     {mode.get('mode', '?')}")
    t = safe_request(r, "admin/time?form=settings", "read") or {}
    print(f"  Time:     {t.get('date', '?')} {t.get('time', '?')} ({t.get('day', '?')})")
    wired = s.get("access_devices_wired", [])
    wireless = s.get("access_devices_wireless_host", [])
    print(f"  Clients:  {len(wired)} wired, {len(wireless)} wireless")
    inet = safe_request(r, "admin/status?form=internet", "read") or {}
    print(f"  Internet: {inet.get('internet_status', '?')}")
    menu = safe_request(r, "admin/status?form=menu_status", "read")
    if menu and isinstance(menu, dict):
        print(f"\n  Menu Status:")
        for k, v in sorted(menu.items()):
            print(f"    {k}: {v}")
    ux = safe_request(r, "admin/status?form=user_experience_plan_switch", "read")
    if ux and isinstance(ux, dict):
        print(f"  User Exp Plan: {ux.get('enable', ux)}")


def cmd_devices(r, label):
    print(f"\n  Connected Devices -- {label}")
    s = safe_request(r, "admin/status?form=all", "read")
    if not s:
        print("    Error: could not reach router")
        return
    rows = []
    for d in s.get("access_devices_wired", []):
        rows.append((d.get("hostname", "?"), d.get("ipaddr", "?"), d.get("macaddr", "?"), "Wired"))
    for d in s.get("access_devices_wireless_host", []):
        rows.append((d.get("hostname", "?"), d.get("ipaddr", "?"), d.get("macaddr", "?"), d.get("wire_type", "WiFi")))
    print_table(rows, ["Hostname", "IP", "MAC", "Connection"])


def cmd_wifi(r, label):
    print(f"\n  WiFi Settings -- {label}")
    for band, path in [("2.4GHz", "wireless_2g"), ("5GHz", "wireless_5g"), ("5GHz-2", "wireless_5g_2")]:
        w = safe_request(r, f"admin/wireless?form={path}", "read")
        if not w or (w.get("enable") == "off" and not w.get("ssid")):
            continue
        print(f"\n  [{band}]")
        print(f"    SSID:       {w.get('ssid')}")
        print(f"    Enabled:    {w.get('enable')}")
        print(f"    Channel:    {w.get('current_channel')} (configured: {w.get('channel')})")
        print(f"    Width:      {w.get('htmode')}")
        print(f"    Encryption: {w.get('encryption')} / {w.get('psk_version')}")
        print(f"    Password:   {w.get('psk_key')}")
        print(f"    TX Power:   {w.get('txpower')}")
        print(f"    MAC:        {w.get('macaddr')}")
    sc = safe_request(r, "admin/wireless?form=smart_connect", "read")
    if sc:
        print(f"\n  Smart Connect: {sc.get('smart_enable')}")
    ofdma = safe_request(r, "admin/wireless?form=ofdma", "read")
    if ofdma:
        print(f"  OFDMA:         {ofdma.get('enable')}")
    mimo = safe_request(r, "admin/wireless?form=ofdma_mimo", "read")
    if mimo:
        for k, v in sorted(mimo.items()):
            print(f"  MIMO {k}: {v}")
    twt = safe_request(r, "admin/wireless?form=twt", "read")
    if twt:
        print(f"  TWT:           {twt.get('enable')}")
    wps = safe_request(r, "admin/wireless?form=syspara_wps", "read")
    if wps and isinstance(wps, dict):
        wps_en = wps.get("wps") or wps.get("enable") or wps.get("wps_enable")
        wps_pin = wps.get("pin") or wps.get("wps_pin")
        wps_time = wps.get("wait_time")
        parts = [f"enabled={wps_en}"]
        if wps_pin:
            parts.append(f"PIN={wps_pin}")
        if wps_time:
            parts.append(f"timeout={wps_time}s")
        print(f"\n  WPS: {' '.join(parts)}")
    wps_conn = safe_request(r, "admin/wireless?form=wps_connect", "read")
    if wps_conn and isinstance(wps_conn, dict):
        print(f"  WPS Connect: disabled={wps_conn.get('disabled','?')} available={wps_conn.get('available','?')} timeout={wps_conn.get('wps_timeout','?')}ms")
    wps_p = safe_request(r, "admin/wireless?form=wps_pin", "read")
    if wps_p and isinstance(wps_p, dict):
        print(f"  WPS PIN:     {wps_p.get('wps_pin','?')} label={wps_p.get('wps_label','?')}")
    region = safe_request(r, "admin/wireless?form=region", "read")
    if region and isinstance(region, dict):
        reg = region.get("region") or region.get("country")
        if reg:
            print(f"  Region:        {reg}")
    adv = safe_request(r, "admin/wireless?form=wireless_addition_setting", "read")
    if adv:
        print(f"\n  Advanced Wireless:")
        for k, v in sorted(adv.items()):
            print(f"    {k}: {v}")
    stats = safe_request(r, "admin/wireless?form=statistics", "load")
    if stats and isinstance(stats, list) and stats:
        print(f"\n  WiFi Client Stats ({len(stats)}):")
        rows = [(s.get("mac", "?"), s.get("type", "?"), s.get("encryption", "?"), str(s.get("rxpkts", 0)), str(s.get("txpkts", 0))) for s in stats if isinstance(s, dict)]
        if rows:
            print_table(rows, ["MAC", "Band", "Encryption", "RX Pkts", "TX Pkts"])


def cmd_dhcp(r, label):
    print(f"\n  DHCP -- {label}")
    d = safe_request(r, "admin/dhcps?form=setting", "read")
    if not d:
        print("    Error: could not read DHCP settings")
        return
    for k, v in sorted(d.items()):
        print(f"    {k}: {v}")
    clients = safe_request(r, "admin/dhcps?form=client", "load")
    if clients and isinstance(clients, list):
        print(f"\n  DHCP Leases ({len(clients)}):")
        rows = [(c.get("name", "?"), c.get("ipaddr", "?"), c.get("macaddr", "?"), c.get("leasetime", "?")) for c in clients]
        print_table(rows, ["Name", "IP", "MAC", "Lease"])
    reservations = safe_request(r, "admin/dhcps?form=reservation", "load")
    if reservations and isinstance(reservations, list) and reservations:
        print(f"\n  Reservations ({len(reservations)}):")
        rows = [(c.get("comment", "?"), c.get("ip", "?"), c.get("mac", "?"), c.get("enable", "?")) for c in reservations]
        print_table(rows, ["Name", "IP", "MAC", "Enabled"])


def cmd_wan(r, label):
    print(f"\n  WAN Status -- {label}")
    net = safe_request(r, "admin/network?form=status_ipv4", "read")
    if not net:
        print("    Error: could not read WAN status")
        return
    for k, v in sorted(net.items()):
        print(f"    {k}: {v}")
    ws = safe_request(r, "admin/network?form=wan_ipv4_status", "read")
    if ws:
        print(f"\n  WAN Detection:")
        for k, v in sorted(ws.items()):
            print(f"    {k}: {v}")
    inet = safe_request(r, "admin/status?form=internet", "read")
    if inet:
        print(f"\n  Internet Status:")
        for k, v in sorted(inet.items()):
            print(f"    {k}: {v}")
    ps = safe_request(r, "admin/network?form=port_speed_current", "read")
    if ps:
        print(f"\n  Port Speed: {ps.get('speed')}")
    protos = safe_request(r, "admin/network?form=wan_ipv4_protos", "read")
    if protos:
        if isinstance(protos, list):
            names = [p.get("name", p) if isinstance(p, dict) else str(p) for p in protos]
            print(f"\n  WAN Protocols: {', '.join(names)}")
        elif isinstance(protos, dict):
            print(f"\n  WAN Protocols:")
            for k, v in sorted(protos.items()):
                print(f"    {k}: {v}")
    wfc = safe_request(r, "admin/network?form=wan_fc", "read")
    if wfc:
        print(f"\n  WAN Flow Control: TX={wfc.get('tx_enable')} RX={wfc.get('rx_enable')}")
    detect = safe_request(r, "admin/network?form=wan_detect_state", "read")
    if detect and isinstance(detect, dict):
        print(f"  WAN Detect: {'on' if detect.get('enable') else 'off'}")
    dnat = safe_request(r, "admin/status?form=wan_dual_nat_state", "read")
    if dnat and isinstance(dnat, dict):
        state = dnat.get("wan_dual_nat", "")
        if state:
            print(f"  Double NAT: {state}")


def cmd_lan(r, label):
    print(f"\n  LAN Settings -- {label}")
    lan = safe_request(r, "admin/network?form=lan_ipv4", "read")
    if not lan:
        print("    Error: could not read LAN settings")
        return
    print(f"    IP Address:  {lan.get('ipaddr')}")
    print(f"    Subnet Mask: {lan.get('mask_type')}")
    print(f"    MAC Address: {lan.get('macaddr')}")
    print(f"    LAN Type:    {lan.get('lan_type')}")
    print(f"    Primary DNS: {lan.get('pri_dns', '(auto)')}")
    print(f"    Second DNS:  {lan.get('snd_dns', '(auto)')}")
    agg = safe_request(r, "admin/network?form=lan_agg", "read")
    if agg:
        print(f"\n  Link Aggregation:")
        print(f"    Enabled:   {agg.get('enable_agg')}")
        print(f"    LACP Mode: {agg.get('lacpmode')}")
        ports = agg.get('port_settings', [])
        if isinstance(ports, list):
            for p in ports:
                print(f"    {p.get('name')}: {'enabled' if p.get('enable') else 'disabled'}")
    fc = safe_request(r, "admin/network?form=lan_fc", "read")
    if fc:
        print(f"\n  Flow Control: TX={fc.get('tx_enable')} RX={fc.get('rx_enable')}")


def cmd_firewall(r, label):
    print(f"\n  Firewall / Security -- {label}")
    sec = safe_request(r, "admin/security_settings?form=new_enable", "read")
    if not sec:
        print("    Error: could not read firewall settings")
        return
    print(f"    SPI Firewall: {sec.get('enable')}")
    print(f"    LAN Ping:     {sec.get('lan_ping')}")
    print(f"    WAN Ping:     {sec.get('wan_ping')}")
    iot = safe_request(r, "admin/iot_security?form=enable", "read")
    if iot:
        print(f"    IoT Security: {iot.get('enable')}")
    iot_main = safe_request(r, "admin/iot_security?form=isolated_devices_main", "load")
    if iot_main and isinstance(iot_main, list) and iot_main:
        print(f"\n  IoT Isolated Devices - Main ({len(iot_main)}):")
        for d in iot_main:
            if isinstance(d, dict):
                print(f"    {d.get('name','?'):20s} {d.get('mac','?'):18s} {d.get('ipaddr','?')}")
    iot_iot = safe_request(r, "admin/iot_security?form=isolated_devices_iot", "load")
    if iot_iot and isinstance(iot_iot, list) and iot_iot:
        print(f"\n  IoT Isolated Devices - IoT ({len(iot_iot)}):")
        for d in iot_iot:
            if isinstance(d, dict):
                print(f"    {d.get('name','?'):20s} {d.get('mac','?'):18s} {d.get('ipaddr','?')}")
    ac = safe_request(r, "admin/access_control?form=enable", "read")
    if ac:
        print(f"\n  Access Control:")
        print(f"    Enabled:  {ac.get('enable')}")
        print(f"    Host MAC: {ac.get('host_mac')}")
    mode = safe_request(r, "admin/access_control?form=mode", "read")
    if mode:
        print(f"    Mode:     {mode.get('access_mode')}")


def cmd_nat(r, label):
    print(f"\n  NAT / Port Forwarding -- {label}")
    setting = safe_request(r, "admin/nat?form=setting", "read")
    if setting:
        print(f"    NAT Boost:   {setting.get('enable')}")
        print(f"    HW Boost:    {setting.get('boost_enable')}")
    dmz = safe_request(r, "admin/nat?form=dmz", "read")
    if dmz:
        print(f"\n  DMZ: enabled={dmz.get('enable')} host={dmz.get('ipaddr')}")
    alg = safe_request(r, "admin/nat?form=alg", "read")
    if alg:
        print(f"\n  ALG:")
        for k, v in sorted(alg.items()):
            print(f"    {k}: {v}")
    vs = safe_request(r, "admin/nat?form=vs", "load")
    if vs:
        items = vs.get("data", vs) if isinstance(vs, dict) else vs
        if isinstance(items, list) and items:
            print(f"\n  Virtual Servers ({len(items)}):")
            for v in items:
                if isinstance(v, dict):
                    print(f"    {v.get('name','?')}: {v.get('ipaddr','?')}:{v.get('intport','?')}->{v.get('extport','?')} [{v.get('protocol','?')}] enabled={v.get('enable','?')}")
    pt = safe_request(r, "admin/nat?form=pt", "load")
    if pt:
        items = pt.get("data", pt) if isinstance(pt, dict) else pt
        if isinstance(items, list) and items:
            print(f"\n  Port Triggering ({len(items)}):")
            for t in items:
                if isinstance(t, dict):
                    print(f"    {t}")


def cmd_ddns(r, label):
    print(f"\n  DDNS -- {label}")
    prov = safe_request(r, "admin/ddns?form=provider", "read")
    if prov:
        print(f"    Provider: {prov.get('provider')}")
    for name, ep in [("TP-Link", "admin/ddns?form=tplink"), ("DynDNS", "admin/ddns?form=dyndns"), ("No-IP", "admin/ddns?form=noip")]:
        data = safe_request(r, ep, "read") or safe_request(r, ep, "load")
        if data:
            print(f"\n  [{name}]")
            if isinstance(data, dict):
                for k, v in sorted(data.items()):
                    print(f"    {k}: {v}")


def cmd_qos(r, label):
    print(f"\n  QoS / Smart Network -- {label}")
    qos = safe_request(r, "admin/smart_network?form=qos", "read")
    if qos:
        print(f"    Enabled:      {qos.get('enable')}")
        print(f"    App Control:  {qos.get('enable_app')}")
        print(f"    Upload:       {qos.get('up_band')} (max {qos.get('max_up_band')})")
        print(f"    Download max: {qos.get('max_down_band')}")
        print(f"    WAN Speed:    {qos.get('max_wan_speed')}")
        print(f"    Priority:     high={qos.get('high')} low={qos.get('low')}")
    dp = safe_request(r, "admin/smart_network?form=device_priority", "load")
    if dp and isinstance(dp, list) and dp:
        print(f"\n  Device Priority ({len(dp)}):")
        rows = [(d.get("deviceName","?"), d.get("mac","?"), d.get("deviceType","?"), d.get("deviceTag","?"),
                 "ON" if d.get("enablePriority") else "off", d.get("timePeriod","?"),
                 f"{d.get('downloadSpeed',0)}/{d.get('uploadSpeed',0)}") for d in dp if isinstance(d, dict)]
        print_table(rows, ["Name", "MAC", "Type", "Conn", "Priority", "Time", "DL/UL"])
    ga = safe_request(r, "admin/smart_network?form=game_accelerator", "loadDevice")
    if ga and isinstance(ga, list) and ga:
        print(f"\n  Game Accelerator ({len(ga)} devices):")
        for d in ga:
            if isinstance(d, dict):
                print(f"    {d.get('deviceName', d.get('name','?')):20s} {d.get('mac','?')} [{d.get('deviceType', d.get('type','?'))}]")


def cmd_imb(r, label):
    print(f"\n  IP-MAC Binding -- {label}")
    setting = safe_request(r, "admin/imb?form=setting", "read")
    if setting:
        print(f"    Enabled: {setting.get('enable')}")
    arp = safe_request(r, "admin/imb?form=arp_list", "load")
    if arp and isinstance(arp, list):
        items = arp[0].get("data", arp) if isinstance(arp[0], dict) and "data" in arp[0] else arp
        if isinstance(items, list):
            print(f"\n  ARP Table ({len(items)}):")
            rows = [(e.get("name", "?"), e.get("ipaddr", "?"), e.get("mac", "?"), e.get("enable", "?")) for e in items if isinstance(e, dict)]
            if rows:
                print_table(rows, ["Name", "IP", "MAC", "Bound"])


def cmd_access(r, label):
    print(f"\n  Access Control -- {label}")
    en = safe_request(r, "admin/access_control?form=enable", "read")
    if en:
        print(f"    Enabled:  {en.get('enable')}")
        print(f"    Host MAC: {en.get('host_mac')}")
    mode = safe_request(r, "admin/access_control?form=mode", "read")
    if mode:
        print(f"    Mode:     {mode.get('access_mode')}")
    wl = safe_request(r, "admin/access_control?form=white_list", "load")
    if wl:
        items = wl.get("data", wl) if isinstance(wl, dict) else wl
        if isinstance(items, list) and items:
            print(f"\n  Whitelist ({len(items)}):")
            for d in items:
                if isinstance(d, dict):
                    print(f"    {d.get('name','?'):20s} {d.get('mac','?'):18s}")
        else:
            print(f"\n  Whitelist: (empty)")
    bl = safe_request(r, "admin/access_control?form=black_list", "load")
    if bl:
        items = bl.get("data", bl) if isinstance(bl, dict) else bl
        if isinstance(items, list) and items:
            print(f"\n  Blacklist ({len(items)}):")
            for d in items:
                if isinstance(d, dict):
                    print(f"    {d.get('name','?'):20s} {d.get('mac','?'):18s}")
        else:
            print(f"\n  Blacklist: (empty)")


def cmd_guest(r, label):
    print(f"\n  Guest Network -- {label}")
    g = safe_request(r, "admin/wireless?form=guest", "read")
    if g:
        for k, v in sorted(g.items()):
            print(f"    {k}: {v}")
    portal = safe_request(r, "admin/wireless?form=portal_content", "read")
    if portal:
        print(f"\n  Portal Page:")
        print(f"    Title:       {portal.get('title')}")
        print(f"    Content:     {portal.get('content')}")
        print(f"    Theme:       {portal.get('theme_color')} (opacity {portal.get('theme_opacity')})")
        print(f"    Font:        {portal.get('font_color')} (opacity {portal.get('font_opacity')})")
    bg = safe_request(r, "admin/wifidog?form=portal_background", "read")
    if bg:
        print(f"    Background:  {bg.get('url', bg)}")
    logo = safe_request(r, "admin/wifidog?form=portal_logo", "read")
    if logo:
        print(f"    Logo:        {logo.get('url', logo)}")


def cmd_iptv(r, label):
    print(f"\n  IPTV / Port Assignments -- {label}")
    iptv = safe_request(r, "admin/iptv?form=setting", "read")
    if not iptv:
        print("    Error: could not read IPTV settings")
        return
    ports = iptv.get("port_settings", [])
    if isinstance(ports, list):
        rows = [(p.get("name", "?"), p.get("type", "?")) for p in ports]
        print_table(rows, ["Port", "Type"])
    print(f"\n    IPTV enable:       {iptv.get('enable')}")
    print(f"    IGMP enable:       {iptv.get('igmp_enable')}")
    print(f"    IGMP snooping:     {iptv.get('igmp_snooping_enable')}")
    print(f"    IGMP version:      {iptv.get('igmp_version')}")
    print(f"    Multicast WiFi:    {iptv.get('mcwifi_enable')}")
    udp = safe_request(r, "admin/iptv?form=udp_proxy_setting", "read")
    if udp:
        print(f"    UDP Proxy:         {udp.get('udp_proxy_enable')} (port {udp.get('udp_proxy')})")


def cmd_mesh(r, label):
    print(f"\n  EasyMesh -- {label}")
    en = safe_request(r, "admin/easymesh?form=easymesh_enable", "read")
    if en:
        print(f"    Enabled: {en.get('enable')}")
        print(f"    Time:    {en.get('time')}")
    topo = safe_request(r, "admin/easymesh_network?form=get_mesh_topo", "read")
    if topo:
        if isinstance(topo, dict) and topo:
            print(f"\n  Topology:")
            for k, v in sorted(topo.items()):
                print(f"    {k}: {v}")
        elif isinstance(topo, list) and topo:
            print(f"\n  Topology ({len(topo)} nodes):")
            for node in topo:
                print(f"    {node}")
        else:
            print(f"    Topology: (no mesh nodes)")


def cmd_cloud(r, label):
    print(f"\n  TP-Link Cloud -- {label}")
    bind = safe_request(r, "admin/cloud_account?form=cloud_bind_status", "read")
    if bind:
        print(f"    Bound: {bind.get('isbind')}")
    info = safe_request(r, "admin/cloud_account?form=get_deviceInfo", "read")
    if info:
        print(f"    Model: {info.get('model')}")
    upgrade = safe_request(r, "admin/cloud_account?form=cloud_upgrade", "read")
    if upgrade:
        print(f"    Latest FW:  {upgrade.get('latest_version', 'n/a')}")
        print(f"    Up to date: {upgrade.get('latest_flag')}")
    remind = safe_request(r, "admin/cloud_account?form=remind", "read")
    if remind:
        print(f"    Remind:     {remind.get('type')}")
    pop = safe_request(r, "admin/status?form=cloud_login_window_pop", "read")
    if pop and isinstance(pop, dict):
        print(f"    Login Pop:  {pop.get('cloud_login_window_pop', pop)}")


def cmd_disk(r, label):
    print(f"\n  USB / Disk -- {label}")
    meta = safe_request(r, "admin/disk_setting?form=metadata", "read")
    if meta:
        print(f"    Disk count: {meta.get('number')}")
        for d in meta.get('list', []):
            if isinstance(d, dict):
                for k, v in d.items():
                    print(f"    {k}: {v}")
    scan = safe_request(r, "admin/disk_setting?form=scan", "read")
    if scan:
        print(f"    Scan count: {scan.get('number')}")
    tm = safe_request(r, "admin/time_machine?form=settings", "read")
    if tm:
        print(f"\n  Time Machine:")
        print(f"    Enabled:  {tm.get('enable')}")
        print(f"    Capacity: {tm.get('capacity')}")
        print(f"    Free:     {tm.get('free')}")
        print(f"    Status:   {tm.get('disk_status')}")


def cmd_speedtest(r, label):
    print(f"\n  Speed Test -- {label}")
    st = safe_request(r, "admin/status?form=speedtest", "read")
    if st:
        print(f"    Download: {st.get('down_speed')} bps")
        print(f"    Upload:   {st.get('up_speed')} bps")
        print(f"    Time:     {st.get('test_time')}")
        print(f"    Status:   {st.get('status')}")
    ws = safe_request(r, "admin/status?form=wan_speed", "read")
    if ws:
        print(f"\n  Current WAN Speed:")
        print(f"    Download: {ws.get('down_speed')} bps")
        print(f"    Upload:   {ws.get('up_speed')} bps")


def cmd_ports(r, label):
    print(f"\n  Port Status -- {label}")
    ports = safe_request(r, "admin/status?form=router", "read")
    if ports and isinstance(ports, list):
        rows = [(p.get("name", "?"), p.get("status", "?"), f"{p.get('speed', '?')}Mbps", p.get("duplex", "?"), "WAN" if p.get("is_wan") else "LAN") for p in ports]
        print_table(rows, ["Port", "Status", "Speed", "Duplex", "Type"])
    names = safe_request(r, "admin/network?form=get_port_display_name", "read")
    if names and isinstance(names, dict) and names.get("port_name"):
        print(f"\n  Port Names:")
        for p in names.get("port_name", []):
            if isinstance(p, dict):
                print(f"    {p.get('port','?')}: {p.get('name','?')}")
    wp = safe_request(r, "admin/network?form=wan_port_status", "read")
    if wp and isinstance(wp, dict):
        print(f"\n  WAN Port: {wp.get('wan_port', wp)}")


def cmd_logs(r, label, log_type="ALL"):
    if log_type != "ALL":
        safe_request(r, "admin/syslog?form=filter", "read")
        try:
            r.request("admin/syslog?form=filter", f"operation=write&type={log_type}&level=ALL")
        except Exception as e:
            print(f"  Warning: could not set log filter: {e}")
    logs = safe_request(r, "admin/syslog?form=log", "load")
    if logs is None:
        print(f"\n  System Logs -- {label} (filter: {log_type})")
        print("    Error: could not retrieve logs")
        return
    print(f"\n  System Logs -- {label} (filter: {log_type}, {len(logs)} entries)")
    if isinstance(logs, list):
        for entry in logs:
            if isinstance(entry, dict):
                print(f"  [{entry.get('time', '')}] [{entry.get('type', '')}] [{entry.get('level', '')}] {entry.get('content', '')}")
    if log_type != "ALL":
        try:
            r.request("admin/syslog?form=filter", "operation=write&type=ALL&level=ALL")
        except Exception:
            pass


def cmd_time(r, label):
    print(f"\n  Time/NTP -- {label}")
    t = safe_request(r, "admin/time?form=settings", "read")
    if not t:
        print("    Error: could not read time settings")
        return
    for k, v in sorted(t.items()):
        print(f"    {k}: {v}")
    dst = safe_request(r, "admin/time?form=dst", "read")
    if dst:
        print(f"\n  DST:")
        for k, v in sorted(dst.items()):
            print(f"    {k}: {v}")


def cmd_led(r, label):
    print(f"\n  LED Control -- {label}")
    g = safe_request(r, "admin/ledgeneral?form=setting", "read")
    if g:
        print(f"  General: enabled={g.get('enable')}")
    pm = safe_request(r, "admin/ledpm?form=setting", "read")
    if pm:
        print(f"  Night Mode: enabled={pm.get('enable')} ({pm.get('time_start')} - {pm.get('time_end')})")


def cmd_mode(r, label):
    print(f"\n  Operation Mode -- {label}")
    m = safe_request(r, "admin/system?form=sysmode", "read")
    if not m:
        print("    Error: could not read operation mode")
        return
    for k, v in sorted(m.items()):
        print(f"    {k}: {v}")


def cmd_firmware(r, label):
    print(f"\n  Firmware -- {label}")
    fw = safe_request(r, "admin/firmware?form=upgrade", "read")
    if not fw:
        print("    Error: could not read firmware info")
        return
    for k, v in sorted(fw.items()):
        print(f"    {k}: {v}")
    au = safe_request(r, "admin/firmware?form=auto_upgrade", "read")
    if au:
        print(f"\n  Auto Upgrade: enabled={au.get('enable')} time={au.get('time')}:00")
    cfg = safe_request(r, "admin/firmware?form=config", "read")
    if cfg and isinstance(cfg, dict):
        print(f"\n  Config Backup:")
        for k, v in sorted(cfg.items()):
            print(f"    {k}: {v}")


def cmd_vpn(r, label):
    print(f"\n  VPN -- {label}")
    for name, ep in [("OpenVPN", "admin/openvpn?form=config"), ("PPTP", "admin/pptpd?form=config"), ("WireGuard", "admin/wireguard?form=config")]:
        data = safe_request(r, ep, "read")
        if data:
            print(f"\n  [{name}]")
            for k, v in sorted(data.items()):
                print(f"    {k}: {v}")
    accts = safe_request(r, "admin/pptpd?form=accounts", "load")
    if accts and isinstance(accts, list) and accts:
        print(f"\n  PPTP Accounts ({len(accts)}):")
        for a in accts:
            print(f"    {a}")
    wg_accts = safe_request(r, "admin/wireguard?form=account", "load")
    if wg_accts and isinstance(wg_accts, list) and wg_accts:
        print(f"\n  WireGuard Peers ({len(wg_accts)}):")
        for a in wg_accts:
            if isinstance(a, dict):
                print(f"    {a.get('name','?')}: {a.get('public_key','?')[:20]}... allowed={a.get('allowed_ips','?')}")
            else:
                print(f"    {a}")


def cmd_eco(r, label):
    print(f"\n  Eco Mode -- {label}")
    eco = safe_request(r, "admin/eco_mode?form=settings", "read")
    if not eco:
        print("    Error: could not read eco mode settings")
        return
    for k, v in sorted(eco.items()):
        print(f"    {k}: {v}")


def cmd_upnp(r, label):
    print(f"\n  UPnP -- {label}")
    en = safe_request(r, "admin/upnp?form=enable", "read")
    if en:
        print(f"    Enabled: {en.get('enable')}")
    svc = safe_request(r, "admin/upnp?form=service", "load")
    if svc:
        items = svc.get("data", svc) if isinstance(svc, dict) else svc
        if isinstance(items, list) and items:
            print(f"\n  Active Services ({len(items)}):")
            for s in items:
                if isinstance(s, dict):
                    print(f"    {s.get('name','?')}: {s.get('ipaddr','?')}:{s.get('internal_port','?')} -> {s.get('external_port','?')} [{s.get('protocol','?')}]")


def cmd_admin(r, label):
    print(f"\n  Administration -- {label}")
    acct = safe_request(r, "admin/administration?form=account", "read")
    if acct and isinstance(acct, dict):
        name = acct.get("name") or acct.get("old_acc") or "(default)"
        print(f"    Account: {name}")
    mode = safe_request(r, "admin/administration?form=mode", "read")
    if mode:
        print(f"    Admin Mode: {mode.get('mode')}")
    remote = safe_request(r, "admin/administration?form=remote", "read")
    if remote:
        print(f"\n  Remote Management:")
        print(f"    Enabled:    {remote.get('enable')}")
        print(f"    HTTP Port:  {remote.get('http_port')}")
        print(f"    HTTPS Port: {remote.get('https_port')}")
    https = safe_request(r, "admin/administration?form=https", "read")
    if https:
        print(f"    HTTPS:      {https.get('https_enable')}")
    recovery = safe_request(r, "admin/administration?form=recovery", "read")
    if recovery:
        print(f"\n  Password Recovery: {recovery.get('enable_rec')}")
    local = safe_request(r, "admin/administration?form=local", "load")
    if local and isinstance(local, list) and local:
        print(f"\n  Local Management ({len(local)}):")
        for entry in local:
            if isinstance(entry, dict):
                print(f"    {entry.get('mac','?')} ({entry.get('name','?')})")
    mail = safe_request(r, "admin/syslog?form=mail", "read")
    if mail:
        print(f"\n  Log Email Alerts:")
        print(f"    Enabled: {mail.get('enable')}")
        if mail.get('server'):
            print(f"    Server:  {mail.get('server')}:{mail.get('port')}")
            print(f"    From:    {mail.get('from_addr')}")
            print(f"    To:      {mail.get('to_addr')}")
    qs = safe_request(r, "admin/quick_setup?form=quick_setup", "read")
    if qs and isinstance(qs, dict):
        print(f"\n  Quick Setup:")
        for k, v in sorted(qs.items()):
            print(f"    {k}: {v}")
    fing = safe_request(r, "admin/privacy_policy?form=fing_auth_state", "read")
    if fing and isinstance(fing, dict):
        print(f"\n  Fing Fingerprint: {fing.get('enable', fing)}")
    ffs = safe_request(r, "admin/ffs?form=config", "read")
    if ffs and isinstance(ffs, dict):
        print(f"  FFS Config: {ffs}")


def cmd_diag(r, label):
    print(f"\n  Diagnostics -- {label}")
    d = safe_request(r, "admin/diag?form=diag", "read")
    if not d:
        print("    Error: could not read diagnostics")
        return
    for k, v in sorted(d.items()):
        print(f"    {k}: {v}")


def cmd_sharing(r, label):
    print(f"\n  USB / Folder Sharing -- {label}")
    for name, ep in [("Settings", "admin/folder_sharing?form=settings"), ("Server", "admin/folder_sharing?form=server"), ("Mode", "admin/folder_sharing?form=mode"), ("Auth", "admin/folder_sharing?form=auth"), ("Media", "admin/folder_sharing?form=media")]:
        data = safe_request(r, ep, "read")
        if data:
            print(f"  {name}: {data}")


def cmd_ipv6(r, label):
    print(f"\n  IPv6 -- {label}")
    for name, ep in [("Status", "admin/network?form=wan_ipv6_status"), ("LAN", "admin/network?form=lan_ipv6"), ("Dynamic", "admin/network?form=wan_ipv6_dynamic"), ("Static", "admin/network?form=wan_ipv6_static"), ("PPPoE", "admin/network?form=wan_ipv6_pppoe"), ("Passthrough", "admin/network?form=wan_ipv6_pass"), ("Tunnel", "admin/network?form=wan_ipv6_tunnel")]:
        data = safe_request(r, ep, "read")
        if data:
            print(f"\n  [{name}]")
            for k, v in sorted(data.items()):
                print(f"    {k}: {v}")


def cmd_rebootsched(r, label):
    print(f"\n  Reboot Schedule -- {label}")
    sched = safe_request(r, "admin/reboot?form=schedule", "read")
    if sched:
        print(f"    Enabled: {sched.get('enable')}")
        print(f"    Time:    {sched.get('time')}")
        print(f"    Days:    {sched.get('day')}")
    else:
        print(f"    (not configured)")


def cmd_routes(r, label):
    print(f"\n  Routing Table -- {label}")
    sys_routes = safe_request(r, "admin/network?form=routes_system", "load")
    if sys_routes and isinstance(sys_routes, list):
        print(f"\n  System Routes ({len(sys_routes)}):")
        rows = [(rt.get("dest", "?"), rt.get("mask", "?"), rt.get("gateway", "?"), rt.get("interface", "?")) for rt in sys_routes]
        print_table(rows, ["Destination", "Mask", "Gateway", "Interface"])
    static = safe_request(r, "admin/network?form=routes_static", "load")
    if static and isinstance(static, list) and static:
        print(f"\n  Static Routes ({len(static)}):")
        rows = [(rt.get("dest", "?"), rt.get("mask", "?"), rt.get("gateway", "?"), rt.get("interface", "?"), rt.get("enable", "?")) for rt in static]
        print_table(rows, ["Destination", "Mask", "Gateway", "Interface", "Enabled"])


def cmd_read(r, label, endpoint):
    if endpoint in ENDPOINTS:
        path = ENDPOINTS[endpoint][0]
    elif "/" in endpoint and "?" not in endpoint:
        path = f"admin/{endpoint.replace('/', '?form=')}"
    else:
        path = endpoint
    for op in ["read", "load"]:
        data = safe_request(r, path, op)
        if data is not None:
            print(f"\n  {path} [{op}] -- {label}")
            print(fmt(data))
            return
    print(f"  Endpoint not found or not responding: {path}")


def cmd_write(r, label, endpoint, params):
    if endpoint in ENDPOINTS:
        path = ENDPOINTS[endpoint][0]
    elif "/" in endpoint and "?" not in endpoint:
        path = f"admin/{endpoint.replace('/', '?form=')}"
    else:
        path = endpoint
    current = safe_request(r, path, "read")
    if current is None:
        current = safe_request(r, path, "load")
    if current is None:
        current = {}
    if isinstance(current, dict):
        for p in params:
            if "=" in p:
                k, v = p.split("=", 1)
                current[k] = v
    parts = ["operation=write"]
    if isinstance(current, dict):
        for k, v in current.items():
            parts.append(f"{k}={json.dumps(v) if isinstance(v, (dict, list)) else v}")
    else:
        parts.extend(params)
    write_data = "&".join(parts)
    print(f"\n  Writing to {path} -- {label}")
    print(f"  Payload: {write_data[:300]}...")
    try:
        result = r.request(path, write_data)
        print(f"  OK: {fmt(result)[:500]}")
    except Exception as e:
        print(f"  Error: {str(e)[:300]}")


def cmd_reboot(r, label):
    confirm = input(f"  Reboot {label}? Type 'yes': ")
    if confirm.strip().lower() != "yes":
        print("  Cancelled.")
        return
    print(f"  Rebooting {label}...")
    try:
        r.request("admin/system?form=reboot", "operation=write", ignore_response=True)
    except Exception:
        pass
    print("  Reboot command sent.")


def cmd_endpoints(r, label):
    print(f"\n  Known Endpoints ({len(ENDPOINTS)}):\n")
    by_category = {}
    for key in sorted(ENDPOINTS.keys()):
        cat = key.split("/")[0]
        by_category.setdefault(cat, []).append(key)
    for cat in sorted(by_category.keys()):
        print(f"  [{cat}]")
        for key in by_category[cat]:
            path, op = ENDPOINTS[key]
            print(f"    {key:40s} {path} [{op}]")
        print()


def cmd_dump(r, label, router_key):
    print(f"\n  Dumping all endpoints -- {label}")
    dump = {}
    for key, (path, op) in sorted(ENDPOINTS.items()):
        data = safe_request(r, path, op)
        if data is not None:
            dump[key] = data
            ct = "dict" if isinstance(data, dict) else f"list[{len(data)}]" if isinstance(data, list) else type(data).__name__
            print(f"    OK: {key} ({ct})")
        else:
            print(f"    SKIP: {key}")
    import os
    outfile = os.path.join(os.path.expanduser("~"), f"router_dump_{router_key}.json")
    with open(outfile, "w") as f:
        json.dump(dump, f, indent=2, default=str)
    print(f"\n  Saved {len(dump)} endpoints to {outfile}")


def cmd_monitor(r, label, host, password):
    import platform
    print(f"\n  Monitoring {label} -- Ctrl+C to stop\n")
    is_windows = platform.system() == "Windows"
    prev_uptime = -1
    check = 0
    session = r
    while True:
        check += 1
        now = datetime.datetime.now().strftime("%H:%M:%S")
        lost = 0
        times = []
        try:
            ping_cmd = (
                ["ping", "-n", "4", "-w", "2000", "8.8.8.8"]
                if is_windows
                else ["ping", "-c", "4", "-W", "2", "8.8.8.8"]
            )
            result = subprocess.run(ping_cmd, capture_output=True, text=True, timeout=15)
            for line in result.stdout.split("\n"):
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
        except Exception:
            lost = 4
        avg = sum(times) / len(times) if times else -1
        uptime = -1
        try:
            st = session.request("admin/network?form=status_ipv4", "operation=read")
            uptime = int(st.get("wan_ipv4_uptime", -1))
        except Exception:
            try:
                from tplinkrouterc6u import TplinkRouter as TR
                session = TR(host, password)
                session.authorize()
                st = session.request("admin/network?form=status_ipv4", "operation=read")
                uptime = int(st.get("wan_ipv4_uptime", -1))
            except Exception:
                pass
        reboot_marker = ""
        if 0 <= uptime < prev_uptime:
            reboot_marker = " *** WAN RECONNECTED ***"
        prev_uptime = uptime
        status = "OK" if lost == 0 else f"LOSS({lost}/4)"
        up_str = f"{uptime}s ({uptime // 3600}h{(uptime % 3600) // 60}m)" if uptime >= 0 else "?"
        print(f"  [{now}] #{check:3d}  Ping: {status} avg={avg:.0f}ms  WAN: {up_str}{reboot_marker}")
        time.sleep(25)
