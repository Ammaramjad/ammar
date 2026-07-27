from __future__ import annotations

from pathlib import Path

import pytest

from posu_admin_mvp.app import create_app


@pytest.fixture()
def client(tmp_path: Path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-key",
            "DATABASE": str(tmp_path / "test.db"),
        }
    )
    with app.test_client() as client:
        yield client


def login(client):
    return client.post(
        "/login",
        data={"account": "gp0975717557", "password": "0975717557"},
        follow_redirects=True,
    )


def test_redirects_to_login_when_not_authenticated(client):
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert "社團管理系統登入" in response.get_data(as_text=True)


def test_login_success_and_dashboard_visible(client):
    response = login(client)
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "歡迎使用系統" in body
    assert "會員資料" in body


def test_member_crud_flow(client):
    login(client)

    create_response = client.post(
        "/members/new",
        data={
            "member_no": "M0001",
            "name": "王小明",
            "phone": "0912-111-222",
            "email": "m001@example.com",
            "level": "一般會員",
            "active": "on",
        },
        follow_redirects=True,
    )
    create_body = create_response.get_data(as_text=True)
    assert create_response.status_code == 200
    assert "會員新增成功" in create_body
    assert "王小明" in create_body

    edit_page = client.get("/members")
    body = edit_page.get_data(as_text=True)
    assert "M0001" in body

    update_response = client.post(
        "/members/1/edit",
        data={
            "member_no": "M0001",
            "name": "王小明(更新)",
            "phone": "0912-999-888",
            "email": "m001@updated.com",
            "level": "幹部會員",
            "active": "on",
        },
        follow_redirects=True,
    )
    update_body = update_response.get_data(as_text=True)
    assert "會員資料更新成功" in update_body
    assert "王小明(更新)" in update_body

    delete_response = client.post("/members/1/delete", follow_redirects=True)
    delete_body = delete_response.get_data(as_text=True)
    assert "會員資料已刪除" in delete_body
    assert "王小明(更新)" not in delete_body


def test_settings_tabs_and_persistence(client):
    login(client)

    post_general = client.post(
        "/settings/general",
        data={
            "site_domain": "https://example.org",
            "site_title": "社團達人測試站",
            "line_official_id": "@testline",
            "contact_person": "王管理員",
            "contact_phone": "02-1234-5678",
            "contact_email": "admin@example.org",
        },
        follow_redirects=True,
    )
    assert post_general.status_code == 200
    page_general = post_general.get_data(as_text=True)
    assert "設定已更新" in page_general
    assert "社團達人測試站" in page_general

    post_plugin = client.post(
        "/settings/plugin",
        data={
            "gemini_api_key": "gemini-key-001",
            "google_verify": "google-verify-abc",
            "google_analytics": "GA-TEST-001",
            "google_tag_manager": "GTM-AAAAAA",
            "google_adsense": "ca-pub-123456",
            "openai_api_key": "openai-key-xyz",
            "bing_verify": "bing-verify-777",
            "facebook_pixel": "fb-pixel-123",
        },
        follow_redirects=True,
    )
    assert post_plugin.status_code == 200
    page_plugin = post_plugin.get_data(as_text=True)
    assert "openai-key-xyz" in page_plugin
    assert "fb-pixel-123" in page_plugin


def test_profile_page_persistence_and_password_update(client):
    login(client)

    profile_response = client.post(
        "/profile",
        data={
            "profile_display_enabled": "1",
            "profile_company": "社團達人展示公司",
            "profile_nickname": "b_demo_plus",
            "profile_phone_1": "0911-222-333",
            "profile_email_1": "profile@demo.tw",
            "profile_line_id": "@lineprofile",
            "profile_city": "台北市",
            "profile_intro": "這是個人簡述測試內容",
            "profile_ad_url": "https://ad.demo.tw",
            "profile_account_image_1": "bank-shot-1.png",
            "profile_note": "備註測試",
            "password": "newpass1234",
        },
        follow_redirects=True,
    )
    assert profile_response.status_code == 200
    profile_body = profile_response.get_data(as_text=True)
    assert "個人帳號資料已更新" in profile_body
    assert "社團達人展示公司" in profile_body
    assert "https://ad.demo.tw" in profile_body

    client.get("/logout", follow_redirects=True)

    old_password_login = client.post(
        "/login",
        data={"account": "gp0975717557", "password": "0975717557"},
        follow_redirects=True,
    )
    assert "帳號或密碼錯誤" in old_password_login.get_data(as_text=True)

    new_password_login = client.post(
        "/login",
        data={"account": "gp0975717557", "password": "newpass1234"},
        follow_redirects=True,
    )
    assert "歡迎使用系統" in new_password_login.get_data(as_text=True)


def test_content_module_crud_and_front_visibility(client):
    login(client)

    create_news = client.post(
        "/content/news/new",
        data={
            "title": "國際扶輪交流會",
            "summary": "八月活動預告",
            "body": "歡迎所有會員參加，地點在永康會館。",
            "external_url": "https://example.org/news/1",
            "published": "on",
        },
        follow_redirects=True,
    )
    create_body = create_news.get_data(as_text=True)
    assert create_news.status_code == 200
    assert "最新消息已新增" in create_body
    assert "國際扶輪交流會" in create_body

    update_news = client.post(
        "/content/news/1/edit",
        data={
            "title": "國際扶輪交流會-更新",
            "summary": "九月活動預告",
            "body": "時間已更新，請留意公告。",
            "external_url": "https://example.org/news/updated",
            "published": "on",
        },
        follow_redirects=True,
    )
    update_body = update_news.get_data(as_text=True)
    assert "最新消息已更新" in update_body
    assert "國際扶輪交流會-更新" in update_body

    front_page = client.get("/front/2236")
    front_body = front_page.get_data(as_text=True)
    assert front_page.status_code == 200
    assert "Yongkang International Fellowship" in front_body
    assert "國際扶輪交流會-更新" in front_body

    delete_news = client.post("/content/news/1/delete", follow_redirects=True)
    delete_body = delete_news.get_data(as_text=True)
    assert "最新消息已刪除" in delete_body
    assert "國際扶輪交流會-更新" not in delete_body
