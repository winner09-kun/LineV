# Profil Antigravity dengan Gemini

Panduan kerja untuk Antigravity yang memakai model Gemini pilihan pengguna. Bukan skill untuk chatbot Gemini web, bukan konfigurasi Gemini CLI, dan tidak mengganti model otomatis. Perbedaan profil berasal dari alur integrasi host, bukan asumsi bahwa semua Gemini berperilaku sama.

## Aktivasi dan eksekusi

- Utamakan lokasi workspace `.agents/skills/cisco-pkt-builder`. Sebutkan skill dengan nama; App/CLI yang mendukung pemanggilan skill lewat slash dapat memakai `/cisco-pkt-builder`. Jangan menganggap `/pkt` menjadi menu native: itu protokol internal paket. Pada IDE, periksa daftar skill aktif di Customizations bila skill belum ditemukan.
- Gunakan script sebagai alat siap pakai. Bila argumen belum jelas, baca `scripts/pkt.py --help` atau `COMMANDS.md`, bukan seluruh kode/template. Gunakan path absolut folder skill yang dimuat dan `--workspace` proyek pengguna.
- Jika tugas berjalan dalam mode yang meminta rencana/artifact review, patuhi alur host. Untuk lab kompleks, rencana cukup perangkat, subnet, VLAN dan routing serta asumsi penting; jangan membuat rencana panjang atau mengulang pertanyaan untuk preset sederhana.
- Untuk bahasa natural, tulis satu YAML valid sebelum menjalankan build. Jangan menyalin blok Markdown/fence ke dalam YAML. Perubahan selanjutnya cukup field terkait. Gunakan spec atau topology.json sebagai keadaan terbaru, bukan mengandalkan narasi chat lama.
- Jalankan dispatcher melalui terminal/tool eksekusi yang tersedia. Jika host memberi pekerjaan asynchronous, tunggu completion sebelum membaca stdout final. Jangan menyimpulkan sukses dari tampilan task/artifact yang belum selesai atau memulai build berulang.
- Ikuti review terminal dan batas akses host; jangan menambahkan direktif auto-run, mengubah allowlist, atau mengaktifkan eksekusi tanpa persetujuan. Bootstrap harus berjalan pada mesin yang memiliki instalasi PT; host remote tidak otomatis dapat membaca PC pengguna.

## Bukti dan respons

Gunakan hasil JSON dan exit code sebagai bukti. Jika host memakai walkthrough, cukup tautkan `.pkt`, `summary.md` dan status pemeriksaan. File `.pkt` harus benar-benar ada; artifact teks yang menjelaskan topologi bukan penggantinya. Status GUI tetap belum diuji kecuali ada bukti dari aplikasi.

Prompt awal yang tidak bergantung pada dropdown:

```text
Gunakan skill cisco-pkt-builder. /pkt mode antigravity-gemini
/pkt buat 2 router, 2 switch dan 6 PC, OSPF area 0, IP otomatis
```

Sumber integrasi diperiksa 26 Oktober 2026: [Antigravity Agent skills](https://antigravity.google/docs/skills). Langkah operasional di atas merupakan desain paket ini. Instalasi end-to-end dan pengujian perilaku model Gemini belum dijalankan di sini.
