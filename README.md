# LineV

Skill untuk membuat lab Cisco Packet Tracer dari deskripsi jaringan melalui YAML atau preset LAN, VLAN, dan OSPF.

- [Panduan penggunaan dan instalasi](cisco-pkt-builder/README.md)
- [Paket skill ZIP](cisco-pkt-builder.zip)
- [Metode hemat token AI](cisco-pkt-builder/TOKEN_EFFICIENCY.md)
- [Status penerimaan dan batas kompatibilitas](cisco-pkt-builder/ACCEPTANCE.md)

```sh
python cisco-pkt-builder/scripts/build_topology.py --preset lan --out hasil/lan --json-report
```

Python 3.10+ dan Packet Tracer dengan contoh bawaan. Pengguna cukup menjelaskan jaringan: struktur perangkat disiapkan otomatis dari instalasi lokal, tanpa menyediakan template sendiri. Kode berjalan offline; template/cache dan hasil biner tidak disertakan dalam repository. Pembukaan hasil di Packet Tracer belum terverifikasi. NAT dan edit generik `.pkt` belum didukung.

Paket memakai GPL-3.0-or-later. Lihat [lisensi](cisco-pkt-builder/LICENSE) dan [asal dependensi](cisco-pkt-builder/THIRD_PARTY.md).
