# Cisco Packet Tracer builder

Paket skill dari PRD versi 0.1 untuk mengubah deskripsi jaringan melalui agent menjadi YAML, XML, dan `.pkt`. Paket ini menghasilkan lab LAN, VLAN/trunk, routing statis, OSPF, dan DHCP router. **Status: kandidat MVP; penerimaan aplikasi belum terverifikasi.**

## Menjalankan

Untuk alur hemat token, gunakan `--preset lan|vlan|ospf --json-report` tanpa argumen spec. AI tidak perlu menulis ulang contoh atau membaca XML. Untuk kustomisasi, gunakan spec seperti biasa. Detail: [metode hemat token](TOKEN_EFFICIENCY.md).

Python 3.10 atau lebih baru dan instalasi Cisco Packet Tracer dengan folder contoh `saves/`. Pengguna cukup menjelaskan topologi ke agent; build pertama mencari instalasi PT dan menyiapkan struktur perangkat otomatis. Tidak perlu mencari atau memasukkan template secara manual. Codec dan parser YAML disertakan sehingga proses tidak memerlukan jaringan, compiler, atau pip. Parser memakai SafeLoader.

Struktur perangkat diekstrak dari contoh bawaan aplikasi ke `.cisco-pkt-cache/` di workspace, bukan diunduh atau disertakan dalam repository. Cache diverifikasi dengan SHA-256 sebelum dipakai kembali. Jika PT tidak ditemukan otomatis, agent dapat memakai `--pt-install "C:/Program Files/Cisco Packet Tracer 9.0.0"`. Instalasi tanpa contoh yang mencakup empat model MVP akan ditolak dengan pesan model yang kurang. Penyiapan pertama dibatasi 500 file/sekitar 120 detik (batas dicek antarfile); build berikutnya memakai cache. Windows diuji; deteksi `/opt/pt` dan path aplikasi macOS belum diuji.

Dari direktori yang memuat folder `cisco-pkt-builder`:

```sh
python cisco-pkt-builder/scripts/validate.py cisco-pkt-builder/examples/lan.yaml
python cisco-pkt-builder/scripts/build_topology.py cisco-pkt-builder/examples/lan.yaml --out hasil/lan
python cisco-pkt-builder/scripts/pkt_codec.py decode hasil/lan/lab-lan.pkt hasil/decoded.xml
python cisco-pkt-builder/scripts/pkt_codec.py encode hasil/decoded.xml hasil/rebuilt.pkt
python -m unittest discover -s cisco-pkt-builder/tests -v
```

Gunakan `--workspace PATH` untuk menentukan akar input/output selain direktori aktif. Path relatif dihitung dari akar tersebut. Input/output lab di luar akar ditolak. Bootstrap secara khusus membaca contoh dari direktori instalasi PT dan menulis cache di workspace; kode dibaca dari paket. Output lab lama tidak ditimpa. Tidak ada permintaan jaringan atau pembacaan folder lab pribadi/Downloads. Jangan unggah cache atau output lab tanpa meninjau isinya.

Output build: `.pkt`, XML, spesifikasi normalisasi `topology.json`, ringkasan perangkat/IP/link `summary.md`, dan `configs/<hostname>.txt`. Untuk fallback CLI, masuk `enable`, kemudian `configure terminal`, tempel konfigurasi, dan simpan dengan `copy running-config startup-config`. Baris `version` merupakan metadata running-config dan dapat diabaikan saat ditempel manual.

## Instalasi agent

Salin **seluruh folder** `cisco-pkt-builder` ke lokasi berikut, lalu mulai chat baru atau muat ulang daftar skill:

| Agent | Per proyek | Global |
|---|---|---|
| Codex | `<workspace>/.agents/skills/cisco-pkt-builder/` | `~/.agents/skills/cisco-pkt-builder/` |
| Antigravity | `<workspace>/.agents/skills/cisco-pkt-builder/` | `~/.gemini/config/skills/cisco-pkt-builder/` |

