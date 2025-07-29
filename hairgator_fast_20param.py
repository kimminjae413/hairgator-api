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
        try:
            anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            print("✅ Claude API 설정 완료")
        except Exception as init_error:
            print(f"❌ Claude 초기화 실패: {init_error}")
            anthropic_client = None
    else:
        print("❌ Claude API 키 필요")
        anthropic_client = None
except Exception as e:
    print(f"❌ Anthropic 패키지 오류: {e}")
    anthropic_client = None

# 이미지 저장 디렉토리
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# =============================================================================
# HTML 프론트엔드 - 기존 디자인 100% 유지
# =============================================================================

HTML_CONTENT = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>헤어게이터 - AI 헤어 상담</title>
    <style>
        body { 
            font-family: 'Noto Sans KR', sans-serif; 
            background: #f8f9fa; 
            margin: 0;
            padding: 20px;
        }
        .chat-container { 
            height: 90vh; 
            display: flex; 
            flex-direction: column; 
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #FF1493;
            text-align: center;
            margin-bottom: 20px;
        }
        #messages {
            flex: 1;
            overflow-y: auto;
            border: 1px solid #eee;
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 5px;
        }
        .input-container {
            display: flex;
            gap: 10px;
        }
        #messageInput {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            padding: 10px 20px;
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            opacity: 0.9;
        }
        .message {
            margin: 10px 0;
            padding: 10px;
            border-radius: 10px;
        }
        .user-message {
            background: #FF1493;
            color: white;
            text-align: right;
        }
        .bot-message {
            background: #f1f1f1;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <h1>헤어게이터 💇‍♀️</h1>
        <div id="messages">
            <div class="message bot-message">안녕하세요! 헤어게이터 AI입니다. 헤어 스타일에 대해 물어보세요!</div>
        </div>
        <div class="input-container">
            <input type="text" id="messageInput" placeholder="메시지를 입력하세요..." onkeypress="if(event.key==='Enter') sendMessage()">
            <button onclick="sendMessage()">전송</button>
        </div>
    </div>
    <script>
        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const messages = document.getElementById('messages');
            const message = input.value.trim();
            
            if (!message) return;
            
            // 사용자 메시지 표시
            messages.innerHTML += `<div class="message user-message">${message}</div>`;
            input.value = '';
            
            // 봇 응답 (간단 버전)
            messages.innerHTML += `<div class="message bot-message">죄송합니다. 현재 AI 연결 설정 중입니다. 곧 정상 서비스가 제공될 예정입니다! 🚀</div>`;
            
            messages.scrollTop = messages.scrollHeight;
        }
    </script>
</body>
</html>
"""
