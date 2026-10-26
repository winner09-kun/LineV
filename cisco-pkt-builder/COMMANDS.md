# Perintah singkat

Setelah skill dimuat, ketik salah satu perintah berikut di chat agent:

| Perintah | Hasil |
|---|---|
| `/pkt` atau `/pkt help` | Daftar perintah, tanpa menjalankan generator |
| `/pkt mode auto` | Agent memakai profil sesuai host yang dikenali |
| `/pkt mode codex-gpt` | Panduan kerja Codex dengan GPT untuk chat ini |
| `/pkt mode antigravity-gemini` | Panduan kerja Antigravity dengan Gemini untuk chat ini |
| `/pkt lan` | 1 router, 1 switch, 2 PC satu subnet |
| `/pkt vlan` | 2 switch, VLAN 10/20, trunk, 3 PC dan 1 server |
| `/pkt ospf` | 2 router, 2 switch, 4 PC dengan OSPF |
| `/pkt bgp` | 3 router HWIC-2T, 3 switch, 7 PC, AS 100/200/300 |
| `/pkt buat <deskripsi>` | AI menyusun spec sesuai deskripsi lalu membangun .pkt |
| `/pkt edit <spec> <perubahan>` | AI merevisi spec dan membangun hasil baru |
| `/pkt build <spec.yaml>` | Membangun spec YAML/JSON yang sudah ada |
| `/pkt validate <spec.yaml>` | Memeriksa spec tanpa memerlukan instalasi PT |
| `/pkt decode <input.pkt> <output.xml>` | Membaca struktur file .pkt lokal |
| `/pkt encode <input.xml> <output.pkt>` | Memvalidasi XML lalu membuat .pkt |

Contoh:

```text
/pkt lan
/pkt ospf --out hasil/latihan-routing
/pkt buat 2 router, 2 switch, 6 PC dengan OSPF area 0
/pkt edit "spec kantor.yaml" tambah satu PC di subnet LAN pertama
/pkt validate "spec kantor.yaml"
```

Jika preset diberi penyesuaian bahasa natural, agent membaca satu contoh lalu membuat spec khusus. Jangan menjalankan preset mentah sambil mengabaikan penyesuaian. Untuk edit, pertahankan spec asli dengan membuat salinan revisi kecuali pengguna meminta pengubahan file itu langsung. Edit ini berlaku untuk spec, bukan modifikasi generik .pkt.

## Eksekusi oleh agent

Perintah operasional memiliki dispatcher deterministik:

```sh
python cisco-pkt-builder/scripts/pkt.py lan --workspace .
python cisco-pkt-builder/scripts/pkt.py /pkt validate "spec kantor.yaml" --workspace .
python cisco-pkt-builder/scripts/pkt.py build spec.yaml --out hasil/custom --workspace .
```

Awalan `/pkt` boleh ditulis sebagai argumen terpisah pada CLI. Jangan mengirim seluruh pesan chat sebagai satu string shell. `buat`, `edit`, dan `mode` ditangani AI, bukan parser bahasa natural dalam script. Mode berlaku dalam chat dan tidak mengganti model/provider atau mendaftarkan tool. Tanpa tugas tambahan, mode hanya dikonfirmasi, tidak membangun file. Nama mode asing: tampilkan tiga pilihan yang tersedia. Dispatcher menolak perintah/opsi yang tidak dikenal dan meneruskan exit code validator/generator.

Build menerima `--out`, `--workspace`, dan `--pt-install`. Tanpa `--out`, folder otomatis dipilih dari `hasil/lan`, `hasil/lan-2`, dan seterusnya (sesuai nama perintah). Folder eksplisit yang sudah ada ditolak oleh generator. Validasi menerima `--xml` untuk XML. Codec menerima `--workspace`. Semua pemeriksaan sebelumnya tetap berjalan.

## Kompatibilitas chat

Perintah ini adalah konvensi yang dibaca agent dari skill; tidak otomatis menambahkan dropdown/autocomplete native aplikasi. Jika `/pkt` dicegat oleh aplikasi atau skill belum dimuat, gunakan:

> Gunakan skill cisco-pkt-builder: /pkt lan

Atau minta agent membaca SKILL.md terlebih dahulu. Pembuatan file membutuhkan akses filesystem/terminal dan instalasi PT untuk bootstrap pertama. Help dan validasi spec tidak membutuhkan PT. Pembukaan hasil pada GUI tetap harus diverifikasi terpisah.