Lokasi mengikuti [dokumentasi resmi Codex](https://learn.chatgpt.com/docs/build-skills) dan [dokumentasi resmi Antigravity](https://antigravity.google/docs/skills), diperiksa 25 Oktober 2026. Instalasi baru pada kedua agent belum diuji oleh pengguna independen. Paket diserahkan di workspace, belum dipasang global. Agent yang tidak menemukan skill dapat diminta membaca `cisco-pkt-builder/AGENTS.md`.

Contoh permintaan: “Gunakan cisco-pkt-builder untuk membuat 2 router, 2 switch, dan 4 PC dengan OSPF area 0.”

## Skema input

Top-level: `name`, `devices`, `links`. Nama memakai huruf awal, lalu huruf/angka/underscore/hyphen, maksimum 63 karakter. Field asing ditolak agar fitur tidak hilang diam-diam. Input JSON juga didukung.

Perangkat memerlukan `id`, `type`; `model` dan `position: [x, y]` opsional. Model MVP: router `2911`, switch `2960` atau `2960-24TT`, pc `PC-PT`, server `Server-PT`. Koordinat 0–3800. Default posisi grid dengan jarak 220 × 200. Maksimum 100 perangkat.

- Router: `interfaces: {Gi0/0: 192.168.10.1/24}`. Port Gi0/0 sampai Gi0/2.
- PC/server: `ip: 192.168.10.10/24`, `gateway: 192.168.10.1`. Jika IP tidak ditentukan, NIC tidak diberi alamat; agent sebaiknya mengisi alamat sesuai kebutuhan pengguna.
- Switch: `vlans: {10: DATA}` dan `ports: {Fa0/1: {mode: access, vlan: 10}}`. Port Fa0/1–Fa0/24 serta Gi0/1–Gi0/2. Trunk memakai `{mode: trunk, allowed_vlans: [10, 20], native_vlan: 1}`. VLAN selain 1 harus didefinisikan. Trunk hanya membawa VLAN yang disebut.
- Link ringkas: `[R1:Gi0/0, SW1:Gi0/1]`; bentuk lengkap: `{from: R1:Gi0/0, to: SW1:Gi0/1, cable: straight}`. Kabel otomatis cross untuk switch–switch atau pasangan endpoint non-switch, straight untuk switch–endpoint. Nama port panjang juga diterima.

Konfigurasi router opsional:

```yaml
config:
  ospf:
    process: 1
    area: 0
    networks: [10.0.12.0/30, 192.168.10.0/24]
  static_routes:
    - {network: 0.0.0.0/0, next_hop: 10.0.12.2}
  dhcp:
    - name: LAN
      network: 192.168.10.0/24
      gateway: 192.168.10.1
      dns: 192.168.10.53
      excluded: [192.168.10.2, 192.168.10.3]
```

OSPF mengonversi CIDR menjadi wildcard mask. Next hop statis harus berada di subnet interface router. DHCP MVP hanya pool lokal dengan gateway pada interface router; gateway dan seluruh alamat statis dalam spec otomatis dikecualikan. `excluded` berisi alamat individual, bukan rentang. Klien DHCP harus diaktifkan manual di PT; tidak ada DHCP relay otomatis.

## Contoh

- `examples/lan.yaml`: 1 router, 1 switch, 2 PC, satu subnet.
- `examples/vlan.yaml`: 2 switch, VLAN 10/20, trunk, 3 PC dan 1 server. VLAN berbeda terisolasi; tidak ada routing antar-VLAN. Server dipakai sebagai endpoint IP, layanan aplikasi dinonaktifkan.
- `examples/ospf.yaml`: 2 router, 2 switch, 4 PC, dua LAN dan transit /30.

Repository menyediakan ketiga spesifikasi YAML. File `.pkt` dibuat lokal saat build; XML, cache dan contoh biner tidak didistribusikan dalam paket publik.

## Kompatibilitas dan batas penerimaan

Bootstrap diuji memakai contoh bawaan instalasi **9.0.0**. Sampel dapat berasal dari versi PT lebih lama; versi sumber dicatat dalam manifest cache. Seed yang terpilih pada mesin pengujian bertag **7.1.0.0000**; angka ini bukan klaim kompatibilitas runtime. Dua percobaan peluncuran aplikasi tidak memberi jendela yang dapat ditarget alat otomasi. Tidak ada klaim file telah dibuka atau CLI diterapkan di PT. Jangan mengganti tag VERSION untuk memaksakan kompatibilitas. Runtime PT 7.x/8.x belum diuji.

Validasi mencakup XML well-formed, model/port, nama/ID, IP ganda, gateway, VLAN, link yatim, port ganda, field asing, integritas codec dan round-trip. Validasi ini tidak membuktikan konektivitas, route convergence, atau penerapan konfigurasi oleh PT. Lihat `ACCEPTANCE.md` untuk hasil terukur dan pekerjaan yang tersisa.

NAT, impor/modifikasi otomatis sembarang `.pkt`, IPv6, subinterface/SVI, serial, wireless/IoT/ASA, layanan server dan `.pka` belum tersedia. Untuk mengedit lab hasil skill, ubah YAML atau `topology.json`, lalu bangun ulang. Decode file lain dapat digunakan untuk inspeksi; encoder hanya menerima model MVP. Tidak ada fallback JavaScript yang diklaim bekerja tanpa uji API PT.

## Asal kode dan lisensi

Kode `pkt_core` dan `lab_api.py` berasal dari [packet-tracer-pkt-format](https://github.com/aacanadaa/packet-tracer-pkt-format), dipin ke commit `ce61cd619ccc34e593557b8e0820f671fdeb571d`. Tidak ada seed/template Cisco dalam distribusi publik. Struktur lokal berasal dari instalasi pengguna dan tetap tunduk pada ketentuan sumbernya; lisensi kode tidak memberi hak tambahan atas materi Cisco. Detail ada di `THIRD_PARTY.md`. Kode paket memakai GPL-3.0-or-later; PyYAML memakai MIT.
