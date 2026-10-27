import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import load_spec
from build_topology import build
from check_topology import audit, predict_paths
from validate import normalize
from pkt_core import encode_bytes


class OfflineCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec, cls.xml, cls.configs = build(load_spec(ROOT / "examples/bgp.yaml"))

    def test_bgp_paths_are_predictions_not_runtime_proof(self):
        result = audit(self.spec, self.xml, self.configs)
        self.assertEqual(result["status"], "passed_static")
        self.assertEqual(len(result["paths"]), 21)
        self.assertTrue(all(p["status"] == "predicted_reachable" for p in result["paths"]))
        self.assertEqual(set(result["runtime"].values()), {"not_tested"})

    def test_wrong_bgp_and_shutdown_even_when_both_cli_copies_match(self):
        for old, new, reason in ((b"remote-as 200", b"remote-as 201", "neighbor BGP"), (b"no shutdown", b"shutdown", "no shutdown"), (b"clock rate 64000", b"clock rate 128000", "clock DCE")):
            with self.subTest(reason=reason):
                report = audit(self.spec, self.xml.replace(old, new))
                self.assertEqual(report["status"], "failed")
                self.assertTrue(any(reason in e for e in report["errors"]))
                self.assertEqual(report["paths"], [])

    def test_bad_host_gateway(self):
        root = ET.fromstring(self.xml)
        pc = next(d for d in root.findall("NETWORK/DEVICES/DEVICE") if d.findtext("ENGINE/NAME") == "PC6")
        pc.find("ENGINE/GATEWAY").text = "192.168.10.254"
        self.assertTrue(any("gateway host" in e for e in audit(self.spec, ET.tostring(root))["errors"]))

    def test_serial_hardware_clock_mismatch(self):
        root = ET.fromstring(self.xml)
        serial = next(p for p in root.iter("PORT") if p.findtext("TYPE") == "eSmartSerial")
        serial.find("CLOCKRATE").text = "123"
        self.assertTrue(any("hardware serial" in e for e in audit(self.spec, ET.tostring(root))["errors"]))

    def test_fallback_config_divergence(self):
        configs = dict(self.configs, R1="hostname Wrong\nend\n")
        self.assertEqual(audit(self.spec, self.xml, configs)["status"], "failed")

    def test_unsupported_cli_not_reported_reachable(self):
        root = ET.fromstring(self.xml)
        dev = root.find("NETWORK/DEVICES/DEVICE")
        for section in ("RUNNINGCONFIG", "STARTUPCONFIG"):
            ET.SubElement(dev.find("ENGINE/" + section), "LINE").text = "access-list 1 deny any"
        report = audit(self.spec, ET.tostring(root))
        self.assertEqual(report["status"], "partial")
        self.assertTrue(all(p["status"] == "unknown" for p in report["paths"]))

    def test_disconnected_host_not_predicted_reachable(self):
        s = normalize(load_spec(ROOT / "examples/lan.yaml"))
        s["links"] = s["links"][:-1]
        self.assertEqual(predict_paths(s)[0]["status"], "predicted_unreachable")

    def test_vlan_is_unknown(self):
        s, xml, configs = build(load_spec(ROOT / "examples/vlan.yaml"))
        report = audit(s, xml, configs)
        self.assertEqual(report["status"], "partial")
        self.assertTrue(all(p["status"] == "unknown" for p in report["paths"]))

    def test_repeated_as_does_not_assume_bgp_transit(self):
        spec = load_spec(ROOT / "examples/bgp.yaml")
        spec["devices"][2]["config"]["bgp"]["asn"] = 100
        spec["devices"][1]["config"]["bgp"]["neighbors"][1]["remote_as"] = 100
        s, xml, configs = build(spec)
        report = audit(s, xml, configs)
        self.assertEqual(report["status"], "partial")
        self.assertTrue(all(p["status"] == "unknown" for p in report["paths"]))

    def test_dispatch_reads_pkt_not_stale_xml_and_is_read_only(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            folder = Path(tmp)
            (folder / "topology.json").write_text(json.dumps(self.spec))
            (folder / "lab-bgp.pkt").write_bytes(encode_bytes(self.xml.replace(b"no shutdown", b"shutdown"), "pkt"))
            (folder / "lab-bgp.xml").write_bytes(self.xml)
            (folder / "configs").mkdir()
            for name, cli in self.configs.items():
                (folder / "configs" / (name + ".txt")).write_text(cli)
            before = {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()}
            result = subprocess.run([sys.executable, str(ROOT / "scripts/pkt.py"), "check", ".", "--workspace", tmp], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "failed")
            self.assertEqual(before, {str(p): p.read_bytes() for p in folder.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
