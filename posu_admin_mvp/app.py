from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "posu_admin.db"
SETTINGS_TABS: list[tuple[str, str]] = [
    ("frontend", "前台設定"),
    ("general", "通用"),
    ("notice", "通知"),
    ("activity", "活動"),
    ("plugin", "外掛"),
]
CONTENT_MODULES: dict[str, str] = {
    "news": "最新消息",
    "announcements": "會員公告",
    "activities": "活動管理",
    "recruit": "人才招募",
    "links": "相關連結",
}


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
            {"name": "活動管理", "url": url_for("content_list", module="activities")},
            {"name": "活動花絮", "url": "#"},
            {"name": "關於本會", "url": "#"},
            {"name": "最新消息", "url": url_for("content_list", module="news")},
            {"name": "會員公告", "url": url_for("content_list", module="announcements")},
            {"name": "專欄園地", "url": "#"},
            {"name": "會員商品", "url": "#"},
            {"name": "理事長(幹部)", "url": "#"},
            {"name": "會員資訊", "url": url_for("members")},
            {"name": "留言板", "url": "#"},
            {"name": "人才招募", "url": url_for("content_list", module="recruit")},
            {"name": "相關連結", "url": url_for("content_list", module="links")},
            {"name": "本會記事", "url": "#"},
            {"name": "夥伴介紹", "url": "#"},
            {"name": "社團新聞", "url": "#"},
            {"name": "主題新知", "url": "#"},
            {"name": "紅白帖", "url": "#"},
            {"name": "日記簿", "url": "#"},
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

    @app.route("/settings")
    def settings_index() -> Any:
        return redirect(url_for("settings", tab="frontend"))

    @app.route("/settings/<tab>", methods=["GET", "POST"])
    def settings(tab: str) -> Any:
        guard = require_login()
        if guard:
            return guard
        tab_keys = [k for k, _ in SETTINGS_TABS]
        if tab not in tab_keys:
            flash("找不到設定頁面", "error")
            return redirect(url_for("settings", tab="frontend"))
        fields = get_settings_fields(tab)
        db = get_db()
        if request.method == "POST":
            save_settings_values(fields)
            flash("設定已更新", "success")
            return redirect(url_for("settings", tab=tab))
        values = load_settings_values(fields)
        return render_template(
            "settings.html",
            tabs=SETTINGS_TABS,
            active_tab=tab,
            fields=fields,
            values=values,
        )

    @app.route("/profile", methods=["GET", "POST"])
    def profile() -> Any:
        guard = require_login()
        if guard:
            return guard
        sections = get_profile_sections()
        all_fields = flatten_sections(sections)
        if request.method == "POST":
            persistable_fields = [field for field in all_fields if field.get("type") != "password"]
            save_settings_values(persistable_fields)
            if request.form.get("password"):
                db = get_db()
                db.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(request.form["password"]), g.user["id"]),
                )
                db.commit()
            flash("個人帳號資料已更新", "success")
            return redirect(url_for("profile"))
        values = load_settings_values(all_fields)
        return render_template(
            "profile.html",
            sections=sections,
            values=values,
        )

    @app.route("/content/<module>")
    def content_list(module: str) -> Any:
        guard = require_login()
        if guard:
            return guard
        module_name = CONTENT_MODULES.get(module)
        if not module_name:
            flash("找不到內容模組", "error")
            return redirect(url_for("dashboard"))
        db = get_db()
        items = db.execute(
            """
            SELECT id, title, summary, external_url, published, updated_at
            FROM content_items
            WHERE module = ?
            ORDER BY id DESC
            """,
            (module,),
        ).fetchall()
        return render_template(
            "content_list.html",
            module=module,
            module_name=module_name,
            items=items,
            modules=CONTENT_MODULES,
        )

    @app.route("/content/<module>/new", methods=["GET", "POST"])
    def content_new(module: str) -> Any:
        guard = require_login()
        if guard:
            return guard
        module_name = CONTENT_MODULES.get(module)
        if not module_name:
            flash("找不到內容模組", "error")
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            save_content_item(module)
            flash(f"{module_name}已新增", "success")
            return redirect(url_for("content_list", module=module))
        return render_template(
            "content_form.html",
            module=module,
            module_name=module_name,
            form_action=f"新增{module_name}",
            item=None,
        )

    @app.route("/content/<module>/<int:item_id>/edit", methods=["GET", "POST"])
    def content_edit(module: str, item_id: int) -> Any:
        guard = require_login()
        if guard:
            return guard
        module_name = CONTENT_MODULES.get(module)
        if not module_name:
            flash("找不到內容模組", "error")
            return redirect(url_for("dashboard"))
        db = get_db()
        item = db.execute(
            "SELECT * FROM content_items WHERE module = ? AND id = ?",
            (module, item_id),
        ).fetchone()
        if not item:
            flash("找不到資料", "error")
            return redirect(url_for("content_list", module=module))
        if request.method == "POST":
            save_content_item(module, item_id)
            flash(f"{module_name}已更新", "success")
            return redirect(url_for("content_list", module=module))
        return render_template(
            "content_form.html",
            module=module,
            module_name=module_name,
            form_action=f"編輯{module_name}",
            item=item,
        )

    @app.post("/content/<module>/<int:item_id>/delete")
    def content_delete(module: str, item_id: int) -> Any:
        guard = require_login()
        if guard:
            return guard
        module_name = CONTENT_MODULES.get(module)
        if not module_name:
            flash("找不到內容模組", "error")
            return redirect(url_for("dashboard"))
        db = get_db()
        db.execute("DELETE FROM content_items WHERE module = ? AND id = ?", (module, item_id))
        db.commit()
        flash(f"{module_name}已刪除", "info")
        return redirect(url_for("content_list", module=module))

    @app.route("/front")
    def front_home() -> Any:
        return redirect(url_for("front_site", site_code="2236"))

    @app.route("/front/<site_code>")
    def front_site(site_code: str) -> Any:
        db = get_db()
        rows = db.execute(
            """
            SELECT module, title, summary, body, external_url, updated_at
            FROM content_items
            WHERE published = 1
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        sections: dict[str, list[Any]] = {key: [] for key in CONTENT_MODULES}
        for row in rows:
            sections[row["module"]].append(row)
        title = load_settings_values(
            [{"name": "fellowship_name", "default": "Yongkang International Fellowship"}]
        )["fellowship_name"]
        return render_template(
            "front_home.html",
            site_code=site_code,
            title=title,
            sections=sections,
            modules=CONTENT_MODULES,
        )

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

            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS content_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                external_url TEXT NOT NULL DEFAULT '',
                published INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        seed_default_admin(db)
        seed_default_settings(db)
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


def save_content_item(module: str, item_id: int | None = None) -> None:
    db = get_db()
    form = request.form
    data = (
        module,
        form["title"].strip(),
        form.get("summary", "").strip(),
        form.get("body", "").strip(),
        form.get("external_url", "").strip(),
        1 if form.get("published") == "on" else 0,
    )
    if item_id is None:
        db.execute(
            """
            INSERT INTO content_items (module, title, summary, body, external_url, published)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            data,
        )
    else:
        db.execute(
            """
            UPDATE content_items
            SET title = ?, summary = ?, body = ?, external_url = ?, published = ?, updated_at = CURRENT_TIMESTAMP
            WHERE module = ? AND id = ?
            """,
            (data[1], data[2], data[3], data[4], data[5], module, item_id),
        )
    db.commit()


