import copy
import json
import subprocess
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from common import load_spec, local_path, write_new
from validate import normalize, validate_xml
from build_topology import build
from pkt_core import encode_bytes, decode_bytes
from pkt_core.errors import PacketTracerError

class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec(ROOT / "examples/lan.yaml")
        (ROOT.parent / "qa").mkdir(exist_ok=True)

    def test_three_examples_roundtrip(self):
        for name, count in (("lan", 4), ("vlan", 6), ("ospf", 8)):
            with self.subTest(name=name):
                s, xml, _ = build(load_spec(ROOT / f"examples/{name}.yaml"))
                root = validate_xml(xml)
                self.assertEqual(len(root.findall("NETWORK/DEVICES/DEVICE")), count)
                self.assertEqual(len(root.findall("NETWORK/LINKS/LINK")), len(s["links"]))
                self.assertEqual(decode_bytes(encode_bytes(xml, "pkt"), "pkt").xml, xml)

    def test_deterministic(self):
        a, b = build(self.spec)[1], build(self.spec)[1]
        self.assertEqual(a, b)
        self.assertEqual(encode_bytes(a, "pkt"), encode_bytes(b, "pkt"))

    def test_duplicate_device_memory_rejected(self):
        root = ET.fromstring(build(self.spec)[1])
        devices = root.findall("NETWORK/DEVICES/DEVICE")
        devices[-1].find("WORKSPACE/LOGICAL/MEM_ADDR").text = devices[-2].findtext("WORKSPACE/LOGICAL/MEM_ADDR")
        with self.assertRaisesRegex(ValueError, "memori perangkat"):
            validate_xml(ET.tostring(root))

    def test_mismatched_cable_memory_rejected(self):
        root = ET.fromstring(build(self.spec)[1])
        root.find("NETWORK/LINKS/LINK/CABLE/FROM_DEVICE_MEM_ADDR").text = "1"
        with self.assertRaisesRegex(ValueError, "memori kabel"):
            validate_xml(ET.tostring(root))

    def test_seed_reference_schema_not_version(self):
        from bootstrap import compatible_seed
        root = ET.fromstring('<PACKETTRACER5><VERSION>7.1.0.0000</VERSION><NETWORK><DEVICES><DEVICE><ENGINE><SAVE_REF_ID>save-ref-id:1</SAVE_REF_ID></ENGINE></DEVICE></DEVICES><LINKS><LINK><CABLE><FROM>save-ref-id:1</FROM><TO>save-ref-id:1</TO></CABLE></LINK></LINKS></NETWORK></PACKETTRACER5>')
        self.assertTrue(compatible_seed(root))
        root.find("NETWORK/LINKS/LINK/CABLE/FROM").text = "0"
        self.assertFalse(compatible_seed(root))

    def test_clean_seed_preserves_physical_identity(self):
        from build_topology import clean_seed
        root = ET.fromstring('<PACKETTRACER5><PHYSICALWORKSPACE><UUID>keep</UUID><ENVIRONMENT><TIME_IN_SECONDS>50</TIME_IN_SECONDS><ENVIRONMENT_OPTIONS><VALUE>changed</VALUE></ENVIRONMENT_OPTIONS><KEYFRAMES><FRAME><TIME>0</TIME><ENVIRONMENT_OPTIONS><VALUE>initial</VALUE></ENVIRONMENT_OPTIONS></FRAME><FRAME><TIME>50</TIME></FRAME></KEYFRAMES></ENVIRONMENT></PHYSICALWORKSPACE></PACKETTRACER5>')
        clean_seed(root)
        self.assertEqual(root.findtext("PHYSICALWORKSPACE/UUID"), "keep")
        env = root.find("PHYSICALWORKSPACE/ENVIRONMENT")
        self.assertEqual(env.findtext("TIME_IN_SECONDS"), "0")
        self.assertEqual(len(env.find("KEYFRAMES")), 1)
        self.assertEqual(env.findtext("ENVIRONMENT_OPTIONS/VALUE"), "initial")

    def test_duplicate_ip(self):
        self.spec["devices"][3]["ip"] = self.spec["devices"][2]["ip"]
        with self.assertRaisesRegex(ValueError, "IP ganda"):
            normalize(self.spec)

    def test_duplicate_port_alias(self):
        self.spec["links"].append(["SW1:FastEthernet0/1", "PC2:Fa0"])
        with self.assertRaisesRegex(ValueError, "Port bentrok"):
            normalize(self.spec)

    def test_orphan(self):
        self.spec["links"][0][0] = "R9:Gi0/0"
        with self.assertRaisesRegex(ValueError, "Link yatim"):
            normalize(self.spec)

    def test_nonexistent_port(self):
        self.spec["links"][0][0] = "R1:Gi0/9"
        with self.assertRaisesRegex(ValueError, "Port tidak tersedia"):
            normalize(self.spec)

    def test_gateway(self):
        self.spec["devices"][2]["gateway"] = "10.0.0.1"
        with self.assertRaisesRegex(ValueError, "gateway"):
            normalize(self.spec)

    def test_unknown_feature(self):
        self.spec["devices"][0]["config"] = {"nat": {}}
        with self.assertRaisesRegex(ValueError, "tidak didukung"):
            normalize(self.spec)

    def test_cli_and_gateway(self):
        _, xml, configs = build(self.spec)
        self.assertIn(" ip address 192.168.10.1 255.255.255.0", configs["R1"])
        root = ET.fromstring(xml)
        pc = [d for d in root.findall("NETWORK/DEVICES/DEVICE") if d.findtext("ENGINE/NAME") == "PC1"][0]
        self.assertEqual(pc.findtext("ENGINE/GATEWAY"), "192.168.10.1")
        self.assertEqual(pc.findtext(".//PORT/IP"), "192.168.10.10")
        self.assertEqual(root.findall("COMMAND_LOGS/*"), [])

    def test_vlan_and_crossover(self):
        _, xml, configs = build(load_spec(ROOT / "examples/vlan.yaml"))
        self.assertIn(" switchport trunk allowed vlan 10,20", configs["SW1"])
        self.assertIn(b"eCrossOver", xml)

    def test_ospf_wildcards(self):
        _, _, configs = build(load_spec(ROOT / "examples/ospf.yaml"))
        self.assertIn(" network 10.0.12.0 0.0.0.3 area 0", configs["R1"])

    def test_static_and_dhcp(self):
        self.spec["devices"][0]["config"] = {
            "static_routes": [{"network": "0.0.0.0/0", "next_hop": "192.168.10.254"}],
            "dhcp": [{"name": "LAN", "network": "192.168.10.0/24", "gateway": "192.168.10.1"}]}
        _, _, configs = build(self.spec)
        self.assertIn("ip route 0.0.0.0 0.0.0.0 192.168.10.254", configs["R1"])
        self.assertIn("ip dhcp excluded-address 192.168.10.10", configs["R1"])
        self.assertIn("ip dhcp excluded-address 192.168.10.1\n", configs["R1"])

    def test_tamper(self):
        pkt = bytearray(encode_bytes(build(self.spec)[1], "pkt"))
        pkt[len(pkt)//2] ^= 1
        with self.assertRaises(PacketTracerError):
            decode_bytes(bytes(pkt), "pkt")

    def test_xml_duplicate_ip(self):
        xml = build(self.spec)[1].replace(b"192.168.10.11", b"192.168.10.10")
        with self.assertRaisesRegex(ValueError, "IP XML ganda"):
            validate_xml(xml)

    def test_paths_and_no_overwrite(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            with self.assertRaisesRegex(ValueError, "di luar"):
                local_path("../escape.pkt", tmp)
            f = local_path("ok.pkt", tmp)
            write_new(f, b"original")
            with self.assertRaises(FileExistsError):
                write_new(f, b"replaced")
            self.assertEqual(f.read_bytes(), b"original")

    def test_yaml_duplicate_key(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            p = Path(tmp) / "bad.yaml"
            p.write_text("name: one\nname: two\n")
            with self.assertRaisesRegex(ValueError, "Kunci YAML ganda"):
                load_spec(p)

    def test_preset_report_matches_spec(self):
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            from bootstrap import prepare
            shutil.copytree(prepare(), Path(tmp) / ".cisco-pkt-cache")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/build_topology.py"),
                "--preset", "lan", "--workspace", tmp, "--out", "lab", "--json-report"],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual((report["devices"], report["links"]), (4, 3))
            self.assertEqual(report["pt_gui"], "not_tested")
            self.assertEqual(Path(report["pkt"]).read_bytes(), encode_bytes(build(self.spec)[1], "pkt"))
            self.assertTrue(Path(report["summary"]).is_file())

    def test_preset_and_spec_conflict(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/build_topology.py"),
            "spec.yaml", "--preset", "lan", "--out", "unused"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Pilih tepat satu", result.stderr)

    def test_normalized_spec_rebuild(self):
        self.assertEqual(build(self.spec)[1], build(normalize(self.spec))[1])

    def test_bootstrap_cache_integrity(self):
        from bootstrap import prepare, cached
        with tempfile.TemporaryDirectory(dir=ROOT.parent / "qa") as tmp:
            target = Path(tmp) / ".cisco-pkt-cache"
            shutil.copytree(prepare(), target)
            self.assertTrue(cached(target))
            (target / "2911.xml").write_bytes(b"corrupt")
            self.assertFalse(cached(target))

if __name__ == "__main__":
    unittest.main()
