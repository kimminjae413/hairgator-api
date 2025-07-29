#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헤어게이터 고속 20파라미터 시스템 v8.3 - HTML 프론트엔드 통합 완성
기존 모든 기능 보존 + 웹 UI 추가
- 20파라미터 분석 시스템 ✅
- Claude API 연결 ✅  
- RAG 데이터베이스 ✅
- 파라미터 질문 감지 ✅
- 영어→한글 번역 ✅
- HTML 채팅 프론트엔드 ✅ (NEW!)

Updated: 2025-01-29
Version: 8.3 - Complete System with HTML Frontend
"""

import os
import sys
import json
import uuid
import base64
import asyncio
import pandas as pd
import locale
from datetime import datetime
from typing import Dict, List, Any, Optional

# UTF-8 인코딩 강제 설정
if sys.platform.startswith('win'):
    try:
        locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Korean_Korea.UTF-8')
        except:
            pass

# 환경 변수 로딩
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=".env", override=True)
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않음. 환경 변수를 직접 설정하세요.")

# 환경 변수 확인 및 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_key_here")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_key_here") 
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

print(f"🔑 Environment Variables Check:")
print(f"   OPENAI_API_KEY: {'✅ Set' if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' else '❌ Not Set'}")
print(f"   ANTHROPIC_API_KEY: {'✅ Set' if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_anthropic_key_here' else '❌ Not Set'}")
print(f"   REDIS_URL: {REDIS_URL}")

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
import requests
import re
import shutil
from pathlib import Path

# OpenAI 및 Anthropic 클라이언트 초기화
try:
    import openai
    if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here':
        openai.api_key = OPENAI_API_KEY
        print("✅ OpenAI API 클라이언트 설정 완료")
    else:
        print("❌ OpenAI API 키가 설정되지 않음")
except ImportError:
    print("❌ OpenAI 패키지가 설치되지 않음")
    openai = None

# Claude API 연결 (렌더 호환 버전으로 수정)
try:
    import anthropic
    if ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != 'your_anthropic_key_here':
        # Anthropic 0.18.1 렌더 호환 방식
        anthropic_client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
        print("✅ Anthropic API 클라이언트 설정 완료")
    else:
        anthropic_client = None
        print("❌ Anthropic API 키가 설정되지 않음")
except Exception as e:
    print(f"❌ Anthropic 패키지 오류: {e}")
    anthropic_client = None

# Redis 클라이언트 초기화
try:
    import redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    redis_available = True
    print("✅ Redis 연결 성공")
except Exception as e:
    redis_client = None
    redis_available = False
    print(f"⚠️ Redis 연결 실패 (메모리 모드 사용): {e}")

# PIL 이미지 처리 초기화
try:
    from PIL import Image
    import io
    print("✅ PIL 이미지 처리 모듈 로드 완료")
except ImportError:
    print("❌ PIL 패키지가 설치되지 않음")
    Image = None
    io = None

# 이미지 저장 디렉토리 생성
UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

# =============================================================================
# HTML 프론트엔드 코드 (NEW!)
# =============================================================================

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>헤어게이터 - 미용사 전용 레시피 챗봇</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%23FF1493'/><text x='16' y='22' text-anchor='middle' fill='white' font-family='Arial Black' font-size='20' font-weight='bold'>H</text></svg>" type="image/svg+xml">
    <link rel="apple-touch-icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9zQYyAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAABvlJREFUeJzt3X+IVWUex/H3Z2Z0ysz8NRoz/khnzXRNQyOLMCNYDNZ+EFZEERFB0B8VBEFQfxQRBUER/RERRQRBUFARF/1RQdEfFRHRH1EQFRERERE">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            height: 100vh;
            overflow: hidden;
        }
        
        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 100%;
            margin: 0 auto;
            background: white;
            position: relative;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            color: white;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 2px 10px rgba(255, 20, 147, 0.3);
            position: relative;
            z-index: 1000;
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .back-button {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 5px;
            border-radius: 50%;
            transition: background-color 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 35px;
            height: 35px;
        }
        
        .back-button:hover {
            background-color: rgba(255, 255, 255, 0.2);
        }
        
        .chat-header h1 {
            font-size: 18px;
            font-weight: 700;
            margin: 0;
        }
        
        .header-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .header-button {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            transition: background-color 0.2s;
            font-weight: 500;
        }
        
        .header-button:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 15px;
            background: #f8f9fa;
        }
        
        .welcome-message {
            text-align: center;
            color: #6c757d;
            font-size: 14px;
            margin: 20px;
            padding: 20px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            line-height: 1.6;
        }
        
        .message {
            display: flex;
            margin-bottom: 15px;
            align-items: flex-end;
            gap: 8px;
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 35px;
            height: 35px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            color: white;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        }
        
        .message.assistant .message-avatar {
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
        }
        
        .message-content {
            max-width: 70%;
            position: relative;
        }
        
        .message-bubble {
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
            position: relative;
            line-height: 1.4;
            font-size: 14px;
        }
        
        .message.user .message-bubble {
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            color: white;
            border-bottom-right-radius: 5px;
        }
        
        .message.assistant .message-bubble {
            background: white;
            color: #333;
            border: 1px solid #e9ecef;
            border-bottom-left-radius: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .message-time {
            font-size: 11px;
            color: #6c757d;
            margin-top: 5px;
            text-align: right;
        }
        
        .message.assistant .message-time {
            text-align: left;
        }
        
        .message-images {
            margin-top: 8px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .message-image {
            max-width: 200px;
            max-height: 200px;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        .message-image:hover {
            transform: scale(1.05);
        }
        
        .typing-indicator {
            display: none;
            align-items: center;
            gap: 8px;
            margin: 10px 0;
        }
        
        .typing-indicator.show {
            display: flex;
        }
        
        .typing-dots {
            display: flex;
            gap: 4px;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #FF1493;
            animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
            40% { transform: scale(1); opacity: 1; }
        }
        
        .chat-input-container {
            padding: 15px 20px;
            background: white;
            border-top: 1px solid #e9ecef;
            display: flex;
            align-items: flex-end;
            gap: 10px;
        }
        
        .image-preview-container {
            display: none;
            padding: 10px 20px 0;
            background: white;
        }
        
        .image-preview {
            position: relative;
            display: inline-block;
            margin-right: 10px;
        }
        
        .preview-image {
            max-width: 80px;
            max-height: 80px;
            border-radius: 8px;
            border: 2px solid #FF1493;
        }
        
        .remove-image {
            position: absolute;
            top: -8px;
            right: -8px;
            background: #FF1493;
            color: white;
            border: none;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            font-size: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .input-wrapper {
            flex: 1;
            position: relative;
            display: flex;
            align-items: flex-end;
            background: #f8f9fa;
            border-radius: 25px;
            padding: 8px 15px;
            min-height: 45px;
        }
        
        .attach-button {
            background: none;
            border: none;
            color: #6c757d;
            font-size: 20px;
            cursor: pointer;
            padding: 5px;
            border-radius: 50%;
            transition: color 0.2s;
            margin-right: 8px;
        }
        
        .attach-button:hover {
            color: #FF1493;
        }
        
        .message-input {
            flex: 1;
            border: none;
            outline: none;
            background: transparent;
            font-size: 14px;
            line-height: 1.4;
            resize: none;
            max-height: 100px;
            overflow-y: auto;
            font-family: inherit;
        }
        
        .send-button {
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            border: none;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            transition: transform 0.2s;
            margin-left: 8px;
        }
        
        .send-button:hover {
            transform: scale(1.05);
        }
        
        .send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .file-input {
            display: none;
        }
        
        .image-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 2000;
            justify-content: center;
            align-items: center;
        }
        
        .modal-content {
            max-width: 90%;
            max-height: 90%;
            position: relative;
        }
        
        .modal-image {
            max-width: 100%;
            max-height: 100%;
            border-radius: 8px;
        }
        
        .modal-close {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            font-size: 18px;
            cursor: pointer;
        }
        
        .history-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1500;
            justify-content: center;
            align-items: center;
        }
        
        .history-content {
            background: white;
            border-radius: 12px;
            width: 90%;
            max-width: 500px;
            max-height: 80%;
            display: flex;
            flex-direction: column;
        }
        
        .history-header {
            padding: 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .history-header h3 {
            margin: 0;
            color: #333;
        }
        
        .history-close {
            background: none;
            border: none;
            font-size: 24px;
            color: #6c757d;
            cursor: pointer;
        }
        
        .history-list {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
        }
        
        .history-item {
            padding: 12px;
            border-bottom: 1px solid #f1f3f4;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        .history-item:hover {
            background-color: #f8f9fa;
        }
        
        .history-item-title {
            font-weight: 500;
            color: #333;
            margin-bottom: 4px;
        }
        
        .history-item-time {
            font-size: 12px;
            color: #6c757d;
        }
        
        @media (max-width: 768px) {
            .chat-header {
                padding: 12px 15px;
            }
            
            .chat-header h1 {
                font-size: 16px;
            }
            
            .chat-messages {
                padding: 15px;
            }
            
            .message-content {
                max-width: 85%;
            }
            
            .chat-input-container {
                padding: 12px 15px;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div class="header-left">
                <button class="back-button" onclick="goBack()">←</button>
                <h1>헤어게이터</h1>
            </div>
            <div class="header-right">
                <button class="header-button" onclick="startNewChat()">새 대화</button>
                <button class="header-button" onclick="showHistory()">지난 대화</button>
            </div>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="welcome-message">
                <strong>안녕하세요! 헤어게이터입니다 💇‍♀️</strong><br><br>
                이 챗봇은 레시피를 알려주는데 특화되어 있어요!<br>
                평소 알고 싶던 레시피 이미지를 첨부해보시거나,<br>
                궁금했던 시술 방법에 대해 편하게 물어보세요.<br><br>
                예: "이 사진 속 스타일로 커트 하는 방법을 알려드립니다"
            </div>
        </div>
        
        <div class="image-preview-container" id="imagePreviewContainer"></div>
        
        <div class="chat-input-container">
            <div class="input-wrapper">
                <button class="attach-button" onclick="document.getElementById('fileInput').click()">📎</button>
                <textarea 
                    class="message-input" 
                    id="messageInput" 
                    placeholder="메시지를 입력하세요..."
                    rows="1"
                    onkeydown="handleKeyPress(event)"
                    oninput="adjustTextareaHeight(this)"
                ></textarea>
            </div>
            <button class="send-button" id="sendButton" onclick="sendMessage()">
                <span>→</span>
            </button>
            <input type="file" id="fileInput" class="file-input" accept="image/*" onchange="handleFileSelect(event)" multiple>
        </div>
    </div>
    
    <div class="image-modal" id="imageModal" onclick="closeImageModal()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <button class="modal-close" onclick="closeImageModal()">×</button>
            <img class="modal-image" id="modalImage" src="" alt="확대 이미지">
        </div>
    </div>
    
    <div class="history-modal" id="historyModal" onclick="closeHistoryModal()">
        <div class="history-content" onclick="event.stopPropagation()">
            <div class="history-header">
                <h3>대화 기록</h3>
                <button class="history-close" onclick="closeHistoryModal()">×</button>
            </div>
            <div class="history-list" id="historyList">
            </div>
        </div>
    </div>

    <script>
        // 전역 변수
        let userId;
        let currentSessionId; 
        let sessionId;
        let uploadedImageUrls = [];
        let conversationHistory = [];
        const API_BASE_URL = window.location.origin;
        
        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            initializeChat();
        });
        
        function initializeChat() {
            // URL 파라미터에서 사용자 정보 추출
            const urlParams = new URLSearchParams(window.location.search);
            userId = urlParams.get('user_id') || 'anonymous_' + Date.now();
            const userName = urlParams.get('user_name') || '사용자';
            
            // 세션 ID 생성
            sessionId = userId + '_session_' + Date.now();
            currentSessionId = sessionId;
            
            console.log('Chat initialized:', { userId, userName, sessionId });
            
            // 저장된 대화 기록 로드
            loadConversationHistory();
        }
        
        function goBack() {
            // 뒤로가기 기능
            if (window.parent && window.parent !== window) {
                // 노코딩 앱 안의 웹뷰인 경우
                try {
                    window.parent.postMessage({
                        type: 'NAVIGATE_BACK',
                        timestamp: Date.now()
                    }, '*');
                } catch (e) {
                    console.log('Parent communication failed, using fallback');
                    if (window.history.length > 1) {
                        window.history.back();
                    } else {
                        window.close();
                    }
                }
            } else {
                // 일반 브라우저인 경우
                if (window.history.length > 1) {
                    window.history.back();
                } else {
                    window.close();
                }
            }
        }
        
        function startNewChat() {
            // 새로운 대화 시작
            sessionId = userId + '_session_' + Date.now();
            currentSessionId = sessionId;
            
            // 화면 초기화
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    <strong>안녕하세요! 헤어게이터입니다 💇‍♀️</strong><br><br>
                    이 챗봇은 레시피를 알려주는데 특화되어 있어요!<br>
                    평소 알고 싶던 레시피 이미지를 첨부해보시거나,<br>
                    궁금했던 시술 방법에 대해 편하게 물어보세요.<br><br>
                    예: "이 사진 속 스타일로 커트 하는 방법을 알려드립니다"
                </div>
            `;
            
            // 업로드된 이미지 초기화
            uploadedImageUrls = [];
            hideImagePreview();
            
            console.log('New chat started:', sessionId);
        }
        
        function showHistory() {
            // 대화 기록 모달 표시
            const historyModal = document.getElementById('historyModal');
            const historyList = document.getElementById('historyList');
            
            // 저장된 세션 목록 가져오기 (실제로는 서버에서 가져와야 함)
            const sessions = getStoredSessions();
            
            historyList.innerHTML = '';
            
            if (sessions.length === 0) {
                historyList.innerHTML = '<div style="text-align: center; color: #6c757d; padding: 20px;">저장된 대화가 없습니다.</div>';
            } else {
                sessions.forEach(session => {
                    const historyItem = document.createElement('div');
                    historyItem.className = 'history-item';
                    historyItem.onclick = () => loadSession(session.id);
                    
                    historyItem.innerHTML = `
                        <div class="history-item-title">${session.title}</div>
                        <div class="history-item-time">${session.time}</div>
                    `;
                    
                    historyList.appendChild(historyItem);
                });
            }
            
            historyModal.style.display = 'flex';
        }
        
        function closeHistoryModal() {
            document.getElementById('historyModal').style.display = 'none';
        }
        
        function getStoredSessions() {
            // 실제로는 서버에서 사용자의 세션 목록을 가져와야 함
            // 여기서는 간단한 예시만 제공
            const stored = [];
            for (let i = 0; i < 5; i++) {
                stored.push({
                    id: `session_${i}`,
                    title: `대화 ${i + 1}`,
                    time: new Date(Date.now() - i * 86400000).toLocaleDateString()
                });
            }
            return stored;
        }
        
        function loadSession(sessionId) {
            // 특정 세션의 대화 기록 로드
            currentSessionId = sessionId;
            closeHistoryModal();
            
            // 실제로는 서버에서 해당 세션의 메시지들을 가져와야 함
            console.log('Loading session:', sessionId);
            
            // 예시: 기존 대화 복원
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    <strong>대화를 복원했습니다</strong><br>
                    세션 ID: ${sessionId}
                </div>
            `;
        }
        
        function loadConversationHistory() {
            // 대화 기록 로드
            conversationHistory = [];
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }
        
        function adjustTextareaHeight(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 100) + 'px';
        }
        
        function handleFileSelect(event) {
            const files = Array.from(event.target.files);
            const imagePreviewContainer = document.getElementById('imagePreviewContainer');
            
            files.forEach(file => {
                if (file.type.startsWith('image/')) {
                    uploadImage(file);
                }
            });
        }
        
        async function uploadImage(file) {
            try {
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch(`${API_BASE_URL}/upload-image`, {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    throw new Error('이미지 업로드 실패');
                }
                
                const result = await response.json();
                const imageUrl = `${API_BASE_URL}${result.image_url}`;
                
                uploadedImageUrls.push(imageUrl);
                showImagePreview(imageUrl);
                
            } catch (error) {
                console.error('Image upload error:', error);
                alert('이미지 업로드 중 오류가 발생했습니다.');
            }
        }
        
        function showImagePreview(imageUrl) {
            const container = document.getElementById('imagePreviewContainer');
            
            const preview = document.createElement('div');
            preview.className = 'image-preview';
            
            preview.innerHTML = `
                <img src="${imageUrl}" class="preview-image" alt="업로드된 이미지">
                <button class="remove-image" onclick="removeImagePreview('${imageUrl}')">×</button>
            `;
            
            container.appendChild(preview);
            container.style.display = 'block';
        }
        
        function removeImagePreview(imageUrl) {
            uploadedImageUrls = uploadedImageUrls.filter(url => url !== imageUrl);
            
            const container = document.getElementById('imagePreviewContainer');
            const previews = container.querySelectorAll('.image-preview');
            
            previews.forEach(preview => {
                const img = preview.querySelector('img');
                if (img.src === imageUrl) {
                    preview.remove();
                }
            });
            
            if (uploadedImageUrls.length === 0) {
                hideImagePreview();
            }
        }
        
        function hideImagePreview() {
            const container = document.getElementById('imagePreviewContainer');
            container.style.display = 'none';
            container.innerHTML = '';
        }
        
        async function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
            
            if (!message && uploadedImageUrls.length === 0) {
                return;
            }
            
            // 사용자 메시지 표시
            if (message || uploadedImageUrls.length > 0) {
                addMessage(message, true, true, uploadedImageUrls.length > 0 ? uploadedImageUrls : null);
            }
            
            // 입력 초기화
            messageInput.value = '';
            messageInput.style.height = 'auto';
            hideImagePreview();
            
            // 타이핑 인디케이터 표시
            showTypingIndicator();
            
            try {
                // API 요청 데이터 구성
                const requestData = {
                    user_id: userId,
                    message: message,
                    conversation_id: currentSessionId,
                    image_url: uploadedImageUrls.length > 0 ? uploadedImageUrls[0] : null,
                    use_rag: true
                };
                
                console.log('Sending request:', requestData);
                
                const response = await fetch(`${API_BASE_URL}/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                hideTypingIndicator();
                
                // AI 응답 표시
                addMessage(result.message, false, true);
                
            } catch (error) {
                console.error('Send message error:', error);
                hideTypingIndicator();
                addMessage('죄송합니다. 오류가 발생했습니다. 다시 시도해 주세요.', false, true);
            }
            
            // 업로드된 이미지 초기화
            uploadedImageUrls = [];
        }
        
        function addMessage(content, isUser = false, showTime = true, imageUrls = null) {
            const chatMessages = document.getElementById('chatMessages');
            
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
            
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'message-avatar';
            avatarDiv.textContent = isUser ? '나' : 'H';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            
            // 메시지 내용 처리
            if (content) {
                // 마크다운 스타일 텍스트를 HTML로 변환
                let formattedContent = content
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/\n/g, '<br>');
                
                bubbleDiv.innerHTML = formattedContent;
            }
            
            // 이미지 추가
            if (imageUrls && imageUrls.length > 0) {
                const imagesDiv = document.createElement('div');
                imagesDiv.className = 'message-images';
                
                imageUrls.forEach(imageUrl => {
                    const img = document.createElement('img');
                    img.src = imageUrl;
                    img.className = 'message-image';
                    img.onclick = () => openImageModal(imageUrl);
                    imagesDiv.appendChild(img);
                });
                
                contentDiv.appendChild(imagesDiv);
            }
            
            contentDiv.appendChild(bubbleDiv);
            
            // 시간 표시
            if (showTime) {
                const timeDiv = document.createElement('div');
                timeDiv.className = 'message-time';
                timeDiv.textContent = getCurrentTime();
                contentDiv.appendChild(timeDiv);
            }
            
            messageDiv.appendChild(avatarDiv);
            messageDiv.appendChild(contentDiv);
            
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function showTypingIndicator() {
            const chatMessages = document.getElementById('chatMessages');
            
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message assistant';
            typingDiv.id = 'typingIndicator';
            
            const avatarDiv = document.createElement('div');
            avatarDiv.className = 'message-avatar';
            avatarDiv.textContent = 'H';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            
            const dotsDiv = document.createElement('div');
            dotsDiv.className = 'typing-dots';
            dotsDiv.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
            
            bubbleDiv.appendChild(dotsDiv);
            contentDiv.appendChild(bubbleDiv);
            typingDiv.appendChild(avatarDiv);
            typingDiv.appendChild(contentDiv);
            
            chatMessages.appendChild(typingDiv);
            scrollToBottom();
        }
        
        function hideTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }
        
        function getCurrentTime() {
            const now = new Date();
            return now.toLocaleTimeString('ko-KR', { 
                hour: '2-digit', 
                minute: '2-digit',
                hour12: false 
            });
        }
        
        function scrollToBottom() {
            const chatMessages = document.getElementById('chatMessages');
            setTimeout(() => {
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 100);
        }
        
        function openImageModal(imageUrl) {
            const modal = document.getElementById('imageModal');
            const modalImage = document.getElementById('modalImage');
            
            modalImage.src = imageUrl;
            modal.style.display = 'flex';
        }
        
        function closeImageModal() {
            const modal = document.getElementById('imageModal');
            modal.style.display = 'none';
        }
        
        // 전역 함수들
        window.goBack = goBack;
        window.startNewChat = startNewChat;
        window.showHistory = showHistory;
        window.closeHistoryModal = closeHistoryModal;
        window.handleKeyPress = handleKeyPress;
        window.adjustTextareaHeight = adjustTextareaHeight; 
        window.handleFileSelect = handleFileSelect;
        window.sendMessage = sendMessage;
        window.removeImagePreview = removeImagePreview;
        window.closeImageModal = closeImageModal;
    </script>
</body>
</html>
"""

