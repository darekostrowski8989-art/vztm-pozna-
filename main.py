
from flask import Flask, request, redirect, session, render_template_string, url_for, abort
from werkzeug.security import generate_password_hash, check_password_hash
from markupsafe import Markup
from pathlib import Path
from functools import wraps
import sqlite3
import secrets
import os

app = Flask(__name__)
app.secret_key = os.environ.get("VZTM_SECRET_KEY", secrets.token_hex(32))
DB = Path(__file__).with_name("vztm.db")


# =====================================================
# BAZA DANYCH
# =====================================================

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Pracownik'
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                created TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                date TEXT NOT NULL,
                duty TEXT NOT NULL,
                details TEXT DEFAULT ''
            )
        """)

        admin = db.execute(
            "SELECT id FROM users WHERE username = 'admin'"
        ).fetchone()

        if not admin:
            db.execute(
                "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                (
                    "admin",
                    generate_password_hash("VztmPoznan2026!"),
                    "Administrator"
                )
            )

        count = db.execute(
            "SELECT COUNT(*) FROM announcements"
        ).fetchone()[0]

        if count == 0:
            db.execute(
                "INSERT INTO announcements(title,content) VALUES(?,?)",
                (
                    "Witamy na stronie VZTM POZNAŃ",
                    "Uruchomiliśmy nową stronę internetową naszego "
                    "wirtualnego przedsiębiorstwa. Zapraszamy do "
                    "zapoznania się z aktualnościami i systemem pracowniczym."
                )
            )


# =====================================================
# ZABEZPIECZENIA I LOGOWANIE
# =====================================================

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(24)
    return session["csrf"]


@app.context_processor
def inject_csrf():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_forms():
    if request.method == "POST":
        sent = request.form.get("csrf", "")
        saved = session.get("csrf", "")
        if not saved or not secrets.compare_digest(sent, saved):
            abort(400, "Nieprawidłowy token formularza.")


def logged_in():
    return "username" in session


def admin_only():
    return session.get("role") == "Administrator"


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        if not admin_only():
            abort(403)
        return func(*args, **kwargs)
    return wrapper


# =====================================================
# WYGLĄD STRONY
# =====================================================

BASE = """
<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | VZTM POZNAŃ</title>
<style>
:root {
    --navy: #102d50;
    --blue: #1d527e;
    --gold: #e4bd50;
    --text: #25364a;
    --muted: #718096;
    --bg: #f3f5f8;
    --border: #e5eaf0;
}
* { box-sizing: border-box; }
body {
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background: var(--bg);
    color: var(--text);
}
a { text-decoration: none; color: inherit; }
.topbar {
    min-height: 76px;
    background: var(--navy);
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 7%;
    gap: 20px;
}
.brand {
    font-size: 25px;
    font-weight: 800;
    letter-spacing: 1px;
    white-space: nowrap;
}
.brand span { color: var(--gold); }
.nav {
    display: flex;
    gap: 23px;
    align-items: center;
    flex-wrap: wrap;
}
.nav a {
    color: #e5edf5;
    font-size: 14px;
}
.nav a:hover { color: var(--gold); }
.nav .nav-button {
    background: var(--gold);
    color: var(--navy);
    padding: 11px 17px;
    border-radius: 4px;
    font-weight: bold;
}
.hero {
    background: linear-gradient(115deg, #102d50, #1d527e);
    color: white;
    padding: 90px 8%;
}
.hero-inner { max-width: 1100px; margin: auto; }
.eyebrow {
    color: var(--gold);
    font-weight: bold;
    letter-spacing: 2px;
    font-size: 12px;
    text-transform: uppercase;
}
.hero h1 {
    font-size: clamp(36px, 6vw, 58px);
    margin: 18px 0;
}
.hero p {
    max-width: 680px;
    color: #dce7f1;
    line-height: 1.8;
    font-size: 17px;
}
.button {
    display: inline-block;
    border: 0;
    border-radius: 4px;
    background: var(--gold);
    color: var(--navy);
    padding: 13px 21px;
    font-weight: bold;
    cursor: pointer;
    font-size: 14px;
}
.button-blue {
    background: var(--navy);
    color: white;
}
.button:hover { opacity: .9; }
.wrap {
    width: min(1120px, 92%);
    margin: 42px auto;
}
.section-head {
    display: flex;
    justify-content: space-between;
    align-items: end;
    gap: 20px;
    margin-bottom: 22px;
}
h2 {
    color: var(--navy);
    margin: 0 0 10px;
    font-size: 27px;
}
.muted { color: var(--muted); line-height: 1.7; }
.grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(235px, 1fr));
    gap: 19px;
}
.card {
    background: white;
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 23px;
    box-shadow: 0 3px 12px #102d5008;
}
.card h3 { color: var(--navy); margin: 0 0 12px; }
.card p { color: var(--muted); line-height: 1.7; font-size: 14px; }
.card-link {
    display: inline-block;
    color: var(--blue);
    font-weight: bold;
    font-size: 14px;
    margin-top: 12px;
}
.news-card { border-left: 4px solid var(--gold); }
.news-date { font-size: 12px; color: var(--muted); margin-top: 14px; }
.banner {
    background: #e8eef5;
    padding: 35px 20px;
    text-align: center;
}
.footer {
    background: var(--navy);
    color: #dce7f1;
    padding: 30px 7%;
    text-align: center;
    font-size: 13px;
    line-height: 1.8;
    margin-top: 55px;
}
.login-area {
    width: min(440px, 92%);
    margin: 65px auto;
}
.login-box {
    background: white;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 34px;
    box-shadow: 0 8px 30px #102d5010;
}
.login-box h1 { color: var(--navy); margin: 0 0 10px; }
label {
    display: block;
    font-weight: bold;
    font-size: 13px;
    margin: 19px 0 8px;
}
input, textarea, select {
    width: 100%;
    padding: 13px;
    border: 1px solid #d6dee8;
    border-radius: 4px;
    font-size: 14px;
    font-family: inherit;
    background: white;
}
textarea { min-height: 120px; resize: vertical; }
input:focus, textarea:focus, select:focus {
    outline: 2px solid #9bbbd8;
    border-color: var(--blue);
}
.full { width: 100%; margin-top: 22px; }
.notice {
    background: #edf4fa;
    color: var(--navy);
    padding: 13px 16px;
    border-radius: 4px;
    margin: 16px 0;
}
.error { background: #fff0f0; color: #9b2929; }
.success { background: #eaf7ee; color: #236b3d; }
.dashboard {
    display: grid;
    grid-template-columns: 245px minmax(0, 1fr);
    min-height: 680px;
}
.sidebar {
    background: var(--navy);
    color: white;
    padding: 27px 17px;
}
.side-title {
    color: #aebfd2;
    font-size: 11px;
    letter-spacing: 1px;
    padding: 0 12px;
    margin: 8px 0 17px;
}
.sidebar a {
    display: block;
    color: #e1eaf3;
    padding: 13px 12px;
    border-radius: 4px;
    font-size: 14px;
    margin: 4px 0;
}
.sidebar a:hover { background: #1d527e; }
.dash-main { padding: 34px; min-width: 0; }
.welcome {
    background: linear-gradient(110deg, #173e65, #28628d);
    color: white;
    border-radius: 7px;
    padding: 28px;
    margin-bottom: 26px;
}
.welcome h1 { margin: 0 0 9px; font-size: 27px; }
.welcome p { color: #dce7f1; margin: 0; }
.stat { font-size: 30px; font-weight: bold; color: var(--navy); }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: white; }
th, td {
    padding: 13px;
    border-bottom: 1px solid var(--border);
    text-align: left;
    font-size: 14px;
}
th { background: #edf2f7; color: var(--navy); }
form.inline { display: inline; }
@media(max-width:760px) {
    .topbar { align-items: flex-start; flex-direction: column; padding: 18px 5%; }
    .nav { gap: 14px; }
    .hero { padding: 60px 6%; }
    .dashboard { grid-template-columns: 1fr; }
    .sidebar { padding: 14px; }
    .sidebar a { display: inline-block; }
    .dash-main { padding: 20px; }
    .section-head { display: block; }
}
</style>
</head>
<body>
<header class="topbar">
    <a class="brand" href="/">VZTM <span>POZNAŃ</span></a>
    <nav class="nav">
        <a href="/">Strona główna</a>
        <a href="/ogloszenia">Ogłoszenia</a>
        <a href="/rozporzadzenia">Rozporządzenia</a>
        <a href="/faq">FAQ</a>
        {% if session.get('username') %}
            <a href="/panel">Panel pracownika</a>
            <a class="nav-button" href="/wyloguj">Wyloguj</a>
        {% else %}
            <a class="nav-button" href="/login">Logowanie</a>
        {% endif %}
    </nav>
</header>
{{ content }}
<footer class="footer">
    <b>VZTM POZNAŃ</b><br>
    Wirtualne przedsiębiorstwo komunikacyjne · Projekt społeczności OMSI 2<br>
    Serwis niezależny, niepowiązany z rzeczywistym ZTM Poznań.
</footer>
</body>
</html>
"""


def page(title, html):
    return render_template_string(
        BASE, title=title, content=Markup(html)
    )


# =====================================================
# STRONA GŁÓWNA
# =====================================================

@app.route("/")
def home():
    with connect() as db:
        news = db.execute(
            "SELECT * FROM announcements ORDER BY id DESC LIMIT 4"
        ).fetchall()

    return page("Strona główna", render_template_string("""
    <section class="hero">
      <div class="hero-inner">
        <div class="eyebrow">Wirtualne przedsiębiorstwo komunikacyjne</div>
        <h1>Witamy w VZTM POZNAŃ</h1>
        <p>
          Transport, organizacja i pasja do komunikacji miejskiej.
          Poznaj nasze wirtualne przedsiębiorstwo, sprawdź aktualności
          i dołącz do społeczności miłośników transportu publicznego.
        </p>
        <a class="button" href="/login">STREFA PRACOWNIKA</a>
      </div>
    </section>

    <main class="wrap">
      <div class="section-head">
        <div>
          <h2>Aktualności</h2>
          <p class="muted">Najnowsze informacje z życia przedsiębiorstwa.</p>
        </div>
        <a class="card-link" href="/ogloszenia">Wszystkie ogłoszenia →</a>
      </div>

      <div class="grid">
        {% for item in news %}
        <article class="card news-card">
          <h3>{{ item.title }}</h3>
          <p>{{ item.content }}</p>
          <div class="news-date">{{ item.created }}</div>
        </article>
        {% else %}
        <div class="card"><p>Nie opublikowano jeszcze aktualności.</p></div>
        {% endfor %}
      </div>
    </main>

    <section class="banner">
      <h2>Dołącz do naszego zespołu</h2>
      <p class="muted">Rozwijaj swoje zainteresowania transportem publicznym w OMSI 2.</p>
      <a class="button button-blue" href="/login">Strefa pracownika</a>
    </section>

    <main class="wrap">
      <h2>Nasze przedsiębiorstwo</h2>
      <p class="muted">
        VZTM POZNAŃ to niezależny projekt wirtualny stworzony
        dla pasjonatów komunikacji miejskiej. Organizujemy
        wirtualne służby, rozwijamy współpracę i tworzymy
        społeczność skupioną wokół symulatora OMSI 2.
      </p>
      <div class="grid" style="margin-top:24px">
        <div class="card"><h3>Organizacja</h3><p>Przejrzysta struktura i podział obowiązków.</p></div>
        <div class="card"><h3>Współpraca</h3><p>Wspólna realizacja służb i projektów.</p></div>
        <div class="card"><h3>Rozwój</h3><p>Możliwość zdobywania doświadczenia w wirtualnym przedsiębiorstwie.</p></div>
      </div>
    </main>
    """, news=news))


# =====================================================
# LOGOWANIE I WYLOGOWANIE
# =====================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with connect() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["csrf"] = secrets.token_hex(24)
            return redirect("/panel")

        error = "Nieprawidłowy login lub hasło."

    return page("Logowanie", render_template_string("""
    <main class="login-area">
      <div class="login-box">
        <div class="eyebrow">VZTM POZNAŃ · SYSTEM WEWNĘTRZNY</div>
        <h1>Logowanie</h1>
        <p class="muted">Zaloguj się do strefy pracownika.</p>
        {% if error %}
        <div class="notice error">{{ error }}</div>
        {% endif %}
        <form method="POST">
          <input type="hidden" name="csrf" value="{{ csrf_token() }}">
          <label>Login</label>
          <input name="username" required autocomplete="username"
                 placeholder="Wprowadź login">
          <label>Hasło</label>
          <input type="password" name="password" required
                 autocomplete="current-password" placeholder="Wprowadź hasło">
          <button class="button button-blue full" type="submit">ZALOGUJ SIĘ</button>
        </form>
        <p class="muted" style="font-size:12px;margin-top:20px">
          Dostęp do systemu mają wyłącznie upoważnieni użytkownicy.
        </p>
      </div>
    </main>
    """, error=error))


@app.route("/wyloguj")
def logout():
    session.clear()
    return redirect("/")


# =====================================================
# PANEL PRACOWNIKA
# =====================================================

@app.route("/panel")
@login_required
def panel():
    username = session["username"]

    with connect() as db:
        reports = db.execute(
            "SELECT COUNT(*) FROM reports WHERE username=?",
            (username,)
        ).fetchone()[0]

        complaints = db.execute(
            "SELECT COUNT(*) FROM complaints WHERE username=?",
            (username,)
        ).fetchone()[0]

        duties = db.execute(
            "SELECT * FROM schedules WHERE username=? ORDER BY date LIMIT 5",
            (username,)
        ).fetchall()

        news = db.execute(
            "SELECT * FROM announcements ORDER BY id DESC LIMIT 3"
        ).fetchall()

    return page("Panel pracownika", render_template_string("""
    <div class="dashboard">
      <aside class="sidebar">
        <div class="side-title">STREFA PRACOWNIKA</div>
        <a href="/panel">⌂ &nbsp; Pulpit</a>
        <a href="/grafik">▦ &nbsp; Grafik służb</a>
        <a href="/raporty">▤ &nbsp; Raporty</a>
        <a href="/skargi">✉ &nbsp; Skargi i wnioski</a>
        <a href="/ogloszenia">▣ &nbsp; Ogłoszenia</a>
        {% if session.get('role') == 'Administrator' %}
        <div class="side-title" style="margin-top:25px">ADMINISTRACJA</div>
        <a href="/admin/pracownicy">♙ &nbsp; Pracownicy</a>
        <a href="/admin/ogloszenia">✎ &nbsp; Zarządzaj ogłoszeniami</a>
        <a href="/admin/grafik">▦ &nbsp; Zarządzaj grafikiem</a>
        {% endif %}
        <a href="/wyloguj">↪ &nbsp; Wyloguj</a>
      </aside>

      <main class="dash-main">
        <section class="welcome">
          <div class="eyebrow">PANEL WEWNĘTRZNY</div>
          <h1>Witaj, {{ username }}!</h1>
          <p>Stanowisko: {{ role }} · VZTM POZNAŃ</p>
        </section>

        <h2>Twój pulpit</h2>
        <p class="muted">Najważniejsze informacje i skróty do systemu.</p>

        <div class="grid" style="margin-top:22px">
          <div class="card"><h3>Raporty</h3><div class="stat">{{ reports }}</div><p>Twoje wysłane raporty</p><a class="card-link" href="/raporty">Otwórz →</a></div>
          <div class="card"><h3>Skargi i wnioski</h3><div class="stat">{{ complaints }}</div><p>Twoje zgłoszenia</p><a class="card-link" href="/skargi">Otwórz →</a></div>
          <div class="card"><h3>Grafik</h3><div class="stat">{{ duties|length }}</div><p>Najbliższe widoczne służby</p><a class="card-link" href="/grafik">Otwórz →</a></div>
        </div>

        <div class="card" style="margin-top:22px">
          <h3>Najbliższe służby</h3>
          {% for d in duties %}
          <p class="item">{{ d.date }} · {{ d.duty }} — {{ d.details }}</p>
          {% else %}
          <p class="muted">Nie masz jeszcze przydzielonych służb.</p>
          {% endfor %}
        </div>

        <div class="card" style="margin-top:22px">
          <h3>Ostatnie ogłoszenia</h3>
          {% for n in news %}
          <div class="item"><b>{{ n.title }}</b><p class="muted">{{ n.content }}</p></div>
          {% else %}
          <p class="muted">Brak ogłoszeń.</p>
          {% endfor %}
          <a class="card-link" href="/ogloszenia">Wszystkie ogłoszenia →</a>
        </div>
      </main>
    </div>
    """, username=username, role=session.get("role", "Pracownik"),
       reports=reports, complaints=complaints, duties=duties, news=news))


# =====================================================
# GRAFIK
# =====================================================

@app.route("/grafik")
@login_required
def grafik():
    with connect() as db:
        if admin_only():
            duties = db.execute(
                "SELECT * FROM schedules ORDER BY date"
            ).fetchall()
        else:
            duties = db.execute(
                "SELECT * FROM schedules WHERE username=? ORDER BY date",
                (session["username"],)
            ).fetchall()

    return page("Grafik służb", render_template_string("""
    <main class="wrap">
      <h2>Grafik służb</h2>
      <p class="muted">Harmonogram pracy pracowników VZTM POZNAŃ.</p>
      <div class="card table-wrap" style="margin-top:22px">
        <table>
          <tr><th>Pracownik</th><th>Data</th><th>Służba</th><th>Informacje</th></tr>
          {% for d in duties %}
          <tr><td>{{ d.username }}</td><td>{{ d.date }}</td><td>{{ d.duty }}</td><td>{{ d.details }}</td></tr>
          {% else %}
          <tr><td colspan="4">Brak przydzielonych służb.</td></tr>
          {% endfor %}
        </table>
      </div>
      <p style="margin-top:22px"><a class="card-link" href="/panel">← Powrót do panelu</a></p>
    </main>
    """, duties=duties))


# =====================================================
# RAPORTY I SKARGI
# =====================================================

def submission_page(kind):
    table = "reports" if kind == "raporty" else "complaints"
    heading = "Raporty służbowe" if kind == "raporty" else "Skargi i wnioski"
    description = (
        "Przekaż raport z wykonanej służby."
        if kind == "raporty"
        else "Przekaż uwagę, skargę lub propozycję."
    )
    message = ""

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            with connect() as db:
                db.execute(
                    f"INSERT INTO {table}(username,content) VALUES(?,?)",
                    (session["username"], content)
                )
            message = "Zgłoszenie zostało zapisane."
        else:
            message = "Wpisz treść zgłoszenia."

    with connect() as db:
        if admin_only():
            rows = db.execute(
                f"SELECT * FROM {table} ORDER BY id DESC LIMIT 50"
            ).fetchall()
        else:
            rows = db.execute(
                f"SELECT * FROM {table} WHERE username=? ORDER BY id DESC",
                (session["username"],)
            ).fetchall()

    return page(heading, render_template_string("""
    <main class="wrap">
      <h2>{{ heading }}</h2>
      <p class="muted">{{ description }}</p>
      {% if message %}<div class="notice success">{{ message }}</div>{% endif %}
      <div class="card" style="margin-top:22px">
        <form method="POST">
          <input type="hidden" name="csrf" value="{{ csrf_token() }}">
          <label>Treść</label>
          <textarea name="content" maxlength="3000" required
                    placeholder="Wpisz treść..."></textarea>
          <button class="button button-blue full">Wyślij</button>
        </form>
      </div>
      <div class="card" style="margin-top:22px">
        <h3>Historia zgłoszeń</h3>
        {% for r in rows %}
        <div class="item">
          <b>{{ r.username }}</b>
          <p>{{ r.content }}</p>
          <small class="muted">{{ r.created }}</small>
        </div>
        {% else %}
        <p class="muted">Brak zgłoszeń.</p>
        {% endfor %}
      </div>
      <p style="margin-top:22px"><a class="card-link" href="/panel">← Powrót do panelu</a></p>
    </main>
    """, heading=heading, description=description, message=message, rows=rows))


@app.route("/raporty", methods=["GET", "POST"])
@login_required
def raporty():
    return submission_page("raporty")


@app.route("/skargi", methods=["GET", "POST"])
@login_required
def skargi():
    return submission_page("skargi")


# =====================================================
# OGŁOSZENIA
# =====================================================

@app.route("/ogloszenia")
def ogloszenia():
    with connect() as db:
        news = db.execute(
            "SELECT * FROM announcements ORDER BY id DESC"
        ).fetchall()

    return page("Ogłoszenia", render_template_string("""
    <main class="wrap">
      <h2>Ogłoszenia i aktualności</h2>
      <p class="muted">Komunikaty i informacje z życia przedsiębiorstwa.</p>
      <div style="margin-top:25px" class="grid">
        {% for n in news %}
        <article class="card news-card">
          <h3>{{ n.title }}</h3>
          <p>{{ n.content }}</p>
          <div class="news-date">{{ n.created }}</div>
        </article>
        {% else %}
        <div class="card">Brak opublikowanych ogłoszeń.</div>
        {% endfor %}
      </div>
    </main>
    """, news=news))


# =====================================================
# ROZPORZĄDZENIA I FAQ
# =====================================================

@app.route("/rozporzadzenia")
def rozporzadzenia():
    return page("Rozporządzenia", """
    <main class="wrap">
      <h2>Rozporządzenia</h2>
      <p class="muted">Dokumenty i zasady obowiązujące w wirtualnym przedsiębiorstwie.</p>
      <div class="card" style="margin-top:22px">
        <h3>Dokumenty przedsiębiorstwa</h3>
        <p>W tym miejscu będą publikowane regulaminy, zarządzenia i rozporządzenia.</p>
      </div>
    </main>
    """)


@app.route("/faq")
def faq():
    return page("FAQ", """
    <main class="wrap">
      <h2>Najczęściej zadawane pytania</h2>
      <div class="card" style="margin-top:22px">
        <h3>Czym jest VZTM POZNAŃ?</h3>
        <p>Jest to niezależne wirtualne przedsiębiorstwo związane z symulatorem OMSI 2.</p>
        <hr>
        <h3>Jak zostać pracownikiem?</h3>
        <p>Informacje o rekrutacji można uzyskać w kanałach społeczności projektu.</p>
        <hr>
        <h3>Jak zalogować się do panelu?</h3>
        <p>Pracownik otrzymuje login i hasło od administratora.</p>
      </div>
    </main>
    """)


# =====================================================
# PANEL ADMINISTRATORA — PRACOWNICY
# =====================================================

@app.route("/admin/pracownicy", methods=["GET", "POST"])
@admin_required
def admin_pracownicy():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "Pracownik")

        allowed_roles = [
            "Administrator", "Dyrektor", "Kierownik",
            "Instruktor", "Kierowca", "Motorniczy", "Pracownik"
        ]

        if not username or len(username) < 3 or len(password) < 8:
            message = "Login musi mieć minimum 3 znaki, a hasło minimum 8."
        elif role not in allowed_roles:
            message = "Nieprawidłowe stanowisko."
        else:
            try:
                with connect() as db:
                    db.execute(
                        "INSERT INTO users(username,password,role) VALUES(?,?,?)",
                        (username, generate_password_hash(password), role)
                    )
                message = "Konto pracownika zostało utworzone."
            except sqlite3.IntegrityError:
                message = "Taki login już istnieje."

    with connect() as db:
        users = db.execute(
            "SELECT id,username,role FROM users ORDER BY username"
        ).fetchall()

    return page("Pracownicy", render_template_string("""
    <main class="wrap">
      <h2>Zarządzanie pracownikami</h2>
      <p class="muted">Tworzenie kont i przydzielanie stanowisk.</p>
      {% if message %}<div class="notice">{{ message }}</div>{% endif %}
      <div class="card" style="margin-top:22px">
        <h3>Dodaj pracownika</h3>
        <form method="POST">
          <input type="hidden" name="csrf" value="{{ csrf_token() }}">
          <label>Login</label>
          <input name="username" minlength="3" required>
          <label>Hasło tymczasowe</label>
          <input name="password" type="password" minlength="8" required>
          <label>Stanowisko</label>
          <select name="role">
            {% for role in roles %}<option>{{ role }}</option>{% endfor %}
          </select>
          <button class="button button-blue full">Utwórz konto</button>
        </form>
      </div>
      <div class="card table-wrap" style="margin-top:22px">
        <h3>Lista pracowników</h3>
        <table>
          <tr><th>Login</th><th>Stanowisko</th></tr>
          {% for u in users %}
          <tr><td>{{ u.username }}</td><td>{{ u.role }}</td></tr>
          {% endfor %}
        </table>
      </div>
      <p style="margin-top:22px"><a class="card-link" href="/panel">← Powrót do panelu</a></p>
    </main>
    """, message=message, users=users, roles=[
        "Pracownik", "Kierowca", "Motorniczy",
        "Instruktor", "Kierownik", "Dyrektor", "Administrator"
    ]))


# =====================================================
# PANEL ADMINISTRATORA — OGŁOSZENIA
# =====================================================

@app.route("/admin/ogloszenia", methods=["GET", "POST"])
@admin_required
def admin_ogloszenia():
    message = ""

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        if title and content:
            with connect() as db:
                db.execute(
                    "INSERT INTO announcements(title,content) VALUES(?,?)",
                    (title, content)
                )
            message = "Ogłoszenie zostało opublikowane."
        else:
            message = "Uzupełnij tytuł i treść."

    with connect() as db:
        news = db.execute(
            "SELECT * FROM announcements ORDER BY id DESC"
        ).fetchall()

    return page("Zarządzanie ogłoszeniami", render_template_string("""
    <main class="wrap">
      <h2>Zarządzanie ogłoszeniami</h2>
      <p class="muted">Publikowanie aktualności na stronie głównej.</p>
      {% if message %}<div class="notice success">{{ message }}</div>{% endif %}
      <div class="card" style="margin-top:22px">
        <form method="POST">
          <input type="hidden" name="csrf" value="{{ csrf_token() }}">
          <label>Tytuł ogłoszenia</label>
          <input name="title" maxlength="150" required>
          <label>Treść ogłoszenia</label>
          <textarea name="content" maxlength="5000" required></textarea>
          <button class="button button-blue full">Opublikuj ogłoszenie</button>
        </form>
      </div>
      <div class="grid" style="margin-top:22px">
        {% for n in news %}
        <div class="card"><h3>{{ n.title }}</h3><p>{{ n.content }}</p></div>
        {% endfor %}
      </div>
      <p style="margin-top:22px"><a class="card-link" href="/panel">← Powrót do panelu</a></p>
    </main>
    """, message=message, news=news))


# =====================================================
# PANEL ADMINISTRATORA — GRAFIK
# =====================================================

@app.route("/admin/grafik", methods=["GET", "POST"])
@admin_required
def admin_grafik():
    message = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        date = request.form.get("date", "")
        duty = request.form.get("duty", "").strip()
        details = request.form.get("details", "").strip()

        with connect() as db:
            user = db.execute(
                "SELECT id FROM users WHERE username=?", (username,)
            ).fetchone()

            if user and date and duty:
                db.execute(
                    "INSERT INTO schedules(username,date,duty,details) VALUES(?,?,?,?)",
                    (username, date, duty, details)
                )
                message = "Służba została dodana."
            else:
                message = "Sprawdź login pracownika, datę i nazwę służby."

    with connect() as db:
        users = db.execute(
            "SELECT username FROM users ORDER BY username"
        ).fetchall()
        duties = db.execute(
            "SELECT * FROM schedules ORDER BY date"
        ).fetchall()

    return page("Zarządzanie grafikiem", render_template_string("""
    <main class="wrap">
      <h2>Zarządzanie grafikiem</h2>
      <p class="muted">Przydzielanie służb pracownikom.</p>
      {% if message %}<div class="notice">{{ message }}</div>{% endif %}
      <div class="card" style="margin-top:22px">
        <form method="POST">
          <input type="hidden" name="csrf" value="{{ csrf_token() }}">
          <label>Pracownik</label>
          <select name="username">
            {% for u in users %}<option>{{ u.username }}</option>{% endfor %}
          </select>
          <label>Data służby</label>
          <input type="date" name="date" required>
          <label>Nazwa służby</label>
          <input name="duty" placeholder="Np. Linia 101" required>
          <label>Dodatkowe informacje</label>
          <input name="details" placeholder="Np. Autobus, brygada, uwagi">
          <button class="button button-blue full">Dodaj służbę</button>
        </form>
      </div>
      <div class="card table-wrap" style="margin-top:22px">
        <h3>Przydzielone służby</h3>
        <table>
          <tr><th>Pracownik</th><th>Data</th><th>Służba</th><th>Informacje</th></tr>
          {% for d in duties %}
          <tr><td>{{ d.username }}</td><td>{{ d.date }}</td><td>{{ d.duty }}</td><td>{{ d.details }}</td></tr>
          {% else %}
          <tr><td colspan="4">Brak służb.</td></tr>
          {% endfor %}
        </table>
      </div>
      <p style="margin-top:22px"><a class="card-link" href="/panel">← Powrót do panelu</a></p>
    </main>
    """, message=message, users=users, duties=duties))


# =====================================================
# URUCHOMIENIE
# =====================================================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
