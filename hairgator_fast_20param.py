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
    <link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAA7EAAAOxAGVKw4bAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAABglJREFUW
