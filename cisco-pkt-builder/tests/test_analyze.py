from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_pkt import analyze_xml, analyze_file
from pkt_core import encode_bytes


def fixture():
    root = ET.Element("PACKETTRACER5")
    net = ET.SubElement(root, "NETWORK")
    ds = ET.SubElement(net, "DEVICES")
    for name, ref, addr, asn, peer_as in (("R1", "1", "10.0.0.1", 100, 200), ("R2", "2", "10.0.0.2", 200, 100)):
        dev = ET.SubElement(ds, "DEVICE")
        eng = ET.SubElement(dev, "ENGINE")
        ET.SubElement(eng, "TYPE", model="2911")
        for key, value in (("NAME", name), ("SAVE_REF_ID", ref), ("POWER", "true")):
            ET.SubElement(eng, key).text = value
        lines = [f"hostname {name}", "interface GigabitEthernet0/0", f"ip address {addr} 255.255.255.252", "no shutdown", "!", f"router bgp {asn}", f"neighbor 10.0.0.{2 if ref == '1' else 1} remote-as {peer_as}", "end"]
        for section in ("RUNNINGCONFIG", "STARTUPCONFIG"):
            parent = ET.SubElement(eng, section)
            for line in lines:
                ET.SubElement(parent, "LINE").text = line
    c = ET.SubElement(ET.SubElement(ET.SubElement(net, "LINKS"), "LINK"), "CABLE")
    for key, value in (("FROM", "1"), ("TO", "2"), ("PORT", "Gi0/0"), ("PORT", "Gi0/0")):
        ET.SubElement(c, key).text = value
    return ET.tostring(root)


class AnalyzeTests(unittest.TestCase):
    def codes(self, xml):
        return {f["code"] for f in analyze_xml(xml)["findings"]}

    def test_no_findings_does_not_claim_runtime(self):
        report = analyze_xml(fixture())
        self.assertEqual(report["status"], "no_findings_in_scope")
        self.assertEqual(report["coverage"], "partial")
        self.assertEqual(set(report["runtime"].values()), {"not_tested"})

    def test_shutdown_subnet_and_as_evidence(self):
        self.assertIn("connected_shutdown", self.codes(fixture().replace(b"no shutdown", b"shutdown")))
        self.assertIn("link_subnet_mismatch", self.codes(fixture().replace(b"ip address 10.0.0.2", b"ip address 10.1.0.2")))
        self.assertIn("possible_bgp_as_mismatch", self.codes(fixture().replace(b"remote-as 200", b"remote-as 300")))

    def test_duplicate_invalid_and_reserved_ips(self):
        self.assertIn("possible_duplicate_ip", self.codes(fixture().replace(b"ip address 10.0.0.2", b"ip address 10.0.0.1")))
        self.assertIn("invalid_ipv4", self.codes(fixture().replace(b"255.255.255.252", b"255.0.255.0")))
        self.assertIn("reserved_host_address", self.codes(fixture().replace(b"ip address 10.0.0.2", b"ip address 10.0.0.3")))

    def test_host_gateway_and_dhcp_limit(self):
        root = ET.fromstring(fixture())
        dev = root.find("NETWORK/DEVICES/DEVICE")
        dev.find("ENGINE/TYPE").set("model", "PC-PT")
        port = ET.SubElement(dev, "PORT")
        for k, v in (("IP", "192.168.1.2"), ("SUBNET", "255.255.255.0"), ("PORT_GATEWAY", "192.168.2.1")):
            ET.SubElement(port, k).text = v
        self.assertIn("invalid_gateway", self.codes(ET.tostring(root)))
        ET.SubElement(port, "PORT_DHCP_ENABLE").text = "true"
        report = analyze_xml(ET.tostring(root))
        self.assertNotIn("invalid_gateway", {f["code"] for f in report["findings"]})
        self.assertTrue(any("DHCP" in x for x in report["limitations"]))

    def test_unknown_schema_and_missing_engine(self):
        with self.assertRaises(ValueError):
            analyze_xml(b"<OTHER/>")
        self.assertIn("missing_engine", self.codes(b"<PACKETTRACER5><NETWORK><DEVICES><DEVICE/></DEVICES></NETWORK></PACKETTRACER5>"))

    def test_unknown_model_missing_cli_and_ambiguous_ref(self):
        root = ET.fromstring(fixture())
        first = root.find("NETWORK/DEVICES/DEVICE/ENGINE")
        first.find("TYPE").set("model", "unknown-model")
        first.remove(first.find("RUNNINGCONFIG"))
        first.find("SAVE_REF_ID").text = "2"
        report = analyze_xml(ET.tostring(root))
        self.assertIn("duplicate_reference", {f["code"] for f in report["findings"]})
        self.assertTrue(any("running-config tidak" in x for x in report["limitations"]))

    def test_standalone_cli_readonly_and_report_no_overwrite(self):
        (ROOT.parent / "qa").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            path = Path(tmp) / "lab 日本.pkt"
            data = encode_bytes(fixture(), "pkt")
            path.write_bytes(data)
            self.assertEqual(analyze_file(path)["source"]["sha256"], hashlib.sha256(data).hexdigest())
            cmd = [sys.executable, str(ROOT / "scripts/pkt.py"), "analisa", path.name, "--workspace", tmp, "--out", "report.json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["coverage"], "partial")
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)
            path.write_bytes(b"corrupt pkt")
            self.assertEqual(subprocess.run(cmd[:-2], capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
