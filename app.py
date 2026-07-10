"""
Kartu Pelajar Digital + Absensi (WebApp) — v2
Fitur: kartu digital (QR + barcode 1D), scanner kamera, log absen
3 tipe: harian, solat, perpustakaan. Profil sekolah. Migrasi dari SQL lama.
Bulk import CSV. Export CSV + sinkron Google Sheets/Drive (via Apps Script webhook).
PWA: installable + cache kartu offline.

Stack: Flask + SQLite + qrcode + python-barcode + html5-qrcode.
"""
import io
import os
import re
import csv
import ast
import json
import sqlite3
import datetime as dt

from flask import (Flask, request, jsonify, render_template,
                   send_file, send_from_directory, g, abort)
import qrcode
import barcode
from barcode.writer import ImageWriter

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data", "absensi.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)

# Konfigurasi sinkron eksternal (isi di .env / env var)
SHEETS_WEBHOOK = os.environ.get("SHEETS_WEBHOOK", "")   # Apps Script doPost URL
DRIVE_WEBHOOK = os.environ.get("DRIVE_WEBHOOK", "")     # Apps Script upload CSV

JENIS_VALID = ["harian", "solat", "perpus"]

app = Flask(__name__)


def get_db():
    db = getattr(g, "_db", None)
    if db is None:
        db = g._db = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, "_db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS profil_sekolah (
            id INTEGER PRIMARY KEY CHECK (id=1),
            nama_sekolah TEXT,
            alamat TEXT,
            kepala_sekolah TEXT,
            jam_masuk TEXT,
            jam_pulang TEXT,
            logo TEXT
        );
        CREATE TABLE IF NOT EXISTS siswa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nis TEXT,
            nisn TEXT,
            nama TEXT NOT NULL,
            kelas TEXT,
            no_wa TEXT,
            rfid_uid TEXT,
            foto TEXT,
            status TEXT DEFAULT 'aktif',
            kode TEXT UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS absensi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            siswa_id INTEGER NOT NULL,
            jenis TEXT NOT NULL,
            waktu TEXT DEFAULT (datetime('now','localtime')),
            keterangan TEXT,
            FOREIGN KEY (siswa_id) REFERENCES siswa(id)
        );
        CREATE INDEX IF NOT EXISTS idx_absensi_siswa ON absensi(siswa_id);
        CREATE INDEX IF NOT EXISTS idx_absensi_waktu ON absensi(waktu);
        """
    )
    db.execute(
        "INSERT OR IGNORE INTO profil_sekolah (id) VALUES (1)"
    )
    db.commit()
    db.close()


init_db()


def gen_kode(nisn):
    return f"ABS-{nisn or ''}"


# ---------- Profil ----------
@app.route("/api/profil", methods=["GET", "POST"])
def profil():
    db = get_db()
    if request.method == "POST":
        d = request.get_json(force=True, silent=True) or {}
        cols = ["nama_sekolah", "alamat", "kepala_sekolah", "jam_masuk", "jam_pulang", "logo"]
        sets = {c: d.get(c) for c in cols}
        db.execute(
            """INSERT INTO profil_sekolah (id, nama_sekolah, alamat, kepala_sekolah, jam_masuk, jam_pulang, logo)
               VALUES (1,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 nama_sekolah=excluded.nama_sekolah, alamat=excluded.alamat,
                 kepala_sekolah=excluded.kepala_sekolah, jam_masuk=excluded.jam_masuk,
                 jam_pulang=excluded.jam_pulang, logo=excluded.logo""",
            tuple(sets.values()),
        )
        db.commit()
    row = db.execute("SELECT * FROM profil_sekolah WHERE id=1").fetchone()
    return jsonify(dict(row) if row else {})


# ---------- Siswa ----------
@app.route("/api/siswa", methods=["POST"])
def add_siswa():
    d = request.get_json(force=True, silent=True) or {}
    nisn = (d.get("nisn") or d.get("nis") or "").strip()
    nama = (d.get("nama") or "").strip()
    if not nisn or not nama:
        return jsonify({"ok": False, "msg": "nisn & nama wajib"}), 400
    kode = gen_kode(nisn)
    db = get_db()
    try:
        cur = db.execute(
            """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, rfid_uid, foto, status, kode)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (d.get("nis", ""), nisn, nama, d.get("kelas", ""), d.get("no_wa", ""),
             d.get("rfid_uid", ""), d.get("foto", ""), d.get("status", "aktif"), kode),
        )
        db.commit()
        sid = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"ok": False, "msg": "NISN sudah ada"}), 409
    return jsonify({"ok": True, "id": sid, "kode": kode})


