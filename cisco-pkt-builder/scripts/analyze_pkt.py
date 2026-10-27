"""Read-only, bounded diagnosis of a standalone .pkt; no spec or simulator needed."""
import argparse
from collections import Counter, defaultdict
import hashlib
import ipaddress as ip
import json
import re
import sys
import xml.etree.ElementTree as ET
from common import local_path, write_new
from pkt_core import decode_bytes
from pkt_core.errors import PacketTracerError


def port_name(value):
    for short, full in (("Fa", "FastEthernet"), ("Gi", "GigabitEthernet"), ("Se", "Serial")):
        if re.fullmatch(short + r"\d[\d/]*", value):
            return full + value[len(short):]
    return value


def analyze_xml(xml):
    root = ET.fromstring(xml)
    if root.tag != "PACKETTRACER5" or root.find("NETWORK/DEVICES") is None:
        raise ValueError("Struktur .pkt tidak dikenali; analisis tidak dijalankan")
    findings, devices, addresses, neighbors = [], [], [], []
    by_ref, endpoints = defaultdict(list), Counter()
    limitations = {"Analisis statis, bukan eksekusi IOS atau hasil ping.",
                   "VLAN/VRF, ACL, NAT, DHCP, IPv6, OSPF, policy BGP, wireless dan jalur forwarding belum dianalisis.",
                   "Tidak ada spec tujuan: konfigurasi yang disengaja tidak selalu dapat dibedakan dari kesalahan."}

    def finding(code, severity, device, evidence, suggestion):
        findings.append(dict(code=code, severity=severity, device=device,
                             evidence=evidence, suggestion=suggestion))

    def address(value, mask, owner, port, source):
        if value in (None, "", "0.0.0.0"):
            return
        try:
            if not mask:
                raise ValueError("missing mask")
            addr = ip.IPv4Interface(f"{value}/{mask}")
        except ValueError:
            finding("invalid_ipv4", "error", owner["id"], f"{source}: {value}/{mask}", "Periksa IP dan subnet mask pada interface ini.")
            return
        row = dict(owner=owner, port=port_name(port), address=addr)
        addresses.append(row)
        owner["addresses"].append(row)
        if addr.network.prefixlen < 31 and addr.ip in (addr.network.network_address, addr.network.broadcast_address):
            finding("reserved_host_address", "error", owner["id"], f"{port}: {addr}", "Gunakan alamat host, bukan alamat network/broadcast.")

    for index, node in enumerate(root.findall("NETWORK/DEVICES/DEVICE"), 1):
        engine = node.find("ENGINE")
        if engine is None:
            finding("missing_engine", "error", f"device-{index}", "ENGINE tidak tersedia", "Periksa struktur file dengan Packet Tracer.")
            continue
        kind = engine.find("TYPE")
        model = kind.get("model", "unknown") if kind is not None else "unknown"
        name = engine.findtext("NAME") or f"device-{index}"
        dev = dict(id=f"{index}:{name}", name=name, model=model, addresses=[], interfaces={}, asn=None)
        devices.append(dev)
        ref = engine.findtext("SAVE_REF_ID")
        if ref:
            by_ref[ref].append(dev)
        else:
            limitations.add(f"{dev['id']}: SAVE_REF_ID tidak tersedia; kabel tidak dapat dipetakan.")
        if engine.findtext("POWER") == "false":
            finding("device_off", "warning", dev["id"], "ENGINE/POWER=false", "Nyalakan perangkat jika seharusnya aktif.")
        if model not in {"2911", "2960-24TT", "PC-PT", "Server-PT"}:
            limitations.add(f"{dev['id']}: model {model} belum diuji; hanya field yang dikenali diperiksa.")
        running = [n.text or "" for n in engine.findall("RUNNINGCONFIG/LINE")]
        startup = [n.text or "" for n in engine.findall("STARTUPCONFIG/LINE")]
        canonical = lambda lines: [s.strip() for s in lines if s.strip() and s.strip() != "!"]
        if running and startup and canonical(running) != canonical(startup):
            finding("unsaved_config", "warning", dev["id"], "Running-config berbeda dari startup-config", "Tinjau perbedaannya; simpan konfigurasi jika perubahan memang diinginkan.")
        if model in {"PC-PT", "Server-PT"}:
            for n, port in enumerate(node.iter("PORT"), 1):
                if port.findtext("PORT_DHCP_ENABLE") == "true":
                    limitations.add(f"{dev['id']}: DHCP aktif; lease dan gateway runtime belum diverifikasi.")
                    continue
                address(port.findtext("IP"), port.findtext("SUBNET"), dev, f"NIC{n}", f"PORT[{n}]")
                gateway = port.findtext("PORT_GATEWAY") or engine.findtext("GATEWAY")
                if gateway and gateway != "0.0.0.0":
                    try:
                        gw = ip.IPv4Address(gateway)
                        rows = [a for a in dev["addresses"] if a["port"] == f"NIC{n}"]
                        if rows and (gw not in rows[0]["address"].network or gw == rows[0]["address"].ip):
                            finding("invalid_gateway", "error", dev["id"], f"NIC{n}: gateway={gw}, IP={rows[0]['address']}", "Gateway harus alamat perangkat lain yang berada dalam subnet host.")
                    except ValueError:
                        finding("invalid_gateway", "error", dev["id"], f"Gateway={gateway}", "Perbaiki format alamat gateway IPv4.")
            continue
        if not running:
            limitations.add(f"{dev['id']}: running-config tidak tersedia; startup tidak diasumsikan aktif.")
        section, ignored = None, 0
        for lineno, raw in enumerate(running, 1):
            line = raw.strip()
            if line.startswith("interface "):
                section = port_name(line.split(maxsplit=1)[1])
                dev["interfaces"].setdefault(section, {})
                continue
            if line.startswith("router bgp "):
                section = "bgp"
                try:
                    dev["asn"] = int(line.split()[-1])
                except ValueError:
                    limitations.add(f"{dev['id']}: ASN BGP tidak dikenali.")
                continue
            if line in ("!", "exit", "end") or line.startswith(("router ", "line ", "vlan ", "ip dhcp pool ")):
                section = None
                continue
            match = re.fullmatch(r"ip address (\S+) (\S+)", line)
            if section in dev["interfaces"] and match:
                address(*match.groups(), dev, section, f"running-config baris {lineno}")
            elif section in dev["interfaces"] and line in ("shutdown", "no shutdown"):
                dev["interfaces"][section]["shutdown"] = line == "shutdown"
            elif section == "bgp" and re.fullmatch(r"neighbor \S+ remote-as \d+", line):
                parts = line.split()
                neighbors.append((dev, parts[1], int(parts[3]), lineno))
            elif line and not line.startswith(("hostname ", "version ")):
                ignored += 1
        if ignored:
            limitations.add(f"{dev['id']}: {ignored} baris CLI di luar parser diagnosis; bukan bukti konfigurasi salah.")

    for ref, owners in by_ref.items():
        if len(owners) > 1:
            finding("duplicate_reference", "error", None, f"SAVE_REF_ID={ref}, perangkat={[d['id'] for d in owners]}", "Referensi perangkat ambigu; periksa file di Packet Tracer.")
    links = root.findall("NETWORK/LINKS/LINK")
    for index, link in enumerate(links, 1):
        cable = link.find("CABLE")
        if cable is None:
            limitations.add(f"Link {index}: struktur kabel tidak dikenali.")
            continue
        ports = [p.text or "" for p in cable.findall("PORT")]
        refs = [cable.findtext(side) for side in ("FROM", "TO")]
        if len(ports) != 2 or any(len(by_ref.get(r, [])) != 1 for r in refs):
            finding("unresolved_link", "warning", None, f"Link {index}: endpoint tidak dapat dipetakan secara unik", "Periksa endpoint kabel; format ini mungkin belum didukung parser.")
            continue
        ends = [(by_ref[r][0], port_name(p)) for r, p in zip(refs, ports)]
        for dev, port in ends:
            endpoints[(dev["id"], port)] += 1
            if dev["interfaces"].get(port, {}).get("shutdown"):
                finding("connected_shutdown", "warning", dev["id"], f"Link {index}, {port}: shutdown", "Jika link ini harus aktif, tinjau lalu gunakan no shutdown pada interface.")
        pair = [[a for a in dev["addresses"] if a["port"] == port] for dev, port in ends]
        if all(len(rows) == 1 for rows in pair):
            a, b = (rows[0]["address"] for rows in pair)
            if a.ip not in b.network or b.ip not in a.network:
                finding("link_subnet_mismatch", "warning", None, f"Link {index}: {ends[0][0]['id']} {a} <-> {ends[1][0]['id']} {b}", "Jika ini link IPv4 langsung biasa, samakan subnet kedua ujung; desain khusus perlu tinjauan manual.")
    for (device, port), count in endpoints.items():
        if count > 1:
            finding("reused_port", "warning", device, f"{port}: {count} kabel", "Periksa penggunaan port; pemetaan tipe kabel khusus belum didukung.")
    for dev in devices:
        if not any(key[0] == dev["id"] for key in endpoints):
            finding("no_mapped_link", "warning", dev["id"], "Tidak ada kabel yang berhasil dipetakan", "Periksa apakah perangkat sengaja terisolasi atau memakai koneksi wireless/format lain.")
    ips = defaultdict(list)
    for row in addresses:
        ips[str(row["address"].ip)].append(row)
    for value, rows in ips.items():
        if len(rows) > 1:
            finding("possible_duplicate_ip", "warning", None, f"{value}: " + ", ".join(f"{r['owner']['id']}:{r['port']}" for r in rows), "Pastikan tidak berada dalam domain jaringan yang sama; IP berulang bisa disengaja pada VLAN/VRF terpisah.")
    for dev, peer, remote_as, line in neighbors:
        owners = {r["owner"]["id"]: r["owner"] for r in ips.get(peer, [])}
        if len(owners) == 1:
            other = next(iter(owners.values()))
            if other["asn"] is not None and other["asn"] != remote_as:
                finding("possible_bgp_as_mismatch", "warning", dev["id"], f"Baris {line}: neighbor {peer} remote-as {remote_as}; ASN tersimpan peer={other['asn']}", "Periksa ASN peer; local-as/VRF dan policy khusus belum dianalisis.")
        else:
            limitations.add(f"{dev['id']}: peer BGP {peer} tidak terpetakan unik; mungkin eksternal, loopback atau format belum didukung.")
    return dict(status="findings" if findings else "no_findings_in_scope", coverage="partial",
                inventory=dict(devices=[{k: d[k] for k in ("id", "name", "model")} for d in devices], links=len(links)),
                findings=findings, limitations=sorted(limitations),
                runtime=dict(gui="not_tested", routing="not_tested", ping="not_tested"))


def analyze_file(path):
    if path.suffix.lower() != ".pkt":
        raise ValueError("Analisis menerima file .pkt, bukan .pka atau XML")
    data = path.read_bytes()
    report = analyze_xml(decode_bytes(data, "pkt").xml)
    report["source"] = {"path": str(path), "sha256": hashlib.sha256(data).hexdigest()}
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--workspace", default=".")
    p.add_argument("--out", help="Optional new JSON report; never overwrites")
    a = p.parse_args()
    try:
        report = analyze_file(local_path(a.input, a.workspace, exists=True))
        text = json.dumps(report, ensure_ascii=True, indent=2)
        if a.out:
            write_new(local_path(a.out, a.workspace), text.encode("utf-8"))
        print(text)
        return 0
    except (ValueError, OSError, ET.ParseError, PacketTracerError) as exc:
        p.exit(2, f"Analisis gagal: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
