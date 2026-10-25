"""Build deterministic Packet Tracer labs from YAML/JSON, offline."""
import argparse
import ipaddress as ip
import json
import sys
import xml.etree.ElementTree as ET
from common import PACKAGE, load_spec, local_path, write_new
from validate import normalize, validate_xml, address
from pkt_core import encode_bytes, decode_bytes
from lab_api import Lab
from bootstrap import prepare

def set_text(parent, tag, value):
    node = parent.find(tag)
    if node is None:
        node = ET.SubElement(parent, tag)
    node.text = value

def ios_config(d, spec):
    lines = ["version 15.1", f"hostname {d['id']}", "no ip domain-lookup"]
    for n, name in sorted(d["vlans"].items()):
        lines += [f"vlan {n}", f" name {name}", " exit"]
    for p, a in sorted(d["interfaces"].items()):
        a = address(a)
        lines += [f"interface {p}", f" ip address {a.ip} {a.netmask}", " no shutdown", " exit"]
    for p, mode in sorted(d["ports"].items()):
        lines += [f"interface {p}", f" switchport mode {mode['mode']}"]
        if mode["mode"] == "access":
            lines += [f" switchport access vlan {mode['vlan']}"]
        else:
            lines += [" switchport trunk allowed vlan " + ",".join(map(str, mode["allowed_vlans"])), f" switchport trunk native vlan {mode['native_vlan']}"]
        lines += [" no shutdown", " exit"]
    config = d["config"]
    for route in config.get("static_routes", []):
        n = ip.IPv4Network(route["network"])
        lines += [f"ip route {n.network_address} {n.netmask} {route['next_hop']}"]
    if "ospf" in config:
        o = config["ospf"]
        lines += [f"router ospf {o.get('process', 1)}"]
        for n in sorted(o["networks"]):
            n = ip.IPv4Network(n)
            lines += [f" network {n.network_address} {n.hostmask} area {o.get('area', 0)}"]
        lines += [" exit"]
    for pool in config.get("dhcp", []):
        n = ip.IPv4Network(pool["network"])
        excluded = set(pool.get("excluded", [])) | {pool["gateway"]}
        for dev in spec["devices"]:
            for a in list(dev["interfaces"].values()) + ([dev["ip"]] if "ip" in dev else []):
                if address(a).ip in n:
                    excluded.add(str(address(a).ip))
        lines += [f"ip dhcp excluded-address {a}" for a in sorted(excluded, key=ip.IPv4Address)]
        lines += [f"ip dhcp pool {pool['name']}", f" network {n.network_address} {n.netmask}", f" default-router {pool['gateway']}"]
        if pool.get("dns"):
            lines += [f" dns-server {pool['dns']}"]
        lines += [" exit"]
    return lines + ["end"]

def clean_model(data):
    """Remove donor state while preserving required hardware/workspace structure."""
    root = ET.fromstring(data)
    eng = root.find("ENGINE")
    for tag in ("RUNNINGCONFIG", "STARTUPCONFIG", "CURRENT_COMMAND_SET", "SYS_CONTACT", "SYS_LOCATION", "DESCRIPTION", "GATEWAY", "GATEWAYV6"):
        for e in eng.findall(tag):
            e.clear()
    for p in root.iter("PORT"):
        for tag in ("IP", "SUBNET", "PORT_GATEWAY", "PORT_DNS", "IPV6_LINK_LOCAL", "IPV6_DEFAULT_LINK_LOCAL"):
            set_text(p, tag, "")
        set_text(p, "PORT_DHCP_ENABLE", "false")
    # Server service payloads are outside MVP; do not inherit donor records/users.
    for tag in ("HTTP_SERVER", "HTTPS_SERVER", "DNS_SERVER", "DHCP_SERVERS", "DHCPV6_SERVER_LIST", "TFTP_SERVER", "FTP_SERVER", "NTP_SERVER", "SYSLOG_SERVER", "ACS_SERVER", "EMAIL_SERVER"):
        for service in eng.findall(tag):
            for e in service.iter():
                if e.tag in ("ENABLED", "HTTPSENABLED"):
                    e.text = "0"
                if e.tag in ("POOLS", "NAMESERVER-DATABASE", "USERS", "CLIENTS", "ACCOUNTS"):
                    e.clear()
    return ET.tostring(root)

