"""
All 130 reverse-engineered API endpoints for the TP-Link Archer BE400.
Discovered by tracing every JavaScript model file in the router's web UI
firmware v1.0.4 (build 2024-09-04), verified on v1.1.2 (build 2025-10-21).

Each entry maps a shortname to (api_path, default_operation).
"""

ENDPOINTS = {
    # === Status ===
    "status/all":                   ("admin/status?form=all", "read"),
    "status/perf":                  ("admin/status?form=perf", "read"),
    "status/internet":              ("admin/status?form=internet", "read"),
    "status/router":                ("admin/status?form=router", "read"),
    "status/wan_speed":             ("admin/status?form=wan_speed", "read"),
    "status/wan_dual_nat":          ("admin/status?form=wan_dual_nat_state", "read"),
    "status/menu":                  ("admin/status?form=menu_status", "read"),
    "status/speedtest":             ("admin/status?form=speedtest", "read"),
    "status/user_exp":              ("admin/status?form=user_experience_plan_switch", "read"),
    "status/cloud_pop":             ("admin/status?form=cloud_login_window_pop", "read"),

    # === System ===
    "system/sysmode":               ("admin/system?form=sysmode", "read"),
    "system/reboot":                ("admin/system?form=reboot", "read"),

    # === Firmware ===
    "firmware/upgrade":             ("admin/firmware?form=upgrade", "read"),
    "firmware/auto_upgrade":        ("admin/firmware?form=auto_upgrade", "read"),
    "firmware/config":              ("admin/firmware?form=config", "read"),

    # === Network - WAN ===
    "network/status_ipv4":          ("admin/network?form=status_ipv4", "read"),
    "network/wan_status":           ("admin/network?form=wan_ipv4_status", "read"),
    "network/wan_protos":           ("admin/network?form=wan_ipv4_protos", "read"),
    "network/wan_fc":               ("admin/network?form=wan_fc", "read"),
    "network/wan_detect":           ("admin/network?form=wan_detect_state", "read"),
    "network/wan_port":             ("admin/network?form=wan_port_status", "read"),
    "network/port_names":           ("admin/network?form=get_port_display_name", "read"),
    "network/port_speed":           ("admin/network?form=port_speed_current", "read"),
    "network/port_speed_supported": ("admin/network?form=port_speed_supported", "read"),

    # === Network - LAN ===
    "network/lan_ipv4":             ("admin/network?form=lan_ipv4", "read"),
    "network/lan_agg":              ("admin/network?form=lan_agg", "read"),
    "network/lan_fc":               ("admin/network?form=lan_fc", "read"),

    # === Network - Routes ===
    "network/routes_system":        ("admin/network?form=routes_system", "load"),
    "network/routes_static":        ("admin/network?form=routes_static", "load"),

    # === Network - IPv6 ===
    "network/lan_ipv6":             ("admin/network?form=lan_ipv6", "read"),
    "network/wan_ipv6_status":      ("admin/network?form=wan_ipv6_status", "read"),
    "network/wan_ipv6_dynamic":     ("admin/network?form=wan_ipv6_dynamic", "read"),
    "network/wan_ipv6_pass":        ("admin/network?form=wan_ipv6_pass", "read"),
    "network/wan_ipv6_pppoe":       ("admin/network?form=wan_ipv6_pppoe", "read"),
    "network/wan_ipv6_protos":      ("admin/network?form=wan_ipv6_protos", "read"),
    "network/wan_ipv6_static":      ("admin/network?form=wan_ipv6_static", "read"),
    "network/wan_ipv6_tunnel":      ("admin/network?form=wan_ipv6_tunnel", "read"),

    # === DHCP ===
    "dhcps/setting":                ("admin/dhcps?form=setting", "read"),
    "dhcps/client":                 ("admin/dhcps?form=client", "load"),
    "dhcps/reservation":            ("admin/dhcps?form=reservation", "load"),

    # === Wireless ===
    "wireless/wireless_2g":         ("admin/wireless?form=wireless_2g", "read"),
    "wireless/wireless_5g":         ("admin/wireless?form=wireless_5g", "read"),
    "wireless/wireless_5g_2":       ("admin/wireless?form=wireless_5g_2", "read"),
    "wireless/guest":               ("admin/wireless?form=guest", "read"),
    "wireless/statistics":          ("admin/wireless?form=statistics", "load"),
    "wireless/wps":                 ("admin/wireless?form=syspara_wps", "read"),
    "wireless/wps_connect":         ("admin/wireless?form=wps_connect", "read"),
    "wireless/wps_pin":             ("admin/wireless?form=wps_pin", "read"),
    "wireless/ofdma":               ("admin/wireless?form=ofdma", "read"),
    "wireless/ofdma_mimo":          ("admin/wireless?form=ofdma_mimo", "read"),
    "wireless/region":              ("admin/wireless?form=region", "read"),
    "wireless/smart_connect":       ("admin/wireless?form=smart_connect", "read"),
    "wireless/twt":                 ("admin/wireless?form=twt", "read"),
    "wireless/advanced":            ("admin/wireless?form=wireless_addition_setting", "read"),
    "wireless/portal_content":      ("admin/wireless?form=portal_content", "read"),

    # === Security / Firewall ===
    "security/firewall":            ("admin/security_settings?form=new_enable", "read"),
    "security/iot":                 ("admin/iot_security?form=enable", "read"),
    "security/iot_devices_main":    ("admin/iot_security?form=isolated_devices_main", "load"),
    "security/iot_devices_iot":     ("admin/iot_security?form=isolated_devices_iot", "load"),
    "security/iot_isolated":        ("admin/iot_security?form=isolated_list", "load"),

    # === Access Control ===
    "access/enable":                ("admin/access_control?form=enable", "read"),
    "access/mode":                  ("admin/access_control?form=mode", "read"),
    "access/white_list":            ("admin/access_control?form=white_list", "load"),
    "access/black_list":            ("admin/access_control?form=black_list", "load"),
    "access/white_devices":         ("admin/access_control?form=white_devices", "load"),
    "access/black_devices":         ("admin/access_control?form=black_devices", "load"),

    # === NAT / Port Forwarding ===
    "nat/setting":                  ("admin/nat?form=setting", "read"),
    "nat/virtual_servers":          ("admin/nat?form=vs", "load"),
    "nat/port_triggering":          ("admin/nat?form=pt", "load"),
    "nat/dmz":                      ("admin/nat?form=dmz", "read"),
    "nat/alg":                      ("admin/nat?form=alg", "read"),
    "nat/clients":                  ("admin/nat?form=client_list", "load"),

    # === DDNS ===
    "ddns/provider":                ("admin/ddns?form=provider", "read"),
    "ddns/tplink":                  ("admin/ddns?form=tplink", "load"),
    "ddns/dyndns":                  ("admin/ddns?form=dyndns", "read"),
    "ddns/noip":                    ("admin/ddns?form=noip", "read"),

    # === QoS / Smart Network ===
    "qos/setting":                  ("admin/smart_network?form=qos", "read"),
    "qos/device_priority":          ("admin/smart_network?form=device_priority", "load"),
    "qos/host_info":                ("admin/smart_network?form=get_host_info", "read"),
    "qos/accelerator":              ("admin/smart_network?form=game_accelerator", "loadDevice"),

    # === IP-MAC Binding ===
    "imb/setting":                  ("admin/imb?form=setting", "read"),
    "imb/arp_list":                 ("admin/imb?form=arp_list", "load"),
    "imb/bind_list":                ("admin/imb?form=bind_list", "load"),
    "imb/client_list":              ("admin/imb?form=client_list", "read"),

    # === IPTV / Ports ===
    "iptv/setting":                 ("admin/iptv?form=setting", "read"),
    "iptv/udp_proxy":               ("admin/iptv?form=udp_proxy_setting", "read"),

    # === UPnP ===
    "upnp/enable":                  ("admin/upnp?form=enable", "read"),
    "upnp/service":                 ("admin/upnp?form=service", "load"),

    # === Logs ===
    "syslog/log":                   ("admin/syslog?form=log", "load"),
    "syslog/types":                 ("admin/syslog?form=types", "load"),
    "syslog/filter":                ("admin/syslog?form=filter", "read"),
    "syslog/mail":                  ("admin/syslog?form=mail", "read"),

    # === Time / NTP ===
    "time/settings":                ("admin/time?form=settings", "read"),
    "time/dst":                     ("admin/time?form=dst", "read"),

    # === LED / Eco ===
    "ledgeneral/setting":           ("admin/ledgeneral?form=setting", "read"),
    "ledpm/setting":                ("admin/ledpm?form=setting", "read"),
    "eco_mode/settings":            ("admin/eco_mode?form=settings", "read"),

    # === Diagnostics ===
    "diag/diag":                    ("admin/diag?form=diag", "read"),

    # === VPN Server ===
    "openvpn/config":               ("admin/openvpn?form=config", "read"),
    "pptpd/config":                 ("admin/pptpd?form=config", "read"),
    "pptpd/accounts":               ("admin/pptpd?form=accounts", "load"),
    "wireguard/config":             ("admin/wireguard?form=config", "read"),
    "wireguard/account":            ("admin/wireguard?form=account", "load"),

    # === Administration ===
    "admin/account":                ("admin/administration?form=account", "read"),
    "admin/mode":                   ("admin/administration?form=mode", "read"),
    "admin/remote":                 ("admin/administration?form=remote", "read"),
    "admin/recovery":               ("admin/administration?form=recovery", "read"),
    "admin/https":                  ("admin/administration?form=https", "read"),
    "admin/local":                  ("admin/administration?form=local", "load"),

    # === Reboot Schedule ===
    "reboot/schedule":              ("admin/reboot?form=set", "read"),

    # === EasyMesh ===
    "easymesh/enable":              ("admin/easymesh?form=easymesh_enable", "read"),
    "easymesh/topo":                ("admin/easymesh_network?form=get_mesh_topo", "read"),

    # === Guest Portal ===
    "guest/portal":                 ("admin/wireless?form=portal_content", "read"),
    "guest/background":             ("admin/wifidog?form=portal_background", "read"),
    "guest/logo":                   ("admin/wifidog?form=portal_logo", "read"),

    # === Quick Setup ===
    "quick_setup/config":           ("admin/quick_setup?form=quick_setup", "read"),

    # === Cloud ===
    "cloud/device_info":            ("admin/cloud_account?form=get_deviceInfo", "read"),
    "cloud/remind":                 ("admin/cloud_account?form=remind", "read"),
    "cloud/bind_status":            ("admin/cloud_account?form=cloud_bind_status", "read"),
    "cloud/upgrade":                ("admin/cloud_account?form=cloud_upgrade", "read"),

    # === Storage / Disk ===
    "disk/metadata":                ("admin/disk_setting?form=metadata", "read"),
    "disk/scan":                    ("admin/disk_setting?form=scan", "read"),
    "time_machine/settings":        ("admin/time_machine?form=settings", "read"),

    # === Folder Sharing ===
    "folder_sharing/settings":      ("admin/folder_sharing?form=settings", "read"),
    "folder_sharing/server":        ("admin/folder_sharing?form=server", "read"),
    "folder_sharing/auth":          ("admin/folder_sharing?form=auth", "read"),
    "folder_sharing/media":         ("admin/folder_sharing?form=media", "read"),
    "folder_sharing/mode":          ("admin/folder_sharing?form=mode", "read"),

    # === Privacy / FFS ===
    "privacy/fing":                 ("admin/privacy_policy?form=fing_auth_state", "read"),
    "ffs/config":                   ("admin/ffs?form=config", "read"),
}
