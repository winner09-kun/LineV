"""Validate the PRD topology schema and load-critical Packet Tracer XML."""
import argparse
import copy
import ipaddress as ip
import math
import re
import sys
import xml.etree.ElementTree as ET
from common import PACKAGE, load_spec, local_path

MODELS = {"router": "2911", "switch": "2960-24TT", "pc": "PC-PT", "server": "Server-PT"}

def require(condition, message):
    if not condition:
        raise ValueError(message)

def keys(obj, allowed, context):
    require(isinstance(obj, dict), f"{context}: harus mapping")
    extra = set(obj) - set(allowed.split())
    require(not extra, f"{context}: field tidak didukung {extra}")

def token(value, context):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,62}", value), f"{context}: nama tidak valid")
    return value

def port_name(value):
    require(isinstance(value, str), "Nama port harus teks")
    for short, full in (("Gi", "GigabitEthernet"), ("Fa", "FastEthernet")):
        if re.fullmatch(short + r"\d+(?:/\d+)*", value):
            return full + value[len(short):]
    return value

def ports(model):
    # These PT modules encode names implicitly by model and slot order.
    if model == "2911":
        return {f"GigabitEthernet0/{i}" for i in range(3)}
    if model == "2960-24TT":
        return {f"FastEthernet0/{i}" for i in range(1, 25)} | {"GigabitEthernet0/1", "GigabitEthernet0/2"}
    return {"FastEthernet0"}

def address(value):
    require(isinstance(value, str) and "/" in value, f"Alamat harus IPv4/CIDR: {value}")
    a = ip.IPv4Interface(value)
    require(a.ip not in (a.network.network_address, a.network.broadcast_address) or a.network.prefixlen >= 31, f"Alamat host tidak valid: {value}")
    return a

def vlan(value):
    n = int(value)
    require(str(n) == str(value) and 1 <= n <= 4094, f"VLAN tidak valid: {value}")
    return n