@app.route("/api/siswa", methods=["GET"])
def list_siswa():
    db = get_db()
    rows = db.execute("SELECT * FROM siswa ORDER BY id DESC").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/siswa/<int:siswa_id>", methods=["DELETE"])
def del_siswa(siswa_id):
    db = get_db()
    s = db.execute("SELECT * FROM siswa WHERE id=?", (siswa_id,)).fetchone()
    if not s:
        return jsonify({"ok": False, "msg": "siswa tidak ada"}), 404
    # hapus foto kalau ada
    foto = s["foto"] or ""
    if foto.startswith("/foto/"):
        try:
            os.remove(os.path.join(UPLOAD_DIR, os.path.basename(foto)))
        except OSError:
            pass
    db.execute("DELETE FROM absensi WHERE siswa_id=?", (siswa_id,))
    db.execute("DELETE FROM siswa WHERE id=?", (siswa_id,))
    db.commit()
    return jsonify({"ok": True, "msg": f"siswa {siswa_id} dihapus"})



@app.route("/api/siswa/bulk", methods=["POST"])
def bulk_siswa():
    """Terima JSON array atau file CSV (multipart, field 'file')."""
    db = get_db()
    added = 0
    skipped = 0
    if "file" in request.files:
        text = request.files["file"].read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        for r in reader:
            nisn = (r.get("nisn") or r.get("nis") or "").strip()
            nama = (r.get("nama") or "").strip()
            if not nisn or not nama:
                skipped += 1
                continue
            try:
                db.execute(
                    """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, rfid_uid, foto, status, kode)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (r.get("nis", ""), nisn, nama, r.get("kelas", ""), r.get("no_wa", ""),
                     r.get("rfid_uid", ""), r.get("foto", ""), r.get("status", "aktif"), gen_kode(nisn)),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    else:
        data = request.get_json(force=True, silent=True) or []
        for d in data:
            nisn = (d.get("nisn") or d.get("nis") or "").strip()
            nama = (d.get("nama") or "").strip()
            if not nisn or not nama:
                skipped += 1
                continue
            try:
                db.execute(
                    """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, rfid_uid, foto, status, kode)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (d.get("nis", ""), nisn, nama, d.get("kelas", ""), d.get("no_wa", ""),
                     d.get("rfid_uid", ""), d.get("foto", ""), d.get("status", "aktif"), gen_kode(nisn)),
                )
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1
    db.commit()
    return jsonify({"ok": True, "added": added, "skipped": skipped})


@app.route("/api/template.csv")
def template_csv():
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["nis", "nisn", "nama", "kelas", "no_wa", "rfid_uid", "foto"])
    w.writerow(["4444", "1010101010", "Nama Siswa", "7A", "62812...", "", ""])
    buf = io.BytesIO()
    buf.write(out.getvalue().encode("utf-8"))
    buf.seek(0)
    return send_file(buf, mimetype="text/csv", as_attachment=True,
                     download_name="template_siswa.csv")


