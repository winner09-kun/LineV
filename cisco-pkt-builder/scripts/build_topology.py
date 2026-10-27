"""Build deterministic Packet Tracer labs from YAML/JSON, offline."""
import argparse
import ipaddress as ip
import json
import sys
import xml.etree.ElementTree as ET
from common import PACKAGE, load_spec, local_path, write_new
from validate import normalize, validate_xml, address, ports
from pkt_core import encode_bytes, decode_bytes
from lab_api import Lab
from bootstrap import prepare, compatible_seed
from check_topology import audit

def clean_seed(root):
    """Remove donor playback/extension state, retaining physical hierarchy/UUIDs."""
    # SCRIPT_MODULE is a structured application loader record, not a disposable
    # log. Clearing it causes PT 9.0.0 to hang/crash after drawing the topology.
    # Preserve its metadata, script containers and loading/saving fields.
    for tag in ("COMMAND_LOGS", "USER_PROFILE", "CODE_TESTING"):
        node = root.find(tag)
        if node is not None:
            node.clear()
    # A fresh lab still needs its default simulation scenario. Clearing the
    # container discarded that required state along with donor PDUs.
    scenarios = root.find("SCENARIOSET")
    if scenarios is None:
        scenarios = ET.SubElement(root, "SCENARIOSET")
    scenarios.clear()
    scenario = ET.SubElement(scenarios, "SCENARIO")
    ET.SubElement(scenario, "NAME", translate="true").text = "Scenario 0"
    ET.SubElement(scenario, "DESCRIPTION", translate="true")
    options = root.find("OPTIONS")
    if options is not None:
        for tag in ("RECENT_FILES", "SCRIPT_MODULE_MANAGER"):
            node = options.find(tag)
            if node is not None:
                node.clear()
        ipc = options.find("IPC_MANAGER")
        if ipc is not None:
            for path in list(ipc.findall("METAFILE_PATH")):
                ipc.remove(path)
    physical = root.find("PHYSICALWORKSPACE")
    if physical is not None:
        notes = physical.find("NOTES")
        if notes is not None:
            notes.clear()
        for environment in physical.iter("ENVIRONMENT"):
            # Keep the donor's initial environmental definitions, not its timeline.
            frames = environment.find("KEYFRAMES")
            if frames is not None:
                initial = next((f for f in frames if f.findtext("TIME") == "0"), None)
                if initial is not None:
                    for frame in list(frames):
                        if frame is not initial:
                            frames.remove(frame)
                    current = environment.find("ENVIRONMENT_OPTIONS")
                    initial_options = initial.find("ENVIRONMENT_OPTIONS")
                    if current is not None and initial_options is not None:
                        import copy
                        current.clear()
                        for option in initial_options:
                            current.append(copy.deepcopy(option))
                    set_text(environment, "TIME_IN_SECONDS", "0")

