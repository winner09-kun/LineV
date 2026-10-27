# Pengujian instalasi dan kompatibilitas

Uji instalasi memakai ZIP yang diekstrak ke lokasi baru, workspace tanpa cache,
path dengan spasi dan Unicode, serta direktori kerja di luar instalasi skill.
Python dijalankan tanpa site-packages (`-S`), tanpa PYTHONPATH/PYTHONHOME warisan,
dan tanpa menulis bytecode. Dependensi yang diperlukan disertakan di `vendor`.
Tidak perlu `pip install` untuk alur ini.

## Cakupan bukti

| Lingkungan / fitur | Cakupan pengujian |
| --- | --- |
| Windows 11, Python 3.12.14, sumber lokal Packet Tracer 9.0.0 | Lulus 40 pemeriksaan instalasi bersih pada 27 Oktober 2026 |
| Python 3.10 | Pemeriksaan sintaks; bukan eksekusi interpreter 3.10 |
| Python lain, Linux, macOS, komputer lain | Belum diuji |
| Penemuan skill otomatis oleh aplikasi AI | Tidak diuji oleh harness ini |
| Membuka GUI, sesi routing, ping | Tidak diuji oleh harness ini |

Keberhasilan instalasi tidak membuktikan simulasi jaringan berjalan. Audit LAN/BGP
diharapkan `passed_static`; audit VLAN/OSPF masih `partial` karena pemeriksaan
semantik protokolnya belum lengkap. Semua status runtime tetap `not_tested`.

## Menjalankan pengujian

Setelah mengekstrak ZIP, jalankan dari folder proyek, sesuaikan path yang dikutip:

```powershell
python "C:/lokasi/cisco-pkt-builder/scripts/verify_install.py" "C:/unduhan/cisco-pkt-builder.zip" --out "qa/install-test-01"
```

Direktori `--out` harus baru. Tambahkan `--pt-install "C:/Program Files/Cisco Packet Tracer 9.0.0"`
bila lokasi instalasi tidak ditemukan otomatis. Tanpa Packet Tracer, tambahkan
`--offline-only`: pemeriksaan ZIP, dependensi dan validasi spesifikasi tetap berjalan,
tetapi bootstrap, build dan codec dilewati secara eksplisit.

Pengujian lengkap mencakup empat preset, bootstrap tanpa cache lama, audit `.pkt`,
decode/encode dengan perbandingan byte, penolakan penimpaan output serta path keluar
workspace. Harness memastikan isi paket instalasi tidak berubah dan direktori kerja
tidak tercemar. Pada Windows, dispatcher mengaktifkan UTF-8 pada proses Python anak
agar codec dapat mencetak path non-ASCII tanpa gagal.

Laporan `install-report.json` mencatat versi Python/OS, SHA-256 ZIP, hasil per langkah,
dan batas pengujian. Exit code 0 berarti lulus, 2 berarti gagal. Tidak ada upload,
akses jaringan, atau kontrol desktop; file pengujian disimpan lokal di `--out`.