# =============================================================================
# 파라미터 질문 감지 시스템 (문제 1 해결)
# =============================================================================

def detect_parameter_question(message: str) -> tuple[bool, str]:
    """파라미터 질문인지 감지하고 해당 파라미터 리턴"""
    if not message or not isinstance(message, str):
        return False, None
    
    message_lower = message.lower().strip()
    
    # 질문 단어들
    question_words = ["뭐야", "무엇", "무슨", "뜻", "의미", "설명", "뭐"]
    
    # 질문 단어가 있는지 확인
    has_question = any(q in message_lower for q in question_words)
    if not has_question:
        return False, None
    
    # 파라미터별 정확한 매칭
    parameter_keywords = {
        "l0": ["l0", "엘제로", "엘 0", "0도"],
        "l1": ["l1", "엘원", "엘 1", "22.5도", "22도"],
        "l2": ["l2", "엘투", "엘 2", "45도"],
        "l3": ["l3", "엘쓰리", "엘 3", "67.5도"],
        "l4": ["l4", "엘포", "엘 4", "90도", "직각"],
        "섹션": ["섹션", "section"],
        "엘리베이션": ["엘리베이션", "elevation"],
        "블런트": ["블런트", "blunt"],
        "포인트": ["포인트", "point"],
        "레이어": ["레이어", "layer"],
        "그래듀에이션": ["그래듀에이션", "graduation"]
    }
    
    # 정확한 매칭 찾기
    for param, keywords in parameter_keywords.items():
        for keyword in keywords:
            if keyword in message_lower:
                return True, param
    
    return False, None

