# Analisis file pengguna

`/pkt analisa "jaringan.pkt"` atau `/pkt analyze "jaringan.pkt"` membaca satu
file tanpa YAML, topology.json, cache, instalasi Packet Tracer atau kontrol desktop.
Input harus berada di `--workspace`; untuk file Downloads gunakan folder itu sebagai
workspace atau salin file hanya bila diperlukan. Path dengan spasi harus dikutip.
`--out` opsional menyimpan JSON baru; file yang sudah ada tidak ditimpa.

```powershell
python "C:/skills/cisco-pkt-builder/scripts/pkt.py" analisa "jaringan.pkt" --workspace "C:/Users/nama/Downloads" --out "analisis-jaringan.json"
```

Pemeriksa membaca bytes `.pkt` aktual dan mencatat SHA-256. File input tidak diubah.
Tidak mengeksekusi CLI/script di dalam file. Laporan tidak menyalin seluruh konfigurasi
atau password; identitas perangkat, alamat jaringan dan bukti terpilih tetap dapat
bersifat privat, sehingga jangan otomatis memublikasikan laporan.

## Cakupan

- IPv4/mask tidak valid, alamat network/broadcast pada host/interface.
- Gateway host statis di luar subnet atau sama dengan alamat host.
- Kemungkinan IP ganda; VLAN/VRF terpisah bisa membuatnya disengaja.
- Power perangkat mati, interface berkabel dengan `shutdown`, perangkat tanpa kabel terpetakan.
- Endpoint kabel ambigu, referensi perangkat ganda, port berkabel berulang.
- Subnet berbeda pada link langsung dengan alamat kedua interface yang dikenali.
- Running/startup config berbeda dan kemungkinan `remote-as` BGP berbeda dari ASN peer yang berhasil dipetakan.

Model yang telah dipakai dalam pengujian: 2911, 2960-24TT, PC-PT, Server-PT.
Model/struktur lain dibaca sebatas field yang dikenali dan ditandai belum diuji;
file asing tidak dipaksa memenuhi skema generator. IP/gateway endpoint saat DHCP
aktif dilewati karena lease tersimpan bukan bukti keadaan runtime.

## Membaca hasil

`status=findings` berarti ada hal untuk ditinjau, bukan otomatis seluruh jaringan rusak.
`no_findings_in_scope` berarti tidak ada temuan dalam cakupan, bukan jaminan benar.
`coverage=partial` selalu digunakan. Severity `error` untuk field/struktur yang terbukti
bermasalah; `warning` untuk kondisi yang bisa disengaja atau membutuhkan konteks.
Setiap temuan berisi kode, perangkat, bukti dan saran. Jangan menyebut dugaan sebagai
penyebab pasti. Jika tujuan desain diperlukan, minta konteks setelah menyajikan temuan.

Exit 0 berarti analisis selesai, termasuk jika ada temuan. Exit 2 berarti input gagal
dibaca/di-decode atau laporan gagal disimpan. Jangan menafsirkan exit 0 sebagai jaringan sehat.
Decode gagal: laporkan keterbatasan; jangan mengganti tag versi atau merekayasa file agar lolos.

Belum menganalisis forwarding, VLAN/VRF, ACL, NAT, DHCP, IPv6, OSPF, policy BGP,
wireless, convergence, status runtime port, atau clock serial. Peer BGP bisa berada
di luar file. Parser tidak menyimpulkan link up, BGP Established atau ping sukses.
Semua status runtime tetap `not_tested`. Untuk perbaikan, jelaskan konfigurasi yang
perlu ditinjau; analisis ini tidak menyediakan editor generik `.pkt`.
