#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헤어게이터 고속 20파라미터 시스템 v8.2 - Claude API 연결 완성
문제1: L3가 뭐야? → 간단 설명만 (레시피 X)
문제2: 단발머리 레시피 → RAG 기반 일관된 답변
문제3: 영어 → 한글 완전 번역
문제4: Claude API 연결 → 이미지 URL 분석 가능

Updated: 2025-01-28
Version: 8.2 - Claude API Connected (Fixed)
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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import requests
import re

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
        
        fast_prompt = f"""Human: 당신은 헤어게이터 20파라미터 전문가입니다.
이미지의 헤어스타일을 보고 빠르게 분석하세요:

분석 요청: {user_message}

다음 20파라미터 형식으로 간결하게 분석:
→ 섹션: [수평/수직/대각선]
→ 엘리베이션: [0~180도]
→ 컷 폼: [O/G/L]
→ 컷 셰이프: [사각형/둥근형/삼각형]
→ 웨이트 플로우: [균형/앞쪽/뒤쪽/사이드]
→ 디자인 라인: [고정/움직임]
→ 길이: [A~H 레벨]
→ 커트 방법: [블런트/포인트/슬라이드]
→ 스타일링 방향: [앞쪽/뒤쪽/사이드]
→ 마무리 룩: [블로우 드라이/자연건조/아이론]
→ 텍스처 마무리: [소프트 글로스/내츄럴/매트]
→ 디자인 강조: [볼륨/셰이프/컬]
→ 자연 가르마: [센터/사이드/랜덤]
→ 스타일링 제품: [라이트/미디움/스트롱 홀드]
→ 앞머리 타입: [풀/사이드/없음]
→ 구조 레이어: [롱/미디움/쇼트]
→ 볼륨 존: [낮음/중간/높음]
→ 내부 디자인: [연결됨/분리됨]
→ 분배: [자연 낙하/이동/수직]
→ 컷 카테고리: [여성/남성 컷]

간결하고 정확하게 분석해주세요.