# Sistem Absensi Digital — WebApp (Kartu Pelajar)

Kartu pelajar digital (QR + barcode 1D) + scanner kamera untuk absensi:
- Harian · Solat · Perpustakaan

## Fitur
1. Kartu digital tiap siswa (QR + Code128), print-ready, header profil sekolah.
2. Scanner kamera (HP/tablet) → pilih jenis → tap kartu → log ke DB.
3. Bulk import siswa dari CSV + migrasi dari dump SQL phpMyAdmin lama.
4. Export absensi ke CSV + (opsional) sinkron Google Sheets via Apps Script.
5. PWA: bisa "Pasang ke layar utama", kartu bisa dibuka offline (service worker).

## Stack
- Flask (backend, SQLite)
- qrcode + python-barcode (generator gambar)
- html5-qrcode (scanner di browser)
- Manifest + Service Worker (PWA)

## Cara jalan
```
cd absensi_web
. .venv/Scripts/activate
python app.py
```
Buka:
- http://localhost:5000/        home
- http://localhost:5000/scanner scanner absen
- http://localhost:5000/admin   admin (tambah/bulk/migrasi/profil/export)
- http://localhost:5000/kartu/1 kartu digital siswa id 1

Akses dari HP (1 WiFi): http://<IP-PC>:5000

## API
- GET/POST  /api/profil                    profil sekolah
- POST      /api/siswa                     {nis,nisn,nama,kelas,no_wa}
- GET       /api/siswa
- POST      /api/siswa/bulk                file CSV / JSON array
- POST      /api/migrate                   migrasi dari drive_import/*.sql
- GET       /api/qr/<id>  /api/barcode/<id>
- POST      /api/log                       {kode,jenis,keterangan}
- GET       /api/logs?jenis=harian&limit=50
- GET       /api/export/csv?jenis=...      download CSV
- POST      /api/export/sheets             (butuh env SHEETS_WEBHOOK)
- GET       /api/template.csv              template import CSV

## Migrasi dari dump lama (db-absensi-qr-v5-39-ok.sql)
Dump phpMyAdmin dari folder Drive: data siswa tersebar di tabel `siswa` (1 row)
DAN tabel `users` (role='siswa', username=NISN). Migrator baca keduanya.
Profil sekolah (SD AL-IHSAN) diambil dari tabel `profil_sekolah`.
Jalankan: tombol "Migrasi dari SQL Drive" di /admin, atau POST /api/migrate.

## Sinkron Google Sheets (#2)
Buat Apps Script (Extensions > Apps Script di Spreadsheet), paste kode doPost:
```
function doPost(e){
  var data=JSON.parse(e.postData.contents);
  var sheet=SpreadsheetApp.getActive().getSheetByName('Absensi')||SpreadsheetApp.getActive().insertSheet('Absensi');
  data.rows.forEach(r=>sheet.appendRow([r.waktu,r.nisn,r.nis,r.nama,r.kelas,r.jenis,r.keterangan]));
  return ContentService.createTextOutput('ok');
}
```
Deploy > New deployment > Web app. Copy URL → set env:
```
export SHEETS_WEBHOOK="https://script.google.com/.../exec"
```
Lalu POST /api/export/sheets.

## Catatan
- Folder Google Drive = backup/export, BUKAN DB realtime.
- Produksi: debug=False, pakai waitress/gunicorn, DB ganti MySQL.