def get_parameter_explanation(param: str) -> str:
    """파라미터별 간단한 설명 제공"""
    explanations = {
        "l0": """## 🔍 L0 (0도 엘리베이션)

**의미:** 바닥과 평행한 0도 각도로 모발을 자연스럽게 떨어뜨린 상태에서 커팅하는 기법이에요.

**효과:** 무게감 있고 깔끔한 라인을 만들어줍니다. 주로 밥컷이나 원랭스 스타일에 사용해요!

더 궁금한 게 있으시면 언제든 물어보세요! 😊""",
        
        "l1": """## 🔍 L1 (22.5도 엘리베이션)

**의미:** 바닥에서 22.5도 각도로 모발을 살짝 들어올려서 자르는 기법이에요.

**효과:** 미세한 그래듀에이션 효과로 자연스러운 볼륨감을 만들어줍니다!

다른 궁금한 점이 있으면 편하게 물어보세요! 😊""",
        
        "l2": """## 🔍 L2 (45도 엘리베이션)

**의미:** 바닥에서 45도 각도로 모발을 들어올려 커팅하는 가장 기본적인 레이어 기법이에요.

**효과:** 적당한 볼륨과 움직임을 만들어주는 가장 많이 사용하는 각도입니다!

또 다른 궁금한 점이 있으시면 언제든 말씀해주세요! 😊""",
        
        "l3": """## 🔍 L3 (67.5도 엘리베이션)

**의미:** 바닥에서 67.5도 각도로 모발을 높이 들어올려서 자르는 기법이에요.

**효과:** 상당한 볼륨과 레이어 효과를 만들어 동적인 느낌을 줍니다!

더 자세한 내용이 궁금하시면 편하게 물어보세요! 😊""",
        
        "l4": """## 🔍 L4 (90도 엘리베이션)

**의미:** 바닥에서 수직으로 90도 각도로 모발을 완전히 세워서 자르는 기법이에요.

**효과:** 최대한의 볼륨과 리프트 효과를 만들어 정수리 볼륨이 필요할 때 사용합니다!

다른 궁금한 게 있으시면 언제든 말씀해주세요! 😊""",
        
        "섹션": """## 🔍 섹션 (Section)

**의미:** 모발을 체계적으로 나누는 구역 분할 방법이에요.

**종류:** 수평섹션, 수직섹션, 대각선섹션이 있어서 원하는 효과에 따라 선택해요!

더 자세한 설명이 필요하시면 편하게 물어보세요! 😊""",
        
        "엘리베이션": """## 🔍 엘리베이션 (Elevation)

**의미:** 모발을 바닥에서 얼마나 들어올리는지를 나타내는 각도예요.

**범위:** L0(0도)부터 L8(180도)까지 있어서 각도에 따라 다른 효과를 만들어요!

궁금한 각도가 있으시면 언제든 물어보세요! 😊""",
        
        "블런트": """## 🔍 블런트 컷 (Blunt Cut)

**의미:** 가위를 모발에 수직으로 대고 일직선으로 똑바르게 자르는 기법이에요.

**효과:** 선명하고 깔끔한 라인을 만들어 무게감 있는 스타일을 연출해요!

다른 커팅 기법도 궁금하시면 편하게 물어보세요! 😊""",
        
        "포인트": """## 🔍 포인트 컷 (Point Cut)

**의미:** 가위 끝을 모발에 비스듬히 대고 지그재그로 자르는 기법이에요.

**효과:** 자연스럽고 부드러운 끝처리로 움직임과 경량감을 만들어줘요!

더 궁금한 기법이 있으시면 언제든 말씀해주세요! 😊""",
        
        "레이어": """## 🔍 레이어 (Layer)

**의미:** 모발을 단계적으로 다른 길이로 잘라서 층을 만드는 기법이에요.

**효과:** 볼륨과 움직임을 만들어 자연스럽고 동적인 스타일을 연출해요!

레이어 종류에 대해 더 궁금하시면 편하게 물어보세요! 😊""",
        
        "그래듀에이션": """## 🔍 그래듀에이션 (Graduation)

**의미:** 모발을 점진적으로 길이를 다르게 해서 자연스러운 연결감을 만드는 기법이에요.

**효과:** 부드러운 연결과 적당한 볼륨으로 세련된 스타일을 만들어줘요!

다른 기법도 궁금하시면 언제든 말씀해주세요! 😊"""
    }
    
    return explanations.get(param, f"'{param}' 파라미터에 대한 설명을 준비 중입니다! 😊")

# =============================================================================
# 헤어디자이너 전용 컨텍스트 감지 시스템
# =============================================================================

class HairgatorProContextSystem:
    """헤어디자이너 전용 컨텍스트 감지 시스템"""
    
    def __init__(self):
        # 헤어디자이너 전문 키워드 (간소화)
        self.professional_hair_keywords = [
            # 기본 헤어 키워드들
            '헤어', '머리', '모발', '컷', '자르', '스타일', '펌', '염색',
            'hair', 'cut', 'style', '단발', '롱', '쇼트', '미디움',
            '볼륨', '레이어', '앞머리', '뒷머리', '옆머리', '가르마',
            '곱슬', '직모', '웨이브', '드라이', '블로우', '스타일링',
            
            # 전문 용어 (간소화)
            '포뮬러', '섹션', '엘리베이션', '디렉션', '리프팅', '디자인라인',
            'formula', 'section', 'elevation', 'direction', 'lifting', 'design line',
            '디스트리뷰션', '웨이트플로우', '아웃라인',
            'distribution', 'weight flow', 'outline'
        ]
        
        # 헤어디자이너 질문 패턴 (간소화)
        self.professional_question_patterns = [
            '레시피', 'recipe', '시술법', '기법', 'technique',
            '어떻게 커트', '어떻게 자르', '커팅방법', 'cutting method',
            '파라미터', 'parameter', '각도', 'angle', '섹션', 'section',
            '몇도로', '어떤 각도', '어떤 섹션', '어떤 방향',
            '볼륨 살리', '무게감 조절', '길이 조절', '레이어', 'layer',
            '이미지 분석', '사진 분석', '헤어스타일 분석', '스타일 해석'
        ]
    
    def is_professional_hair_question(self, query: str) -> bool:
        """헤어디자이너 전문 질문인지 판단 - 모든 헤어 관련 질문을 전문가 질문으로 처리"""
        if not query or not isinstance(query, str):
            return False
            
        query_lower = query.lower()
        
        # 전문 키워드 매칭
        for keyword in self.professional_hair_keywords:
            if keyword.lower() in query_lower:
                return True
        
        # 전문 질문 패턴 매칭
        for pattern in self.professional_question_patterns:
            if pattern.lower() in query_lower:
                return True
        
        return False

# =============================================================================
# 데이터 모델
# =============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., description="메시지 역할")
    content: str = Field(..., description="메시지 내용")
    timestamp: Optional[str] = Field(None, description="타임스탬프")
    
    class Config:
        validate_assignment = True
        str_strip_whitespace = True

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="사용자 ID", min_length=1, max_length=100)
    message: str = Field("", description="메시지 내용 (이미지만 입력 시 빈 문자열 가능)", max_length=2000)
    conversation_id: Optional[str] = Field(None, description="대화 ID")
    image_url: Optional[str] = Field(None, description="이미지 URL")
    use_rag: Optional[bool] = Field(True, description="RAG 사용 여부")
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v, info):
        # 메시지가 비어있으면 빈 문자열로 처리 (이미지만 입력도 허용)
        if not v:
            return ""
        
        v = str(v).strip()
        v = v.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        v = ' '.join(v.split())
        return v
    
    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v):
        if not v or not v.strip():
            raise ValueError('사용자 ID가 비어있습니다')
        return v.strip()

