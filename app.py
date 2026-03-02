from __future__ import annotations

from datetime import datetime
import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).parent
DATABASE = BASE_DIR / "app.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-secret-change-me"

# Легко расширяемая конфигурация уровней.
# Для добавления нового уровня: добавьте словарь в этот список.
LEVELS = [
    {
        "id": 1,
        "name": "Уровень 1: Первые шаги",
        "description": "Доведите персонажа до финиша, используя команды движения.",
        "width": 5,
        "height": 3,
        "start": (1, 1),
        "finish": (3, 1),
        "obstacles": [],
        "allowed_commands": ["left", "right", "up", "down"],
        "time_target_ms": 30000,
        "optimal_commands": 2,
    },
]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: object) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            regdata TEXT NOT NULL,
            total_stars INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS level_progress (
            user_id INTEGER NOT NULL,
            level_id INTEGER NOT NULL,
            completion_star INTEGER NOT NULL DEFAULT 0,
            time_star INTEGER NOT NULL DEFAULT 0,
            code_star INTEGER NOT NULL DEFAULT 0,
            best_time_ms INTEGER,
            best_commands_count INTEGER,
            PRIMARY KEY (user_id, level_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


@app.before_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


@app.context_processor
def inject_header_data():
    stars = 0
    if g.get("user"):
        stars = g.user["total_stars"]
    return {"header_stars": stars, "levels": LEVELS}


def get_level(level_id: int) -> dict | None:
    return next((lvl for lvl in LEVELS if lvl["id"] == level_id), None)


def get_unlocked_level_ids(user_id: int) -> set[int]:
    unlocked = set()
    db = get_db()
    progress = {
        row["level_id"]: row
        for row in db.execute(
            "SELECT * FROM level_progress WHERE user_id = ? ORDER BY level_id", (user_id,)
        ).fetchall()
    }

    for lvl in LEVELS:
        if lvl["id"] == 1:
            unlocked.add(1)
            continue
        prev = progress.get(lvl["id"] - 1)
        if prev and prev["completion_star"] == 1:
            unlocked.add(lvl["id"])
    return unlocked


def recalc_total_stars(user_id: int) -> None:
    db = get_db()
    total = db.execute(
        """
        SELECT COALESCE(SUM(completion_star + time_star + code_star), 0)
        FROM level_progress WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()[0]
    db.execute("UPDATE users SET total_stars = ? WHERE id = ?", (total, user_id))
    db.commit()


@app.route("/")
def index():
    progress_map = {}
    unlocked = {1}
    if g.user:
        db = get_db()
        rows = db.execute(
            "SELECT * FROM level_progress WHERE user_id = ? ORDER BY level_id", (g.user["id"],)
        ).fetchall()
        progress_map = {row["level_id"]: row for row in rows}
        unlocked = get_unlocked_level_ids(g.user["id"])

    return render_template("index.html", progress_map=progress_map, unlocked=unlocked)


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/profile")
@login_required
def profile():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM level_progress WHERE user_id = ? ORDER BY level_id", (g.user["id"],)
    ).fetchall()
    return render_template("profile.html", rows=rows)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        if not username or not password:
            flash("Введите имя пользователя и пароль")
            return render_template("register.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users(username, password_hash, regdata) VALUES(?, ?, ?)",
                (username, generate_password_hash(password), datetime.now().strftime('%d.%m.%Y %H:%M')),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("Пользователь с таким именем уже существует")
            return render_template("register.html")

        flash("Регистрация успешна. Теперь войдите в аккаунт")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Неверные логин или пароль")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/level/<int:level_id>")
@login_required
def level_page(level_id: int):
    level = get_level(level_id)
    if not level:
        return "Уровень не найден", 404

    unlocked = get_unlocked_level_ids(g.user["id"])
    if level_id not in unlocked:
        flash("Этот уровень пока заблокирован")
        return redirect(url_for("index"))

    db = get_db()
    progress = db.execute(
        "SELECT * FROM level_progress WHERE user_id = ? AND level_id = ?",
        (g.user["id"], level_id),
    ).fetchone()

    return render_template("level.html", level=level, progress=progress)


def simulate_level(code: str, level: dict) -> tuple[bool, tuple[int, int], list[str], int]:
    commands = []
    errors = []
    cmd_re = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)\s*$")
    for idx, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        match = cmd_re.match(line)
        if not match:
            errors.append(f"Строка {idx}: используйте формат command()")
            continue
        cmd = match.group(1)
        if cmd not in level["allowed_commands"]:
            errors.append(f"Строка {idx}: команда {cmd} недоступна")
            continue
        commands.append(cmd)

    if errors:
        return False, level["start"], errors, len(commands)

    x, y = level["start"]
    finish = tuple(level["finish"])
    obstacle_set = {tuple(o) for o in level["obstacles"]}

    for cmd in commands:
        nx, ny = x, y
        if cmd == "left":
            nx -= 1
        elif cmd == "right":
            nx += 1
        elif cmd == "up":
            ny -= 1
        elif cmd == "down":
            ny += 1

        if nx < 0 or ny < 0 or nx >= level["width"] or ny >= level["height"]:
            errors.append("Персонаж упёрся в границу поля")
            break
        if (nx, ny) in obstacle_set:
            errors.append("Персонаж столкнулся с препятствием")
            break

        x, y = nx, ny

    success = (x, y) == finish and not errors
    return success, (x, y), errors, len(commands)


@app.route("/api/level/<int:level_id>/run", methods=["POST"])
@login_required
def run_level(level_id: int):
    level = get_level(level_id)
    if not level:
        return jsonify({"error": "Уровень не найден"}), 404

    unlocked = get_unlocked_level_ids(g.user["id"])
    if level_id not in unlocked:
        return jsonify({"error": "Уровень заблокирован"}), 403

    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "")
    elapsed_ms = int(payload.get("elapsed_ms", 0))

    success, final_pos, errors, commands_count = simulate_level(code, level)

    completion_star = 1 if success else 0
    time_star = 1 if success and elapsed_ms > 0 and elapsed_ms <= level["time_target_ms"] else 0
    code_star = 1 if success and commands_count <= level["optimal_commands"] else 0

    db = get_db()
    current = db.execute(
        "SELECT * FROM level_progress WHERE user_id = ? AND level_id = ?",
        (g.user["id"], level_id),
    ).fetchone()

    if current is None:
        db.execute(
            """
            INSERT INTO level_progress(
                user_id, level_id, completion_star, time_star, code_star, best_time_ms, best_commands_count
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                g.user["id"],
                level_id,
                completion_star,
                time_star,
                code_star,
                elapsed_ms if success else None,
                commands_count if success else None,
            ),
        )
    else:
        new_completion = max(current["completion_star"], completion_star)
        new_time = max(current["time_star"], time_star)
        new_code = max(current["code_star"], code_star)

        best_time_ms = current["best_time_ms"]
        if success and elapsed_ms > 0:
            if best_time_ms is None or elapsed_ms < best_time_ms:
                best_time_ms = elapsed_ms

        best_commands = current["best_commands_count"]
        if success:
            if best_commands is None or commands_count < best_commands:
                best_commands = commands_count

        db.execute(
            """
            UPDATE level_progress
            SET completion_star = ?, time_star = ?, code_star = ?, best_time_ms = ?, best_commands_count = ?
            WHERE user_id = ? AND level_id = ?
            """,
            (
                new_completion,
                new_time,
                new_code,
                best_time_ms,
                best_commands,
                g.user["id"],
                level_id,
            ),
        )

    db.commit()
    recalc_total_stars(g.user["id"])

    message = "Уровень пройден!" if success else "Пока не получилось. Попробуйте ещё раз."

    return jsonify(
        {
            "success": success,
            "message": message,
            "errors": errors,
            "final_pos": final_pos,
            "stars": {
                "completion": completion_star,
                "time": time_star,
                "code": code_star,
                "total_attempt": completion_star + time_star + code_star,
            },
        }
    )


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
