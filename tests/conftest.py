"""Pytest configuration and fixtures."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """테스트용 FastAPI 클라이언트
    
    각 테스트에서 사용할 수 있는 테스트 클라이언트를 제공합니다.
    
    사용 예시:
        def test_endpoint(client):
            response = client.get("/api/v1/projects/")
            assert response.status_code == 501
    """
    return TestClient(app)


@pytest.fixture
def db_session():
    """테스트용 데이터베이스 세션
    
    TODO: 실제 데이터베이스 대신 메모리 DB나 SQLite를 사용하도록 설정
    """
    # 현재는 구현되지 않음
    # 향후 테스트 DB 설정 시 구현
    pass