def build(spec, template_dir=None):
    s = normalize(spec)
    template_dir = prepare() if template_dir is None else template_dir
    models = {d["model"]: clean_model((template_dir / (d["model"] + ".xml")).read_bytes()) for d in s["devices"]}
    lab = Lab(str(template_dir / "network_seed.xml"), models)
    lab.prune_seed_devices()
    for tag in ("COMMAND_LOGS", "USER_PROFILE", "CODE_TESTING", "SCENARIOSET", "SCRIPT_MODULE"):
        node = lab.base.find(tag)
        if node is not None:
            node.clear()
    ids, configs = {}, {}
    for d in s["devices"]:
        host = d["type"] in ("pc", "server")
        cli = None if host else ios_config(d, s)
        nic = None
        if "ip" in d:
            a = address(d["ip"])
            nic = (str(a.ip), str(a.netmask), d.get("gateway", ""))
        ids[d["id"]] = lab.add_device(d["model"], d["id"], *d["position"], ios_config=cli, pc_ip=nic)
        el = lab._els[ids[d["id"]]]
        eng = el.find("ENGINE")
        set_text(eng, "SYS_NAME", d["id"])
        if host:
            set_text(eng, "GATEWAY", d.get("gateway", ""))
        else:
            configs[d["id"]] = "\n".join(cli) + "\n"
            # Keep initial config and persistent config aligned.
            startup = eng.find("STARTUPCONFIG")
            if startup is None:
                startup = ET.SubElement(eng, "STARTUPCONFIG")
            startup.clear()
            for line in cli:
                ET.SubElement(startup, "LINE").text = line
    for link in s["links"]:
        ad, ap = link["from"].split(":")
        bd, bp = link["to"].split(":")
        lab.link(ids[ad], ap, ids[bd], bp)
        if link["cable"] == "cross":
            lab.net.find("LINKS")[-1].find("CABLE/TYPE").text = "eCrossOver"
    xml = ET.tostring(lab.base, encoding="utf-8", xml_declaration=True)
    validate_xml(xml)
    return s, xml, configs

def summary(s):
    lines = [f"# {s['name']}", "", "| Device | Model | Posisi |", "|---|---|---|"]
    lines += [f"| {d['id']} | {d['model']} | {d['position']} |" for d in s["devices"]]
    lines += ["", "| Device | Interface | IPv4 | Gateway |", "|---|---|---|---|"]
    for d in s["devices"]:
        for p, a in d["interfaces"].items():
            lines += [f"| {d['id']} | {p} | {a} | — |"]
        if "ip" in d:
            lines += [f"| {d['id']} | FastEthernet0 | {d['ip']} | {d.get('gateway', '—')} |"]
    lines += ["", "| Dari | Ke | Kabel |", "|---|---|---|"]
    lines += [f"| {l['from']} | {l['to']} | {l['cable']} |" for l in s["links"]]
    lines += ["", "Validasi struktur dan round-trip codec lulus. Pembukaan di Packet Tracer dan penerapan CLI perlu diverifikasi di aplikasi; laporan ini bukan hasil ping.", ""]
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("spec", nargs="?")
    p.add_argument("--preset", choices=["lan", "vlan", "ospf"], help="Contoh bawaan tanpa menulis ulang YAML")
    p.add_argument("--json-report", action="store_true", help="Laporan JSON singkat")
    p.add_argument("--out", required=True, help="Direktori hasil baru")
    p.add_argument("--workspace", default=".")
    p.add_argument("--pt-install", help="Lokasi instalasi PT jika tidak ditemukan otomatis")
    a = p.parse_args()
    if bool(a.spec) == bool(a.preset):
        p.error("Pilih tepat satu: spec atau --preset")
    try:
        src = PACKAGE / "examples" / (a.preset + ".yaml") if a.preset else local_path(a.spec, a.workspace, exists=True)
        out = local_path(a.out, a.workspace)
        if out.exists():
            raise ValueError("Direktori output sudah ada; pilih direktori baru")
        spec = normalize(load_spec(src))
        templates = prepare(a.workspace, a.pt_install)
        s, xml, configs = build(spec, templates)
        pkt = encode_bytes(xml, "pkt")
        if decode_bytes(pkt, "pkt").xml != xml:
            raise ValueError("Round-trip codec gagal")
        out.mkdir(parents=True)
        write_new(out / (s["name"] + ".xml"), xml)
        write_new(out / (s["name"] + ".pkt"), pkt)
        write_new(out / "topology.json", json.dumps(s, indent=2).encode())
        write_new(out / "summary.md", summary(s).encode("utf-8"))
        for name, config in configs.items():
            write_new(out / "configs" / (name + ".txt"), config.encode())
        pkt_path = out / (s["name"] + ".pkt")
        if a.json_report:
            print(json.dumps({"status": "ok", "devices": len(s["devices"]), "links": len(s["links"]),
                              "pkt": str(pkt_path), "summary": str(out / "summary.md"),
                              "checks": "spec+xml+roundtrip", "pt_gui": "not_tested"}, separators=(",", ":")))
        else:
            print(pkt_path)
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
        p.exit(2, f"Build gagal: {exc}\n")

if __name__ == "__main__":
    main()
