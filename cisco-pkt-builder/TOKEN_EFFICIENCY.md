# Metode hemat token

AI memilih desain dan menulis perubahan kecil; Python menangani validasi, CLI, XML dan codec. Script tidak memanggil model/API. Penghematan bergantung pada ukuran lab dan perilaku agent; belum diukur sebagai persentase atau biaya.

| Kebutuhan | Tindakan AI |
|---|---|
| Lab persis preset | Pilih lan, vlan, atau ospf; langsung build |
| Variasi standar | Baca satu contoh YAML, salin dan edit field terkait |
| Revisi lab sendiri | Edit spec terakhir atau topology.json |
| Error validasi | Baca pesan singkat, perbaiki bagian terkait |
| Inspeksi impor | Decode ke file lalu cari bagian relevan, jangan cetak seluruh XML |

## Perintah praktis

```sh
python cisco-pkt-builder/scripts/build_topology.py --preset ospf --out hasil/ospf --json-report
```

Preset memakai alamat dan konfigurasi contoh tetap. Jangan memakai preset langsung jika kebutuhan pengguna berbeda. Untuk kustomisasi, salin satu contoh ke `spec.yaml` melalui filesystem, edit seperlunya, lalu:

```sh
python cisco-pkt-builder/scripts/build_topology.py spec.yaml --out hasil/revisi --json-report
```

Tidak perlu menulis ulang semua perangkat di chat. Simpan keadaan terbaru di file. Laporan JSON berisi status, jumlah perangkat/link, path hasil, pemeriksaan, dan status GUI. Detail IP/CLI tetap tersedia sebagai artefak.

## Pembacaan dan pengujian

- Baca SKILL.md dahulu; buka bagian referensi yang relevan saja. Jangan membuka ulang PRD, seluruh README, atau upstream setiap membuat lab.
- Hindari membaca vendor, template XML, base64, dan semua contoh pada alur biasa.
- Build sudah memvalidasi spec/XML serta round-trip. Validator terpisah hanya diperlukan untuk pemeriksaan tanpa membuat file.
- Tes unit paket dijalankan saat kode berubah atau ada dugaan regresi; tidak perlu setiap lab. Jangan melewati validasi build atau uji aplikasi yang diminta pengguna.
- Jawaban normal: link .pkt, link ringkasan IP, jumlah perangkat/link, asumsi penting, dan status uji. Penjelasan panjang tetap diberikan bila diperlukan atau diminta.
- Jika error yang sama berulang setelah perbaikan, inspeksi penyebab; jangan mengulang percobaan dan output identik tanpa batas.

## Pengukuran

Bandingkan permintaan dan hasil setara pada alur lama dan alur preset. Catat token input/output aktual bila platform menyediakannya, jumlah panggilan tool, panjang output, waktu dan hasil validasi. Penghematan = `(token_lama - token_baru) / token_lama × 100%`. Pisahkan cached tokens bila tersedia. Byte/karakter bukan hitungan token pasti; jumlah token juga bukan biaya tanpa tarif terkait.

Metode ini mengurangi penulisan spec, pembacaan konteks, dan keluaran tool. Tidak menjamin batas token keras; anggaran model bergantung pada platform agent.