def device_addresses(index, model, serial=False):
    base = 1_000_000 + index * 1000
    return base, base + 1, {name: base + 10 + i for i, name in enumerate(sorted(ports(model, serial)))}

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
    if "bgp" in config:
        b = config["bgp"]
        lines += [f"router bgp {b['asn']}", " no auto-summary"]
        for network in sorted(set(b["networks"])):
            n = ip.IPv4Network(network)
            lines += [f" network {n.network_address} mask {n.netmask}"]
        for neighbor in sorted(b["neighbors"], key=lambda n: ip.IPv4Address(n["ip"])):
            lines += [f" neighbor {neighbor['ip']} remote-as {neighbor['remote_as']}"]
        lines += [" exit"]
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
    serial = any("module" in d for d in s["devices"])
    template_dir = prepare(serial=serial) if template_dir is None else template_dir
    models = {d["model"]: clean_model((template_dir / (d["model"] + ".xml")).read_bytes()) for d in s["devices"]}
    modules = {}
    if serial:
        module = ET.fromstring((template_dir / "HWIC-2T.xml").read_bytes())
        for port in module.iter("PORT"):
            for tag in ("IP", "SUBNET", "PORT_GATEWAY", "PORT_DNS", "DESCRIPTION", "IPV6_LINK_LOCAL", "IPV6_DEFAULT_LINK_LOCAL", "IPV6_ADDRESSES"):
                node = port.find(tag)
                if node is not None:
                    node.clear()
            for tag, value in (("CLOCKRATE", "0"), ("CLOCKRATEFLAG", "false"), ("POWER", "false"), ("PORT_DHCP_ENABLE", "false")):
                set_text(port, tag, value)
        modules["HWIC-2T"] = ET.tostring(module)
    lab = Lab(str(template_dir / "network_seed.xml"), models, modules)
    if not compatible_seed(lab.base):
        raise ValueError("Seed memakai referensi legacy/tidak lengkap. Regenerasi cache melalui bootstrap; jangan mengubah tag VERSION.")
    lab.prune_seed_devices()
    clean_seed(lab.base)
    ids, configs, addresses = {}, {}, {}
    for index, d in enumerate(s["devices"]):
        host = d["type"] in ("pc", "server")
        cli = None if host else ios_config(d, s)
        nic = None
        if "ip" in d:
            a = address(d["ip"])
            nic = (str(a.ip), str(a.netmask), d.get("gateway", ""))
        ids[d["id"]] = lab.add_device(d["model"], d["id"], *d["position"], ios_config=cli, pc_ip=nic)
        if "module" in d:
            lab.install_module(ids[d["id"]], d["module"], slot=0)
        el = lab._els[ids[d["id"]]]
        eng = el.find("ENGINE")
        logical = el.find("WORKSPACE/LOGICAL")
        mem, dev, port_addresses = device_addresses(index, d["model"], "module" in d)
        set_text(logical, "MEM_ADDR", str(mem))
        set_text(logical, "DEV_ADDR", str(dev))
        addresses[d["id"]] = (dev, port_addresses)
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
        if link["cable"] == "serial":
            dce, dport = (ad, ap) if link["dce"] == "from" else (bd, bp)
            lab.link(ids[ad], ap, ids[bd], bp, kind="serial", dce=ids[dce], dce_port=dport, clock=link["clock_rate"])
        else:
            lab.link(ids[ad], ap, ids[bd], bp)
        cable = lab.net.find("LINKS")[-1].find("CABLE")
        for side, name, port in (("FROM", ad, ap), ("TO", bd, bp)):
            dev, port_addresses = addresses[name]
            set_text(cable, side + "_DEVICE_MEM_ADDR", str(dev))
            set_text(cable, side + "_PORT_MEM_ADDR", str(port_addresses[port]))
        if link["cable"] == "cross":
            cable.find("TYPE").text = "eCrossOver"
    # link(serial) appends DCE clock configuration; persist the final CLI everywhere.
    for name in configs:
        eng = lab._els[ids[name]].find("ENGINE")
        lines = [line.text or "" for line in eng.findall("RUNNINGCONFIG/LINE")]
        configs[name] = "\n".join(lines) + "\n"
        startup = eng.find("STARTUPCONFIG")
        startup.clear()
        for line in lines:
            ET.SubElement(startup, "LINE").text = line
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
    bgp = [d for d in s["devices"] if "bgp" in d["config"]]
    if bgp:
        lines += ["", "## BGP", "", "| Router | AS | Network | Neighbor (remote AS) |", "|---|---|---|---|"]
        for d in bgp:
            b = d["config"]["bgp"]
            peers = ", ".join(f"{n['ip']} ({n['remote_as']})" for n in b["neighbors"])
            lines += [f"| {d['id']} | {b['asn']} | {', '.join(b['networks'])} | {peers} |"]
    for link in s["links"]:
        if link["cable"] == "serial":
            lines += ["", f"Serial DCE: {link[link['dce']]} — clock rate {link['clock_rate']}."]
    lines += ["", "Validasi struktur dan round-trip codec lulus. Audit CLI offline otomatis ada di check-report.json; periksa warnings dan status partial. Pembukaan di Packet Tracer dan penerapan CLI perlu diverifikasi di aplikasi; laporan ini bukan hasil ping.", ""]
    return "\n".join(lines)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("spec", nargs="?")
    p.add_argument("--preset", choices=["lan", "vlan", "ospf", "bgp"], help="Contoh bawaan tanpa menulis ulang YAML")
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
        templates = prepare(a.workspace, a.pt_install, serial=any("module" in d for d in spec["devices"]))
        s, xml, configs = build(spec, templates)
        pkt = encode_bytes(xml, "pkt")
        if decode_bytes(pkt, "pkt").xml != xml:
            raise ValueError("Round-trip codec gagal")
        audit_report = audit(s, xml, configs)
        if audit_report["errors"]:
            raise ValueError("Audit CLI gagal: " + "; ".join(audit_report["errors"]))
        out.mkdir(parents=True)
        write_new(out / (s["name"] + ".xml"), xml)
        write_new(out / (s["name"] + ".pkt"), pkt)
        write_new(out / "topology.json", json.dumps(s, indent=2).encode())
        write_new(out / "summary.md", summary(s).encode("utf-8"))
        import hashlib
        audit_report["pkt_sha256"] = hashlib.sha256(pkt).hexdigest()
        write_new(out / "check-report.json", json.dumps(audit_report, ensure_ascii=False, indent=2).encode("utf-8"))
        for name, config in configs.items():
            write_new(out / "configs" / (name + ".txt"), config.encode())
        pkt_path = out / (s["name"] + ".pkt")
        if a.json_report:
            print(json.dumps({"status": "ok", "devices": len(s["devices"]), "links": len(s["links"]),
                              "pkt": str(pkt_path), "summary": str(out / "summary.md"),
                              "checks": "spec+xml+roundtrip+offline_cli", "offline_audit": audit_report["status"], "pt_gui": "not_tested"}, separators=(",", ":")))
        else:
            print(pkt_path)
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as exc:
        p.exit(2, f"Build gagal: {exc}\n")

if __name__ == "__main__":
    main()
