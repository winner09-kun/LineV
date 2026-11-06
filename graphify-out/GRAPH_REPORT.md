# Graph Report - LineV  (2026-11-05)

## Corpus Check
- 20 files · ~21,156 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 276 nodes · 635 edges · 12 communities (10 shown, 2 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 102 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c078ecc3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- check_topology.py
- BuilderTests
- verify_install.py
- normalize
- devices
- devices
- audit
- devices
- analyze_xml
- devices
- CommandTests
- interface

## God Nodes (most connected - your core abstractions)
1. `BuilderTests` - 39 edges
2. `build()` - 36 edges
3. `normalize()` - 34 edges
4. `load_spec()` - 31 edges
5. `validate_xml()` - 23 edges
6. `audit()` - 21 edges
7. `local_path()` - 19 edges
8. `prepare()` - 15 edges
9. `OfflineCheckTests` - 14 edges
10. `run_checks()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `router_spec()` --calls--> `load_spec()`  [INFERRED]
  cisco-pkt-builder/tests/test_builder.py → cisco-pkt-builder/scripts/common.py
- `server_spec()` --calls--> `load_spec()`  [INFERRED]
  cisco-pkt-builder/tests/test_builder.py → cisco-pkt-builder/scripts/common.py
- `build()` --calls--> `prepare()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/bootstrap.py
- `build()` --calls--> `address()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/validate.py
- `build()` --calls--> `normalize()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/validate.py

## Import Cycles
- None detected.

## Communities (12 total, 2 thin omitted)

### Community 0 - "check_topology.py"
Cohesion: 0.11
Nodes (16): analyze_file(), main(), cached(), installation(), main(), prepare(), main(), local_path() (+8 more)

### Community 1 - "BuilderTests"
Cohesion: 0.07
Nodes (15): compatible_seed(), build(), clean_model(), clean_seed(), configure_services(), device_addresses(), main(), set_text() (+7 more)

### Community 2 - "verify_install.py"
Cohesion: 0.19
Nodes (5): main(), run_checks(), check(), command(), InstallTests

### Community 3 - "normalize"
Cohesion: 0.17
Nodes (15): ios_config(), parse_cli(), predict_paths(), access(), gateway(), reachable(), address(), keys() (+7 more)

### Community 4 - "devices"
Cohesion: 0.08
Nodes (25): asn, neighbors, networks, bgp, devices, config, gateway, id (+17 more)

### Community 5 - "devices"
Cohesion: 0.10
Nodes (20): devices, id, ip, ports, position, type, vlans, mode (+12 more)

### Community 7 - "devices"
Cohesion: 0.12
Nodes (16): ospf, devices, config, gateway, id, interfaces, ip, position (+8 more)

### Community 8 - "analyze_xml"
Cohesion: 0.27
Nodes (7): analyze_xml(), address(), finding(), port_name(), AnalyzeTests, with_subinterface(), fixture()

### Community 9 - "devices"
Cohesion: 0.18
Nodes (10): devices, gateway, id, interfaces, ip, position, type, Gi0/0 (+2 more)

### Community 11 - "interface"
Cohesion: 0.29
Nodes (6): interface, default_prompt, display_name, short_description, policy, allow_implicit_invocation

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_spec()` connect `BuilderTests` to `check_topology.py`, `normalize`, `audit`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `build()` (e.g. with `.test_bgp_serial_config_and_hardware()` and `.test_cli_and_gateway()`) actually correct?**
  _`build()` has 23 INFERRED edges - model-reasoned connections that need verification._
- **Should `check_topology.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11010558069381599 - nodes in this community are weakly interconnected._
- **Why does `normalize()` connect `normalize` to `check_topology.py`, `BuilderTests`, `audit`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `normalize()` (e.g. with `.test_bgp_invalid_peer_and_network()` and `.test_duplicate_ip()`) actually correct?**
  _`normalize()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Should `BuilderTests` be split into smaller, more focused modules?**
  _Cohesion score 0.07130333138515488 - nodes in this community are weakly interconnected._
- **Why does `BuilderTests` connect `BuilderTests` to `check_topology.py`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._