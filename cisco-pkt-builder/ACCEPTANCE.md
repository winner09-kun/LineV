# Status penerimaan PRD

Tanggal 25 Oktober 2026. Kandidat MVP; pembukaan aplikasi belum terverifikasi.

## Alur pengguna

Pengguna menjelaskan jaringan ke agent. Agent membuat spec kecil atau memilih preset. Build mencari instalasi Packet Tracer dan mengekstrak struktur model dari contoh bawaan secara otomatis ke cache lokal. Pengguna tidak diminta menyiapkan template. Python 3.10+ dan Packet Tracer dengan contoh model yang dibutuhkan merupakan prasyarat.

## Bukti pengujian

Perbaikan laporan lambat pada “Opening file”, 26 Oktober 2026: cache schema 2 memilih seed dengan endpoint `save-ref-id` yang konsisten, tanpa mengganti tag VERSION. Bootstrap lokal memeriksa 82 sampel dan memilih seed bertag 7.2.0.0000. Generator memberi ID memori unik pada perangkat dan menyelaraskan referensi memori kabel, serta membersihkan timeline lingkungan dan metadata ekstensi donor. Cache schema lama dibangun ulang otomatis. Seluruh 31 tes lulus, termasuk regresi ID ganda, kabel salah referensi, pemilihan skema seed dan pelestarian identitas physical workspace. LAN baru: 22.767 byte PKT / 387.410 byte XML, sebelumnya 37.112 / 678.362 byte. Waktu buka GUI belum terukur; ini kandidat perbaikan, bukan bukti masalah loading sudah selesai.

Profil `codex-gpt` dan `antigravity-gemini` ditambahkan bersama metadata Codex dan panduan instalasi workspace/global. Profil adalah instruksi host, bukan perubahan model atau pengujian empiris antar-model. Seluruh 27 tes tetap lulus. ZIP diverifikasi memuat kedua profil dan metadata, tanpa template/biner Cisco; validator skill lulus. Ekstraksi ke workspace baru pada `.agents/skills/cisco-pkt-builder` lalu eksekusi `help` dan `validate` berhasil. Ini smoke test filesystem/CLI, belum uji end-to-end Antigravity/Gemini atau matriks versi GPT.

Pembaruan 26 Oktober 2026: 27 tes lulus setelah penambahan dispatcher `/pkt`. Tujuh tes baru memeriksa help tanpa eksekusi, pemetaan preset/opsi, pemilihan direktori baru, argumen tanpa shell, penolakan perintah asing, validasi melalui dispatcher dan pembatasan path. Smoke test dispatcher `lan` berhasil menghasilkan 4 perangkat/3 link dengan validasi XML dan round-trip. Ini bukan bukti registrasi menu slash native atau uji GUI PT.

Bootstrap berhasil pada instalasi Packet Tracer 9.0.0 Windows setelah memeriksa 75 sampel bawaan. Empat model ditemukan: 2911, 2960-24TT, PC-PT dan Server-PT. Seed sampel bertag 7.1.0.0000; versi file sampel bukan klaim versi aplikasi yang telah menerima output.

Seluruh 20 tes lulus. Tes mencakup tiga contoh round-trip, determinisme dengan cache yang sama, duplicate IP/port/link, gateway, VLAN/trunk, OSPF, DHCP/routing statis, integritas codec/cache, batas path, no-overwrite, preset, dan rebuild spec normalisasi.

Waktu sekitar 1,6 detik per contoh pada implementasi template lama adalah hasil historis; bukan benchmark bootstrap baru. Cache berbeda dapat menghasilkan XML berbeda karena donor perangkat berbeda. Input dan cache yang sama menghasilkan output deterministik.

## Kebutuhan

| ID | Hasil implementasi |
|---|---|
| FR-1 | Spec ke XML dan .pkt; round-trip teruji, GUI belum |
| FR-2 | Router 2911, switch 2960-24TT, PC dan server |
| FR-3 | Kabel straight/cross otomatis dan override |
| FR-4 | Hostname dan IPv4/gateway |
| FR-5 | VLAN, trunk, access port melalui CLI |
| FR-6 | Routing statis dan OSPF melalui CLI |
| FR-7 | DHCP router lokal; NAT belum |
| FR-8 | Decode/encode dan rebuild spec; edit generik .pkt belum |
| FR-9 | Validasi spec/XML dan round-trip |
| FR-10 | Ringkasan perangkat, tabel IP, link dan file CLI |

## Batas penerimaan

- Dua percobaan peluncuran PT melalui alat otomasi tidak menghasilkan jendela yang dapat ditarget. File belum dibuktikan terbuka atau menerapkan CLI. Uji ping bukan bagian wajib MVP.
- Instalasi bersih dan pemanggilan oleh orang lain pada Codex/Antigravity belum diuji. Deteksi instalasi Linux/macOS belum diuji.
- Tiga YAML disertakan. Hasil .pkt/XML dibuat lokal, tidak didistribusikan di GitHub/ZIP. Ini perubahan pengemasan dari PRD agar bahan Cisco tidak ikut dipublikasikan.
- Cache dan hasil lokal tidak memiliki izin distribusi tambahan dari lisensi kode paket. Jangan unggah otomatis.
- Metrik 100% file terbuka dan 90% dari 10 skenario belum terbukti. Tiga donor manual buatan sendiri belum dibuat; bootstrap menggunakan contoh bawaan instalasi.
- Fallback JavaScript belum tersedia; fallback saat gagal adalah spec, ringkasan dan CLI, bukan API PT tebakan.
- Efisiensi token memakai preset, pembacaan referensi sesuai kebutuhan, cache lokal dan laporan JSON singkat; persentase penghematan belum diukur.
