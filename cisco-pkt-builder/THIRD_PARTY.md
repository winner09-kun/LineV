# Third party provenance

## Packet Tracer format library

Source: https://github.com/aacanadaa/packet-tracer-pkt-format

Commit: `ce61cd619ccc34e593557b8e0820f671fdeb571d`

License: GPL-3.0-or-later, copyright 2026 aacanadaa. Full license in `LICENSE`; original source headers retained. Included Python source is the corresponding source, not compiled binaries.

Included code: `src/pkt_core/` copied to `vendor/pkt_core/`; `tools/lab_api.py` copied to `vendor/lab_api.py`. No upstream XML seed, device templates or Packet Tracer binary examples are included in the public package.

Local changes: lab_api seed file now uses a context manager. The upstream Linux-only pt9 module is replaced by our `vendor/pt9.py` shim calling portable pkt_core. Bootstrap, runtime cleanup, validation, YAML translation, CLI generation and reports are in `scripts/`. Bootstrap reads only bundled samples from the user's installed Packet Tracer. Derived XML remains in a private, gitignored workspace cache. No user campus files are included. The GPL license covers code, not rights to redistribute Cisco materials extracted locally.

This package has not independently recreated the PRD's three manual donor labs. Do not treat upstream claims of GUI verification as local acceptance results. Cache manifests record donor paths and hashes locally, without publishing those files.

## PyYAML

Version 6.0.3, source https://github.com/yaml/pyyaml, MIT license in `vendor/pyyaml-6.0.3.dist-info/licenses/LICENSE`. Vendored Python parser used through SafeLoader. Native accelerator is unnecessary and excluded from the release archive to keep it portable.
