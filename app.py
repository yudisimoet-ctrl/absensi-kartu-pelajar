"""
Kartu Pelajar Digital + Absensi (WebApp) — v3
Fitur: kartu digital (QR + barcode 1D), scanner kamera, log absen
3 tipe: harian, solat, perpustakaan. Profil sekolah. Migrasi dari SQL lama.
Bulk import CSV. Export CSV + sinkron Google Sheets/Drive (via Apps Script webhook).
PWA: installable + cache kartu offline.
DB: SQLite (local) or PostgreSQL (production via DATABASE_URL).
"""
import io
import os
import re
import csv
import ast
import json
import hashlib
import datetime as dt

from functools import wraps
from flask import (Flask, request, jsonify, render_template,
                   send_file, send_from_directory, g, abort,
                   session, redirect, url_for)
import qrcode
import barcode
from barcode.writer import ImageWriter

import db as _db

BASE = os.path.dirname(os.path.abspath(__file__))

# Konfigurasi sinkron eksternal (isi di .env / env var)
SHEETS_WEBHOOK = os.environ.get("SHEETS_WEBHOOK", "")   # Apps Script doPost URL
DRIVE_WEBHOOK = os.environ.get("DRIVE_WEBHOOK", "")     # Apps Script upload CSV

JENIS_VALID = ["harian", "solat", "perpus"]

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "absensi-secret-key-change-me")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")
GURU_USER = os.environ.get("GURU_USER", "guru")
GURU_PASS = os.environ.get("GURU_PASS", "guru123")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "msg": "unauthorized"}), 401
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


def guru_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("guru_id"):
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "msg": "unauthorized"}), 401
            return redirect(url_for("scanner_login"))
        return f(*args, **kwargs)
    return decorated


def get_db():
    conn = getattr(g, "_db", None)
    if conn is None:
        conn = g._db = _db.connect()
    return conn


@app.teardown_appcontext
def close_db(exc):
    conn = getattr(g, "_db", None)
    if conn is not None:
        conn.close()


