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
