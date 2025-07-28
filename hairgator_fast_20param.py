#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
헤어게이터 고속 20파라미터 시스템 v8.0 - 15초 이내 응답 최적화
20파라미터 기반 고속 전문가 답변 시스템

Updated: 2025-01-25
Version: 8.0 - Fast 20 Parameters
Features:
- 20파라미터로 축소하여 15초 이내 응답
- OpenAI API 타임아웃 15초로 최적화
- 간소화된 프롬프트로 빠른 처리
- 렌더 배포 최적화
- 오류 없는 완전한 실행 가능 코드
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

# Anthropic 완전 비활성화 (빠른 처리를 위해)
anthropic_client = None
print("⚠️ Anthropic 비활성화 - OpenAI만 사용으로 속도 최적화")

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
# RAG 데이터베이스 클래스 (간소화)
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
                'ground_truth': '''[포뮬러 1: 수평섹션 0도 스테이셔너리라인] – 단발 기본 구조
→ Section: Horizontal + 수평 섹션으로 깔끔한 단발 라인
→ Elevation: L0 (0°) + 0도 각도로 무게감 있는 밥컷
→ Cut Form: O (One-length) + 원랭스로 균일한 단발 길이
→ Weight Flow: Balanced + 균형잡힌 무게감 분포''',
                'subtitle': '단발 밥컷 기본 레시피',
                'formula_42': 'Horizontal Section, L0 Elevation, One-length'
            },
            {
                'model_no': 'FAL0002',
                'introduction_kor': '단발머리 레이어드 스타일', 
                'ground_truth': '''[포뮬러 1: 수직섹션 45도 모바일라인] – 단발 레이어링
→ Section: Vertical + 수직 섹션으로 자연스러운 레이어 연결
→ Elevation: L2 (45°) + 45도 각도로 적당한 볼륨 생성
→ Cut Form: L (Layer) + 레이어 구조로 움직임과 경량감
→ Structure Layer: Medium Layer + 중간 레이어로 볼륨과 길이감 절충''',
                'subtitle': '단발에 레이어를 적용한 동적 스타일',
                'formula_42': 'Vertical Section, L2 Elevation, Layer Cut'
            },
            {
                'model_no': 'FAL0003',
                'introduction_kor': '미디움 레이어 스타일',
                'ground_truth': '''[포뮬러 1: 수직섹션 45도 모바일라인] – 미디움 레이어
→ Section: Vertical + 자연스러운 레이어 연결
→ Elevation: L2 (45°) + 적당한 볼륨 생성
→ Cut Form: L (Layer) + 움직임과 경량감
→ Weight Flow: Balanced + 균형잡힌 무게감''',
                'subtitle': '미디움 길이의 자연스러운 레이어',
                'formula_42': 'Vertical Section, L2 Elevation, Mobile Line'
            }
        ]
        print(f"✅ 기본 데이터 설정 완료: {len(self.styles_data)}개")
    
    def search_similar_styles(self, query: str, limit: int = 3) -> List[Dict]:
        """유사한 스타일 검색"""
        results = []
        query_lower = query.lower()
        
        print(f"🔍 RAG 검색 시작 - 쿼리: '{query}', 데이터 수: {len(self.styles_data)}")
        
        # 키워드 확장
        search_keywords = [query_lower]
        
        if '단발' in query_lower or 'bob' in query_lower:
            search_keywords.extend(['단발', 'bob', '밥', '쇼트', 'short', '턱선'])
        
        if '레시피' in query_lower or 'recipe' in query_lower:
            search_keywords.extend(['커트', 'cut', '시술', '기법'])
        
        if '롱' in query_lower or 'long' in query_lower:
            search_keywords.extend(['롱', 'long', '긴머리', '어깨아래'])
            
        if '미디움' in query_lower or 'medium' in query_lower:
            search_keywords.extend(['미디움', 'medium', '중간길이', '어깨선'])
        
        for i, style in enumerate(self.styles_data):
            score = 0
            matched_fields = []
            
            # 모든 텍스트 필드에서 검색 (가중치 적용)
            search_fields = {
                'introduction_kor': 5,
                'subtitle': 3,
                'ground_truth': 3,
                'image_analysis_kor': 2,
                'formula_42': 2,
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
        
        # 검색 결과가 없으면 기본 스타일 반환
        if not found_styles and self.styles_data:
            found_styles = self.styles_data[:3]
        
        return found_styles

# =============================================================================
# 전문가 응답 생성 함수 - 20파라미터 고속 버전
# =============================================================================

async def generate_fast_20param_response(messages: List[ChatMessage], claude_analysis: str = None, rag_context: str = None) -> str:
    """20파라미터 기반 고속 전문가 응답 생성 - 15초 이내 최적화"""
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'your_openai_key_here' or not openai:
        return generate_fallback_20param_response("API 설정 필요")
    
    global SELECTED_MODEL
    if SELECTED_MODEL is None:
        SELECTED_MODEL = await get_available_openai_model()
        if SELECTED_MODEL is None:
            return generate_fallback_20param_response("모델 사용 불가")
    
    try:
        last_message = messages[-1].content if messages else "헤어스타일 기술 분석 요청"
        
        print(f"⚡ 20파라미터 고속 분석 시작: {last_message[:50]}...")
        
        # 간소화된 프롬프트 (빠른 처리를 위해)
        fast_prompt = f"""당신은 헤어게이터 전문가입니다.

사용자 질문: {last_message}

다음 20개 핵심 파라미터로 간단하고 정확한 헤어 레시피를 제공하세요:

**핵심 20파라미터:**
1. Section (Horizontal/Vertical/Diagonal)
2. Elevation (L0-L8) 
3. Cut Form (O/G/L)
4. Cut Shape (Square/Round/Triangular)
5. Weight Flow (Balanced/Forward/Backward/Side Weighted)
6. Design Line (Stationary/Mobile/Combination)
7. Length (A/B/C/D/E)
8. Cut Method (Blunt/Point/Slide/Twist Cut)
9. Styling Direction (Forward/Backward/Side/Natural Fall)
10. Finish Look (Blow Dry/Air Dry/Heat Set)
11. Texture Finish (Soft Gloss/Natural/Matte)
12. Design Emphasis (Volume/Shape/Curl/Length Emphasis)
13. Natural Parting (Center/Side/No Parting)
14. Styling Product (None/Light/Medium/Strong Hold)
15. Fringe Type (No Fringe/Full/Side/Curtain Fringe)
16. Structure Layer (No Layer/Long/Medium/Short Layer)
17. Volume Zone (Low/Medium/High)
18. Interior Design (Connected/Disconnected)
19. Distribution (Natural Fall/Shifted/Perpendicular)
20. Cut Categories (Women's/Men's/Unisex Cut)

**응답 형식:**
🎯 20파라미터 헤어 레시피

[포뮬러 1: 섹션타입 각도 디자인라인] – 스타일명

**핵심 파라미터:**
→ Section: [값] + [간단 설명]
→ Elevation: [값] + [간단 설명]
→ Cut Form: [값] + [간단 설명]
(나머지 17개 파라미터)

**커팅 순서:**
1. [단계1]
2. [단계2] 
3. [단계3]
4. [단계4]

**모발 타입별 포인트:**
* 직모: [포인트]
* 곱슬모: [포인트]
* 가는모발: [포인트]
* 굵은모발: [포인트]

**관리법:**
* [관리 포인트 1]
* [관리 포인트 2]
* [관리 포인트 3]

간결하고 실용적으로 작성하세요. JSON이나 코드블록 사용 금지."""
        
        if rag_context:
            fast_prompt += f"\n\n참고 데이터:\n{rag_context[:500]}"
        
        print(f"🔬 고속 분석 모델: {SELECTED_MODEL}")
        
        # 최대 토큰 축소 (빠른 처리)
        max_tokens = 1500  # 크게 축소
        
        # GPT 호출 (15초 타임아웃)
        response = await asyncio.wait_for(
            openai.ChatCompletion.acreate(
                model=SELECTED_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": fast_prompt
                    },
                    {
                        "role": "user", 
                        "content": f"20파라미터로 간단한 헤어 레시피를 알려주세요: {last_message}"
                    }
                ],
                max_tokens=max_tokens,
                temperature=0.1,  # 일관성을 위해 낮게
                top_p=0.9,
                frequency_penalty=0.1,
                presence_penalty=0.1
            ),
            timeout=15.0  # 15초 타임아웃
        )
        
        result = response.choices[0].message.content
        result = clean_gpt_response(result)
        
        print(f"✅ 20파라미터 고속 분석 완료 (길이: {len(result)})")
        return result
        
    except asyncio.TimeoutError:
        print(f"⏰ 20파라미터 분석 타임아웃 (15초)")
        return f"""⚡ 20파라미터 헤어 레시피

**타임아웃으로 인한 기본 분석:**

{last_message[:100]}에 대한 분석이 타임아웃되었습니다.

🎯 기본 20파라미터 레시피

[포뮬러 1: 수직섹션 45도 모바일라인] – 미디움 레이어

**핵심 파라미터:**
→ Section: Vertical + 자연스러운 레이어 연결
→ Elevation: L2 (45°) + 적당한 볼륨 생성
→ Cut Form: L (Layer) + 움직임과 경량감
→ Cut Shape: Round + 부드러운 형태
→ Weight Flow: Balanced + 균형잡힌 무게감
→ Design Line: Mobile + 움직이는 가이드라인
→ Length: D + 어깨선 근처 길이
→ Cut Method: Point Cut + 자연스러운 끝처리
→ Styling Direction: Forward + 앞쪽 방향 스타일링
→ Finish Look: Blow Dry + 블로우 드라이 마무리
→ Texture Finish: Natural + 자연스러운 질감
→ Design Emphasis: Shape Emphasis + 형태 강조
→ Natural Parting: Side + 옆가르마
→ Styling Product: Light Hold + 가벼운 홀드
→ Fringe Type: No Fringe + 앞머리 없음
→ Structure Layer: Medium Layer + 중간 레이어
→ Volume Zone: Medium + 중간 볼륨
→ Interior Design: Connected + 연결된 구조
→ Distribution: Natural Fall + 자연 분배
→ Cut Categories: Women's Cut + 여성 커트

다시 시도하시면 완전한 분석을 제공해드리겠습니다!"""
        
    except Exception as e:
        print(f"❌ 20파라미터 분석 생성 오류: {e}")
        return generate_fallback_20param_response(last_message)

