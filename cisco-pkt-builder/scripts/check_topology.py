"""Read-only offline audit of generated CLI and topology; never runs Packet Tracer."""
import argparse
import hashlib
import ipaddress as ip
import itertools
import json
import re
import sys
import xml.etree.ElementTree as ET
from common import load_spec, local_path
from validate import normalize, validate_xml
from pkt_core import decode_bytes
from pkt_core.errors import PacketTracerError


def parse_cli(lines):
    result = {"interfaces": {}, "bgp": {}, "hostname": None}
    section = None
    for raw in lines:
        line = raw.strip()
        if line.startswith("hostname "):
            result["hostname"] = line.split(maxsplit=1)[1]
        elif line.startswith("interface "):
            section = result["interfaces"].setdefault(line.split(maxsplit=1)[1], {})
        elif line.startswith("router bgp "):
            asn = int(line.split()[-1])
            section = result["bgp"].setdefault(asn, {"neighbors": {}, "networks": []})
        elif line in ("exit", "end") or line.startswith(("router ", "vlan ", "ip dhcp pool ")):
            section = None
        elif section is not None:
            match = re.fullmatch(r"ip address (\S+) (\S+)", line)
            if match:
                section["ip"] = str(ip.IPv4Interface(f"{match[1]}/{match[2]}"))
            elif line in ("shutdown", "no shutdown"):
                section["enabled"] = line == "no shutdown"
            elif line.startswith("clock rate "):
                section["clock_rate"] = int(line.split()[-1])
            elif "neighbors" in section:
                match = re.fullmatch(r"neighbor (\S+) remote-as (\d+)", line)
                if match:
                    section["neighbors"][match[1]] = int(match[2])
                match = re.fullmatch(r"network (\S+) mask (\S+)", line)
                if match:
                    section["networks"].append(str(ip.IPv4Network(f"{match[1]}/{match[2]}")))
    return result


def reachable(graph, start, end):
    seen, queue = {start}, [start]
    while queue:
        node = queue.pop(0)
        if node == end:
            return True
        for nxt in graph.get(node, set()) - seen:
            seen.add(nxt)
            queue.append(nxt)
    return False


def predict_paths(spec):
    """Limited static model: flat L2 + reciprocal directly connected eBGP.

    No packet forwarding, IOS execution, convergence or measured ping is implied.
    Unsupported routing/VLAN semantics produce unknown, never a pass.
    """
    ds = {d["id"]: d for d in spec["devices"]}
    hosts = [d for d in ds.values() if d["type"] in ("pc", "server") and "ip" in d]
    unsupported = any(d["vlans"] or d["ports"] or set(d["config"]) - {"bgp"} for d in ds.values())
    asns = [d["config"]["bgp"]["asn"] for d in ds.values() if "bgp" in d["config"]]
    unsupported = unsupported or len(asns) != len(set(asns))
    l2, bgp = {}, {}
    for link in spec["links"]:
        a, b = (link[k].split(":")[0] for k in ("from", "to"))
        l2.setdefault(a, set()).add(b)
        l2.setdefault(b, set()).add(a)
        if all("bgp" in ds[n]["config"] for n in (a, b)):
            # normalize() already checked that every configured peer is reciprocal.
            ap, bp = (link[k].split(":")[1] for k in ("from", "to"))
            ai, bi = ds[a]["interfaces"].get(ap), ds[b]["interfaces"].get(bp)
            if ai and bi and any(n["ip"] == str(ip.ip_interface(bi).ip) for n in ds[a]["config"]["bgp"]["neighbors"]):
                bgp.setdefault(a, set()).add(b)
                bgp.setdefault(b, set()).add(a)

    def access(host, target):
        # Routers and other hosts cannot act as transparent L2 transit nodes.
        allowed = {n for n, d in ds.items() if d["type"] == "switch"} | {host, target}
        graph = {n: neighbors & allowed for n, neighbors in l2.items() if n in allowed}
        return reachable(graph, host, target)

    def gateway(host):
        for d in ds.values():
            for value in d["interfaces"].values():
                if str(ip.ip_interface(value).ip) == host.get("gateway") and access(host["id"], d["id"]):
                    return d
        return None

    rows = []
    for a, b in itertools.combinations(hosts, 2):
        status, reason = "unknown", "VLAN/OSPF/static/DHCP atau AS berulang belum dimodelkan oleh pemeriksa jalur"
        if not unsupported:
            an, bn = ip.ip_interface(a["ip"]).network, ip.ip_interface(b["ip"]).network
            if an == bn:
                ok = access(a["id"], b["id"])
            else:
                ag, bg = gateway(a), gateway(b)
                ok = bool(ag and bg)
                if ok and ag["id"] != bg["id"]:
                    ok = (str(an) in ag["config"].get("bgp", {}).get("networks", [])
                          and str(bn) in bg["config"].get("bgp", {}).get("networks", [])
                          and reachable(bgp, ag["id"], bg["id"]))
            status = "predicted_reachable" if ok else "predicted_unreachable"
            reason = "Prediksi dua arah dari kabel, gateway dan advertisement eBGP; bukan ping"
        rows.append({"from": a["id"], "to": b["id"], "status": status, "reason": reason})
    return rows


