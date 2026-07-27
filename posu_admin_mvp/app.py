from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "posu_admin.db"


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "posu-admin-local-dev-key"
    app.config["DATABASE"] = str(DB_PATH)
    if test_config:
        app.config.update(test_config)

    @app.before_request
    def load_logged_user() -> None:
        g.user = None
        user_id = session.get("user_id")
        if not user_id:
            return
        db = get_db()
        g.user = db.execute(
            "SELECT id, account, display_name FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    @app.route("/")
    def index() -> Any:
        if g.user:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login() -> Any:
        if request.method == "POST":
            account = request.form["account"].strip()
            password = request.form["password"]
            db = get_db()
            user = db.execute(
                "SELECT id, account, password_hash, display_name FROM users WHERE account = ?",
                (account,),
            ).fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                flash("帳號或密碼錯誤", "error")
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash(f"歡迎回來，{user['display_name']}", "success")
                return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/logout")
    def logout() -> Any:
        session.clear()
        flash("已成功登出", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    def dashboard() -> Any:
        guard = require_login()
        if guard:
            return guard
        modules = [
            "活動管理",
            "活動花絮",
            "關於本會",
            "最新消息",
            "會員公告",
            "專欄園地",
            "會員商品",
            "理事長(幹部)",
            "會員資訊",
            "留言板",
            "人才招募",
            "相關連結",
            "本會記事",
            "夥伴介紹",
            "社團新聞",
            "主題新知",
            "紅白帖",
            "日記簿",
        ]
        return render_template("dashboard.html", modules=modules)

    @app.route("/members")
    def members() -> Any:
        guard = require_login()
        if guard:
            return guard
        db = get_db()
        items = db.execute(
            """
            SELECT id, member_no, name, phone, email, level, active
            FROM members
            ORDER BY id DESC
            """
        ).fetchall()
        return render_template("members.html", members=items)

    @app.route("/members/new", methods=["GET", "POST"])
    def members_new() -> Any:
        guard = require_login()
        if guard:
            return guard
        if request.method == "POST":
            try:
                save_member()
            except sqlite3.IntegrityError:
                flash("會員編號已存在，請使用其他編號", "error")
                return render_template("member_form.html", member=None, form_action="新增會員")
            flash("會員新增成功", "success")
            return redirect(url_for("members"))
        return render_template("member_form.html", member=None, form_action="新增會員")

    @app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
    def members_edit(member_id: int) -> Any:
        guard = require_login()
        if guard:
            return guard
        db = get_db()
        member = db.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if member is None:
            flash("找不到會員資料", "error")
            return redirect(url_for("members"))
        if request.method == "POST":
            try:
                save_member(member_id)
            except sqlite3.IntegrityError:
                flash("會員編號已被其他會員使用", "error")
                return render_template("member_form.html", member=member, form_action="編輯會員")
            flash("會員資料更新成功", "success")
            return redirect(url_for("members"))
        return render_template("member_form.html", member=member, form_action="編輯會員")

    @app.post("/members/<int:member_id>/delete")
    def members_delete(member_id: int) -> Any:
        guard = require_login()
        if guard:
            return guard
        db = get_db()
        db.execute("DELETE FROM members WHERE id = ?", (member_id,))
        db.commit()
        flash("會員資料已刪除", "info")
        return redirect(url_for("members"))

    @app.teardown_appcontext
    def close_db(_: Any) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    init_db(app)
    return app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


def init_db(app: Flask) -> None:
    with app.app_context():
        db = get_db()
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_no TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                level TEXT NOT NULL DEFAULT '一般會員',
                active INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        seed_default_admin(db)
        db.commit()


def seed_default_admin(db: sqlite3.Connection) -> None:
    known_accounts = [
        ("gp0975717557", "社團管理者", "0975717557"),
        ("admin", "系統管理員", "admin1234"),
    ]
    for account, display_name, password in known_accounts:
        existing = db.execute("SELECT id FROM users WHERE account = ?", (account,)).fetchone()
        if existing:
            continue
        db.execute(
            """
            INSERT INTO users (account, password_hash, display_name)
            VALUES (?, ?, ?)
            """,
            (account, generate_password_hash(password), display_name),
        )


def require_login() -> Any:
    if g.user is None:
        flash("請先登入系統", "error")
        return redirect(url_for("login"))
    return None


def save_member(member_id: int | None = None) -> None:
    db = get_db()
    form = request.form
    data = (
        form["member_no"].strip(),
        form["name"].strip(),
        form["phone"].strip(),
        form.get("email", "").strip(),
        form["level"].strip() or "一般會員",
        1 if form.get("active") == "on" else 0,
    )
    if member_id is None:
        db.execute(
            """
            INSERT INTO members (member_no, name, phone, email, level, active)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            data,
        )
    else:
        db.execute(
            """
            UPDATE members
            SET member_no = ?, name = ?, phone = ?, email = ?, level = ?, active = ?
            WHERE id = ?
            """,
            (*data, member_id),
        )
    db.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
