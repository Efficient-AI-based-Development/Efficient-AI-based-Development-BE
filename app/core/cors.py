"""CORS configuration."""

from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app) -> None:
    """Configure CORS middleware.

    CORS(Cross-Origin Resource Sharing) 설정:
    - allowed_origins: 허용할 출처 목록
    - allowed_methods: 허용할 HTTP 메소드
    - allowed_headers: 허용할 요청 헤더
    - allow_credentials: 쿠키/인증 정보 전송 허용

    주의:
    - 프로덕션에서는 특정 도메인만 허용해야 함
    - 현재는 개발 편의를 위해 모든 출처 허용
    """
    origins = [
        "https://atrina.vercel.app",
        "http://localhost:5173",  # 개발용
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