# ---------- Migrasi dari SQL lama (phpMyAdmin dump) ----------
@app.route("/api/migrate", methods=["POST"])
def migrate():
    path = request.get_json(force=True, silent=True) or {}
    sql_path = path.get("path") or os.path.join(BASE, "drive_import", "db-absensi-qr-v5-39-ok.sql")
    if not os.path.exists(sql_path):
        sql_path = os.path.join(BASE, "data_seed", "db-absensi-qr-v5-39-ok.sql")
    if not os.path.exists(sql_path):
        return jsonify({"ok": False, "msg": f"file tidak ada: {sql_path}"}), 404
    with open(sql_path, encoding="utf-8") as f:
        sql = f.read()

    db = get_db()
    added_siswa = 0
    added_profil = False

    # profil sekolah (1 row)
    m = re.search(r"INSERT INTO `profil_sekolah`.*?VALUES\s*\((.*?)\);", sql, re.S)
    if m:
        vals = ast.literal_eval("(" + m.group(1) + ")")
        # kolom: id,nama_sekolah,alamat,kepala_sekolah,nip_kepala,logo,background,key_wa,jam_masuk,jam_pulang
        db.execute(
            """INSERT INTO profil_sekolah (id, nama_sekolah, alamat, kepala_sekolah, jam_masuk, jam_pulang, logo)
               VALUES (1,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 nama_sekolah=excluded.nama_sekolah, alamat=excluded.alamat,
                 kepala_sekolah=excluded.kepala_sekolah, jam_masuk=excluded.jam_masuk,
                 jam_pulang=excluded.jam_pulang, logo=excluded.logo""",
            (vals[1], vals[2], vals[3], vals[8], vals[9], vals[5]),
        )
        added_profil = True

    # siswa (tabel `siswa` + tabel `users` role='siswa', karena dump lama
    # simpan 100 siswa di tabel users dengan username=NISN, password=hash, nama, role)
    def _parse_block(block):
        out = []
        for t in re.findall(r"\((.*?)\)", block, re.S):
            try:
                out.append(ast.literal_eval("(" + t + ")"))
            except Exception:
                pass
        return out

    seen = set()
    added_siswa = 0

    def _insert(nisn, nama, kelas="", no_wa="", nis=""):
        nonlocal added_siswa
        nisn = str(nisn or "").strip()
        nama = str(nama or "").strip()
        if not nisn or not nama or nisn in seen:
            return
        seen.add(nisn)
        try:
            db.execute(
                """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, status, kode)
                   VALUES (?,?,?,?,?,?,?)""",
                (nis, nisn, nama, kelas, no_wa, "aktif", gen_kode(nisn)),
            )
            added_siswa += 1
        except sqlite3.IntegrityError:
            pass

    m = re.search(r"INSERT INTO `siswa`.*?VALUES\s*(.*?);", sql, re.S)
    if m:
        for v in _parse_block(m.group(1)):
            # id,nis,nisn,nama,kelas,status,no_wa,rfid_uid,foto
            _insert(v[2], v[3], str(v[4] or ""), str(v[6] or ""), str(v[1] or ""))

    m = re.search(r"INSERT INTO `users`.*?VALUES\s*(.*?);", sql, re.S)
    if m:
        for v in _parse_block(m.group(1)):
            # id,username,password,nama,role
            if len(v) >= 5 and str(v[4] or "").lower() == "siswa":
                # username = NISN, nama = nama siswa
                _insert(v[1], v[3])
    db.commit()
    return jsonify({"ok": True, "siswa": added_siswa, "profil": added_profil})


# ---------- Kartu ----------
@app.route("/kartu/<int:siswa_id>")
def kartu(siswa_id):
    db = get_db()
    s = db.execute("SELECT * FROM siswa WHERE id=?", (siswa_id,)).fetchone()
    p = db.execute("SELECT * FROM profil_sekolah WHERE id=1").fetchone()
    if not s:
        abort(404)
    return render_template("kartu.html", s=dict(s), p=dict(p) if p else {})


@app.route("/api/qr/<int:siswa_id>")
def qr(siswa_id):
    db = get_db()
    s = db.execute("SELECT * FROM siswa WHERE id=?", (siswa_id,)).fetchone()
    if not s:
        abort(404)
    payload = s["kode"]   # encode kode langsung (ABS-xxx) → scanner resolve fleksibel
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/barcode/<int:siswa_id>")
def bar(siswa_id):
    db = get_db()
    s = db.execute("SELECT * FROM siswa WHERE id=?", (siswa_id,)).fetchone()
    if not s:
        abort(404)
    opts = {"module_height": 12.0, "font_size": 12, "text_distance": 4, "quiet_zone": 4}
    rv = io.BytesIO()
    code128 = barcode.get_barcode_class("code128")
    code128(s["kode"], writer=ImageWriter()).write(rv, options=opts)
    rv.seek(0)
    return send_file(rv, mimetype="image/png")


