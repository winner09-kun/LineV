# LineV

Skill untuk membuat lab Cisco Packet Tracer dari deskripsi jaringan melalui YAML atau preset LAN, VLAN, OSPF, dan eBGP dengan kabel serial (`/pkt bgp`).

## Instalasi singkat

1. Siapkan Python 3.10+ dan Cisco Packet Tracer dengan contoh bawaan pada komputer agent.
2. Unduh [ZIP rilis](cisco-pkt-builder.zip) melalui **Download raw file**, lalu ekstrak.
3. Salin folder `cisco-pkt-builder` ke `<proyek>/.agents/skills/cisco-pkt-builder/`.
4. Buka proyek di Codex dengan GPT atau Antigravity dengan Gemini dan mulai chat baru.
5. Kirim salah satu prompt berikut:

```text
Gunakan skill cisco-pkt-builder. /pkt mode codex-gpt
/pkt lan
```

```text
Gunakan skill cisco-pkt-builder. /pkt mode antigravity-gemini
/pkt lan
```

Mode memilih panduan kerja, bukan mengganti model aplikasi. Petunjuk instalasi global, aktivasi khusus host, tes terminal, dan troubleshooting tersedia di [README skill](cisco-pkt-builder/README.md#instalasi-agent). Profil Gemini/GPT masih memerlukan uji penggunaan langsung di aplikasi masing-masing.

- [Panduan penggunaan dan instalasi](cisco-pkt-builder/README.md)
- [Paket skill ZIP](cisco-pkt-builder.zip)
- [Metode hemat token AI](cisco-pkt-builder/TOKEN_EFFICIENCY.md)
- [Perintah chat /pkt](cisco-pkt-builder/COMMANDS.md)
- [Status penerimaan dan batas kompatibilitas](cisco-pkt-builder/ACCEPTANCE.md)

```sh
python cisco-pkt-builder/scripts/build_topology.py --preset lan --out hasil/lan --json-report
```

Python 3.10+ dan Packet Tracer dengan contoh bawaan. Pengguna cukup menjelaskan jaringan: struktur perangkat disiapkan otomatis dari instalasi lokal, tanpa menyediakan template sendiri. Kode berjalan offline; template/cache dan hasil biner tidak disertakan dalam repository. Pembukaan hasil di Packet Tracer belum terverifikasi. NAT dan edit generik `.pkt` belum didukung.

Paket memakai GPL-3.0-or-later. Lihat [lisensi](cisco-pkt-builder/LICENSE) dan [asal dependensi](cisco-pkt-builder/THIRD_PARTY.md).