class ChatResponse(BaseModel):
    conversation_id: str = Field(..., description="대화 ID")
    message: str = Field(..., description="응답 메시지")
    timestamp: str = Field(..., description="응답 시간")
    message_type: str = Field(default="chat", description="메시지 타입")
    additional_data: Optional[Dict] = Field(None, description="추가 데이터")

# =============================================================================
# OpenAI 모델 확인 및 선택
# =============================================================================

async def get_available_openai_model():
    """사용 가능한 OpenAI 모델 확인 및 선택"""
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'your_openai_key_here' or not openai:
        return None
    
    preferred_models = [
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo"
    ]
    
    try:
        models_response = await openai.Model.alist()
        available_models = [model.id for model in models_response.data]
        
        for model in preferred_models:
            if model in available_models:
                print(f"✅ 선택된 OpenAI 모델: {model}")
                return model
        
        print("⚠️ 선호 모델을 찾을 수 없음, gpt-3.5-turbo 사용")
        return "gpt-3.5-turbo"
        
    except Exception as e:
        print(f"⚠️ 모델 목록 조회 실패: {e}, gpt-3.5-turbo 사용")
        return "gpt-3.5-turbo"

SELECTED_MODEL = None

# =============================================================================
# RAG 데이터베이스 클래스 (문제 2 해결)
# =============================================================================