# ---------- Scanner / log ----------
@app.route("/scanner")
def scanner():
    return render_template("scanner.html")


def resolve_siswa(kode_raw):
    """Terima berbagai format hasil scan & kembalikan row siswa.
    Format: ABS-123, 123 (angka→ABS-123), atau URL kartu https://x/kartu/ID.
    """
    k = (kode_raw or "").strip()
    db = get_db()
    # 1) URL kartu → ambil id
    m = re.search(r"/kartu/(\d+)", k)
    if m:
        row = db.execute("SELECT * FROM siswa WHERE id=?", (int(m.group(1)),)).fetchone()
        return dict(row) if row else None
    # 2) angka doang → ABS-xxx
    if re.fullmatch(r"\d+", k):
        k = "ABS-" + k
    else:
        k = k.upper()
    # 3) kode langsung
    row = db.execute("SELECT * FROM siswa WHERE kode=?", (k,)).fetchone()
    return dict(row) if row else None


def now_wib():
    """Waktu lokal WIB (+7) tanpa dependensi tzdata."""
    return (dt.datetime.utcnow() + dt.timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")


def sudah_absen_hari_ini(siswa_id, jenis, tanggal):
    db = get_db()
    c = db.execute(
        "SELECT COUNT(*) AS n FROM absensi WHERE siswa_id=? AND jenis=? AND substr(waktu,1,10)=?",
        (siswa_id, jenis, tanggal),
    ).fetchone()
    return c["n"] > 0


@app.route("/api/log", methods=["POST"])
def log_absen():
    d = request.get_json(force=True, silent=True) or {}
    kode = (d.get("kode") or "").strip()
    jenis = (d.get("jenis") or "").strip().lower()
    ket = (d.get("keterangan") or "").strip()
    if not kode or jenis not in JENIS_VALID:
        return jsonify({"ok": False, "msg": "kode & jenis tidak valid"}), 400
    s = resolve_siswa(kode)
    if not s:
        return jsonify({"ok": False, "msg": f"kode '{kode}' tidak terdaftar"}), 404
    if str(s.get("status") or "aktif").lower() != "aktif":
        return jsonify({"ok": False, "msg": f"{s['nama']} status non-aktif, hubungi admin"}), 403
    # Anti fraud: 1 siswa 1x per jenis per hari
    now = now_wib()
    tanggal = now[:10]
    if sudah_absen_hari_ini(s["id"], jenis, tanggal):
        return jsonify({"ok": False, "sudah": True,
                        "msg": f"{s['nama']} sudah absen {jenis} hari ini",
                        "nama": s["nama"], "kelas": s.get("kelas") or "",
                        "nisn": s.get("nisn") or "", "foto": s.get("foto") or "",
                        "jenis": jenis, "waktu": now})
    db = get_db()
    db.execute(
        "INSERT INTO absensi (siswa_id, jenis, waktu, keterangan) VALUES (?,?,?,?)",
        (s["id"], jenis, now, ket),
    )
    db.commit()
    return jsonify({"ok": True, "nama": s["nama"], "kelas": s.get("kelas") or "",
                    "nisn": s.get("nisn") or "", "kode": s["kode"],
                    "foto": s.get("foto") or "",
                    "jenis": jenis, "waktu": now})


@app.route("/api/logs")
def logs():
    db = get_db()
    jenis = request.args.get("jenis")
    limit = int(request.args.get("limit", 100))
    q = "SELECT a.*, s.nama, s.kelas, s.nis, s.nisn FROM absensi a JOIN siswa s ON s.id=a.siswa_id"
    params = []
    if jenis in JENIS_VALID:
        q += " WHERE a.jenis=? "
        params.append(jenis)
    q += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)
    rows = db.execute(q, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------- Export ----------
def _rows_csv(jenis=None):
    db = get_db()
    q = "SELECT a.waktu, s.nisn, s.nis, s.nama, s.kelas, a.jenis, a.keterangan FROM absensi a JOIN siswa s ON s.id=a.siswa_id"
    params = []
    if jenis in JENIS_VALID:
        q += " WHERE a.jenis=? "
        params.append(jenis)
    q += " ORDER BY a.id DESC"
    return db.execute(q, params).fetchall()


@app.route("/api/export/csv")
def export_csv():
    jenis = request.args.get("jenis")
    rows = _rows_csv(jenis)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["waktu", "nisn", "nis", "nama", "kelas", "jenis", "keterangan"])
    for r in rows:
        w.writerow([r["waktu"], r["nisn"], r["nis"], r["nama"], r["kelas"], r["jenis"], r["keterangan"]])
    buf = io.BytesIO()
    buf.write(out.getvalue().encode("utf-8-sig"))
    buf.seek(0)
    name = f"absensi_{jenis or 'semua'}_{dt.date.today()}.csv"
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=name)