def audit(spec, xml, configs=None):
    s, root = normalize(spec), validate_xml(xml)
    errors, warnings = [], []
    def check(condition, message):
        if not condition:
            errors.append(message)
    actual = {d.findtext("ENGINE/NAME"): d for d in root.findall("NETWORK/DEVICES/DEVICE")}
    check(set(actual) == {d["id"] for d in s["devices"]}, "Daftar perangkat file berbeda dari spec")
    refs = {d.findtext("ENGINE/SAVE_REF_ID"): name for name, d in actual.items()}
    actual_links = set()
    cable_by_ends = {}
    for link in root.findall("NETWORK/LINKS/LINK"):
        c = link.find("CABLE")
        ends = [f"{refs[c.findtext(side)]}:{p.text}" for side, p in zip(("FROM", "TO"), c.findall("PORT"))]
        actual_links.add(frozenset(ends))
        cable_by_ends[frozenset(ends)] = c
    check(actual_links == {frozenset((l["from"], l["to"])) for l in s["links"]}, "Kabel aktual berbeda dari spec")
    for link in s["links"]:
        c = cable_by_ends.get(frozenset((link["from"], link["to"])))
        if c is None:
            continue
        if link["cable"] == "serial":
            check(f"{refs.get(c.findtext('DCEDEV'))}:{c.findtext('DCEPORT')}" == link[link["dce"]], "Sisi DCE aktual berbeda dari spec")
            for side in ("from", "to"):
                name, port = link[side].split(":")
                dev = actual.get(name)
                if dev is None:
                    continue
                bays = [sl for sl in dev.iter("SLOT") if sl.findtext("TYPE") == "eInterfaceCard"]
                ps = bays[0].findall("MODULE/PORT") if bays else []
                index = int(port.split("/")[-1])
                check(index < len(ps), f"{name}:{port}: hardware serial hilang")
                if index < len(ps):
                    expected_clock = link["clock_rate"] if side == link["dce"] else 0
                    check(ps[index].findtext("POWER") == "true" and ps[index].findtext("CLOCKRATE") == str(expected_clock), f"{name}:{port}: power/clock hardware serial berbeda")
        else:
            check(c.findtext("TYPE") == ("eCrossOver" if link["cable"] == "cross" else "eStraightThrough"), "Tipe kabel copper berbeda dari spec")
    for d in s["devices"]:
        name = d["id"]
        if name not in actual:
            continue
        dev = actual[name]
        check(dev.find("ENGINE/TYPE").get("model") == d["model"], f"{name}: model berbeda")
        check(dev.findtext("ENGINE/POWER") == "true", f"{name}: perangkat tidak menyala")
        if d["type"] in ("pc", "server"):
            if "ip" in d:
                addr = ip.ip_interface(d["ip"])
                check(any(p.findtext("IP") == str(addr.ip) and p.findtext("SUBNET") == str(addr.netmask) for p in dev.iter("PORT")), f"{name}: IP/mask host berbeda")
                check((dev.findtext("ENGINE/GATEWAY") or "") == d.get("gateway", ""), f"{name}: gateway host berbeda")
            continue
        running = [n.text or "" for n in dev.findall("ENGINE/RUNNINGCONFIG/LINE")]
        startup = [n.text or "" for n in dev.findall("ENGINE/STARTUPCONFIG/LINE")]
        canonical = lambda lines: [x.strip() for x in lines if x.strip() and x.strip() != "!"]
        check(canonical(running) == canonical(startup), f"{name}: running/startup CLI berbeda")
        if configs is not None:
            check(name in configs and canonical(configs.get(name, "").splitlines()) == canonical(running), f"{name}: file fallback CLI berbeda/hilang")
        parsed = parse_cli(running)
        check({p: v["ip"] for p, v in parsed["interfaces"].items() if "ip" in v} ==
              {p: str(ip.ip_interface(v)) for p, v in d["interfaces"].items()}, f"{name}: himpunan interface IP CLI berbeda dari spec")
        supported_line = r"(?:!|version \S+|hostname \S+|no ip domain-lookup|interface \S+|ip address \S+ \S+|no shutdown|shutdown|exit|end|router bgp \d+|no auto-summary|network \S+ mask \S+|neighbor \S+ remote-as \d+|clock rate \d+)"
        unknown = [line.strip() for line in running if line.strip() and not re.fullmatch(supported_line, line.strip())]
        if unknown:
            warnings.append(f"{name}: {len(unknown)} baris CLI di luar cakupan parser; prediksi jalur tidak disimpulkan")
        check(parsed["hostname"] == name, f"{name}: hostname CLI berbeda")
        for port, value in d["interfaces"].items():
            got = parsed["interfaces"].get(port, {})
            check(got.get("ip") == str(ip.ip_interface(value)), f"{name}:{port}: IP CLI berbeda/hilang")
            check(got.get("enabled") is True, f"{name}:{port}: no shutdown hilang")
        expected = d["config"].get("bgp")
        if expected:
            got = parsed["bgp"].get(expected["asn"], {})
            check(set(parsed["bgp"]) == {expected["asn"]}, f"{name}: ASN BGP berbeda")
            check(got.get("neighbors") == {n["ip"]: n["remote_as"] for n in expected["neighbors"]}, f"{name}: neighbor BGP berbeda")
            check(set(got.get("networks", [])) == set(expected["networks"]), f"{name}: advertisement BGP berbeda")
        else:
            check(not parsed["bgp"], f"{name}: BGP tidak diminta spec")
        if d["vlans"] or d["ports"] or set(d["config"]) - {"bgp"}:
            warnings.append(f"{name}: semantik VLAN/OSPF/static/DHCP belum diaudit; hanya konsistensi salinan CLI")
        for link in s["links"]:
            if link["cable"] == "serial":
                endpoint = link[link["dce"]]
                if endpoint.split(":")[0] == name:
                    port = endpoint.split(":")[1]
                    check(parsed["interfaces"].get(port, {}).get("clock_rate") == link["clock_rate"], f"{name}:{port}: clock DCE berbeda")
    paths = predict_paths(s) if not errors else []
    if any(row["status"] == "unknown" for row in paths) and not warnings:
        warnings.append("Prediksi jalur di luar cakupan model statis")
    if warnings:
        for row in paths:
            row["status"] = "unknown"
            row["reason"] = "Ada bagian CLI di luar cakupan audit; tidak menyimpulkan konektivitas"
    for row in paths:
        if row["status"] == "predicted_unreachable":
            warnings.append(f"{row['from']} ↔ {row['to']}: tidak ada jalur dalam model statis")
    return {"status": "failed" if errors else "partial" if warnings else "passed_static",
            "scope": "offline_configuration_only", "runtime": {"gui": "not_tested", "bgp_established": "not_tested", "ping": "not_tested"},
            "errors": errors, "warnings": warnings, "paths": paths,
            "limits": "Parser CLI terbatas pada hostname/interface/IPv4/shutdown/BGP/clock. Prediksi jalur hanya flat LAN/eBGP; tidak menjalankan IOS atau Packet Tracer."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", help="Folder output generator berisi topology.json, .pkt dan configs/")
    p.add_argument("--workspace", default=".")
    a = p.parse_args()
    try:
        folder = local_path(a.folder, a.workspace)
        spec = normalize(load_spec(local_path(folder / "topology.json", a.workspace, exists=True)))
        pkt = local_path(folder / (spec["name"] + ".pkt"), a.workspace, exists=True).read_bytes()
        configs = {}
        for d in spec["devices"]:
            if d["type"] in ("router", "switch"):
                path = local_path(folder / "configs" / (d["id"] + ".txt"), a.workspace)
                if path.is_file():
                    configs[d["id"]] = path.read_text(encoding="utf-8")
        report = audit(spec, decode_bytes(pkt, "pkt").xml, configs)
        report["pkt_sha256"] = hashlib.sha256(pkt).hexdigest()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if report["errors"] else 0
    except (ValueError, KeyError, TypeError, OSError, ET.ParseError, PacketTracerError) as exc:
        print(json.dumps({"status": "failed", "errors": [str(exc)], "runtime": "not_tested"}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