class HairgatorRAGDatabase:
    def __init__(self):
        self.styles_data = []
        self.parameters_data = {}
        self.conversation_data = {}
        self.load_excel_data()
    
    def load_excel_data(self):
        """엑셀 데이터 로드 - 간소화된 버전"""
        try:
            print("📚 RAG 데이터베이스 로딩 중...")
            
            excel_file = '헤어게이터 스타일 메뉴 텍스트_women_rag_v2.xlsx'
            if not os.path.exists(excel_file):
                print(f"⚠️ 엑셀 파일을 찾을 수 없음: {excel_file}")
                self.setup_default_data()
                return
            
            # 엑셀 파일 읽기
            try:
                df_styles = pd.read_excel(excel_file, 
                            sheet_name='Style menu_Female',
                            header=7)
                print(f"📊 엑셀 컬럼들: {list(df_styles.columns)}")
            except Exception as e:
                print(f"⚠️ header=7로 읽기 실패: {e}")
                df_styles = pd.read_excel(excel_file, 
                            sheet_name='Style menu_Female',
                            header=0)
                print(f"📊 엑셀 컬럼들: {list(df_styles.columns)}")
            
            print(f"📊 전체 행 수: {len(df_styles)}")
            
            # 데이터 처리
            loaded_count = 0
            for idx, row in df_styles.iterrows():
                model_no = row.get('St model no.') or row.get('model_no') or row.get('St model no') 
                
                if pd.notna(model_no) and str(model_no).strip():
                    style_data = {
                        'model_no': str(model_no).strip(),
                        'introduction_kor': str(row.get('Style Introduction(KOR)', row.get('introduction_kor', ''))).strip(),
                        'management_kor': str(row.get('Management(KOR)', row.get('management_kor', ''))).strip(),
                        'image_analysis_kor': str(row.get('Image Analysis(KOR)', row.get('image_analysis_kor', ''))).strip(),
                        'subtitle': str(row.get('subtitle', '')).strip(),
                        'formula_42': str(row.get('42fomular', row.get('formula_42', ''))).strip(),
                        'session_meaning': str(row.get('세션전환의미', row.get('session_meaning', ''))).strip(),
                        'ground_truth': str(row.get('groundtruce', row.get('ground_truth', ''))).strip(),
                        'image_url': str(row.get('이미지 URL', row.get('image_url', ''))).strip()
                    }
                    
                    # 빈 문자열과 'nan' 처리
                    for key, value in style_data.items():
                        if value in ['nan', 'None', '']:
                            style_data[key] = ''
                    
                    self.styles_data.append(style_data)
                    loaded_count += 1
                    
                    if loaded_count <= 3:
                        print(f"📝 [{loaded_count}] {style_data['model_no']}: {style_data['introduction_kor'][:30]}...")
            
            print(f"✅ RAG 스타일 데이터 로드 완료: {loaded_count}개")
            
        except Exception as e:
            print(f"❌ 엑셀 데이터 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            self.setup_default_data()
    
    def setup_default_data(self):
        """기본 데이터 설정 - 단발 관련 데이터 포함"""
        print("🔧 기본 데이터 설정 중...")
        self.styles_data = [
            {
                'model_no': 'FAL0001',
                'introduction_kor': '클래식 단발 밥컷',
                'ground_truth': '''🎯 20파라미터 헤어 레시피

[포뮬러 1: 수평섹션 0도 고정라인] – 단발 기본 구조

**핵심 파라미터:**
→ 섹션: 수평 + 깔끔한 단발 라인을 위한 수평 분할
→ 엘리베이션: L0 (0°) + 0도 각도로 무게감 있는 밥컷
→ 컷 폼: O (원랭스) + 원랭스로 균일한 단발 길이
→ 컷 셰이프: 사각형 + 구조적이고 깔끔한 형태
→ 웨이트 플로우: 균형 + 균형잡힌 무게감 분포
→ 디자인 라인: 고정 + 일정한 길이의 가이드라인
→ 길이: C + 턱선 길이의 클래식 단발
→ 커트 방법: 블런트 컷 + 선명하고 깔끔한 끝처리
→ 스타일링 방향: 센터 + 중앙 정렬 스타일링
→ 마무리 룩: 블로우 드라이 + 깔끔한 마무리
→ 텍스처 마무리: 소프트 글로스 + 부드러운 윤기
→ 디자인 강조: 셰이프 강조 + 형태가 주요 포인트
→ 자연 가르마: 센터 + 중앙 가르마로 대칭 균형
→ 스타일링 제품: 미디움 홀드 + 적당한 홀드력
→ 앞머리 타입: 풀 프린지 + 이마를 덮는 앞머리
→ 구조 레이어: 레이어 없음 + 단순한 원랭스 구조
→ 볼륨 존: 낮음 + 무게감 있는 볼륨
→ 내부 디자인: 연결됨 + 균일하게 연결된 구조
→ 분배: 자연 낙하 + 자연스러운 스타일링
→ 컷 카테고리: 여성 컷 + 기본 원칙 적용

**커팅 순서:**
1. 준비단계: 모발 상태 체크 및 수평 섹션 분할
2. 1차 커팅: 넥라인에서 가이드라인 설정, L0 0도 유지
3. 2차 정밀: 사이드 영역 수평 연결로 균일한 길이
4. 마감 처리: 블런트 컷으로 선명한 끝처리

**모발 타입별 포인트:**
* 직모: 텐션 일정하게 유지, 웨트 커팅 권장
* 곱슬모: 드라이 커팅으로 실제 길이에서 조정
* 가는모발: 무게감 유지를 위해 레이어 최소화
* 굵은모발: 내부 텍스처링으로 무게감 분산

**관리법:**
* 매일 간단한 블로우 드라이로 형태 유지
* 4-5주 후 재방문으로 라인 정리 권장
* 볼륨 스프레이나 글로스 세럼 소량 사용

더 궁금한 점이 있으시면 편하게 물어보세요! 😊''',
                'subtitle': '단발 밥컷 기본 레시피',
                'formula_42': 'Horizontal Section, L0 Elevation, One-length'
            },
            {
                'model_no': 'FAL0002',
                'introduction_kor': '단발머리 레이어드 스타일', 
                'ground_truth': '''🎯 20파라미터 헤어 레시피

[포뮬러 1: 수직섹션 45도 움직임라인] – 단발 레이어링

**핵심 파라미터:**
→ 섹션: 수직 + 자연스러운 레이어 연결을 위한 수직 분할
→ 엘리베이션: L2 (45°) + 45도 각도로 적당한 볼륨 생성
→ 컷 폼: L (레이어) + 레이어 구조로 움직임과 경량감
→ 컷 셰이프: 둥근형 + 부드러운 여성스러운 형태
→ 웨이트 플로우: 균형 + 전체적으로 균형잡힌 무게감
→ 디자인 라인: 움직임 + 자연스러운 연결감의 가이드라인
→ 길이: C + 턱선 근처의 단발 길이
→ 커트 방법: 포인트 컷 + 자연스러운 끝처리
→ 스타일링 방향: 앞쪽 + 얼굴을 감싸는 방향
→ 마무리 룩: 블로우 드라이 + 자연스러운 볼륨과 윤기
→ 텍스처 마무리: 내츄럴 + 자연스러운 질감
→ 디자인 강조: 셰이프 강조 + 형태가 주요 포인트
→ 자연 가르마: 사이드 + 자연스러운 비대칭 균형
→ 스타일링 제품: 라이트 홀드 + 가벼운 홀드력
→ 앞머리 타입: 사이드 프린지 + 옆으로 흘리는 앞머리
→ 구조 레이어: 쇼트 레이어 + 단발에 맞는 짧은 레이어
→ 볼륨 존: 중간 + 적당한 볼륨감
→ 내부 디자인: 연결됨 + 자연스럽게 연결된 구조
→ 분배: 자연 낙하 + 자연스러운 스타일링
→ 컷 카테고리: 여성 컷 + 기본 원칙 적용

**커팅 순서:**
1. 준비단계: 모발 상태 체크 및 수직 섹션 분할
2. 1차 커팅: 백 센터에서 가이드라인 설정, L2 45도 유지
3. 2차 정밀: 사이드 영역 자연스러운 레이어 연결
4. 마감 처리: 포인트 컷으로 자연스러운 끝처리

**모발 타입별 포인트:**
* 직모: L3로 각도 상향 조정하여 볼륨감 증가
* 곱슬모: 드라이 커팅으로 실제 컬 상태에서 조정
* 가는모발: 과도한 레이어 방지, 무게감 유지
* 굵은모발: 내부 텍스처링으로 경량감 구현

**관리법:**
* 2일에 1회 가벼운 스타일링으로 충분
* 5-6주 후 재방문으로 레이어 정리 권장
* 볼륨 무스나 텍스처 에센스 소량 사용

다른 궁금한 점이 있으시면 언제든 말씀해주세요! 😊''',
                'subtitle': '단발에 레이어를 적용한 동적 스타일',
                'formula_42': 'Vertical Section, L2 Elevation, Layer Cut'
            },
            {
                'model_no': 'FAL0003',
                'introduction_kor': '미디움 레이어 스타일',
                'ground_truth': '''🎯 20파라미터 헤어 레시피

[포뮬러 1: 수직섹션 45도 움직임라인] – 미디움 레이어

**핵심 파라미터:**
→ 섹션: 수직 + 자연스러운 레이어 연결을 위한 수직 분할
→ 엘리베이션: L2 (45°) + 45도 각도로 적당한 볼륨 생성
→ 컷 폼: L (레이어) + 레이어 구조로 움직임과 경량감
→ 컷 셰이프: 둥근형 + 부드러운 여성스러운 형태
→ 웨이트 플로우: 균형 + 전체적으로 균형잡힌 무게감
→ 디자인 라인: 움직임 + 자연스러운 연결감의 가이드라인
→ 길이: D + 어깨선 근처의 미디움 길이
→ 커트 방법: 포인트 컷 + 자연스러운 끝처리
→ 스타일링 방향: 앞쪽 + 얼굴을 감싸는 방향
→ 마무리 룩: 블로우 드라이 + 자연스러운 볼륨과 윤기
→ 텍스처 마무리: 내츄럴 + 자연스러운 질감
→ 디자인 강조: 셰이프 강조 + 형태가 주요 포인트
→ 자연 가르마: 사이드 + 자연스러운 비대칭 균형
→ 스타일링 제품: 라이트 홀드 + 가벼운 홀드력
→ 앞머리 타입: 앞머리 없음 + 이마를 시원하게 노출
→ 구조 레이어: 미디움 레이어 + 볼륨과 길이감의 절충점
→ 볼륨 존: 중간 + 자연스러운 볼륨감
→ 내부 디자인: 연결됨 + 자연스럽게 연결된 구조
→ 분배: 자연 낙하 + 자연스러운 스타일링
→ 컷 카테고리: 여성 컷 + 기본 원칙 적용

**커팅 순서:**
1. 준비단계: 모발 상태 체크 및 수직 섹션 분할
2. 1차 커팅: 백 센터에서 가이드라인 설정, L2 45도 유지
3. 2차 정밀: 사이드 영역 자연스러운 레이어 연결
4. 마감 처리: 포인트 컷으로 자연스러운 끝처리

**모발 타입별 포인트:**
* 직모: L3로 각도 상향 조정하여 볼륨감 증가
* 곱슬모: 드라이 커팅으로 실제 컬 상태에서 조정
* 가는모발: 과도한 레이어 방지, 앞쪽집중 적용
* 굵은모발: 내부 텍스처링으로 무게감 분산

**관리법:**
* 2일에 1회 가벼운 스타일링으로 충분
* 6주 후 재방문으로 레이어 정리 권장
* 볼륨 무스나 텍스처 에센스 소량 사용

또 다른 궁금한 점이 있으시면 편하게 말씀해주세요! 😊''',
                'subtitle': '미디움 길이의 자연스러운 레이어',
                'formula_42': 'Vertical Section, L2 Elevation, Mobile Line'
            }
        ]
        print(f"✅ 기본 데이터 설정 완료: {len(self.styles_data)}개")
    
    def search_similar_styles(self, query: str, limit: int = 3) -> List[Dict]:
        """유사한 스타일 검색 - RAG 기반 일관된 답변을 위해 + 검색 실패시 대안 제공"""
        results = []
        query_lower = query.lower()
        
        print(f"🔍 RAG 검색 시작 - 쿼리: '{query}', 데이터 수: {len(self.styles_data)}")
        
        # 키워드 확장 - 더 유연한 매칭
        search_keywords = [query_lower]
        
        # 기존 키워드 확장
        if '단발' in query_lower or 'bob' in query_lower or '밥' in query_lower:
            search_keywords.extend(['단발', 'bob', '밥', '쇼트', 'short', '턱선', '짧은', '숏'])
        
        if '레시피' in query_lower or 'recipe' in query_lower:
            search_keywords.extend(['커트', 'cut', '시술', '기법', '스타일'])
        
        if '롱' in query_lower or 'long' in query_lower:
            search_keywords.extend(['롱', 'long', '긴머리', '어깨아래', '긴'])
            
        if '미디움' in query_lower or 'medium' in query_lower:
            search_keywords.extend(['미디움', 'medium', '중간길이', '어깨선'])
        
        # 웨이브, 컬 관련 키워드 추가
        if '웨이브' in query_lower or 'wave' in query_lower:
            search_keywords.extend(['웨이브', 'wave', '컬', 'curl', 'S컬', 'C컬'])
        
        if '컬' in query_lower or 'curl' in query_lower:
            search_keywords.extend(['컬', 'curl', '웨이브', 'wave', 'S컬', 'C컬'])
        
        for i, style in enumerate(self.styles_data):
            score = 0
            matched_fields = []
            
            # 모든 텍스트 필드에서 검색 (가중치 적용)
            search_fields = {
                'introduction_kor': 10,  # 가중치 높임
                'ground_truth': 8,       # 가중치 높임
                'subtitle': 5,
                'formula_42': 3,
                'image_analysis_kor': 2,
                'session_meaning': 1,
                'management_kor': 1
            }
            
            for field_name, weight in search_fields.items():
                field_value = str(style.get(field_name, '')).lower()
                
                if field_value and field_value != 'nan':
                    for keyword in search_keywords:
                        if keyword in field_value:
                            score += weight
                            matched_fields.append(f"{field_name}:{keyword}")
            
            if score > 0:
                results.append({
                    'style': style,
                    'score': score,
                    'matched_fields': matched_fields
                })
        
        # 점수순 정렬
        results.sort(key=lambda x: x['score'], reverse=True)
        found_styles = [r['style'] for r in results[:limit]]
        
        print(f"✅ RAG 검색 완료 - 찾은 스타일: {len(found_styles)}개")
        for i, style in enumerate(found_styles):
            print(f"  [{i+1}] {style['model_no']}: {style['introduction_kor']}")
        
        # ★★★ 핵심 수정: 검색 결과가 없어도 기본 스타일 활용 ★★★
        if not found_styles and self.styles_data:
            # 랜덤하게 3개 선택해서 조합 재료로 제공
            import random
            selected_styles = random.sample(self.styles_data, min(3, len(self.styles_data)))
            found_styles = selected_styles
            print(f"⚠️ 정확한 매칭 없음 - RAG 데이터 조합용으로 {len(found_styles)}개 스타일 선택")
            for i, style in enumerate(found_styles):
                print(f"  [조합용{i+1}] {style['model_no']}: {style['introduction_kor']}")
        
        return found_styles

def is_valid_url(url: str) -> bool:
    """URL 유효성 검사"""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        return False
    
    if len(url) < 10 or len(url) > 2000:
        return False
    
    return True

# =============================================================================
# Claude 이미지 분석 함수들 (렌더 호환 버전으로 수정)
# =============================================================================

async def analyze_image_with_claude_fast(image_data: bytes, user_message: str = "") -> str:
    """Claude API를 사용한 고속 이미지 분석 - 렌더 호환 버전"""
    if not anthropic_client:
        return "Claude API 설정 필요"
    
    try:
        # Base64 인코딩
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        print("🧠 Claude 고속 분석 시작...")
        
        # 문자열을 단순하게 처리 (f-string 문제 해결)
        prompt_text = "Human: 당신은 헤어게이터 20파라미터 전문가입니다.\n"
        prompt_text += "이미지의 헤어스타일을 보고 빠르게 분석하세요:\n\n"
        prompt_text += f"분석 요청: {user_message}\n\n"
        prompt_text += "다음 20파라미터 형식으로 간결하게 분석:\n"
        prompt_text += "→ 섹션: [수평/수직/대각선]\n"
        prompt_text += "→ 엘리베이션: [0~180도]\n"
        prompt_text += "→ 컷 폼: [O/G/L]\n"
        prompt_text += "→ 컷 셰이프: [사각형/둥근형/삼각형]\n"
        prompt_text += "→ 웨이트 플로우: [균형/앞쪽/뒤쪽/사이드]\n"
        prompt_text += "→ 디자인 라인: [고정/움직임]\n"
        prompt_text += "→ 길이: [A~H 레벨]\n"
        prompt_text += "→ 커트 방법: [블런트/포인트/슬라이드]\n"
        prompt_text += "→ 스타일링 방향: [앞쪽/뒤쪽/사이드]\n"
        prompt_text += "→ 마무리 룩: [블로우 드라이/자연건조/아이론]\n"
        prompt_text += "→ 텍스처 마무리: [소프트 글로스/내츄럴/매트]\n"
        prompt_text += "→ 디자인 강조: [볼륨/셰이프/컬]\n"
        prompt_text += "→ 자연 가르마: [센터/사이드/랜덤]\n"
        prompt_text += "→ 스타일링 제품: [라이트/미디움/스트롱 홀드]\n"
        prompt_text += "→ 앞머리 타입: [풀/사이드/없음]\n"
        prompt_text += "→ 구조 레이어: [롱/미디움/쇼트]\n"
        prompt_text += "→ 볼륨 존: [낮음/중간/높음]\n"
        prompt_text += "→ 내부 디자인: [연결됨/분리됨]\n"
        prompt_text += "→ 분배: [자연 낙하/이동/수직]\n"
        prompt_text += "→ 컷 카테고리: [여성/남성 컷]\n\n"
        prompt_text += "간결하고 정확하게 분석해주세요."

        # Anthropic 0.18.1 호환 방식
        response = anthropic_client.completions.create(
            model="claude-3-sonnet-20240229",
            max_tokens_to_sample=1200,
            prompt=prompt_text + "\n\nAssistant:",
            stop_sequences=["Human:"]
        )
        
        result = response.completion
        print("✅ Claude 고속 분석 완료!")
        return result
        
    except Exception as e:
        print(f"❌ Claude 분석 오류: {e}")
        return f"이미지 분석 중 오류: {str(e)}"

async def download_image_from_url(url: str) -> bytes:
    """URL에서 이미지 다운로드"""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"❌ 이미지 다운로드 오류: {e}")
        raise HTTPException(status_code=400, detail=f"이미지 다운로드 실패: {str(e)}")

def process_image_fast(image_data: bytes) -> bytes:
    """고속 이미지 처리"""
    try:
        from PIL import Image
        import io
        
        image = Image.open(io.BytesIO(image_data))
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        max_size = (768, 768)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=75, optimize=True)
        return output.getvalue()
        
    except Exception as e:
        print(f"⚠️ 이미지 처리 오류: {e}")
        return image_data

# =============================================================================
# 전문가 응답 생성 함수 - 20파라미터 고속 버전 (문제 3 해결)
# =============================================================================

