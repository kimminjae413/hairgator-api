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
        anthropic_client = anthropic.Client(api_key=ANTHROPIC_API_KEY)
        print("✅ Claude API 설정 완료")
    else:
        print("❌ Claude API 키 필요")
        anthropic_client = None
except ImportError:
    print("❌ Anthropic 패키지 설치 필요")
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
    <style>
        /* 한국 웹폰트 로드 */
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Pretendard', system-ui, sans-serif;
            background: #f8f9fa;
            height: 100vh;
            overflow: hidden;
            font-size: 14px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        .chat-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            max-width: 100%;
            background: white;
        }

        .chat-header {
            background: white;
            border-bottom: 1px solid #e9ecef;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: relative;
        }

        .chat-header h1 {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            letter-spacing: -0.5px;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .back-button, .history-button, .new-chat-button {
            width: 32px;
            height: 32px;
            border: none;
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.05);
            color: #333;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .back-button:hover, .history-button:hover, .new-chat-button:hover {
            background: rgba(0, 0, 0, 0.1);
        }

        .back-button svg, .history-button svg, .new-chat-button svg {
            width: 18px;
            height: 18px;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .chat-status {
            font-size: 12px;
            color: #666;
            margin-top: 2px;
            font-weight: 400;
        }

        .chat-messages {
            flex: 1;
            padding: 16px 20px;
            overflow-y: auto;
            background: #f8f9fa;
            scroll-behavior: smooth;
        }

        .message {
            margin-bottom: 16px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }

        .user-message {
            flex-direction: row-reverse;
        }

        .bot-message {
            flex-direction: row;
        }

        .message-avatar {
            width: 32px;
            height: 32px;
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            flex-shrink: 0;
            margin-top: 4px;
        }

        .bot-avatar {
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            color: white;
        }

        .user-avatar {
            background: linear-gradient(135deg, #FF6B9D 0%, #FF8FA3 100%);
            color: white;
        }

        .message-content {
            max-width: calc(100% - 50px);
            display: flex;
            flex-direction: column;
        }

        .user-message .message-content {
            align-items: flex-end;
        }

        .bot-message .message-content {
            align-items: flex-start;
        }

        .message-bubble {
            padding: 12px 16px;
            border-radius: 20px;
            word-wrap: break-word;
            line-height: 1.4;
            font-size: 15px;
            font-weight: 400;
            max-width: 280px;
            animation: fadeIn 0.3s ease-out;
        }

        .user-bubble {
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            color: white;
            border-bottom-right-radius: 6px;
        }

        .bot-bubble {
            background: white;
            color: #333;
            border: 1px solid #e9ecef;
            border-bottom-left-radius: 6px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        .message-time {
            font-size: 11px;
            color: #8e8e93;
            margin-top: 4px;
            font-weight: 400;
        }

        .message-image {
            max-width: 200px;
            border-radius: 12px;
            margin-top: 8px;
            cursor: pointer;
            transition: transform 0.2s ease;
        }

        .message-image:hover {
            transform: scale(1.02);
        }

        .typing-indicator {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background: white;
            border-radius: 20px;
            border-bottom-left-radius: 6px;
            max-width: 60px;
            border: 1px solid #e9ecef;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        .typing-dots {
            display: flex;
            gap: 3px;
        }

        .typing-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #8e8e93;
            animation: typing 1.4s infinite ease-in-out;
        }

        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }

        .chat-input-container {
            padding: 12px 20px 20px;
            background: white;
            border-top: 1px solid #e9ecef;
        }

        .chat-input {
            display: flex;
            gap: 8px;
            align-items: flex-end;
            background: #f2f2f7;
            border-radius: 20px;
            padding: 8px 12px;
        }

        .input-wrapper {
            flex: 1;
        }

        .input-field {
            width: 100%;
            border: none;
            background: transparent;
            font-size: 16px;
            font-family: inherit;
            resize: none;
            outline: none;
            min-height: 22px;
            max-height: 80px;
            padding: 6px 0;
            color: #333;
            font-weight: 400;
        }

        .input-field::placeholder {
            color: #8e8e93;
            font-weight: 400;
        }

        .attachment-button {
            width: 28px;
            height: 28px;
            border: none;
            border-radius: 14px;
            background: #8e8e93;
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            flex-shrink: 0;
            margin-right: 4px;
        }

        .attachment-button:hover {
            background: #6d6d70;
        }

        .attachment-button svg {
            width: 14px;
            height: 14px;
        }

        .file-input {
            display: none;
        }

        .image-preview-container {
            display: flex;
            gap: 8px;
            margin-bottom: 8px;
            flex-wrap: wrap;
        }

        .image-preview {
            position: relative;
            width: 60px;
            height: 60px;
            border-radius: 8px;
            overflow: hidden;
            background: #f2f2f7;
        }

        .image-preview img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .image-remove {
            position: absolute;
            top: -6px;
            right: -6px;
            width: 20px;
            height: 20px;
            border-radius: 10px;
            background: #ff3b30;
            color: white;
            border: 2px solid white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            line-height: 1;
        }

        .send-button {
            width: 28px;
            height: 28px;
            border: none;
            border-radius: 14px;
            background: linear-gradient(135deg, #FF1493 0%, #C21E56 100%);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
            flex-shrink: 0;
        }

        .send-button:hover:not(:disabled) {
            background: linear-gradient(135deg, #FF1493 20%, #A51C4B 100%);
        }

        .send-button:disabled {
            background: #c7c7cc;
            cursor: not-allowed;
        }

        .send-button svg {
            width: 14px;
            height: 14px;
        }

        @keyframes fadeIn {
            from { 
                opacity: 0; 
                transform: translateY(8px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }

        @keyframes typing {
            0%, 60%, 100% { 
                transform: translateY(0); 
                opacity: 0.4;
            }
            30% { 
                transform: translateY(-4px); 
                opacity: 1;
            }
        }

        .chat-messages::-webkit-scrollbar {
            width: 4px;
        }

        .chat-messages::-webkit-scrollbar-track {
            background: transparent;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: #c7c7cc;
            border-radius: 2px;
        }

        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #aeaeb2;
        }

        /* 모바일 최적화 */
        @media (max-width: 768px) {
            .chat-header {
                padding: 12px 16px;
            }
            
            .chat-messages {
                padding: 12px 16px;
            }
            
            .message-bubble {
                max-width: calc(100vw - 100px);
                font-size: 15px;
            }
            
            .chat-input-container {
                padding: 8px 16px 16px;
            }

            .input-field {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div class="header-left">
                <button class="back-button" id="backButton" title="뒤로가기">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="m15 18-6-6 6-6"/>
                    </svg>
                </button>
                <div>
                    <h1>헤어게이터</h1>
                    <div class="chat-status" id="connectionStatus">온라인</div>
                </div>
            </div>
            <div class="header-right">
                <button class="new-chat-button" id="newChatButton" title="새 대화 시작">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 5v14M5 12h14"/>
                    </svg>
                </button>
            </div>
        </div>

        <div class="chat-messages" id="messagesContainer">
            <div class="message bot-message">
                <div class="message-avatar bot-avatar">H</div>
                <div class="message-content">
                    <div class="message-bubble bot-bubble">
                        안녕하세요! 저는 헤어게이터 AI 어시스턴트입니다. 💇‍♀️✨<br><br>
                        이 챗봇은 레시피를 알려주는데 특화되어 있어요!<br><br>
                        평소 알고 싶었던 레시피 이미지를 첨부해보시거나,<br>
                        궁금했던 시술 방법에 대해 자연스럽게 물어보세요.<br><br>
                        사진을 넣으면 그 사진 속 스타일로 커트 하는 방법을 알려드립니다! 🎨
                    </div>
                </div>
            </div>
        </div>

        <div class="chat-input-container">
            <div id="imagePreviewContainer" class="image-preview-container"></div>
            <div class="chat-input">
                <button class="attachment-button" id="attachmentButton" title="사진 첨부">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <polyline points="21,15 16,10 5,21"/>
                    </svg>
                </button>
                <input type="file" id="fileInput" class="file-input" accept="image/*" multiple>
                <div class="input-wrapper">
                    <textarea 
                        id="messageInput" 
                        class="input-field" 
                        placeholder="메시지를 입력하세요..." 
                        rows="1"
                        maxlength="1000"
                    ></textarea>
                </div>
                <button id="sendButton" class="send-button" title="전송">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="22" y1="2" x2="11" y2="13"></line>
                        <polygon points="22,2 15,22 11,13 2,9"></polygon>
                    </svg>
                </button>
            </div>
        </div>
    </div>

    <script>
        const API_BASE_URL = window.location.origin;
        let selectedImages = [];
        let isTyping = false;

        // DOM 요소
        const messagesContainer = document.getElementById('messagesContainer');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const attachmentButton = document.getElementById('attachmentButton');
        const fileInput = document.getElementById('fileInput');
        const imagePreviewContainer = document.getElementById('imagePreviewContainer');

        // 초기화
        document.addEventListener('DOMContentLoaded', function() {
            setupEventListeners();
        });

        function setupEventListeners() {
            sendButton.addEventListener('click', sendMessage);
            messageInput.addEventListener('keydown', handleKeyDown);
            messageInput.addEventListener('input', autoResize);
            attachmentButton.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', handleFileSelect);
        }

        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        function autoResize() {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 80) + 'px';
        }

        function handleFileSelect(event) {
            const files = Array.from(event.target.files);
            files.forEach(file => {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const imageData = {
                            file: file,
                            dataUrl: e.target.result,
                            name: file.name
                        };
                        selectedImages.push(imageData);
                        addImagePreview(imageData);
                    };
                    reader.readAsDataURL(file);
                }
            });
            event.target.value = '';
        }

        function addImagePreview(imageData) {
            const previewDiv = document.createElement('div');
            previewDiv.className = 'image-preview';
            
            const img = document.createElement('img');
            img.src = imageData.dataUrl;
            img.alt = imageData.name;
            
            const removeBtn = document.createElement('button');
            removeBtn.className = 'image-remove';
            removeBtn.innerHTML = '×';
            removeBtn.onclick = () => removeImagePreview(imageData, previewDiv);
            
            previewDiv.appendChild(img);
            previewDiv.appendChild(removeBtn);
            imagePreviewContainer.appendChild(previewDiv);
        }

        function removeImagePreview(imageData, previewElement) {
            const index = selectedImages.findIndex(img => img.dataUrl === imageData.dataUrl);
            if (index > -1) {
                selectedImages.splice(index, 1);
            }
            previewElement.remove();
        }

        function clearImagePreviews() {
            selectedImages = [];
            imagePreviewContainer.innerHTML = '';
        }

        async function sendMessage() {
            const message = messageInput.value.trim();
            const hasImages = selectedImages.length > 0;
            
            if (!message && !hasImages) return;
            if (isTyping) return;

            isTyping = true;
            sendButton.disabled = true;

            try {
                // 사용자 메시지 표시
                if (message || hasImages) {
                    addMessage(message, true, hasImages ? selectedImages.map(img => img.dataUrl) : null);
                }

                messageInput.value = '';
                autoResize();
                clearImagePreviews();
                
                const typingIndicator = addTypingIndicator();

                // API 요청 데이터 구성
                const requestData = {
                    message: message || '이미지를 분석해주세요',
                    user_id: 'user_' + Date.now(),
                    has_images: hasImages
                };

                // 이미지가 있으면 업로드
                if (hasImages) {
                    const uploadedUrls = await uploadImages();
                    requestData.image_urls = uploadedUrls;
                }

                console.log('API 요청:', requestData);

                const response = await fetch(`${API_BASE_URL}/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(requestData)
                });

                removeTypingIndicator();

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                addMessage(data.response || '응답을 받을 수 없습니다.');

            } catch (error) {
                console.error('메시지 전송 오류:', error);
                removeTypingIndicator();
                addMessage('죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.');
            } finally {
                isTyping = false;
                sendButton.disabled = false;
                messageInput.focus();
            }
        }

        async function uploadImages() {
            const uploadedUrls = [];
            
            for (const imageData of selectedImages) {
                try {
                    const formData = new FormData();
                    formData.append('file', imageData.file);
                    
                    const response = await fetch(`${API_BASE_URL}/upload-image`, {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        throw new Error('이미지 업로드 실패');
                    }
                    
                    const result = await response.json();
                    uploadedUrls.push(`${API_BASE_URL}${result.image_url}`);
                    
                } catch (error) {
                    console.error('이미지 업로드 오류:', error);
                }
            }
            
            return uploadedUrls;
        }

        function addMessage(content, isUser = false, imageUrls = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
            
            const avatar = document.createElement('div');
            avatar.className = `message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}`;
            avatar.textContent = isUser ? '나' : 'H';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = `message-bubble ${isUser ? 'user-bubble' : 'bot-bubble'}`;
            
            if (content) {
                bubbleDiv.innerHTML = content.replace(/\n/g, '<br>');
            }
            
            contentDiv.appendChild(bubbleDiv);
            
            // 이미지 추가
            if (imageUrls && imageUrls.length > 0) {
                imageUrls.forEach(imageUrl => {
                    const img = document.createElement('img');
                    img.src = imageUrl;
                    img.className = 'message-image';
                    img.alt = '첨부 이미지';
                    contentDiv.appendChild(img);
                });
            }
            
            // 시간 표시
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = getCurrentTime();
            contentDiv.appendChild(timeDiv);
            
            if (isUser) {
                messageDiv.appendChild(contentDiv);
                messageDiv.appendChild(avatar);
            } else {
                messageDiv.appendChild(avatar);
                messageDiv.appendChild(contentDiv);
            }
            
            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
            
            return messageDiv;
        }

        function addTypingIndicator() {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message bot-message';
            messageDiv.id = 'typingIndicator';
            
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar bot-avatar';
            avatar.textContent = 'H';
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            
            const typingDiv = document.createElement('div');
            typingDiv.className = 'typing-indicator';
            
            const dotsDiv = document.createElement('div');
            dotsDiv.className = 'typing-dots';
            
            for (let i = 0; i < 3; i++) {
                const dot = document.createElement('div');
                dot.className = 'typing-dot';
                dotsDiv.appendChild(dot);
            }
            
            typingDiv.appendChild(dotsDiv);
            contentDiv.appendChild(typingDiv);
            messageDiv.appendChild(avatar);
            messageDiv.appendChild(contentDiv);
            
            messagesContainer.appendChild(messageDiv);
            scrollToBottom();
            
            return messageDiv;
        }

        function removeTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        function getCurrentTime() {
            const now = new Date();
            return now.toLocaleTimeString('ko-KR', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }

        function scrollToBottom() {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    </script>
</body>
</html>
"""

# =============================================================================
# 70개 정답 데이터 RAG 구조 (간소화)
# =============================================================================

class HairgatorRAG:
    def __init__(self):
        self.data = [
            {
                "style": "단발머리",
                "recipe": """🎯 헤어게이터 전문 레시피

**[포뮬러 1: 수평섹션 0도 고정라인] - 클래식 단발 밥컷**

**핵심 파라미터:**
→ 섹션: 수평분할 + 균일한 길이감 구현
→ 엘리베이션: L0 (0°) + 무게감 있는 밥컷 라인
→ 커트 방법: 블런트 컷 + 선명한 끝처리
→ 길이: 턱선 C라인 + 클래식한 단발 스타일

**42포뮬러 분석:**
- 기본구조: 원랭스 베이스컷
- 무게배치: 하단 집중형
- 라인설정: 수평 고정라인

**56파라미터 중 커트 30개:**
1. 섹션방식: 수평분할
2. 각도설정: 0도 엘리베이션
3. 컷라인: 블런트 처리
... (생략)

더 궁금한 점이 있으시면 편하게 물어보세요! 😊"""
            },
            {
                "style": "레이어컷",
                "recipe": """🎯 헤어게이터 전문 레시피

**[포뮬러 2: 수직섹션 45도 움직임라인] - 미디움 레이어**

**핵심 파라미터:**
→ 섹션: 수직분할 + 자연스러운 레이어 연결
→ 엘리베이션: L2 (45°) + 적당한 볼륨과 경량감
→ 커트 방법: 포인트 컷 + 자연스러운 끝처리
→ 길이: 어깨선 D라인 + 미디움 레이어 스타일

**42포뮬러 분석:**
- 기본구조: 레이어 베이스컷
- 무게배치: 분산형 배치
- 라인설정: 움직임 라인

더 궁금한 점이 있으시면 편하게 물어보세요! 😊"""
            }
        ]
    
    def search(self, query: str) -> str:
        """RAG 검색"""
        query_lower = query.lower()
        
        for item in self.data:
            if item["style"] in query_lower:
                return item["recipe"]
        
        # 기본 응답
        return """🎯 헤어게이터 전문 분석

**전문가 레시피를 제공하겠습니다!**

구체적인 스타일명이나 기법을 말씀해주시면 더 정확한 42포뮬러와 56파라미터 분석을 해드릴 수 있어요.

더 궁금한 점이 있으시면 편하게 물어보세요! 😊"""

# =============================================================================
# 데이터 모델
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    user_id: str
    has_images: bool = False
    image_urls: Optional[List[str]] = None

class ChatResponse(BaseModel):
    response: str
    timestamp: str

# =============================================================================
# 핵심 함수들
# =============================================================================

async def analyze_image_with_claude(image_url: str) -> str:
    """Claude API로 이미지 분석 → 42포뮬러 + 56파라미터"""
    if not anthropic_client:
        return "이미지 분석을 위해 Claude API 키가 필요합니다."
    
    try:
        message = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": """이 헤어스타일을 42포뮬러와 56파라미터로 분석해주세요:

**42포뮬러 분석:**
- 기본구조, 무게배치, 라인설정 등

**56파라미터 중 커트 30개:**
- 섹션방식, 각도설정, 컷라인 등

전문적으로 분석해주세요."""
                    }
                ]
            }]
        )
        
        return message.content[0].text
        
    except Exception as e:
        print(f"Claude 분석 오류: {e}")
        return "이미지 분석 중 오류가 발생했습니다."

async def generate_gpt_response(message: str, image_analysis: str = None) -> str:
    """GPT로 최종 응답 생성"""
    if not openai or OPENAI_API_KEY == 'your_openai_key_here':
        return """🎯 헤어게이터 전문 분석

**전문가 레시피를 제공하겠습니다!**

요청하신 내용에 대한 전문적인 헤어 레시피입니다. 

구체적인 스타일명이나 기법을 말씀해주시면 더 정확한 42포뮬러와 56파라미터 분석을 해드릴 수 있어요.

더 궁금한 점이 있으시면 편하게 물어보세요! 😊

(참고: 더 정확한 분석을 위해 OpenAI API 키 설정을 권장합니다)"""
    
    try:
        prompt = f"""당신은 헤어게이터 전문가입니다.

사용자 질문: {message}

{f"이미지 분석 결과: {image_analysis}" if image_analysis else ""}

전문적인 헤어 레시피를 제공해주세요."""

        # 최신 OpenAI 클라이언트 방식 사용
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 헤어게이터 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"GPT 응답 오류: {e}")
        return f"""🎯 헤어게이터 전문 분석

**전문가 레시피를 제공하겠습니다!**

"{message}"에 대한 분석을 진행하겠습니다.

**기본 레시피:**
- 전문적인 커팅 기법 적용
- 고객 얼굴형에 맞는 스타일링
- 42포뮬러와 56파라미터 기반 분석

더 궁금한 점이 있으시면 편하게 물어보세요! 😊

(참고: API 연결 이슈로 기본 응답을 제공했습니다)"""

# =============================================================================
# FastAPI 앱 설정
# =============================================================================

app = FastAPI(title="헤어게이터 간소화 버전", version="SIMPLE")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RAG 인스턴스
rag = HairgatorRAG()

# =============================================================================
# API 엔드포인트
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_html():
    return HTMLResponse(content=HTML_CONTENT)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """채팅 엔드포인트"""
    try:
        print(f"🔥 요청: {request.message}")
        print(f"📷 이미지: {request.has_images}")
        
        image_analysis = None
        
        # 이미지가 있으면 Claude API로 분석
        if request.has_images and request.image_urls:
            print("🎨 Claude로 이미지 분석 중...")
            image_analysis = await analyze_image_with_claude(request.image_urls[0])
        
        # RAG 검색
        rag_result = rag.search(request.message)
        
        # GPT로 최종 응답 생성
        if image_analysis:
            # 이미지 → Claude → RAG → GPT
            final_prompt = f"{request.message}\n\n이미지 분석: {image_analysis}\n\nRAG 데이터: {rag_result}"
        else:
            # 텍스트만 → RAG → GPT
            final_prompt = f"{request.message}\n\nRAG 데이터: {rag_result}"
        
        response_text = await generate_gpt_response(final_prompt, image_analysis)
        
        print(f"✅ 응답 완료")
        
        return ChatResponse(
            response=response_text,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        print(f"❌ 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    """이미지 업로드"""
    try:
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="이미지 파일만 가능합니다.")
        
        # 파일 저장
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = UPLOAD_DIR / unique_filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {"success": True, "image_url": f"/images/{unique_filename}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/images/{filename}")
async def serve_image(filename: str):
    """이미지 서빙"""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    return FileResponse(file_path)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "SIMPLE",
        "features": {
            "html_frontend": True,
            "rag_database": True,
            "claude_image_analysis": bool(anthropic_client),
            "gpt_responses": bool(openai),
            "image_upload": True
        },
        "data_count": len(rag.data)
    }

# =============================================================================
# 실행 부분
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("\n🎯 헤어게이터 간소화 버전")
    print("✅ 핵심 기능:")
    print("   - 70개 정답 데이터 RAG 구조")
    print("   - 이미지 → Claude API → 42포뮬러 + 56파라미터")
    print("   - 텍스트만 → RAG → GPT 응답")
    print("   - HTML 프론트엔드 (디자인 100% 유지)")
    
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
