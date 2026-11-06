# Graph Report - LineV  (2026-11-05)

## Corpus Check
- 20 files · ~20,192 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 2 file(s) not represented in the graph (top: (none) 2)

## Summary
- 270 nodes · 614 edges · 12 communities
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 91 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c078ecc3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- check_topology.py
- BuilderTests
- verify_install.py
- re
- devices
- devices
- audit
- devices
- analyze_xml
- devices
- pkt.py
- interface

## God Nodes (most connected - your core abstractions)
1. `BuilderTests` - 37 edges
2. `build()` - 33 edges
3. `normalize()` - 31 edges
4. `load_spec()` - 27 edges
5. `validate_xml()` - 22 edges
6. `audit()` - 20 edges
7. `local_path()` - 19 edges
8. `prepare()` - 15 edges
9. `analyze_xml()` - 13 edges
10. `OfflineCheckTests` - 13 edges

## Surprising Connections (you probably didn't know these)
- `router_spec()` --calls--> `load_spec()`  [INFERRED]
  cisco-pkt-builder/tests/test_builder.py → cisco-pkt-builder/scripts/common.py
- `build()` --calls--> `prepare()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/bootstrap.py
- `main()` --calls--> `prepare()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/bootstrap.py
- `main()` --calls--> `audit()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/check_topology.py
- `main()` --calls--> `local_path()`  [EXTRACTED]
  cisco-pkt-builder/scripts/build_topology.py → cisco-pkt-builder/scripts/common.py

## Import Cycles
- None detected.

## Communities (12 total, 0 thin omitted)

### Community 0 - "check_topology.py"
Cohesion: 0.16
Nodes (10): main(), cached(), installation(), main(), prepare(), main(), local_path(), write_new() (+2 more)

### Community 1 - "BuilderTests"
Cohesion: 0.08
Nodes (16): compatible_seed(), build(), clean_model(), clean_seed(), device_addresses(), ios_config(), main(), set_text() (+8 more)

### Community 2 - "verify_install.py"
Cohesion: 0.16
Nodes (7): main(), release_files(), main(), run_checks(), check(), command(), InstallTests

### Community 3 - "re"
Cohesion: 0.28
Nodes (7): parse_cli(), keys(), port_name(), require(), split_subinterface(), token(), vlan()

### Community 4 - "devices"
Cohesion: 0.08
Nodes (25): asn, neighbors, networks, bgp, devices, config, gateway, id (+17 more)

### Community 5 - "devices"
Cohesion: 0.10
Nodes (20): devices, id, ip, ports, position, type, vlans, mode (+12 more)

### Community 6 - "audit"
Cohesion: 0.16
Nodes (6): audit(), predict_paths(), access(), gateway(), reachable(), OfflineCheckTests

### Community 7 - "devices"
Cohesion: 0.12
Nodes (16): ospf, devices, config, gateway, id, interfaces, ip, position (+8 more)

### Community 8 - "analyze_xml"
Cohesion: 0.25
Nodes (8): analyze_file(), analyze_xml(), address(), finding(), port_name(), AnalyzeTests, with_subinterface(), fixture()

### Community 9 - "devices"
Cohesion: 0.18
Nodes (10): devices, gateway, id, interfaces, ip, position, type, Gi0/0 (+2 more)

### Community 10 - "pkt.py"
Cohesion: 0.12
Nodes (5): command_args(), main(), next_output(), parser(), CommandTests

### Community 11 - "interface"
Cohesion: 0.29
Nodes (6): interface, default_prompt, display_name, short_description, policy, allow_implicit_invocation

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_spec()` connect `BuilderTests` to `check_topology.py`, `audit`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `build()` (e.g. with `.test_bgp_serial_config_and_hardware()` and `.test_cli_and_gateway()`) actually correct?**
  _`build()` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Should `BuilderTests` be split into smaller, more focused modules?**
  _Cohesion score 0.07796610169491526 - nodes in this community are weakly interconnected._
- **Why does `normalize()` connect `BuilderTests` to `check_topology.py`, `re`, `audit`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `normalize()` (e.g. with `.test_bgp_invalid_peer_and_network()` and `.test_duplicate_ip()`) actually correct?**
  _`normalize()` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Should `devices` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._
- **Why does `BuilderTests` connect `BuilderTests` to `check_topology.py`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._