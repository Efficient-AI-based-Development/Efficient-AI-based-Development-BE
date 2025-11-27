#!/bin/bash

# 웹 UI 플로우 테스트 스크립트

set -e

# 색상 정의
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 테스트 설정
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
PROJECT_ID="${PROJECT_ID:-148}"
TASK_ID="${TASK_ID:-243}"

echo "=========================================="
echo "🧪 웹 UI 플로우 테스트"
echo "=========================================="
echo ""

# 1. 백엔드 서버 확인
echo "1️⃣  백엔드 서버 확인..."
if curl -s -f "${BACKEND_URL}/docs" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 백엔드 서버 실행 중${NC}"
else
    echo -e "${RED}❌ 백엔드 서버가 실행되지 않았습니다${NC}"
    echo ""
    echo "다음 명령어로 서버를 실행하세요:"
    echo "  uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    exit 1
fi

# 2. Health check
echo ""
echo "2️⃣  Health check..."
HEALTH_RESPONSE=$(curl -s "${BACKEND_URL}/health" || echo "")
if [ -n "$HEALTH_RESPONSE" ]; then
    echo -e "${GREEN}✅ Health check 성공${NC}"
else
    echo -e "${YELLOW}⚠️  Health check 엔드포인트가 없습니다 (무시 가능)${NC}"
fi

# 3. 사용자에게 토큰 입력 요청
echo ""
echo "3️⃣  API 토큰 입력"
echo "   웹에서 로그인 후 개발자 도구(F12) → Application → Local Storage → access_token 복사"
echo "   또는 다음 명령어로 토큰을 발급받을 수 있습니다:"
echo "   curl http://localhost:8000/api/v1/auth/login/google"
echo ""
read -p "Access Token을 입력하세요 (또는 Enter로 건너뛰기): " ACCESS_TOKEN

if [ -z "$ACCESS_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  토큰이 입력되지 않았습니다. 토큰이 필요한 테스트를 건너뜁니다.${NC}"
    echo ""
    echo "토큰 없이 테스트할 수 있는 항목:"
    echo "  - 백엔드 서버 실행 확인 ✅"
    echo ""
    echo "토큰이 필요한 항목:"
    echo "  - MCP 설정 파일 생성"
    echo "  - 태스크 명령어 생성"
    exit 0
fi

# 4. MCP 설정 파일 생성 테스트
echo ""
echo "4️⃣  MCP 설정 파일 생성 테스트..."
CONFIG_RESPONSE=$(curl -s -X GET "${BACKEND_URL}/api/v1/mcp/projects/${PROJECT_ID}/config-file?provider_id=cursor&os=macOS" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json")

if echo "$CONFIG_RESPONSE" | grep -q "configContent"; then
    echo -e "${GREEN}✅ MCP 설정 파일 생성 성공${NC}"
    
    # configContent 추출 및 확인
    CONFIG_CONTENT=$(echo "$CONFIG_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['configContent'])" 2>/dev/null || echo "")
    
    if echo "$CONFIG_CONTENT" | grep -q "API_TOKEN"; then
        echo -e "${GREEN}   ✅ API_TOKEN이 자동으로 포함되어 있습니다${NC}"
    else
        echo -e "${RED}   ❌ API_TOKEN이 포함되어 있지 않습니다${NC}"
    fi
    
    if echo "$CONFIG_CONTENT" | grep -q "atlas-ai"; then
        echo -e "${GREEN}   ✅ MCP 서버 이름이 'atlas-ai'로 설정되어 있습니다${NC}"
    else
        echo -e "${RED}   ❌ MCP 서버 이름이 올바르지 않습니다${NC}"
    fi
    
    if echo "$CONFIG_CONTENT" | grep -q "CONNECTION_ID"; then
        echo -e "${GREEN}   ✅ CONNECTION_ID가 생성되어 있습니다${NC}"
    else
        echo -e "${RED}   ❌ CONNECTION_ID가 생성되지 않았습니다${NC}"
    fi
    
    echo ""
    echo "생성된 설정 파일 내용 (일부):"
    echo "$CONFIG_CONTENT" | head -10
    echo "..."
else
    echo -e "${RED}❌ MCP 설정 파일 생성 실패${NC}"
    echo "응답:"
    echo "$CONFIG_RESPONSE" | head -20
    exit 1
fi

# 5. 태스크 명령어 생성 테스트
echo ""
echo "5️⃣  태스크 명령어 생성 테스트..."
COMMAND_RESPONSE=$(curl -s -X GET "${BACKEND_URL}/api/v1/mcp/tasks/${TASK_ID}/command?provider_id=cursor&command_format=vooster" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  -H "Content-Type: application/json")

if echo "$COMMAND_RESPONSE" | grep -q "command"; then
    echo -e "${GREEN}✅ 태스크 명령어 생성 성공${NC}"
    
    COMMAND=$(echo "$COMMAND_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['command'])" 2>/dev/null || echo "")
    TASK_TITLE=$(echo "$COMMAND_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('taskTitle', 'N/A'))" 2>/dev/null || echo "N/A")
    
    echo "   태스크 제목: $TASK_TITLE"
    echo "   생성된 명령어:"
    echo "   $COMMAND"
    
    if echo "$COMMAND" | grep -q "atlas-ai"; then
        echo -e "${GREEN}   ✅ 명령어에 'atlas-ai'가 포함되어 있습니다${NC}"
    else
        echo -e "${RED}   ❌ 명령어에 'atlas-ai'가 포함되어 있지 않습니다${NC}"
    fi
else
    echo -e "${RED}❌ 태스크 명령어 생성 실패${NC}"
    echo "응답:"
    echo "$COMMAND_RESPONSE" | head -20
    exit 1
fi

# 6. 요약
echo ""
echo "=========================================="
echo -e "${GREEN}✅ 테스트 완료!${NC}"
echo "=========================================="
echo ""
echo "다음 단계:"
echo "1. 위에서 생성된 mcp.json 내용을 Cursor 설정 파일에 붙여넣기"
echo "   위치: ~/Library/Application Support/Cursor/User/globalStorage/mcp.json"
echo ""
echo "2. Cursor 재시작"
echo ""
echo "3. 생성된 명령어를 Cursor MCP 채팅창에 붙여넣기:"
echo "   $COMMAND"
echo ""
echo "4. 자동으로 코드 생성 확인"
echo ""