async def generate_fast_20param_response(messages: List[ChatMessage], claude_analysis: str = None, rag_context: str = None) -> str:
    """20파라미터 기반 고속 전문가 응답 생성 - 영어→한글 완전 번역"""
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'your_openai_key_here' or not openai:
        return generate_fallback_20param_response("API 설정 필요")
    
    global SELECTED_MODEL
    if SELECTED_MODEL is None:
        SELECTED_MODEL = await get_available_openai_model()
        if SELECTED_MODEL is None:
            return generate_fallback_20param_response("모델 사용 불가")
    
    try:
        last_message = messages[-1].content if messages else "헤어스타일 기술 분석 요청"
        
        print(f"⚡ 메시지 분석: {last_message[:50]}...")
        print(f"📊 전체 메시지 수: {len(messages)}")
        
        # RAG 기반 프롬프트 (문제 2 해결) - 전문성 강화
        prompt_base = f"""당신은 헤어게이터 전문가입니다. 아래 RAG 데이터베이스의 정보를 **최우선**으로 활용하여 매우 전문적이고 상세한 답변을 해주세요.

사용자 질문: {last_message}

RAG 데이터베이스 정보:
{rag_context if rag_context else ""}

Claude 이미지 분석 결과:
{claude_analysis if claude_analysis else "이미지 분석 없음"}

위 RAG 데이터와 Claude 분석을 기반으로 다음 형식으로 **매우 상세하고 전문적**으로 답변하세요:

🎯 20파라미터 헤어 레시피

[포뮬러 1: 섹션방식 각도 라인타입] – 스타일명

**핵심 파라미터:**
→ 섹션: [방식] + [상세한 분할 방법과 이유]
→ 엘리베이션: [각도] + [정확한 각도와 볼륨 효과 설명]
→ 컷 폼: [타입] + [구조적 특징과 장점]
→ 컷 셰이프: [형태] + [얼굴형에 따른 인상 변화]
→ 웨이트 플로우: [분배] + [무게감 분포와 시각적 효과]
→ 디자인 라인: [타입] + [연결감과 가이드라인 역할]
→ 길이: [레벨] + [구체적인 길이와 실용성]
→ 커트 방법: [기법] + [정확한 커팅 기술과 끝처리]
→ 스타일링 방향: [방향] + [얼굴 보정 효과]
→ 마무리 룩: [방식] + [최종 결과물과 윤기감]
→ 텍스처 마무리: [질감] + [터치감과 자연스러움]
→ 디자인 강조: [포인트] + [스타일의 핵심 요소]
→ 자연 가르마: [위치] + [균형감과 비례]
→ 스타일링 제품: [홀드력] + [제품 특성과 사용법]
→ 앞머리 타입: [스타일] + [이마 라인과 조화]
→ 구조 레이어: [타입] + [레이어링 목적과 효과]
→ 볼륨 존: [레벨] + [볼륨 위치와 시각적 효과]
→ 내부 디자인: [연결방식] + [내부 구조와 연결성]
→ 분배: [방식] + [자연스러운 흐름과 움직임]
→ 컷 카테고리: [분류] + [적용 원칙과 응용]

**상세한 커팅 순서:**
1. **사전 준비**: [모발 상태와 성장패턴 분석, 얼굴형과 라이프스타일 상담, 정확한 섹션 분할 계획 수립]
2. **1차 가이드라인**: [백 센터 또는 사이드에서 정확한 첫 가이드 설정, 엘리베이션 각도 정밀 측정, 길이 기준점 명확히 설정]
3. **2차 연결 커팅**: [각 섹션별로 가이드라인과의 정확한 연결, 점진적 각도 조정으로 자연스러운 흐름 생성, 볼륨 분산 조절]
4. **3차 정밀 조정**: [연결부위의 미세한 단차 제거, 전체적인 밸런스와 비례 확인, 고객 얼굴형에 맞는 세부 조정]
5. **최종 마무리**: [엔드 텍스처링으로 자연스러운 끝처리, 전체 실루엣 점검, 스타일링 방향성 확인]

**전문 관리법:**
* **일상 관리**: [아침 스타일링은 젖은 모발에 볼륨 무스 소량 발라 자연건조 또는 디퓨저 사용, 저녁엔 브러시로 결을 정리하여 엉킴 방지, 주 2-3회 딥 트리트먼트로 모발 건강 유지]
* **재방문 주기**: [4-6주마다 정기 트림으로 끝단 정리 및 형태 유지, 성장 패턴에 따른 길이 조절, 계절 변화 시 스타일 미세 조정 상담]
* **제품 사용법**: [세팅 제품은 손바닥에 충분히 펴 발라 고르게 분포, 뿌리부터 끝까지 순차적으로 적용, 과도한 사용 피하고 모발 상태에 따라 양 조절]
* **계절별 관리**: [여름철엔 UV 차단 제품과 수분 공급 중심, 겨울철엔 정전기 방지와 유수분 밸런스 관리, 장마철엔 습도 대응 세팅 제품 활용]

**고객 상담 포인트:**
* [아침 스타일링 시간 10분 이내, 주간 관리 난이도 하-중, 직장인 및 학생 추천 스타일]

RAG 데이터와 Claude 이미지 분석을 최대한 활용하여 매우 상세하고 실무적인 답변을 만들어주세요.

**중요: 모든 영어 용어를 한글로 완전 번역하고, RAG 데이터의 전문적인 내용을 그대로 반영하세요.**

영어→한글 번역 예시:
- Section → 섹션
- Elevation → 엘리베이션  
- Cut Form → 컷 폼
- Blunt Cut → 블런트 컷
- Point Cut → 포인트 컷
- Weight Flow → 웨이트 플로우
- Natural Fall → 자연 낙하
- Light Hold → 라이트 홀드
- Medium Layer → 미디움 레이어
- Connected → 연결됨
- Balanced → 균형
- Forward → 앞쪽
- Side → 사이드
- Round → 둥근형
- Natural → 내츄럴"""
        
        print(f"🔬 고속 분석 모델: {SELECTED_MODEL}")
        
        # GPT 호출 (12초 타임아웃으로 다시 조정)
        response = await asyncio.wait_for(
            openai.ChatCompletion.acreate(
                model=SELECTED_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": prompt_base
                    },
                    {
                        "role": "user", 
                        "content": f"RAG 데이터베이스와 Claude 분석 기반으로 20파라미터 헤어 레시피를 모든 영어를 한글로 번역해서 매우 상세하고 전문적으로 알려주세요: {last_message}"
                    }
                ],
                max_tokens=1300,  # 토큰 수 최적화 (모발타입별 포인트 제거로 감소)
                temperature=0.1,
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            ),
            timeout=12.0  # 12초로 다시 조정
        )
        
        result = response.choices[0].message.content
        result = clean_gpt_response(result)  # 영어→한글 번역 적용
        
        print(f"✅ 20파라미터 고속 분석 완료 (길이: {len(result)})")
        return result
        
    except asyncio.TimeoutError:
        print(f"⏰ 20파라미터 분석 타임아웃 (12초)")
        return generate_fallback_20param_response(last_message)
        
    except Exception as e:
        print(f"❌ 20파라미터 분석 생성 오류: {e}")
        return generate_fallback_20param_response(last_message)

def clean_gpt_response(response_text: str) -> str:
    """GPT 응답에서 영어를 한글로 번역하고 텍스트 정리 (문제 3 해결)"""
    try:
        # 완전한 영어 → 한글 번역 사전
        translation_dict = {
            # 파라미터 이름들
            'Section': '섹션',
            'Elevation': '엘리베이션', 
            'Cut Form': '컷 폼',
            'Cut Shape': '컷 셰이프',
            'Weight Flow': '웨이트 플로우',
            'Design Line': '디자인 라인',
            'Length': '길이',
            'Cut Method': '커트 방법',
            'Styling Direction': '스타일링 방향',
            'Finish Look': '마무리 룩',
            'Texture Finish': '텍스처 마무리',
            'Design Emphasis': '디자인 강조',
            'Natural Parting': '자연 가르마',
            'Styling Product': '스타일링 제품',
            'Fringe Type': '앞머리 타입',
            'Structure Layer': '구조 레이어',
            'Volume Zone': '볼륨 존',
            'Interior Design': '내부 디자인',
            'Distribution': '분배',
            'Cut Categories': '컷 카테고리',
            
            # 섹션 타입들
            'Vertical': '수직',
            'Horizontal': '수평',
            'Diagonal': '대각선',
            
            # 웨이트 플로우들
            'Balanced': '균형',
            'Forward': '앞쪽',
            'Backward': '뒤쪽',
            'Side': '사이드',
            'Forward Weighted': '앞쪽집중',
            'Backward Weighted': '뒤쪽집중', 
            'Side Weighted': '사이드집중',
            
            # 디자인 라인들
            'Stationary': '고정',
            'Mobile': '움직임',
            'Combination': '혼합',
            
            # 커트 방법들
            'Blunt': '블런트',
            'Point': '포인트',
            'Blunt Cut': '블런트 컷',
            'Point Cut': '포인트 컷',
            'Slide Cut': '슬라이드 컷',
            
            # 셰이프들
            'Square': '사각형',
            'Round': '둥근형',
            'Triangular': '삼각형',
            
            # 분배 방식들
            'Natural Fall': '자연 낙하',
            'Shifted': '이동된',
            'Perpendicular': '수직',
            
            # 마무리 룩들
            'Blow Dry': '블로우 드라이',
            'Air Dry': '자연 건조',
            'Finger Dry': '핑거 드라이',
            
            # 텍스처들
            'Soft Gloss': '소프트 글로스',
            'Natural': '내츄럴',
            'Matte': '매트',
            
            # 강조 포인트들
            'Volume': '볼륨',
            'Shape': '셰이프',
            'Curl': '컬',
            'Shape Emphasis': '셰이프 강조',
            'Volume Emphasis': '볼륨 강조',
            
            # 가르마들
            'Center': '센터',
            'Side': '사이드',
            'Random': '랜덤',
            
            # 제품 홀드력들
            'Light Hold': '라이트 홀드',
            'Medium Hold': '미디움 홀드',
            'Strong Hold': '스트롱 홀드',
            
            # 앞머리 타입들
            'No Fringe': '앞머리 없음',
            'Full Fringe': '풀 프린지',
            'Side Fringe': '사이드 프린지',
            'Long Fringe': '롱 프린지',
            
            # 레이어 구조들
            'No Layer': '레이어 없음',
            'Long Layer': '롱 레이어',
            'Medium Layer': '미디움 레이어',
            'Short Layer': '쇼트 레이어',
            
            # 볼륨존들
            'Low': '낮음',
            'Medium': '중간',
            'High': '높음',
            
            # 내부 디자인들
            'Connected': '연결됨',
            'Disconnected': '분리됨',
            
            # 컷 카테고리들
            "Women's Cut": '여성 컷',
            "Men's Cut": '남성 컷',
            
            # 기타 자주 사용되는 용어들
            'One-length': '원랭스',
            'Layer': '레이어',
            'Graduation': '그래듀에이션',
            'Texture': '텍스처',
            'Volume': '볼륨',
            'Movement': '움직임',
            'Connection': '연결감',
            'Balance': '균형감',
            'Lifting': '리프팅',
            'Tension': '텐션'
        }
        
        cleaned_text = response_text
        
        # 영어 → 한글 번역 적용 (대소문자 모두 처리)
        for english, korean in translation_dict.items():
            # 정확한 매칭 우선
            cleaned_text = cleaned_text.replace(english, korean)
            # 소문자도 처리
            cleaned_text = cleaned_text.replace(english.lower(), korean)
            # 첫글자만 대문자인 경우도 처리
            cleaned_text = cleaned_text.replace(english.capitalize(), korean)
        
        # JSON 블록 제거
        json_patterns = [
            r'```json.*?```',
            r'```.*?```',
            r'`[^`]*`'
        ]
        
        for pattern in json_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
        
        # 텍스트 정리
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
        cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        print(f"✅ 영어→한글 번역 적용 완료")
        return cleaned_text if cleaned_text else response_text
        
    except Exception as e:
        print(f"⚠️ 응답 정리 중 오류: {e}")
        return response_text

