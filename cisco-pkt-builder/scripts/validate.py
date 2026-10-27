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
    for short, full in (("Gi", "GigabitEthernet"), ("Fa", "FastEthernet"), ("Se", "Serial")):
        if re.fullmatch(short + r"\d+(?:/\d+)*", value):
            return full + value[len(short):]
    return value

def ports(model, serial=False):
    # These PT modules encode names implicitly by model and slot order.
    if model == "2911":
        return {f"GigabitEthernet0/{i}" for i in range(3)} | ({"Serial0/0/0", "Serial0/0/1"} if serial else set())
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
        keys(d, "id type model position interfaces config vlans ports ip gateway module", "device")
        name = token(d.get("id"), "device.id")
        require(name not in devices, f"ID ganda: {name}")
        require(d.get("type") in MODELS, f"{name}: tipe tidak didukung")
        model = str(d.get("model", MODELS[d["type"]]))
        d["model"] = "2960-24TT" if model == "2960" else model
        require(d["model"] == MODELS[d["type"]], f"{name}: model MVP tidak didukung {model}")
        d.setdefault("position", [160 + (i % 5) * 220, 130 + (i // 5) * 200])
        require(isinstance(d["position"], list) and len(d["position"]) == 2 and all(type(n) in (int, float) and math.isfinite(n) and 0 <= n <= 3800 for n in d["position"]), f"{name}: position tidak valid")
        require("module" not in d or (d["model"] == "2911" and d["module"] == "HWIC-2T"), "Module hanya HWIC-2T pada 2911 slot 0")
        valid_ports = ports(d["model"], "module" in d)
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
        keys(config, "ospf static_routes dhcp bgp", f"{name}.config")
        require(not config or d["type"] == "router", "Routing/DHCP hanya pada router")
        if "bgp" in config:
            b = config["bgp"]
            keys(b, "asn networks neighbors", "bgp")
            require(type(b.get("asn")) is int and 1 <= b["asn"] <= 65535, "BGP ASN harus 1-65535")
            require(isinstance(b.get("networks"), list) and b["networks"], "BGP networks wajib")
            connected = {address(a).network for a in d["interfaces"].values()}
            for network in b["networks"]:
                require(ip.IPv4Network(network) in connected, "BGP network harus subnet interface lokal (MVP)")
            require(isinstance(b.get("neighbors"), list) and b["neighbors"], "BGP neighbors wajib")
            seen = set()
            for neighbor in b["neighbors"]:
                keys(neighbor, "ip remote_as", "bgp neighbor")
                peer = ip.IPv4Address(neighbor["ip"])
                require(str(peer) not in seen, "BGP neighbor ganda")
                seen.add(str(peer))
                require(type(neighbor.get("remote_as")) is int and 1 <= neighbor["remote_as"] <= 65535 and neighbor["remote_as"] != b["asn"], "BGP MVP hanya eBGP dengan remote_as berbeda")
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
        keys(link, "from to cable dce clock_rate", "link")
        endpoints = []
        for side in ("from", "to"):
            endpoint = link.get(side)
            require(isinstance(endpoint, str) and endpoint.count(":") == 1, "Endpoint harus device:port")
            dev, p = endpoint.split(":")
            p = port_name(p)
            require(dev in devices, f"Link yatim: {dev}")
            require(p in ports(devices[dev]["model"], "module" in devices[dev]), f"Port tidak tersedia: {dev}:{p}")
            endpoint = f"{dev}:{p}"
            require(endpoint not in used_ports, f"Port bentrok: {endpoint}")
            used_ports.add(endpoint)
            link[side] = endpoint
            endpoints.append(dev)
        require(endpoints[0] != endpoints[1], "Link ke perangkat sendiri tidak didukung")
        types = [devices[n]["type"] == "switch" for n in endpoints]
        serial_ports = [link[side].split(":")[1].startswith("Serial") for side in ("from", "to")]
        require(serial_ports[0] == serial_ports[1], "Serial harus terhubung ke port serial")
        link.setdefault("cable", "serial" if all(serial_ports) else "cross" if types[0] == types[1] else "straight")
        require(link["cable"] in ("cross", "straight", "serial"), "cable harus straight/cross/serial")
        require((link["cable"] == "serial") == all(serial_ports), "Jenis kabel tidak cocok dengan port")
        if link["cable"] == "serial":
            link.setdefault("dce", "from")
            link.setdefault("clock_rate", 64000)
            require(link["dce"] in ("from", "to"), "dce harus from/to")
            require(type(link["clock_rate"]) is int and link["clock_rate"] in (64000, 128000, 2000000), "clock_rate didukung: 64000, 128000, 2000000")
        else:
            require("dce" not in link and "clock_rate" not in link, "Clock/DCE hanya untuk serial")
        links.append(link)
    s["links"] = links
    # Closed-lab eBGP: peers must really be cabled, addressed and reciprocal.
    for name, d in devices.items():
        b = d["config"].get("bgp")
        if b is None:
            continue
        for neighbor in b["neighbors"]:
            matches = []
            for link in links:
                for side, other in (("from", "to"), ("to", "from")):
                    local, lp = link[side].split(":")
                    remote, rp = link[other].split(":")
                    if local != name or lp not in d["interfaces"] or rp not in devices[remote]["interfaces"]:
                        continue
                    la, ra = address(d["interfaces"][lp]), address(devices[remote]["interfaces"][rp])
                    if str(ra.ip) == neighbor["ip"] and la.network == ra.network:
                        matches.append((devices[remote], str(la.ip)))
            require(len(matches) == 1, f"{name}: BGP neighbor harus terhubung langsung pada subnet yang sama")
            peer, local_ip = matches[0]
            pb = peer["config"].get("bgp", {})
            require(pb.get("asn") == neighbor["remote_as"] and {"ip": local_ip, "remote_as": b["asn"]} in pb.get("neighbors", []), f"{name}: ASN/neighbor BGP tidak timbal balik")
    return s

def validate_xml(data):
    require(b"<!ENTITY" not in data.upper() and b"<!DOCTYPE" not in data.upper(), "DTD/entity XML tidak didukung")
    root = ET.fromstring(data)
    require(root.tag == "PACKETTRACER5", "Bukan XML topologi .pkt")
    scenarios = root.findall("SCENARIOSET/SCENARIO")
    require(scenarios and all(s.findtext("NAME") for s in scenarios), "Skenario simulasi XML kosong; build ulang dengan generator terbaru")
    script = root.find("SCRIPT_MODULE")
    if script is not None:
        require(script.find("PT_APP_META") is not None and script.find("SCRIPTS") is not None,
                "Metadata SCRIPT_MODULE XML tidak lengkap; build ulang dengan generator terbaru")
    devs = root.findall("NETWORK/DEVICES/DEVICE")
    ids, names, used_ips = {}, set(), {}
    device_refs, memory_ids = {}, set()
    for d in devs:
        sid, name = d.findtext("ENGINE/SAVE_REF_ID"), d.findtext("ENGINE/NAME")
        require(sid and sid not in ids and name and name not in names, "ID/nama perangkat XML ganda atau kosong")
        model = d.find("ENGINE/TYPE").get("model")
        require(model in MODELS.values(), f"Model XML belum didukung: {model}")
        bays = [slot for slot in d.iter("SLOT") if slot.findtext("TYPE") == "eInterfaceCard"]
        serial = bool(bays and bays[0].findtext("MODULE/MODEL") == "HWIC-2T")
        if serial:
            require(model == "2911" and len(bays[0].findall("MODULE/PORT")) == 2 and all(p.findtext("TYPE") == "eSmartSerial" for p in bays[0].findall("MODULE/PORT")), "Modul serial XML tidak valid")
        ids[sid] = ports(model, serial)
        names.add(name)
        for tag in ("MEM_ADDR", "DEV_ADDR"):
            value = d.findtext("WORKSPACE/LOGICAL/" + tag)
            require(value and value not in memory_ids, "Alamat memori perangkat XML ganda atau kosong")
            memory_ids.add(value)
        device_refs[sid] = d.findtext("WORKSPACE/LOGICAL/DEV_ADDR")
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
        is_serial = all((p.text or "").startswith("Serial") for p in ps)
        require(all((p.text or "").startswith("Serial") == is_serial for p in ps), "Port kabel XML campuran serial/Ethernet")
        require(link.findtext("TYPE") == ("eSerial" if is_serial else "eCopper"), "Jenis kabel XML tidak cocok")
        if is_serial:
            require((c.findtext("DCEDEV"), c.findtext("DCEPORT")) in ((c.findtext("FROM"), ps[0].text), (c.findtext("TO"), ps[1].text)), "Endpoint DCE XML tidak valid")
        for side, p in zip(("FROM", "TO"), ps):
            sid = c.findtext(side)
            require(sid in ids and p.text in ids[sid], "Link XML yatim atau port tidak valid")
            require(c.findtext(side + "_DEVICE_MEM_ADDR") == device_refs[sid], "Referensi memori kabel XML tidak cocok")
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
