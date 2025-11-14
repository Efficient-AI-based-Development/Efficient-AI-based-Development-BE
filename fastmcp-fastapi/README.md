# FastMCP API Server

FastMCP (Fast Model Context Protocol) API 서버입니다.

## 배포 방법

### Docker를 사용한 배포

```bash
# Docker 이미지 빌드
docker build -t fastmcp-api:latest .

# Docker 컨테이너 실행
docker run -d \
  --name fastmcp-api \
  -p 8787:8787 \
  -e FASTMCP_TOKEN=your-token-here \
  -e FASTMCP_MODE=mock \
  -e OPENAI_API_KEY=your-openai-key \
  -e ANTHROPIC_API_KEY=your-anthropic-key \
  fastmcp-api:latest
```

### 환경 변수

- `FASTMCP_TOKEN`: FastMCP 인증 토큰 (필수)
- `FASTMCP_MODE`: 실행 모드 (`mock` 또는 `real`, 기본값: `mock`)
- `OPENAI_API_KEY`: OpenAI API 키 (real 모드에서 필요)
- `ANTHROPIC_API_KEY`: Anthropic API 키 (real 모드에서 필요)

### 포트

- 기본 포트: `8787`

### Health Check

```bash
curl http://localhost:8787/health
```