def generate_fallback_20param_response(user_message: str) -> str:
    """20파라미터용 기본 응답 생성"""
    return f"""⚡ 20파라미터 헤어 레시피

**전문가 질문 분석**: {user_message[:100]}...

🎯 [포뮬러 1: 수직섹션 45도 움직임라인] – 미디움 레이어 설정

**핵심 파라미터:**
→ 섹션: 수직 + 자연스러운 레이어 연결을 위한 수직 분할
→ 엘리베이션: L2 (45°) + 45도 각도로 적당한 볼륨과 움직임 생성
→ 컷 폼: L (레이어) + 레이어 구조로 움직임과 경량감 동시 구현
→ 컷 셰이프: 둥근형 + 둥근 형태로 부드러운 여성스러운 인상
→ 웨이트 플로우: 균형 + 전체적으로 균형잡힌 무게감 분포
→ 디자인 라인: 움직임 + 움직이는 가이드라인으로 자연스러운 연결감
→ 길이: D + 어깨선 근처 길이로 실용성과 여성스러움 동시 추구
→ 커트 방법: 포인트 컷 + 포인트 컷으로 자연스러운 끝처리
→ 스타일링 방향: 앞쪽 + 앞쪽 방향 스타일링으로 얼굴을 감싸는 효과
→ 마무리 룩: 블로우 드라이 + 블로우 드라이 마무리로 자연스러운 볼륨과 윤기
→ 텍스처 마무리: 내츄럴 + 자연스러운 질감으로 인위적이지 않은 마무리
→ 디자인 강조: 셰이프 강조 + 형태 강조로 헤어스타일의 실루엣이 주요 포인트
→ 자연 가르마: 사이드 + 옆가르마로 자연스러운 비대칭 균형
→ 스타일링 제품: 라이트 홀드 + 가벼운 홀드력 제품으로 자연스러운 움직임
→ 앞머리 타입: 앞머리 없음 + 앞머리 없는 스타일로 이마를 시원하게 노출
→ 구조 레이어: 미디움 레이어 + 중간 레이어 구조로 볼륨과 길이감의 절충점
→ 볼륨 존: 중간 + 중간 정도의 볼륨존으로 자연스러운 볼륨
→ 내부 디자인: 연결됨 + 내부가 자연스럽게 연결된 구조
→ 분배: 자연 낙하 + 자연스러운 낙하감으로 무리 없는 스타일링
→ 컷 카테고리: 여성 컷 + 여성 커트의 기본 원칙 적용

**커팅 순서:**
1. **준비단계**: 모발 상태 체크 및 7개 구역 분할
2. **1차 커팅**: 백 센터에서 가이드라인 설정, L2 45도 유지
3. **2차 정밀**: 사이드와 백 영역 자연스러운 연결
4. **마감 처리**: 포인트 컷으로 자연스러운 끝처리

**모발 타입별 포인트:**
* **직모**: L3로 각도 상향 조정, 웨트 커팅 권장
* **곱슬모**: 드라이 커팅으로 실제 컬 상태에서 조정
* **가는모발**: 과도한 레이어 방지, 앞쪽집중 적용
* **굵은모발**: 내부 텍스처링으로 무게감 분산

**관리법:**
* 2일에 1회 가벼운 스타일링으로 충분
* 6주 후 재방문 권장
* 볼륨 무스나 텍스처 에센스 소량 사용

더 궁금한 점이 있으시면 편하게 물어보세요! 😊"""

# =============================================================================
# 대화 관리자
# =============================================================================

class ConversationManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.redis_available = redis_client is not None
        self.conversation_ttl = 86400 * 7
        self.memory_storage = {}
    
    def get_conversation_key(self, user_id: str, conversation_id: str) -> str:
        return f"hairgator:conversation:{user_id}:{conversation_id}"
    
    def create_conversation(self, user_id: str) -> str:
        return str(uuid.uuid4())
    
    def add_message(self, user_id: str, conversation_id: str, message: ChatMessage):
        conversation_key = self.get_conversation_key(user_id, conversation_id)
        
        if not message.timestamp:
            message.timestamp = datetime.now().isoformat()
        
        if self.redis_available:
            try:
                self.redis.lpush(conversation_key, message.model_dump_json())
                self.redis.expire(conversation_key, self.conversation_ttl)
            except:
                if conversation_key not in self.memory_storage:
                    self.memory_storage[conversation_key] = []
                self.memory_storage[conversation_key].insert(0, message.model_dump_json())
        else:
            if conversation_key not in self.memory_storage:
                self.memory_storage[conversation_key] = []
            self.memory_storage[conversation_key].insert(0, message.model_dump_json())
    
    def get_conversation_history(self, user_id: str, conversation_id: str, limit: int = 10) -> List[ChatMessage]:
        conversation_key = self.get_conversation_key(user_id, conversation_id)
        
        messages_json = []
        
        if self.redis_available:
            try:
                messages_json = self.redis.lrange(conversation_key, 0, limit - 1)
            except:
                messages_json = self.memory_storage.get(conversation_key, [])[:limit]
        else:
            messages_json = self.memory_storage.get(conversation_key, [])[:limit]
        
        messages = []
        for msg_json in reversed(messages_json):
            try:
                msg_data = json.loads(msg_json)
                messages.append(ChatMessage(**msg_data))
            except:
                continue
        
        return messages

# startup 이벤트 핸들러를 lifespan으로 수정
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 실행
    global SELECTED_MODEL
    if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' and openai:
        print("🔍 사용 가능한 OpenAI 모델 확인 중...")
        SELECTED_MODEL = await get_available_openai_model()
    yield
    # 종료 시 실행 (필요시)

# FastAPI 앱에 lifespan 적용
app = FastAPI(
    title="헤어게이터 고속 20파라미터 시스템 v8.3 - HTML 프론트엔드 통합 완성",
    description="기존 모든 고급 기능 + HTML 웹 UI 추가 완료",
    version="8.3-html-integrated",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 예외 핸들러
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    print(f"❌ 422 JSON 오류 발생: {exc}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": "JSON 형식 오류가 발생했습니다.",
            "error": str(exc)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc):
    print(f"❌ 일반 오류: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "서버 처리 중 오류가 발생했습니다.",
            "error": str(exc)
        }
    )