def normalize(spec):
    s = copy.deepcopy(spec)
    keys(s, "name devices links", "spec")
    token(s.get("name"), "name")
    require(isinstance(s.get("devices"), list) and 0 < len(s["devices"]) <= 100, "devices harus berisi 1-100 perangkat")
    require(isinstance(s.get("links", []), list), "links harus list")
    devices, used_ips = {}, {}
    for i, d in enumerate(s["devices"]):
        keys(d, "id type model position interfaces config vlans ports ip gateway", "device")
        name = token(d.get("id"), "device.id")
        require(name not in devices, f"ID ganda: {name}")
        require(d.get("type") in MODELS, f"{name}: tipe tidak didukung")
        model = str(d.get("model", MODELS[d["type"]]))
        d["model"] = "2960-24TT" if model == "2960" else model
        require(d["model"] == MODELS[d["type"]], f"{name}: model MVP tidak didukung {model}")
        d.setdefault("position", [160 + (i % 5) * 220, 130 + (i // 5) * 200])
        require(isinstance(d["position"], list) and len(d["position"]) == 2 and all(type(n) in (int, float) and math.isfinite(n) and 0 <= n <= 3800 for n in d["position"]), f"{name}: position tidak valid")
        valid_ports = ports(d["model"])
        interfaces = d.get("interfaces", {})
        require(isinstance(interfaces, dict), f"{name}: interfaces harus mapping")
        d["interfaces"] = {}
        for p, a in interfaces.items():
            p = port_name(p)
            require(p in valid_ports and p not in d["interfaces"], f"{name}: port interface tidak valid/ganda {p}")
            require(d["type"] == "router", "interfaces IPv4 MVP hanya untuk router; gunakan ip untuk PC/server")
            address(a)
            d["interfaces"][p] = a
        if d["type"] in ("pc", "server"):
            require(not d.get("vlans") and not d.get("ports") and not d.get("config"), f"{name}: konfigurasi IOS tidak berlaku pada host")
            if "ip" in d:
                a = address(d["ip"])
                if d.get("gateway"):
                    gw = ip.IPv4Address(d["gateway"])
                    require(gw in a.network and gw != a.ip and gw not in (a.network.network_address, a.network.broadcast_address), f"{name}: gateway tidak valid atau beda subnet")
            else:
                require("gateway" not in d, f"{name}: gateway memerlukan ip")
        else:
            require("ip" not in d and "gateway" not in d, f"{name}: gunakan interfaces untuk router")
        for a in list(d["interfaces"].values()) + ([d["ip"]] if "ip" in d else []):
            host = str(address(a).ip)
            require(host not in used_ips, f"IP ganda {host}: {used_ips.get(host)} dan {name}")
            used_ips[host] = name
        raw_vlans = d.get("vlans", {})
        require(isinstance(raw_vlans, dict), f"{name}: vlans harus mapping")
        d["vlans"] = {vlan(k): token(v, "VLAN name") for k, v in raw_vlans.items()}
        require(not d["vlans"] or d["type"] == "switch", "VLAN hanya untuk switch")
        raw_ports = d.get("ports", {})
        require(isinstance(raw_ports, dict), f"{name}: ports harus mapping")
        d["ports"] = {}
        for p, mode in raw_ports.items():
            p = port_name(p)
            require(d["type"] == "switch" and p in valid_ports and p not in d["ports"], f"{name}: switch port tidak valid/ganda {p}")
            keys(mode, "mode vlan allowed_vlans native_vlan", "switch port")
            require(mode.get("mode") in ("access", "trunk"), "mode harus access/trunk")
            if mode["mode"] == "access":
                require("allowed_vlans" not in mode and "native_vlan" not in mode, "access tidak menerima parameter trunk")
                mode["vlan"] = vlan(mode.get("vlan", 1))
                selected = [mode["vlan"]]
            else:
                require("vlan" not in mode, "trunk memakai allowed_vlans")
                require(isinstance(mode.get("allowed_vlans"), list) and mode["allowed_vlans"], "trunk memerlukan allowed_vlans")
                mode["allowed_vlans"] = sorted({vlan(v) for v in mode["allowed_vlans"]})
                mode["native_vlan"] = vlan(mode.get("native_vlan", 1))
                selected = mode["allowed_vlans"] + [mode["native_vlan"]]
            require(all(v == 1 or v in d["vlans"] for v in selected), f"{name}: VLAN port belum didefinisikan")
            d["ports"][p] = mode
        config = d.setdefault("config", {})
        keys(config, "ospf static_routes dhcp", f"{name}.config")
        require(not config or d["type"] == "router", "Routing/DHCP hanya pada router")
        if "ospf" in config:
            o = config["ospf"]
            keys(o, "process networks area", "ospf")
            require(type(o.get("process", 1)) is int and 1 <= o.get("process", 1) <= 65535, "OSPF process tidak valid")
            require(type(o.get("area", 0)) is int and 0 <= o.get("area", 0) <= 4294967295, "OSPF area tidak valid")
            require(isinstance(o.get("networks"), list) and o["networks"], "OSPF networks wajib")
            for n in o["networks"]:
                ip.IPv4Network(n)
        require(isinstance(config.get("static_routes", []), list), "static_routes harus list")
        for r in config.get("static_routes", []):
            keys(r, "network next_hop", "static route")
            ip.IPv4Network(r["network"])
            hop = ip.IPv4Address(r["next_hop"])
            require(any(hop in address(a).network and hop != address(a).ip for a in d["interfaces"].values()), f"{name}: next hop tidak terhubung langsung")
        require(isinstance(config.get("dhcp", []), list), "dhcp harus list")
        pools = set()
        for p in config.get("dhcp", []):
            keys(p, "name network gateway dns excluded", "dhcp")
            token(p.get("name"), "DHCP pool")
            require(p["name"] not in pools, "DHCP pool ganda")
            pools.add(p["name"])
            net = ip.IPv4Network(p["network"])
            require(ip.IPv4Address(p["gateway"]) in net, "Gateway DHCP beda subnet")
            require(any(address(a).network == net and str(address(a).ip) == p["gateway"] for a in d["interfaces"].values()), "DHCP MVP memerlukan gateway interface lokal")
            if p.get("dns"):
                ip.IPv4Address(p["dns"])
            require(isinstance(p.get("excluded", []), list), "excluded harus list alamat IPv4")
            for a in p.get("excluded", []):
                require(ip.IPv4Address(a) in net, "Excluded DHCP beda subnet")
        devices[name] = d
    used_ports, links = set(), []
    for link in s.get("links", []):
        if isinstance(link, list):
            require(len(link) == 2, "Link harus dua endpoint")
            link = {"from": link[0], "to": link[1]}
        keys(link, "from to cable", "link")
        endpoints = []
        for side in ("from", "to"):
            endpoint = link.get(side)
            require(isinstance(endpoint, str) and endpoint.count(":") == 1, "Endpoint harus device:port")
            dev, p = endpoint.split(":")
            p = port_name(p)
            require(dev in devices, f"Link yatim: {dev}")
            require(p in ports(devices[dev]["model"]), f"Port tidak tersedia: {dev}:{p}")
            endpoint = f"{dev}:{p}"
            require(endpoint not in used_ports, f"Port bentrok: {endpoint}")
            used_ports.add(endpoint)
            link[side] = endpoint
            endpoints.append(dev)
        require(endpoints[0] != endpoints[1], "Link ke perangkat sendiri tidak didukung")
        types = [devices[n]["type"] == "switch" for n in endpoints]
        link.setdefault("cable", "cross" if types[0] == types[1] else "straight")
        require(link["cable"] in ("cross", "straight"), "cable harus straight/cross")
        links.append(link)
    s["links"] = links
    return s

def validate_xml(data):
    require(b"<!ENTITY" not in data.upper() and b"<!DOCTYPE" not in data.upper(), "DTD/entity XML tidak didukung")
    root = ET.fromstring(data)
    require(root.tag == "PACKETTRACER5", "Bukan XML topologi .pkt")
    devs = root.findall("NETWORK/DEVICES/DEVICE")
    ids, names, used_ips = {}, set(), {}
    for d in devs:
        sid, name = d.findtext("ENGINE/SAVE_REF_ID"), d.findtext("ENGINE/NAME")
        require(sid and sid not in ids and name and name not in names, "ID/nama perangkat XML ganda atau kosong")
        model = d.find("ENGINE/TYPE").get("model")
        require(model in MODELS.values(), f"Model XML belum didukung: {model}")
        ids[sid] = ports(model)
        names.add(name)
        actual = []
        if model in ("PC-PT", "Server-PT"):
            actual = [p.findtext("IP") for p in d.iter("PORT")]
        else:
            for line in d.findall("ENGINE/RUNNINGCONFIG/LINE"):
                m = re.fullmatch(r"\s*ip address (\S+) (\S+)\s*", line.text or "")
                if m:
                    ip.IPv4Interface(f"{m[1]}/{m[2]}")
                    actual.append(m[1])
        for value in actual:
            if value and value != "0.0.0.0":
                host = str(ip.IPv4Address(value))
                require(host not in used_ips, f"IP XML ganda {host}: {used_ips.get(host)} dan {name}")
                used_ips[host] = name
    occupied = set()
    for link in root.findall("NETWORK/LINKS/LINK"):
        c = link.find("CABLE")
        require(c is not None, "Cable XML tidak ada")
        ps = c.findall("PORT")
        require(len(ps) == 2, "Cable XML perlu dua port")
        for sid, p in zip((c.findtext("FROM"), c.findtext("TO")), ps):
            require(sid in ids and p.text in ids[sid], "Link XML yatim atau port tidak valid")
            pair = (sid, p.text)
            require(pair not in occupied, "Port XML bentrok")
            occupied.add(pair)
    return root

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--workspace", default=".")
    p.add_argument("--xml", action="store_true")
    a = p.parse_args()
    try:
        f = local_path(a.input, a.workspace, exists=True)
        validate_xml(f.read_bytes()) if a.xml else normalize(load_spec(f))
        print("Valid")
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
        p.exit(2, f"Validasi gagal: {exc}\n")

if __name__ == "__main__":
    main()