@app.route("/api/export/sheets", methods=["POST"])
def export_sheets():
    """Kirim baris terbaru ke Google Sheets via Apps Script doPost webhook.
    Butuh env SHEETS_WEBHOOK = URL Apps Script."""
    if not SHEETS_WEBHOOK:
        return jsonify({"ok": False, "msg": "SHEETS_WEBHOOK belum di-set (buat Apps Script doPost)."}), 400
    rows = _rows_csv((request.get_json(force=True, silent=True) or {}).get("jenis"))
    import urllib.request
    payload = json.dumps({"rows": [dict(r) for r in rows]}).encode()
    req = urllib.request.Request(SHEETS_WEBHOOK, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return jsonify({"ok": True, "http": resp.status, "count": len(rows)})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 502


# ---------- Pages ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ---------- Foto siswa ----------
UPLOAD_DIR = os.path.join(BASE, "data", "foto")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/api/siswa/<int:siswa_id>/foto", methods=["POST"])
def upload_foto(siswa_id):
    db = get_db()
    s = db.execute("SELECT id FROM siswa WHERE id=?", (siswa_id,)).fetchone()
    if not s:
        return jsonify({"ok": False, "msg": "siswa tidak ada"}), 404
    f = request.files.get("file")
    if not f:
        return jsonify({"ok": False, "msg": "file kosong"}), 400
    ext = "jpg"
    fn = f"{siswa_id}.{ext}"
    path = os.path.join(UPLOAD_DIR, fn)
    f.save(path)
    url = f"/foto/{fn}"
    db.execute("UPDATE siswa SET foto=? WHERE id=?", (url, siswa_id))
    db.commit()
    return jsonify({"ok": True, "url": url})


@app.route("/foto/<path:fn>")
def serve_foto(fn):
    return send_from_directory(UPLOAD_DIR, fn)


# ---------- PWA ----------
@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(BASE, "static/manifest.webmanifest",
                               mimetype="application/manifest+json")


@app.route("/sw.js")
def sw():
    return send_from_directory(BASE, "static/sw.js", mimetype="application/javascript")


if __name__ == "__main__":
    import ssl
    port = int(os.environ.get("PORT", 5000))
    # Di Render, TLS ditangani edge (RENDER env ada) → jalan HTTP biasa.
    # Lokal: pakai self-signed kalau ada sertifikat.
    use_ssl = os.environ.get("RENDER") is None
    ctx = None
    if use_ssl:
        key = os.path.join(BASE, "data", "key.pem")
        cert = os.path.join(BASE, "data", "cert.pem")
        if os.path.exists(key) and os.path.exists(cert):
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(cert, key)
            print("HTTPS lokal aktif (self-signed): https://0.0.0.0:5443")
    app.run(host="0.0.0.0", port=port, debug=(ctx is None), ssl_context=ctx)