# ---------- Init DB ----------
def init_db():
    conn = _db.connect()
    cur = conn.cursor()

    if _db.IS_PG:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS profil_sekolah (
                id INTEGER PRIMARY KEY,
                nama_sekolah TEXT,
                alamat TEXT,
                kepala_sekolah TEXT,
                logo TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS siswa (
                id SERIAL PRIMARY KEY,
                nis TEXT,
                nisn TEXT,
                nama TEXT NOT NULL,
                kelas TEXT,
                no_wa TEXT,
                rfid_uid TEXT,
                foto TEXT,
                status TEXT DEFAULT 'aktif',
                kode TEXT UNIQUE NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS absensi (
                id SERIAL PRIMARY KEY,
                siswa_id INTEGER NOT NULL REFERENCES siswa(id),
                jenis TEXT NOT NULL,
                waktu TIMESTAMPTZ DEFAULT NOW(),
                keterangan TEXT,
                guru_id INTEGER REFERENCES guru(id)
            );
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_absensi_siswa ON absensi(siswa_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_absensi_waktu ON absensi(waktu);")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS guru (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nama TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()

        # Seed profil sekolah
        cur.execute("INSERT INTO profil_sekolah (id) VALUES (1) ON CONFLICT DO NOTHING")
        conn.commit()
    else:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profil_sekolah (
                id INTEGER PRIMARY KEY CHECK (id=1),
                nama_sekolah TEXT,
                alamat TEXT,
                kepala_sekolah TEXT,
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
            CREATE TABLE IF NOT EXISTS guru (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nama TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        # Migrasi: buang kolom jam_masuk/jam_pulang kalau masih ada
        cols = [r[1] for r in conn.execute("PRAGMA table_info(profil_sekolah)")]
        if "jam_masuk" in cols or "jam_pulang" in cols:
            conn.executescript("""CREATE TABLE profil_sekolah_new (
                id INTEGER PRIMARY KEY CHECK (id=1),
                nama_sekolah TEXT, alamat TEXT, kepala_sekolah TEXT, logo TEXT);
                INSERT INTO profil_sekolah_new (id,nama_sekolah,alamat,kepala_sekolah,logo)
                    SELECT id,nama_sekolah,alamat,kepala_sekolah,logo FROM profil_sekolah;
                DROP TABLE profil_sekolah;
                ALTER TABLE profil_sekolah_new RENAME TO profil_sekolah;
            """)
        conn.execute("INSERT OR IGNORE INTO profil_sekolah (id) VALUES (1)")
        # Migrasi: tambah kolom guru_id di absensi kalau belum ada
        abs_cols = [r[1] for r in conn.execute("PRAGMA table_info(absensi)")]
        if "guru_id" not in abs_cols:
            conn.execute("ALTER TABLE absensi ADD COLUMN guru_id INTEGER REFERENCES guru(id)")
        conn.commit()

    # Seed default guru kalau tabel kosong
    n = _db.fetchone(cur if _db.IS_PG else conn.execute("SELECT COUNT(*) AS n FROM guru"))
    if n and n["n"] == 0:
        default_pw = hashlib.sha256("guru123".encode()).hexdigest()
        cur2 = conn.cursor() if _db.IS_PG else conn
        cur2.execute(_db.adapt("INSERT INTO guru (username, password, nama) VALUES (?, ?, ?)"),
                     ("guru", default_pw, "Guru Default"))
        conn.commit()

    conn.close()


init_db()


def gen_kode(nisn):
    return f"ABS-{nisn or ''}"


# ---------- Profil ----------
@app.route("/api/profil", methods=["GET", "POST"])
def profil():
    conn = get_db()
    if request.method == "POST":
        if not session.get("admin_logged"):
            return jsonify({"ok": False, "msg": "unauthorized"}), 401
        d = request.get_json(force=True, silent=True) or {}
        cols = ["nama_sekolah", "alamat", "kepala_sekolah", "logo"]
        sets = {c: d.get(c) for c in cols}
        _db.run(conn,
            """INSERT INTO profil_sekolah (id, nama_sekolah, alamat, kepala_sekolah, logo)
               VALUES (1,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 nama_sekolah=excluded.nama_sekolah, alamat=excluded.alamat,
                 kepala_sekolah=excluded.kepala_sekolah, logo=excluded.logo""",
            tuple(sets.values()),
        )
        conn.commit()
    row = _db.fetchone(_db.run(conn, "SELECT * FROM profil_sekolah WHERE id=1"))
    res = row or {}
    if request.method == "POST":
        res = {"ok": True, **res}
    return jsonify(res)


# ---------- Siswa ----------
@app.route("/api/siswa", methods=["POST"])
@admin_required
def add_siswa():
    d = request.get_json(force=True, silent=True) or {}
    nisn = (d.get("nisn") or d.get("nis") or "").strip()
    nama = (d.get("nama") or "").strip()
    if not nisn or not nama:
        return jsonify({"ok": False, "msg": "nisn & nama wajib"}), 400
    kode = gen_kode(nisn)
    conn = get_db()
    try:
        sid = _db.insert_returning(conn,
            """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, rfid_uid, foto, status, kode)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (d.get("nis", ""), nisn, nama, d.get("kelas", ""), d.get("no_wa", ""),
             d.get("rfid_uid", ""), d.get("foto", ""), d.get("status", "aktif"), kode),
        )
        conn.commit()
    except _db.IntegrityError:
        return jsonify({"ok": False, "msg": "NISN sudah ada"}), 409
    return jsonify({"ok": True, "id": sid, "kode": kode})


@app.route("/api/siswa", methods=["GET"])
def list_siswa():
    conn = get_db()
    rows = _db.fetchall(_db.run(conn, "SELECT * FROM siswa ORDER BY id DESC"))
    return jsonify(rows)


@app.route("/api/siswa/<int:siswa_id>", methods=["GET"])
def get_siswa(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (siswa_id,)))
    if not s:
        return jsonify({"ok": False, "msg": "siswa tidak ada"}), 404
    return jsonify(s)


@app.route("/api/siswa/<int:siswa_id>", methods=["PUT"])
@admin_required
def edit_siswa(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (siswa_id,)))
    if not s:
        return jsonify({"ok": False, "msg": "siswa tidak ada"}), 404
    d = request.get_json(force=True, silent=True) or {}
    nis = (d.get("nis") or "").strip()
    nisn = (d.get("nisn") or "").strip()
    nama = (d.get("nama") or "").strip()
    kelas = (d.get("kelas") or "").strip()
    no_wa = (d.get("no_wa") or "").strip()
    status = (d.get("status") or "aktif").strip()
    if not nisn or not nama:
        return jsonify({"ok": False, "msg": "nisn & nama wajib"}), 400
    kode = gen_kode(nisn)
    try:
        _db.run(conn,
            """UPDATE siswa SET nis=?, nisn=?, nama=?, kelas=?, no_wa=?, status=?, kode=?
               WHERE id=?""",
            (nis, nisn, nama, kelas, no_wa, status, kode, siswa_id),
        )
        conn.commit()
    except _db.IntegrityError:
        return jsonify({"ok": False, "msg": "NISN sudah dipakai siswa lain"}), 409
    return jsonify({"ok": True, "msg": f"Data {nama} diupdate"})


@app.route("/api/siswa/<int:siswa_id>", methods=["DELETE"])
@admin_required
def del_siswa(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (siswa_id,)))
    if not s:
        return jsonify({"ok": False, "msg": "siswa tidak ada"}), 404
    foto = s.get("foto") or ""
    if foto.startswith("/foto/"):
        try:
            os.remove(os.path.join(UPLOAD_DIR, os.path.basename(foto)))
        except OSError:
            pass
    _db.run(conn, "DELETE FROM absensi WHERE siswa_id=?", (siswa_id,))
    _db.run(conn, "DELETE FROM siswa WHERE id=?", (siswa_id,))
    conn.commit()
    return jsonify({"ok": True, "msg": f"siswa {siswa_id} dihapus"})


@app.route("/api/siswa/bulk", methods=["POST"])
@admin_required
def bulk_siswa():
    """Terima JSON array atau file CSV (multipart, field 'file')."""
    conn = get_db()
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
                _db.run(conn,
                    """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, rfid_uid, foto, status, kode)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (r.get("nis", ""), nisn, nama, r.get("kelas", ""), r.get("no_wa", ""),
                     r.get("rfid_uid", ""), r.get("foto", ""), r.get("status", "aktif"), gen_kode(nisn)),
                )
                added += 1
            except _db.IntegrityError:
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
                _db.run(conn,
                    """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, rfid_uid, foto, status, kode)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (d.get("nis", ""), nisn, nama, d.get("kelas", ""), d.get("no_wa", ""),
                     d.get("rfid_uid", ""), d.get("foto", ""), d.get("status", "aktif"), gen_kode(nisn)),
                )
                added += 1
            except _db.IntegrityError:
                skipped += 1
    conn.commit()
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
@admin_required
def migrate():
    path = request.get_json(force=True, silent=True) or {}
    sql_path = path.get("path") or os.path.join(BASE, "drive_import", "db-absensi-qr-v5-39-ok.sql")
    if not os.path.exists(sql_path):
        sql_path = os.path.join(BASE, "data_seed", "db-absensi-qr-v5-39-ok.sql")
    if not os.path.exists(sql_path):
        return jsonify({"ok": False, "msg": f"file tidak ada: {sql_path}"}), 404
    with open(sql_path, encoding="utf-8") as f:
        sql = f.read()

    conn = get_db()
    added_profil = False

    m = re.search(r"INSERT INTO `profil_sekolah`.*?VALUES\s*\((.*?)\);", sql, re.S)
    if m:
        vals = ast.literal_eval("(" + m.group(1) + ")")
        _db.run(conn,
            """INSERT INTO profil_sekolah (id, nama_sekolah, alamat, kepala_sekolah, logo)
               VALUES (1,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 nama_sekolah=excluded.nama_sekolah, alamat=excluded.alamat,
                 kepala_sekolah=excluded.kepala_sekolah, logo=excluded.logo""",
            (vals[1], vals[2], vals[3], vals[5]),
        )
        added_profil = True

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
            _db.run(conn,
                """INSERT INTO siswa (nis, nisn, nama, kelas, no_wa, status, kode)
                   VALUES (?,?,?,?,?,?,?)""",
                (nis, nisn, nama, kelas, no_wa, "aktif", gen_kode(nisn)),
            )
            added_siswa += 1
        except _db.IntegrityError:
            pass

    m = re.search(r"INSERT INTO `siswa`.*?VALUES\s*(.*?);", sql, re.S)
    if m:
        for v in _parse_block(m.group(1)):
            _insert(v[2], v[3], str(v[4] or ""), str(v[6] or ""), str(v[1] or ""))

    m = re.search(r"INSERT INTO `users`.*?VALUES\s*(.*?);", sql, re.S)
    if m:
        for v in _parse_block(m.group(1)):
            if len(v) >= 5 and str(v[4] or "").lower() == "siswa":
                _insert(v[1], v[3])
    conn.commit()
    return jsonify({"ok": True, "siswa": added_siswa, "profil": added_profil})


# ---------- Kartu ----------
@app.route("/kartu/<int:siswa_id>")
def kartu(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (siswa_id,)))
    p = _db.fetchone(_db.run(conn, "SELECT * FROM profil_sekolah WHERE id=1"))
    if not s:
        abort(404)
    return render_template("kartu.html", s=s, p=p or {})


@app.route("/api/qr/<int:siswa_id>")
def qr(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (siswa_id,)))
    if not s:
        abort(404)
    payload = s["kode"]
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/barcode/<int:siswa_id>")
def bar(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (siswa_id,)))
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
@guru_required
def scanner():
    return render_template("scanner.html")


@app.route("/scanner/login", methods=["GET", "POST"])
def scanner_login():
    err = None
    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        pw_hash = hashlib.sha256(p.encode()).hexdigest()
        conn = _db.connect()
        row = _db.fetchone(
            _db.run(conn, "SELECT * FROM guru WHERE username=? AND password=?", (u, pw_hash))
        )
        conn.close()
        if row:
            session["guru_id"] = row["id"]
            session["guru_nama"] = row["nama"]
            return redirect(url_for("scanner"))
        err = "Username atau password salah"
    return render_template("login_guru.html", error=err)


@app.route("/scanner/logout")
def scanner_logout():
    session.pop("guru_id", None)
    session.pop("guru_nama", None)
    return redirect(url_for("scanner_login"))


# ---------- Guru CRUD ----------
@app.route("/api/guru", methods=["GET"])
@admin_required
def list_guru():
    conn = get_db()
    rows = _db.fetchall(_db.run(conn, "SELECT id, username, nama, created_at FROM guru ORDER BY id"))
    return jsonify(rows)


@app.route("/api/guru", methods=["POST"])
@admin_required
def add_guru():
    d = request.get_json(force=True, silent=True) or {}
    username = (d.get("username") or "").strip()
    password = (d.get("password") or "").strip()
    nama = (d.get("nama") or "").strip()
    if not username or not password or not nama:
        return jsonify({"ok": False, "msg": "username, password, nama wajib diisi"}), 400
    if len(password) < 4:
        return jsonify({"ok": False, "msg": "password min 4 karakter"}), 400
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    conn = get_db()
    try:
        _db.run(conn, "INSERT INTO guru (username, password, nama) VALUES (?,?,?)",
                (username, pw_hash, nama))
        conn.commit()
    except _db.IntegrityError:
        return jsonify({"ok": False, "msg": "username sudah dipakai"}), 409
    return jsonify({"ok": True, "msg": f"Guru '{nama}' ditambahkan"})


@app.route("/api/guru/<int:guru_id>", methods=["PUT"])
@admin_required
def edit_guru(guru_id):
    conn = get_db()
    g = _db.fetchone(_db.run(conn, "SELECT * FROM guru WHERE id=?", (guru_id,)))
    if not g:
        return jsonify({"ok": False, "msg": "guru tidak ada"}), 404
    d = request.get_json(force=True, silent=True) or {}
    username = (d.get("username") or "").strip()
    nama = (d.get("nama") or "").strip()
    if not username or not nama:
        return jsonify({"ok": False, "msg": "username & nama wajib"}), 400
    try:
        _db.run(conn, "UPDATE guru SET username=?, nama=? WHERE id=?",
                (username, nama, guru_id))
        conn.commit()
    except _db.IntegrityError:
        return jsonify({"ok": False, "msg": "username sudah dipakai"}), 409
    return jsonify({"ok": True, "msg": f"Guru '{nama}' diupdate"})


@app.route("/api/guru/<int:guru_id>", methods=["DELETE"])
@admin_required
def del_guru(guru_id):
    conn = get_db()
    g = _db.fetchone(_db.run(conn, "SELECT * FROM guru WHERE id=?", (guru_id,)))
    if not g:
        return jsonify({"ok": False, "msg": "guru tidak ada"}), 404
    _db.run(conn, "DELETE FROM guru WHERE id=?", (guru_id,))
    conn.commit()
    return jsonify({"ok": True, "msg": f"Guru '{g['nama']}' dihapus"})


@app.route("/api/guru/<int:guru_id>/reset", methods=["POST"])
@admin_required
def reset_pw_guru(guru_id):
    d = request.get_json(force=True, silent=True) or {}
    new_pw = (d.get("password") or "").strip()
    if len(new_pw) < 4:
        return jsonify({"ok": False, "msg": "password min 4 karakter"}), 400
    conn = get_db()
    g = _db.fetchone(_db.run(conn, "SELECT * FROM guru WHERE id=?", (guru_id,)))
    if not g:
        return jsonify({"ok": False, "msg": "guru tidak ada"}), 404
    pw_hash = hashlib.sha256(new_pw.encode()).hexdigest()
    _db.run(conn, "UPDATE guru SET password=? WHERE id=?", (pw_hash, guru_id))
    conn.commit()
    return jsonify({"ok": True, "msg": f"Password guru '{g['nama']}' direset"})


def resolve_siswa(kode_raw):
    """Terima berbagai format hasil scan & kembalikan row siswa."""
    k = (kode_raw or "").strip()
    conn = get_db()
    m = re.search(r"/kartu/(\d+)", k)
    if m:
        return _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE id=?", (int(m.group(1)),)))
    if re.fullmatch(r"\d+", k):
        k = "ABS-" + k
    else:
        k = k.upper()
    return _db.fetchone(_db.run(conn, "SELECT * FROM siswa WHERE kode=?", (k,)))


def now_wib():
    """Waktu lokal WIB (+7) tanpa dependensi tzdata."""
    return (dt.datetime.utcnow() + dt.timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")


def sudah_absen_hari_ini(siswa_id, jenis, tanggal):
    conn = get_db()
    c = _db.fetchone(_db.run(conn,
        "SELECT COUNT(*) AS n FROM absensi WHERE siswa_id=? AND jenis=? AND substr(waktu,1,10)=?",
        (siswa_id, jenis, tanggal),
    ))
    return (c["n"] if c else 0) > 0


@app.route("/api/log", methods=["POST"])
@guru_required
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
    now = now_wib()
    tanggal = now[:10]
    if sudah_absen_hari_ini(s["id"], jenis, tanggal):
        return jsonify({"ok": False, "sudah": True,
                        "msg": f"{s['nama']} sudah absen {jenis} hari ini",
                        "nama": s["nama"], "kelas": s.get("kelas") or "",
                        "nisn": s.get("nisn") or "", "foto": s.get("foto") or "",
                        "jenis": jenis, "waktu": now})
    conn = get_db()
    guru_id = session.get("guru_id")
    _db.run(conn,
        "INSERT INTO absensi (siswa_id, jenis, waktu, keterangan, guru_id) VALUES (?,?,?,?,?)",
        (s["id"], jenis, now, ket, guru_id),
    )
    conn.commit()
    return jsonify({"ok": True, "nama": s["nama"], "kelas": s.get("kelas") or "",
                    "nisn": s.get("nisn") or "", "kode": s["kode"],
                    "foto": s.get("foto") or "",
                    "jenis": jenis, "waktu": now,
                    "guru": session.get("guru_nama", "")})


@app.route("/api/logs")
@admin_required
def logs():
    conn = get_db()
    jenis = request.args.get("jenis")
    limit = int(request.args.get("limit", 100))
    q = "SELECT a.*, s.nama, s.kelas, s.nis, s.nisn, g.nama as guru_nama FROM absensi a JOIN siswa s ON s.id=a.siswa_id LEFT JOIN guru g ON g.id=a.guru_id"
    params = []
    if jenis in JENIS_VALID:
        q += " WHERE a.jenis=? "
        params.append(jenis)
    q += " ORDER BY a.id DESC LIMIT ?"
    params.append(limit)
    rows = _db.fetchall(_db.run(conn, q, params))
    return jsonify(rows)


# ---------- Export ----------
def _rows_csv(jenis=None):
    conn = get_db()
    q = "SELECT a.waktu, s.nisn, s.nis, s.nama, s.kelas, a.jenis, a.keterangan, g.nama as guru_nama FROM absensi a JOIN siswa s ON s.id=a.siswa_id LEFT JOIN guru g ON g.id=a.guru_id"
    params = []
    if jenis in JENIS_VALID:
        q += " WHERE a.jenis=? "
        params.append(jenis)
    q += " ORDER BY a.id DESC"
    return _db.fetchall(_db.run(conn, q, params))


@app.route("/api/export/csv")
@admin_required
def export_csv():
    jenis = request.args.get("jenis")
    rows = _rows_csv(jenis)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["waktu", "nisn", "nis", "nama", "kelas", "jenis", "keterangan", "guru"])
    for r in rows:
        w.writerow([r["waktu"], r["nisn"], r["nis"], r["nama"], r["kelas"], r["jenis"], r["keterangan"], r.get("guru_nama") or ""])
    buf = io.BytesIO()
    buf.write(out.getvalue().encode("utf-8-sig"))
    buf.seek(0)
    name = f"absensi_{jenis or 'semua'}_{dt.date.today()}.csv"
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=name)


@app.route("/api/export/sheets", methods=["POST"])
def export_sheets():
    """Kirim baris terbaru ke Google Sheets via Apps Script doPost webhook."""
    if not SHEETS_WEBHOOK:
        return jsonify({"ok": False, "msg": "SHEETS_WEBHOOK belum di-set (buat Apps Script doPost)."}), 400
    rows = _rows_csv((request.get_json(force=True, silent=True) or {}).get("jenis"))
    import urllib.request
    payload = json.dumps({"rows": rows}).encode()
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
    return redirect(url_for("scanner_login"))


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    err = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin_logged"] = True
            return redirect(url_for("admin"))
        err = "Username atau password salah"
    return render_template("login.html", error=err)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged", None)
    return redirect(url_for("admin_login"))


# ---------- Foto siswa ----------
UPLOAD_DIR = os.path.join(BASE, "data", "foto")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.route("/api/siswa/<int:siswa_id>/foto", methods=["POST"])
@admin_required
def upload_foto(siswa_id):
    conn = get_db()
    s = _db.fetchone(_db.run(conn, "SELECT id FROM siswa WHERE id=?", (siswa_id,)))
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
    _db.run(conn, "UPDATE siswa SET foto=? WHERE id=?", (url, siswa_id))
    conn.commit()
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
