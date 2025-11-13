"""프로젝트 라우터 테스트."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_project_not_implemented():
    """프로젝트 생성 엔드포인트 스텁 테스트"""
    response = client.post("/api/v1/projects/", json={
        "name": "Test Project",
        "description": "Test Description",
        "status": "active"
    })
    assert response.status_code == 501
    assert response.json()["detail"] == "Not implemented"


def test_list_projects_not_implemented():
    """프로젝트 목록 조회 엔드포인트 스텁 테스트"""
    response = client.get("/api/v1/projects/")
    assert response.status_code == 501


def test_get_project_not_implemented():
    """프로젝트 조회 엔드포인트 스텁 테스트"""
    response = client.get("/api/v1/projects/1")
    assert response.status_code == 501


def test_update_project_not_implemented():
    """프로젝트 수정 엔드포인트 스텁 테스트"""
    response = client.patch("/api/v1/projects/1", json={
        "name": "Updated Project"
    })
    assert response.status_code == 501


def test_delete_project_not_implemented():
    """프로젝트 삭제 엔드포인트 스텁 테스트"""
    response = client.delete("/api/v1/projects/1")
    assert response.status_code == 501