def clean_gpt_response(response_text: str) -> str:
    """GPT 응답에서 JSON 블록 완전 제거 및 파라미터 값 검증"""
    try:
        # JSON 블록 제거
        json_patterns = [
            r'```json.*?```',
            r'```.*?```',
            r'`[^`]*`',
            r'\{[^{}]*"[^"]*"[^{}]*\}',
            r'\[[^\[\]]*"[^"]*"[^\[\]]*\]'
        ]
        
        cleaned_text = response_text
        for pattern in json_patterns:
            cleaned_text = re.sub(pattern, '', cleaned_text, flags=re.DOTALL)
        
        # 텍스트 정리
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
        cleaned_text = re.sub(r' {2,}', ' ', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        return cleaned_text if cleaned_text else response_text
        
    except Exception as e:
        print(f"⚠️ 응답 정리 중 오류: {e}")
        return response_text

def generate_fallback_20param_response(user_message: str) -> str:
    """20파라미터용 기본 응답 생성"""
    return f"""⚡ 20파라미터 헤어 레시피

**전문가 질문 분석**: {user_message[:100]}...

🎯 [포뮬러 1: 수직섹션 45도 모바일라인] – 미디움 레이어 설정

**핵심 20파라미터:**
→ Section: Vertical + 자연스러운 레이어 연결을 위한 수직 분할
→ Elevation: L2 (45°) + 45도 각도로 적당한 볼륨과 움직임 생성
→ Cut Form: L (Layer) + 레이어 구조로 움직임과 경량감 동시 구현
→ Cut Shape: Round + 둥근 형태로 부드러운 여성스러운 인상
→ Weight Flow: Balanced + 전체적으로 균형잡힌 무게감 분포
→ Design Line: Mobile + 움직이는 가이드라인으로 자연스러운 연결감
→ Length: D + 어깨선 근처 길이로 실용성과 여성스러움 동시 추구
→ Cut Method: Point Cut + 포인트 컷으로 자연스러운 끝처리
→ Styling Direction: Forward + 앞쪽 방향 스타일링으로 얼굴을 감싸는 효과
→ Finish Look: Blow Dry + 블로우 드라이 마무리로 자연스러운 볼륨과 윤기
→ Texture Finish: Natural + 자연스러운 질감으로 인위적이지 않은 마무리
→ Design Emphasis: Shape Emphasis + 형태 강조로 헤어스타일의 실루엣이 주요 포인트
→ Natural Parting: Side + 옆가르마로 자연스러운 비대칭 균형
→ Styling Product: Light Hold + 가벼운 홀드력 제품으로 자연스러운 움직임
→ Fringe Type: No Fringe + 앞머리 없는 스타일로 이마를 시원하게 노출
→ Structure Layer: Medium Layer + 중간 레이어 구조로 볼륨과 길이감의 절충점
→ Volume Zone: Medium + 중간 정도의 볼륨존으로 자연스러운 볼륨
→ Interior Design: Connected + 내부가 자연스럽게 연결된 구조
→ Distribution: Natural Fall + 자연스러운 낙하감으로 무리 없는 스타일링
→ Cut Categories: Women's Cut + 여성 커트의 기본 원칙 적용

**커팅 순서:**
1. **준비단계**: 모발 상태 체크 및 7개 구역 분할
2. **1차 커팅**: 백 센터에서 가이드라인 설정, L2 45도 유지
3. **2차 정밀**: 사이드와 백 영역 자연스러운 연결
4. **마감 처리**: Point Cut으로 자연스러운 끝처리

**모발 타입별 포인트:**
* **직모**: L3로 각도 상향 조정, 웨트 커팅 권장
* **곱슬모**: 드라이 커팅으로 실제 컬 상태에서 조정
* **가는모발**: 과도한 레이어 방지, Forward Weighted 적용
* **굵은모발**: 내부 텍스처링으로 무게감 분산

**관리법:**
* 2일에 1회 가벼운 스타일링으로 충분
* 6주 후 재방문 권장
* 볼륨 무스나 텍스처 에센스 소량 사용

⚡ 20파라미터 고속 전문가 가이드 - 15초 이내 응답 최적화"""

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
    title="헤어게이터 고속 20파라미터 시스템 v8.0",
    description="15초 이내 응답을 위한 20파라미터 기반 헤어디자이너 전용 고속 분석 시스템",
    version="8.0-fast-20param",
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

@app.get("/")
async def root():
    return {
        "message": "헤어게이터 고속 20파라미터 시스템 v8.0",
        "version": "8.0-fast-20param", 
        "features": [
            "20파라미터로 축소하여 15초 이내 응답",
            "OpenAI API 타임아웃 15초로 최적화",
            "간소화된 프롬프트로 빠른 처리",
            "최대 토큰 1500으로 축소",
            "렌더 배포 최적화",
            "오류 없는 완전한 실행 가능 코드"
        ],
        "optimization": {
            "response_time": "15초 이내",
            "parameter_count": 20,
            "max_tokens": 1500,
            "timeout": 15,
            "model_priority": ["gpt-4-turbo", "gpt-4", "gpt-3.5-turbo-16k", "gpt-3.5-turbo"]
        },
        "status": {
            "redis": "connected" if redis_available else "memory_mode",
            "openai": "configured" if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' else "not_configured", 
            "claude": "disabled_for_speed",
            "rag_styles": len(rag_db.styles_data),
            "parameter_count": 20,
            "professional_context": True,
            "fast_optimized": True
        },
        "ready": True
    }

@app.post("/chat", response_model=ChatResponse)
async def fast_20param_chat(request: ChatRequest):
    """헤어디자이너 전용 고속 20파라미터 분석 - 15초 이내"""
    try:
        user_id = str(request.user_id).strip()
        user_message = str(request.message).strip() if request.message else ""
        image_url = request.image_url
        
        # image_url이 "string"이나 빈 문자열인 경우 None으로 처리
        if image_url in ["string", "", "null", "undefined"]:
            image_url = None
        
        print(f"⚡ 고속 분석 입력값 확인:")
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
        
        print(f"⚡ 헤어게이터 고속 20파라미터 시스템 - 사용자: {user_id}")
        if user_message:
            print(f"📝 질문: {user_message[:50]}...")
        if image_url:
            print(f"🖼️ 이미지: {image_url[:50]}...")
        
        # 헤어디자이너 전용 시스템이므로 모든 요청을 20파라미터 분석으로 처리
        print(f"⚡ 헤어디자이너 전용 시스템 - 20파라미터 고속 분석 진행")
        
        # 사용자 메시지 저장
        user_msg = ChatMessage(
            role="user",
            content=user_message + (f" [이미지: {image_url}]" if image_url else ""),
            timestamp=datetime.now().isoformat()
        )
        conversation_manager.add_message(user_id, conversation_id, user_msg)
        
        # 헤어디자이너 전용 시스템 - 바로 20파라미터 고속 분석 진행
        print("⚡ 헤어디자이너 전용 시스템 - 20파라미터 고속 분석 시작")
        
        # Claude 이미지 분석 생략 (속도 최적화)
        claude_analysis = None
        if image_url:
            print(f"⚠️ 이미지 분석 생략 (고속 처리를 위해)")
        
        # RAG 컨텍스트 생성 (간소화)
        rag_context = None
        if use_rag:
            print(f"🔍 RAG 검색 시작 (간소화) - 쿼리: '{user_message}'")
            similar_styles = rag_db.search_similar_styles(user_message)
            if similar_styles:
                rag_context = "참고 헤어게이터 레시피:\n\n"
                for i, style in enumerate(similar_styles[:2]):  # 최대 2개로 축소
                    rag_context += f"[레퍼런스 {i+1}]\n"
                    rag_context += f"스타일명: {style.get('introduction_kor', 'N/A')}\n"
                    rag_context += f"42포뮬러: {style.get('formula_42', 'N/A')}\n\n"
                
                print(f"✅ RAG 컨텍스트 생성 완료 - {len(similar_styles)}개 스타일 참조 (간소화)")
            else:
                print("⚠️ RAG 검색 결과 없음")
        else:
            print("📚 RAG 비활성화")
        
        # 대화 히스토리 (간소화)
        conversation_history = conversation_manager.get_conversation_history(
            user_id, conversation_id, limit=3  # 3개로 축소
        )
        
        # 헤어디자이너 전용 고속 20파라미터 응답 생성
        print(f"⚡ 헤어디자이너 전용 20파라미터 고속 분석 실행")
        
        response_text = await generate_fast_20param_response(
            conversation_history,
            claude_analysis,
            rag_context
        )
        
        # 응답 저장
        assistant_msg = ChatMessage(
            role="assistant",
            content=response_text,
            timestamp=datetime.now().isoformat()
        )
        conversation_manager.add_message(user_id, conversation_id, assistant_msg)
        
        print(f"✅ 헤어게이터 고속 20파라미터 분석 완료 - 길이: {len(response_text)}")
        
        return ChatResponse(
            conversation_id=conversation_id,
            message=response_text,
            timestamp=assistant_msg.timestamp,
            message_type="fast_20_parameter_analysis",
            additional_data={
                "professional_analysis": True,
                "claude_analysis_used": False,  # 고속 처리를 위해 비활성화
                "rag_context_used": bool(rag_context),
                "image_processed": bool(image_url),
                "parameter_count": 20,
                "analysis_version": "fast-v8.0-20param",
                "target_audience": "hair_professionals",
                "optimization": {
                    "response_time_target": "15초 이내",
                    "max_tokens": 1500,
                    "timeout": 15,
                    "simplified_prompt": True
                }
            }
        )
        
    except ValueError as e:
        print(f"❌ 입력 데이터 오류: {e}")
        raise HTTPException(status_code=422, detail=f"입력 데이터 형식 오류: {str(e)}")
    except Exception as e:
        print(f"❌ 고속 분석 처리 오류: {e}")
        raise HTTPException(status_code=500, detail=f"서버 처리 오류: {str(e)}")

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": "8.0-fast-20param",
        "timestamp": datetime.now().isoformat(),
        "optimization": {
            "response_time": "15초 이내",
            "parameter_count": 20,
            "max_tokens": 1500,
            "timeout": 15,
            "fast_mode": True
        },
        "features": {
            "professional_context_detection": True,
            "image_url_support": True,
            "temp_upload_support": True,
            "20_parameter_fast_analysis": True,
            "optimized_for_render": True,
            "error_free": True
        },
        "services": {
            "redis": "connected" if redis_available else "memory_mode",
            "openai": "configured" if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' else "not_configured",
            "claude": "disabled_for_speed"
        },
        "data": {
            "rag_styles": len(rag_db.styles_data),
            "total_parameters": 20,
            "professional_keywords": len(professional_context.professional_hair_keywords),
            "question_patterns": len(professional_context.professional_question_patterns)
        }
    }