def flatten_sections(sections: list[dict[str, Any]]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for section in sections:
        fields.extend(section["fields"])
    return fields


def save_settings_values(fields: list[dict[str, str]]) -> None:
    db = get_db()
    for field in fields:
        value = request.form.get(field["name"], "")
        if field.get("type") == "checkbox":
            value = "1" if request.form.get(field["name"]) == "on" else "0"
        db.execute(
            """
            INSERT INTO settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """,
            (field["name"], value.strip() if isinstance(value, str) else value),
        )
    db.commit()


def load_settings_values(fields: list[dict[str, str]]) -> dict[str, str]:
    db = get_db()
    values = {}
    for field in fields:
        row = db.execute(
            "SELECT setting_value FROM settings WHERE setting_key = ?",
            (field["name"],),
        ).fetchone()
        if row:
            values[field["name"]] = row["setting_value"]
        else:
            values[field["name"]] = field.get("default", "")
    return values


def seed_default_settings(db: sqlite3.Connection) -> None:
    defaults = {
        "privacy_policy": (
            "本網站重視您的隱私權，將依個人資料保護法妥善處理個人資料。"
            "若您對隱私政策有任何疑問，請聯繫管理員。"
        ),
        "site_name": "社團達人展示",
        "category_name": "總公司公告",
        "notify_email_enabled": "1",
        "notify_line_enabled": "1",
        "fellowship_name": "Yongkang International Fellowship",
    }
    for key, value in defaults.items():
        db.execute(
            """
            INSERT INTO settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key) DO NOTHING
            """,
            (key, value),
        )


def get_settings_fields(tab: str) -> list[dict[str, str]]:
    if tab == "frontend":
        return [
            {"name": "site_public_notice", "label": "總公司的公告", "type": "radio"},
            {"name": "site_name", "label": "公告開放後名稱", "type": "text", "default": "社團達人展示"},
            {"name": "category_name", "label": "分類名稱", "type": "text", "default": "總公司公告"},
            {"name": "join_message", "label": "加入會員說明", "type": "textarea"},
            {"name": "privacy_policy", "label": "隱私權說明", "type": "textarea"},
        ]
    if tab == "general":
        return [
            {"name": "site_domain", "label": "網址網域", "type": "text"},
            {"name": "site_title", "label": "網站標題", "type": "text"},
            {"name": "line_official_id", "label": "Line 帳號", "type": "text"},
            {"name": "contact_person", "label": "聯絡人", "type": "text"},
            {"name": "contact_phone", "label": "聯絡電話", "type": "text"},
            {"name": "contact_email", "label": "E-Mail", "type": "text"},
        ]
    if tab == "notice":
        return [
            {"name": "notify_email_enabled", "label": "寄信通知", "type": "checkbox"},
            {"name": "notify_line_enabled", "label": "Line 通知", "type": "checkbox"},
            {"name": "notify_member_enabled", "label": "會員通知", "type": "checkbox"},
            {"name": "notify_digest_text", "label": "通知內容", "type": "textarea"},
        ]
    if tab == "activity":
        return [
            {"name": "activity_open", "label": "活動開放", "type": "radio"},
            {"name": "activity_title", "label": "活動標題", "type": "text"},
            {"name": "activity_desc", "label": "活動說明", "type": "textarea"},
            {"name": "activity_rules", "label": "活動規範", "type": "textarea"},
        ]
    return [
        {"name": "gemini_api_key", "label": "Gemini AI APIKEY", "type": "text"},
        {"name": "google_verify", "label": "Google 驗證碼", "type": "text"},
        {"name": "google_analytics", "label": "Google Analytics", "type": "text"},
        {"name": "google_tag_manager", "label": "Google Tag Manager", "type": "text"},
        {"name": "google_adsense", "label": "Google AdSense", "type": "text"},
        {"name": "openai_api_key", "label": "OpenAI APIKEY", "type": "text"},
        {"name": "bing_verify", "label": "Bing 驗證碼", "type": "text"},
        {"name": "facebook_pixel", "label": "FB Pixel 代碼", "type": "text"},
    ]


def get_profile_sections() -> list[dict[str, Any]]:
    return [
        {
            "title": "帳戶",
            "fields": [
                {"name": "profile_display_enabled", "label": "是否發佈", "type": "radio"},
                {"name": "profile_email_public", "label": "電子名片", "type": "radio"},
                {"name": "profile_audio_public", "label": "視訊會議", "type": "radio"},
                {"name": "profile_company", "label": "姓名", "type": "text", "default": "社團達人展示"},
                {"name": "profile_nickname", "label": "暱稱", "type": "text", "default": "b_demo"},
                {"name": "profile_phone_1", "label": "電話1", "type": "text"},
                {"name": "profile_phone_2", "label": "電話2", "type": "text"},
                {"name": "profile_email_1", "label": "E-Mail(1)", "type": "text"},
                {"name": "profile_email_2", "label": "E-mail(2)", "type": "text"},
                {"name": "password", "label": "密碼", "type": "password"},
            ],
        },
        {
            "title": "通訊社群",
            "fields": [
                {"name": "profile_line_id", "label": "LINE ID", "type": "text"},
                {"name": "profile_line_url", "label": "LINE 連結站", "type": "text"},
                {"name": "profile_line_enabled", "label": "啟動 LINE 通知", "type": "checkbox"},
                {"name": "profile_line_channel", "label": "頻道編號", "type": "text"},
                {"name": "profile_line_secret", "label": "頻道令牌", "type": "text"},
                {"name": "profile_line_receiver", "label": "接收者ID", "type": "text"},
                {"name": "profile_wechat", "label": "WeChat", "type": "text"},
                {"name": "profile_skype", "label": "SKYPE", "type": "text"},
                {"name": "profile_facebook", "label": "Facebook", "type": "text"},
                {"name": "profile_ig", "label": "IG", "type": "text"},
                {"name": "profile_twitter", "label": "TWITTER", "type": "text"},
                {"name": "profile_weibo", "label": "微博", "type": "text"},
            ],
        },
        {
            "title": "個人介紹",
            "fields": [
                {"name": "profile_city", "label": "所在地區", "type": "text"},
                {"name": "profile_address", "label": "地址", "type": "text"},
                {"name": "profile_website", "label": "網址", "type": "text"},
                {"name": "profile_business_hour", "label": "個人營業時間", "type": "text"},
                {"name": "profile_slogan", "label": "Slogan", "type": "text"},
                {"name": "profile_intro", "label": "個人簡述", "type": "textarea"},
                {"name": "profile_detail", "label": "個人詳細", "type": "textarea"},
                {"name": "profile_vendor", "label": "廠商名稱", "type": "text"},
                {"name": "profile_tax_id", "label": "統編", "type": "text"},
                {"name": "profile_fax", "label": "傳真", "type": "text"},
                {"name": "profile_service_desc", "label": "服務說明", "type": "text"},
                {"name": "profile_service_area", "label": "服務地區", "type": "text"},
                {"name": "profile_service_items", "label": "服務項目", "type": "textarea"},
            ],
        },
        {
            "title": "興趣與活動",
            "fields": [
                {"name": "profile_interest", "label": "有興趣的", "type": "text"},
                {"name": "profile_interest_notify", "label": "通知 E-Mail", "type": "checkbox"},
                {"name": "profile_activity_type", "label": "活動分類", "type": "text"},
                {"name": "profile_activity_area", "label": "活動所在", "type": "text"},
                {"name": "profile_activity_name", "label": "社團活動", "type": "text"},
            ],
        },
        {
            "title": "廣告與帳務",
            "fields": [
                {"name": "profile_ad_content", "label": "廣告內容", "type": "textarea"},
                {"name": "profile_ad_url", "label": "廣告網址", "type": "text"},
                {"name": "profile_ad_note", "label": "廣告說明", "type": "textarea"},
                {"name": "profile_bank_info", "label": "銀行帳戶", "type": "textarea"},
                {"name": "profile_account_image_1", "label": "帳號相片1", "type": "text"},
                {"name": "profile_account_image_2", "label": "帳號相片2", "type": "text"},
                {"name": "profile_account_image_3", "label": "帳號相片3", "type": "text"},
                {"name": "profile_account_image_4", "label": "帳號相片4", "type": "text"},
                {"name": "profile_note", "label": "備註", "type": "textarea"},
            ],
        },
    ]


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
