#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헤어게이터 간소화 버전 - 핵심 기능만 유지
- 70개 정답 데이터 RAG 구조 ✅
- 이미지 → Claude API → 42포뮬러 + 56파라미터 → GPT ✅
- 텍스트만 → 바로 GPT 응답 ✅
- HTML 프론트엔드 (디자인 100% 유지) ✅

Version: SIMPLE - Core Features Only
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

# 환경 변수 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_key_here")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_key_here")

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import requests
import shutil
from pathlib import Path

# 클라이언트 초기화
try:
    import openai
    if OPENAI_API_KEY != 'your_openai_key_here':
        openai.api_key = OPENAI_API_KEY
        print("✅ OpenAI API 설정 완료")
    else:
        print("❌ OpenAI API 키 필요")
        openai = None
except ImportError:
    print("❌ OpenAI 패키지 설치 필요")
    openai = None

try:
    import anthropic
    if ANTHROPIC_API_KEY != 'your_anthropic_key_here':
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print("✅ Claude API 설정 완료")
    else:
        print("❌ Claude API 키 필요")
        anthropic_client = None
except Exception as e:
    print(f"❌ Anthropic 설정 오류: {e}")
    anthropic_client = None

# 이미지 저장 디렉토리
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# =============================================================================
# HTML 프론트엔드 - 기존 디자인 100% 유지
# =============================================================================

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>헤어게이터 - AI 헤어 상담</title>
    <link rel="icon" type="image/png" href="data:image/png;base64,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" />