# 정적 파일 서빙
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("📁 Static 파일 서빙 활성화")
except Exception:
    os.makedirs("static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("📁 Static 폴더 생성 및 서빙 활성화")

# 인스턴스 생성
rag_db = HairgatorRAGDatabase()
professional_context = HairgatorProContextSystem()
conversation_manager = ConversationManager(redis_client)

# =============================================================================
# API 엔드포인트
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_html():
    """HTML 프론트엔드 서빙 (NEW!)"""
    return HTMLResponse(content=HTML_CONTENT)

@app.post("/chat", response_model=ChatResponse)
async def fast_20param_chat(request: ChatRequest):
    """헤어디자이너 전용 고속 20파라미터 분석 - 4가지 문제 해결 + Claude API 연결"""
    try:
        user_id = str(request.user_id).strip()
        user_message = str(request.message).strip() if request.message else ""
        image_url = request.image_url
        
        # image_url이 "string"이나 빈 문자열인 경우 None으로 처리
        if image_url in ["string", "", "null", "undefined"]:
            image_url = None
        
        print(f"⚡ 입력값 확인:")
        print(f"   user_message: '{user_message}'")
        print(f"   image_url: {image_url}")
        
        # 이미지만 있고 메시지가 없는 경우 기본 메시지 설정
        if not user_message and image_url:
            user_message = "이미지 헤어스타일 분석해줘"
            print(f"🖼️ 이미지만 입력 - 기본 메시지 설정: {user_message}")
        
        # 이미지도 메시지도 없는 경우에만 에러
        if not user_message and not image_url:
            user_message = "헤어스타일 분석 요청"
            print(f"⚠️ 빈 요청 - 기본 메시지 설정: {user_message}")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="사용자 ID가 비어있습니다")
        
        conversation_id = request.conversation_id or conversation_manager.create_conversation(user_id)
        use_rag = request.use_rag
        
        print(f"⚡ 헤어게이터 v8.3 - HTML 프론트엔드 통합 완성 버전")
        print(f"📝 질문: {user_message[:50]}...")
        
        # **문제 1 해결: 파라미터 질문 감지를 최우선으로 처리**
        is_param_question, param_name = detect_parameter_question(user_message)
        
        if is_param_question and param_name:
            print(f"🎯 파라미터 질문 감지: {param_name} - 즉시 설명 제공")
            
            # 파라미터 설명만 제공 (GPT 호출 안함)
            param_explanation = get_parameter_explanation(param_name)
            
            # 사용자 메시지 저장
            user_msg = ChatMessage(
                role="user",
                content=user_message,
                timestamp=datetime.now().isoformat()
            )
            conversation_manager.add_message(user_id, conversation_id, user_msg)
            
            # 파라미터 설명 응답 저장
            assistant_msg = ChatMessage(
                role="assistant",
                content=param_explanation,
                timestamp=datetime.now().isoformat()
            )
            conversation_manager.add_message(user_id, conversation_id, assistant_msg)
            
            return ChatResponse(
                conversation_id=conversation_id,
                message=param_explanation,
                timestamp=assistant_msg.timestamp,
                message_type="parameter_explanation",
                additional_data={
                    "parameter_detected": param_name,
                    "explanation_only": True,
                    "gpt_call": False
                }
            )
        
        # 파라미터 질문이 아닌 경우: 레시피 요청으로 처리
        print(f"📋 레시피 요청으로 처리 - RAG 우선 적용")
        
        # 사용자 메시지 저장 - 먼저 저장해서 히스토리에 포함
        user_msg = ChatMessage(
            role="user",
            content=user_message + (f" [이미지: {image_url}]" if image_url else ""),
            timestamp=datetime.now().isoformat()
        )
        conversation_manager.add_message(user_id, conversation_id, user_msg)
        
        # Claude 이미지 분석 (활성화됨)
        claude_analysis = None
        if image_url and anthropic_client and is_valid_url(image_url):
            try:
                print(f"🖼️ 이미지 분석 시작: {image_url[:50]}...")
                image_data = await download_image_from_url(image_url)
                processed_image = process_image_fast(image_data)
                claude_analysis = await analyze_image_with_claude_fast(processed_image, user_message)
                print(f"✅ Claude 분석 완료 - 길이: {len(claude_analysis)}")
            except Exception as e:
                print(f"⚠️ 이미지 분석 실패: {e}")
                claude_analysis = f"이미지 처리 오류: {str(e)}"
        elif image_url:
            print(f"⚠️ Claude API 미설정 - 이미지 분석 생략")

        # **문제 2 해결: RAG 컨텍스트 생성 강화 - 검색 실패시에도 조합 재료 제공**
        rag_context = None
        if use_rag:
            print(f"🔍 RAG 검색 시작 - 쿼리: '{user_message}', 데이터 수: {len(rag_db.styles_data)}")
            similar_styles = rag_db.search_similar_styles(user_message)
            if similar_styles:
                # 정확한 매칭이든 조합용이든 관계없이 RAG 컨텍스트 생성
                rag_context = f"**RAG 데이터베이스 기반 레시피 생성 ('{user_message}' 요청 기반):**\n\n"
                rag_context += "아래 기존 데이터들을 참고하여 요청에 맞는 새로운 레시피를 생성하세요:\n\n"
                
                for i, style in enumerate(similar_styles[:3]):  # 최대 3개
                    rag_context += f"[참고 데이터 {i+1}]\n"
                    rag_context += f"모델번호: {style.get('model_no', 'N/A')}\n"
                    rag_context += f"스타일명: {style.get('introduction_kor', 'N/A')}\n"
                    rag_context += f"42포뮬러: {style.get('formula_42', 'N/A')}\n"
                    if style.get('ground_truth'):
                        # Ground Truth 전체 포함 (전문성 강화를 위해)
                        full_truth = style.get('ground_truth', '')
                        rag_context += f"완전한 레시피: {full_truth}\n"
                    rag_context += "\n" + "-"*30 + "\n"
                
                rag_context += f"\n위 데이터들을 창조적으로 조합하여 '{user_message}' 요청에 최적화된 20파라미터 레시피를 생성해주세요."
                
                print(f"✅ RAG 컨텍스트 생성 완료 - {len(similar_styles)}개 스타일 기반 조합")
            else:
                print("⚠️ RAG 검색 결과 없음 - 기본 조합 재료 제공 불가")
        else:
            print("📚 RAG 비활성화")
        
        # 대화 히스토리 (간소화) - 반드시 현재 메시지 포함해서 전달
        conversation_history = conversation_manager.get_conversation_history(
            user_id, conversation_id, limit=5
        )
        
        # 현재 사용자 메시지도 포함
        current_user_msg = ChatMessage(
            role="user",
            content=user_message,
            timestamp=datetime.now().isoformat()
        )
        conversation_history.append(current_user_msg)
        
        print(f"📋 대화 히스토리: {len(conversation_history)}개 메시지")
        
        # **문제 3 해결: 영어→한글 완전 번역이 적용된 20파라미터 응답 생성**
        print(f"⚡ 20파라미터 고속 분석 실행 (영어→한글 번역 적용)")
        
        response_text = await generate_fast_20param_response(
            conversation_history,
            claude_analysis,
            rag_context
        )
        
        # 응답 저장 - 대화 히스토리 유지를 위해
        assistant_msg = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat()
        )
        
        # Redis나 메모리에 assistant 응답도 저장
        conversation_manager.add_message(user_id, conversation_id, assistant_msg)
        
        print(f"✅ 헤어게이터 v8.3 분석 완료 - 길이: {len(response_text)}")
        print(f"📋 대화 히스토리 저장 완료 - 총 메시지: {len(conversation_manager.get_conversation_history(user_id, conversation_id, limit=20))}개")
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=response_text,
            timestamp=assistant_msg.timestamp,
            message_type="fast_20_parameter_analysis",
            additional_data={
                "professional_analysis": True,
                "claude_analysis_used": bool(claude_analysis and "오류" not in claude_analysis),
                "rag_context_used": bool(rag_context),
                "image_processed": bool(image_url),
                "parameter_count": 20,
                "analysis_version": "v8.3-html-integrated",
                "fixes_applied": {
                    "parameter_detection": True,
                    "rag_consistency": True,
                    "korean_translation": True,
                    "claude_api_connection": True,
                    "html_frontend": True
                },
                "conversation_saved": True
            }
        )
        
    except ValueError as e:
        print(f"❌ 입력 데이터 오류: {e}")
        raise HTTPException(status_code=422, detail=f"입력 데이터 형식 오류: {str(e)}")
    except Exception as e:
        print(f"❌ 분석 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 처리 오류: {str(e)}")

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """이미지 업로드 엔드포인트 (NEW!)"""
    try:
        # 파일 검증
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")
        
        # 고유 파일명 생성
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        # 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 이미지 URL 반환
        image_url = f"/images/{unique_filename}"
        
        return {"success": True, "image_url": image_url, "filename": unique_filename}
        
    except Exception as e:
        print(f"❌ 이미지 업로드 오류: {e}")
        raise HTTPException(status_code=500, detail="이미지 업로드 중 오류가 발생했습니다.")

@app.get("/images/{filename}")
async def serve_image(filename: str):
    """업로드된 이미지 서빙 (NEW!)"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    
    return FileResponse(file_path)

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": "8.3-html-integrated",
        "timestamp": datetime.now().isoformat(),
        "features": {
            "html_frontend": True,
            "parameter_question_detection": True,
            "rag_based_consistency": True,
            "korean_translation": True,
            "conversation_history": True,
            "natural_chat": True,
            "image_url_support": True,
            "claude_image_analysis": True,
            "20_parameter_analysis": True,
            "image_upload": True,
            "web_ui": True
        },
        "services": {
            "redis": "connected" if redis_available else "memory_mode",
            "openai": "configured" if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' else "not_configured",
            "claude": "configured" if anthropic_client else "not_configured"
        },
        "data": {
            "rag_styles": len(rag_db.styles_data),
            "parameter_explanations": 11,
            "translation_pairs": 50,
            "professional_keywords": len(professional_context.professional_hair_keywords)
        },
        "flows": {
            "web_ui": "browser > html_frontend > chat_interface > api",
            "text_only": "user > fastapi > rag > gpt > 20param_recipe",
            "image_url": "user > fastapi > claude_analysis > rag > gpt > enhanced_20param_recipe",
            "image_upload": "user > upload > html > chat > fastapi > claude > rag > gpt > recipe"
        },
        "new_features_v8_3": [
            "완전한 HTML 웹 UI 추가",
            "이미지 업로드 기능 구현",
            "채팅 인터페이스 완성",
            "오마이앱 웹뷰 최적화",
            "기존 모든 고급 기능 보존"
        ]
    }

# main 실행 부분
if __name__ == "__main__":
    import uvicorn
    
    print("\n⚡ 헤어게이터 고속 20파라미터 시스템 v8.3 - HTML 프론트엔드 통합 완성")
    print("🔧 v8.3 새로운 기능:")
    print("   ✅ 완전한 HTML 웹 UI 추가 - 채팅 인터페이스 완성")
    print("   ✅ 이미지 업로드 기능 구현 - 파일 업로드 + 서빙")
    print("   ✅ 오마이앱 웹뷰 최적화 - 모바일 환경 완벽 지원")
    print("   ✅ 기존 모든 고급 기능 100% 보존:")
    print("       - 20파라미터 분석 시스템")
    print("       - Claude API 이미지 분석")
    print("       - RAG 데이터베이스 활용")
    print("       - 파라미터 질문 감지")
    print("       - 영어→한글 완전 번역")
    print("       - 대화 히스토리 관리")
    
    # 렌더 환경 감지 및 포트 설정
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"\n🚀 서버 시작:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   OpenAI: {'✅ 설정됨' if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' else '❌ 미설정'}")
    print(f"   Claude: {'✅ 설정됨' if anthropic_client else '❌ 미설정'}")
    print(f"   Redis: {'메모리모드' if not redis_available else '연결됨'}")
    print(f"   RAG 스타일: {len(rag_db.styles_data)}개")
    
    print(f"\n🎯 지원하는 사용 방식:")
    print(f"   🌐 웹 브라우저: http://localhost:{port} (HTML UI)")
    print(f"   📱 오마이앱: 웹뷰로 HTML 로드")
    print(f"   🔌 API 직접: POST /chat (JSON)")
    
    print(f"\n✨ 완전한 통합 시스템:")
    print(f"   📝 텍스트만: 웹UI > fastapi > rag > gpt > 답변")
    print(f"   🖼️ 이미지 업로드: 웹UI > 업로드 > claude > rag > gpt > 답변")
    print(f"   🔗 이미지 URL: 웹UI > claude > rag > gpt > 답변")
    
    print(f"\n🎉 v8.3 완성 - 기존 전문 기능 + 완전한 웹 UI!")
    
    try:
        uvicorn.run(
            app, 
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            workers=1,
            timeout_keep_alive=30,
            limit_concurrency=10
        )
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
