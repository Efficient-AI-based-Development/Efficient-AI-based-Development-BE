"""메인 애플리케이션 테스트."""

from fastapi.testclient import TestClient

from app.main import app


def test_root_redirect():
    """루트 엔드포인트가 /docs로 리다이렉트하는지 확인"""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200


def test_health_check():
    """헬스 체크 엔드포인트 테스트"""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_docs_endpoint():
    """API 문서 엔드포인트 접근 확인"""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200

