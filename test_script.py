#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_hairgator_api.py
헤어게이터 시스템 v5.0 API 테스트 스크립트

이 스크립트는 헤어게이터 시스템의 모든 주요 기능을 테스트합니다:
- 기본 API 엔드포인트
- 텍스트 채팅
- 이미지 업로드 및 분석
- RAG 검색
- 헬스 체크

사용법:
    python test_hairgator_api.py
    python test_hairgator_api.py --host localhost --port 8000
"""

import requests
import json
import base64
import time
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional

class HairgatorTester:
    def __init__(self, host: str = "localhost", port: int = 8000, https: bool = False):
        protocol = "https" if https else "http"
        self.base_url = f"{protocol}://{host}:{port}"
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", response_data: Any = None):
        """테스트 결과 로깅"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data
        })
        
    def test_health_check(self):
        """헬스 체크 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False
    
    def test_root_endpoint(self):
        """루트 엔드포인트 테스트"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")
                self.log_test("Root Endpoint", True, f"Version: {version}")
                return True
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Error: {str(e)}")
            return False
    
    def test_text_chat(self):
        """텍스트 채팅 테스트"""
        try:
            payload = {
                "user_id": "test_user_001",
                "message": "숄더 밥 헤어스타일을 만들고 싶어요. 어떤 레시피가 좋을까요?",
                "use_rag": True
            }
            
            response = self.session.post(
                f"{self.base_url}/chat", 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                conversation_id = data.get("conversation_id")
                message_length = len(data.get("message", ""))
                self.log_test("Text Chat", True, 
                            f"Response length: {message_length} chars, Conv ID: {conversation_id}")
                return conversation_id
            else:
                self.log_test("Text Chat", False, f"HTTP {response.status_code}")
                return None
        except Exception as e:
            self.log_test("Text Chat", False, f"Error: {str(e)}")
            return None
    
    def test_follow_up_chat(self, conversation_id: str):
        """대화 연속성 테스트"""
        if not conversation_id:
            self.log_test("Follow-up Chat", False, "No conversation ID")
            return
            
        try:
            payload = {
                "user_id": "test_user_001",
                "message": "방금 답변해준 레시피에서 레이어 구조만 자세히 설명해주세요.",
                "conversation_id": conversation_id,
                "use_rag": True
            }
            
            response = self.session.post(
                f"{self.base_url}/chat", 
                json=payload, 
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Follow-up Chat", True, 
                            f"Follow-up response received, same conv ID: {data.get('conversation_id') == conversation_id}")
            else:
                self.log_test("Follow-up Chat", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Follow-up Chat", False, f"Error: {str(e)}")
    
    def create_test_image(self) -> str:
        """테스트용 더미 이미지 생성 (base64)"""
        # 간단한 1x1 픽셀 PNG 이미지 (투명)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAG9GQlVVgAAAABJRU5ErkJggg=="
        )
        return base64.b64encode(png_data).decode('utf-8')
    
    def test_image_analysis_base64(self):
        """Base64 이미지 분석 테스트"""
        try:
            test_image = self.create_test_image()
            
            payload = {
                "user_id": "test_user_002",
                "message": "이 헤어스타일을 분석해주세요. 어떤 컷 형태인가요?",
                "image_data": f"data:image/png;base64,{test_image}",
                "use_rag": True
            }
            
            response = self.session.post(
                f"{self.base_url}/analyze-image", 
                json=payload, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Image Analysis (Base64)", True, 
                            f"Analysis completed, type: {data.get('message_type')}")
                return True
            else:
                self.log_test("Image Analysis (Base64)", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Image Analysis (Base64)", False, f"Error: {str(e)}")
            return False
    
    def test_image_upload(self):
        """파일 업로드 방식 이미지 분석 테스트"""
        try:
            # 더미 이미지 파일 생성
            test_image_data = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAG9GQlVVgAAAABJRU5ErkJggg=="
            )
            
            files = {
                'file': ('test_hair.png', test_image_data, 'image/png')
            }
            data = {
                'user_id': 'test_user_003',
                'message': '이 헤어스타일의 레이어 구조를 분석해주세요.',
                'use_rag': 'true'
            }
            
            response = self.session.post(
                f"{self.base_url}/upload-image", 
                files=files, 
                data=data, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Image Upload", True, 
                            f"Upload analysis completed, type: {data.get('message_type')}")
                return True
            else:
                self.log_test("Image Upload", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Image Upload", False, f"Error: {str(e)}")
            return False
    
    def test_style_search(self):
        """스타일 검색 테스트"""
        try:
            params = {
                "query": "숄더 밥",
                "limit": 3
            }
            
            response = self.session.get(
                f"{self.base_url}/styles/search", 
                params=params, 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                result_count = len(data.get("results", []))
                self.log_test("Style Search", True, f"Found {result_count} results")
                return True
            else:
                self.log_test("Style Search", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Style Search", False, f"Error: {str(e)}")
            return False
    
    def test_parameter_info(self):
        """파라미터 정보 조회 테스트"""
        try:
            response = self.session.get(
                f"{self.base_url}/parameters/section", 
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Parameter Info", True, f"Parameter: {data.get('parameter')}")
                return True
            else:
                self.log_test("Parameter Info", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Parameter Info", False, f"Error: {str(e)}")
            return False
    
    def test_chat_with_image_url(self):
        """이미지 URL을 포함한 채팅 테스트"""
        try:
            payload = {
                "user_id": "test_user_004",
                "message": "이 이미지의 헤어스타일을 분석해서 42포뮬러로 설명해주세요.",
                "image_url": "https://via.placeholder.com/400x400.png",
                "use_rag": True
            }
            
            response = self.session.post(
                f"{self.base_url}/chat", 
                json=payload, 
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test("Chat with Image URL", True, 
                            f"Image analysis chat completed")
                return True
            else:
                self.log_test("Chat with Image URL", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Chat with Image URL", False, f"Error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🎨 헤어게이터 시스템 v5.0 API 테스트 시작")
        print(f"🌐 Target: {self.base_url}")
        print("=" * 60)
        
        # 기본 연결 테스트
        if not self.test_health_check():
            print("\n❌ 기본 연결에 실패했습니다. 서버가 실행 중인지 확인하세요.")
            return False
        
        self.test_root_endpoint()
        
        # 채팅 기능 테스트
        conversation_id = self.test_text_chat()
        if conversation_id:
            self.test_follow_up_chat(conversation_id)
        
        # 이미지 분석 테스트
        self.test_image_analysis_base64()
        self.test_image_upload()
        self.test_chat_with_image_url()
        
        # RAG 기능 테스트
        self.test_style_search()
        self.test_parameter_info()
        
        # 결과 요약
        self.print_summary()
        
        return True
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("📋 테스트 결과 요약")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"전체 테스트: {total_tests}")
        print(f"성공: {passed_tests} ✅")
        print(f"실패: {failed_tests} ❌")
        print(f"성공률: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n실패한 테스트:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n🎉 테스트 완료!")

def main():
    parser = argparse.ArgumentParser(description="헤어게이터 API 테스트 스크립트")
    parser.add_argument("--host", default="localhost", help="서버 호스트 (기본값: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="서버 포트 (기본값: 8000)")
    parser.add_argument("--https", action="store_true", help="HTTPS 사용")
    parser.add_argument("--test", choices=[
        "health", "root", "chat", "image", "search", "params", "all"
    ], default="all", help="실행할 테스트 선택")
    
    args = parser.parse_args()
    
    tester = HairgatorTester(args.host, args.port, args.https)
    
    if args.test == "all":
        tester.run_all_tests()
    elif args.test == "health":
        tester.test_health_check()
    elif args.test == "root":
        tester.test_root_endpoint()
    elif args.test == "chat":
        tester.test_text_chat()
    elif args.test == "image":
        tester.test_image_analysis_base64()
        tester.test_image_upload()
    elif args.test == "search":
        tester.test_style_search()
    elif args.test == "params":
        tester.test_parameter_info()

if __name__ == "__main__":
    main()