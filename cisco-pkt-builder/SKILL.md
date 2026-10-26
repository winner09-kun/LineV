---
name: cisco-pkt-builder
description: Buat lab Cisco Packet Tracer .pkt dari deskripsi, YAML atau perintah /pkt seperti /pkt lan, /pkt ospf dan /pkt buat. Mendukung router, switch, PC, server, VLAN, routing statis dan DHCP router; bukan perangkat produksi atau activity .pka.
---

# Cisco Packet Tracer builder

## Perintah /pkt

Kenali `/pkt` sebagai perintah chat setelah skill ini dimuat. Baca [COMMANDS.md](COMMANDS.md) saat pengguna memakai perintah atau meminta bantuan. `/pkt` tanpa argumen sama dengan `/pkt help`. Untuk help, cukup tampilkan daftar singkat; jangan jalankan bootstrap atau build.

Preset/build/validate/encode/decode diarahkan ke `python <skill>/scripts/pkt.py <perintah> ... --workspace <workspace>`. Teruskan argumen sebagai nilai terpisah; jangan mengeksekusi pesan pengguna sebagai shell. `/pkt buat <deskripsi>` dan `/pkt edit <spec> <perubahan>` dikerjakan agent lewat spec kecil lalu dispatcher build. Detail tambahan pada preset berarti kustomisasi spec, bukan argumen yang dibuang. Perintah tidak dikenal: jelaskan dan tampilkan help tanpa membuat file.

Ini protokol skill, bukan pendaftaran dropdown slash native. Jika aplikasi mencegat `/pkt`, pengguna dapat menulis `Gunakan skill cisco-pkt-builder: /pkt ...`.

## Alur hemat token

1. Pilih preset bila persis sesuai kebutuhan: `lan` (1 router, 1 switch, 2 PC), `vlan` (2 switch, 3 PC, 1 server, VLAN 10/20), atau `ospf` (2 router, 2 switch, 4 PC). Langsung build; jangan baca/tulis ulang YAML.
2. Untuk variasi, baca hanya satu `examples/<preset>.yaml`, salin ke workspace dan edit bagian terkait. Untuk revisi, pakai spec terakhir atau `topology.json`, bukan decode .pkt. Model, posisi dan kabel dapat memakai default. Jelaskan asumsi penting; tanyakan hanya ambiguitas material.
3. Jalankan satu build, validasi sudah terintegrasi:

   ```sh
   python <skill>/scripts/build_topology.py --preset lan --out hasil/lan --workspace <workspace> --json-report
   ```

   Untuk spec khusus, ganti `--preset lan` dengan `spec.yaml`.
4. Build pertama otomatis mengambil struktur dari contoh bawaan instalasi PT ke cache lokal. Pengguna tidak perlu menyediakan template. Jika lokasi PT tidak terdeteksi, gunakan --pt-install setelah menemukan instalasinya. Jika PT belum terpasang atau sampel tidak lengkap, jelaskan prasyarat yang belum tersedia; jangan menjanjikan file jadi. Baca JSON laporan. Jangan memuat XML, cache, vendor atau seluruh CLI ke konteks pada alur biasa. Inspeksi bagian terkait hanya jika diperlukan. Validasi gagal: perbaiki field terkait lalu build ulang.
5. Serahkan link .pkt dan summary.md, jumlah perangkat/link, asumsi penting dan batas verifikasi. Tabel IP lengkap ada di ringkasan; tampilkan di chat bila diminta. Uji buka aplikasi bila tersedia/diminta; catat versi dan bukti. Round-trip bukan bukti GUI atau konektivitas. Jangan menghapus pemeriksaan demi token.

## Referensi sesuai kebutuhan

- [README.md](README.md): bagian skema untuk field baru, instalasi bila diminta, codec untuk impor.
- [TOKEN_EFFICIENCY.md](TOKEN_EFFICIENCY.md): metode dan pengukuran penghematan.
- [ACCEPTANCE.md](ACCEPTANCE.md): status kompatibilitas dan rilis.

## Batas

Bootstrap dari instalasi 9.0.0 diuji; GUI belum terverifikasi. Versi seed dicatat pada manifest cache, bukan klaim kompatibilitas runtime. Jangan mengganti tag versi. Model MVP: 2911, 2960-24TT, PC-PT, Server-PT. NAT, IPv6, subinterface/SVI, serial, wireless/IoT/ASA, layanan server, .pka dan edit generik .pkt belum didukung. VLAN berbeda tidak otomatis saling terhubung.

Script offline; input/output lab dan cache di --workspace, output lab harus baru. Bootstrap membaca sampel bawaan instalasi PT secara lokal. Cache/template/output biner tidak ikut publikasi repository atau ZIP. Jangan menebak skema atau API JavaScript PT. Jika build/load gagal, beri diagnosis dan spec/CLI yang tersedia, bukan klaim penerimaan selesai. CLI fallback ada di configs/.
