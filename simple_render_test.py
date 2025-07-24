#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simple_test.py - Render 배포 테스트용 간단한 앱
"""

import os
import sys
from datetime import datetime

print("🔍 Python 환경 확인 중...")
print(f"Python 버전: {sys.version}")
print(f"현재 경로: {os.getcwd()}")

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("✅ FastAPI 가져오기 성공")
except ImportError as e:
    print(f"❌ FastAPI 가져오기 실패: {e}")
    sys.exit(1)

try:
    from pydantic import BaseModel
    print("✅ Pydantic 가져오기 성공")
except ImportError as e:
    print(f"❌ Pydantic 가져오기 실패: {e}")
    sys.exit(1)

# 환경 변수 확인
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

print(f"🔑 환경 변수 확인:")
print(f"   OPENAI_API_KEY: {'✅ 설정됨' if OPENAI_API_KEY else '❌ 미설정'}")
print(f"   ANTHROPIC_API_KEY: {'✅ 설정됨' if ANTHROPIC_API_KEY else '❌ 미설정'}")
print(f"   PORT: {os.getenv('PORT', '기본값 사용')}")

# FastAPI 앱 생성
app = FastAPI(
    title="헤어게이터 테스트 앱",
    description="Render 배포 테스트용",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기본 엔드포인트
@app.get("/")
async def root():
    return {
        "message": "🎨 헤어게이터 테스트 앱 - Render 배포 성공!",
        "status": "✅ 정상 작동",
        "timestamp": datetime.now().isoformat(),
        "environment": {
            "python_version": sys.version,
            "port": os.getenv("PORT", "없음"),
            "openai_key": "✅ 설정됨" if OPENAI_API_KEY else "❌ 미설정",
            "anthropic_key": "✅ 설정됨" if ANTHROPIC_API_KEY else "❌ 미설정"
        }
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "테스트 앱 정상 작동 중"
    }

# 간단한 채팅 테스트
class ChatRequest(BaseModel):
    message: str

@app.post("/test-chat")
async def test_chat(request: ChatRequest):
    return {
        "response": f"테스트 응답: {request.message}",
        "timestamp": datetime.now().isoformat(),
        "status": "✅ 채팅 기능 작동"
    }

# 메인 실행 부분
if __name__ == "__main__":
    try:
        import uvicorn
        print("✅ uvicorn 가져오기 성공")
    except ImportError as e:
        print(f"❌ uvicorn 가져오기 실패: {e}")
        sys.exit(1)
    
    # 렌더 포트 설정
    port = int(os.environ.get("PORT", 8000))
    
    print(f"\n🚀 테스트 앱 시작:")
    print(f"   Host: 0.0.0.0")
    print(f"   Port: {port}")
    print(f"   모든 패키지 로드 성공!")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
    except Exception as e:
        print(f"❌ 앱 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)