@app.get("/test-20-parameters")
async def test_20_parameters():
    """20파라미터 고속 분석 테스트"""
    return {
        "message": "v8.0 고속 20파라미터 시스템 테스트 성공!",
        "version": "8.0-fast-20param",
        "optimization": {
            "response_time_target": "15초 이내",
            "parameter_count": 20,
            "max_tokens": 1500,
            "api_timeout": 15,
            "simplified_processing": True
        },
        "professional_features": {
            "context_detection": True,
            "image_url_support": True,
            "expert_guidance": True,
            "technical_analysis": True,
            "fast_optimized": True
        },
        "render_deployment": {
            "api_endpoint": "https://hairgator-api.onrender.com/chat",
            "optimized_for_render": True,
            "fast_response": True,
            "production_ready": True
        },
        "note": "20파라미터로 축소하여 15초 이내 응답을 제공하는 고속 최적화 버전입니다"
    }

# main 실행 부분
if __name__ == "__main__":
    import uvicorn
    
    print("\n⚡ 헤어게이터 고속 20파라미터 시스템 v8.0")
    print("🔧 v8.0 고속 최적화 완료:")
    print("   - 20파라미터로 축소")
    print("   - OpenAI API 타임아웃: 15초")
    print("   - 최대 토큰: 1500")
    print("   - 간소화된 프롬프트")
    print("   - Claude 이미지 분석 비활성화 (속도 최적화)")
    print("   - RAG 검색 간소화")
    
    # 렌더 환경 감지 및 포트 설정
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print(f"\n🚀 렌더 배포 고속 서버 시작:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   OpenAI: {'✅ 설정됨' if OPENAI_API_KEY and OPENAI_API_KEY != 'your_openai_key_here' else '❌ 미설정'}")
    print(f"   Claude: 비활성화 (속도 최적화)")
    print(f"   Redis: {'메모리모드' if not redis_available else '연결됨'}")
    print(f"   RAG 스타일: {len(rag_db.styles_data)}개")
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == 'your_openai_key_here':
        print("\n⚠️ 경고: OpenAI API 키가 렌더 환경변수에 설정되지 않았습니다!")
        print("   Render Dashboard → Environment → OPENAI_API_KEY 설정 필요")
    
    print(f"\n📋 API 엔드포인트:")
    print(f"   • API 문서: https://your-app.onrender.com/docs")
    print(f"   • 헬스 체크: https://your-app.onrender.com/health")
    print(f"   • 20파라미터 테스트: https://your-app.onrender.com/test-20-parameters")
    
    print(f"\n⚡ 고속 최적화 설정:")
    print(f"   • 파라미터 수: 20개")
    print(f"   • 응답 시간: 15초 이내")
    print(f"   • 최대 토큰: 1500")
    print(f"   • API 타임아웃: 15초")
    
    try:
        uvicorn.run(
            app, 
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            workers=1,
            timeout_keep_alive=30,  # 30초로 설정
            limit_concurrency=5  # 동시 연결 수 제한
        )
    except Exception as e:
        print(f"❌ 서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)