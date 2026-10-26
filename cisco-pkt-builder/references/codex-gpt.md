# Profil Codex dengan GPT

Panduan kerja untuk host Codex yang memakai model GPT pilihan pengguna. Tidak mengunci versi model, mengubah reasoning effort, atau membutuhkan API key. Profil menyesuaikan integrasi host, bukan mengasumsikan semua model GPT memiliki kemampuan yang sama.

## Aktivasi dan eksekusi

- Skill berada di `.agents/skills/cisco-pkt-builder` pada workspace atau `~/.agents/skills/cisco-pkt-builder` untuk pengguna. Aktifkan dengan `$cisco-pkt-builder` pada permukaan yang mendukungnya, atau sebutkan nama skill. `/pkt` adalah protokol internal sesudah skill dimuat.
- Resolusi path: gunakan direktori SKILL.md yang benar-benar dimuat sebagai akar script; gunakan direktori proyek pengguna sebagai `--workspace`. Jangan mengasumsikan cwd sama dengan folder skill. Output dan cache tetap di proyek, termasuk saat skill dipasang global.
- Preset standar: satu panggilan terminal ke `scripts/pkt.py`. Gunakan tool filesystem/patch yang tersedia untuk spec khusus. Jangan minta model menulis XML atau menyalin source codec.
- Untuk topologi baru yang kompleks, buat rencana ringkas berdasarkan subnet, VLAN dan routing, lalu terjemahkan menjadi satu spec. Jika sesi memang dalam mode perencanaan, hormati mode itu; jangan menjalankan build sebelum host/pengguna mengizinkan eksekusi.
- Jika proses terminal mengembalikan session/job ID, tunggu melalui tool host yang sesuai. Jangan menjalankan proses build kedua hanya karena proses pertama belum selesai. Pisahkan error sintaks, bootstrap dan persetujuan sandbox; pesan izin bukan bukti konfigurasi jaringan salah.
- Ikuti persetujuan dan sandbox host; jangan mengubah pengaturan keamanan untuk membuat bootstrap berhasil. Dalam lingkungan cloud/remote, gunakan instalasi PT pada host eksekusi yang dapat diakses, bukan menganggap aplikasi di PC pengguna tersedia.

## Bukti dan respons

Gunakan JSON stdout serta exit code untuk menentukan hasil. Pada error, baca bagian spec yang disebut dan lakukan perubahan kecil. Laporan akhir: link `.pkt`, link ringkasan IP, jumlah device/link dan status GUI. File lokal ditautkan sesuai kemampuan host. Jangan mengklaim ping atau GUI teruji hanya karena build lulus.

Prompt awal:

```text
$cisco-pkt-builder /pkt mode codex-gpt
/pkt buat 2 router, 2 switch dan 6 PC, OSPF area 0, IP otomatis
```

Sumber integrasi diperiksa 26 Oktober 2026: [OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills). Langkah operasional di atas merupakan desain paket ini. Pengujian perilaku lintas model GPT belum dilakukan.
