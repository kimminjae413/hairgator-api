# 🎨 헤어게이터 시스템 v5.0

**Claude 이미지 분석 + GPT 전문 응답 + RAG 시스템**

헤어게이터는 42포뮬러와 56파라미터를 기반으로 한 전문 헤어스타일 분석 및 추천 시스템입니다. Claude API를 통한 이미지 분석과 GPT-4를 통한 전문적인 헤어 레시피 생성을 제공합니다.

## ✨ 주요 기능

### 🖼️ 이미지 분석
- **Claude API 기반 헤어스타일 이미지 분석**
- 42포뮬러 관점에서의 기술적 해석
- Cut Form, Section, Elevation 등 전문 파라미터 분석
- 이미지 URL 또는 파일 업로드 지원

### 💬 전문 채팅
- **GPT-4 기반 헤어게이터 전문 상담**
- 56개 파라미터를 활용한 정확한 레시피 생성
- 현장 용어 → 전문 파라미터 실시간 번역
- 대화 히스토리 관리 (Redis 기반)

### 📚 RAG 시스템
- **엑셀 기반 스타일 데이터베이스**
- 검증된 42포뮬러 구조 활용
- 유사 스타일 검색 및 추천
- 실제 적용 가능한 레시피 생성

### 🎯 파라미터 시스템
- **42포뮬러**: 3D 절단 벡터 + 공간 경로 + 연결성
- **56파라미터**: Cut Form, Section, Direction, Elevation 등
- **정합성 검증**: 허용값 엄격 준수
- **상황 기반 논리**: 기계적 공식 적용 금지

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd hairgator-system

# 환경 변수 설정
cp env_setup_v5.sh .env
# .env 파일에서 API 키 설정
nano .env
```

### 2. Docker로 실행 (권장)

```bash
# 자동 배포 스크립트 실행
chmod +x deploy.sh
./deploy.sh

# 또는 Docker Compose 직접 사용
docker-compose up --build -d
```

### 3. 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements_v5.txt

# Redis 시작 (별도 터미널)
redis-server

# 애플리케이션 시작
python hairgator_integrated_v5.py
```

## 📋 API 엔드포인트

### 기본 정보
```http
GET  /              # 시스템 정보
GET  /health        # 헬스 체크
```

### 채팅 기능
```http
POST /chat          # 통합 채팅 (텍스트 + 이미지 URL)
POST /analyze-image # 이미지 분석 (Base64)
POST /upload-image  # 파일 업로드 분석
```

### RAG 기능
```http
GET  /styles/search        # 스타일 검색
GET  /parameters/{name}    # 파라미터 정보
```

## 💻 사용 예시

### 1. 텍스트 채팅
```python
import requests

response = requests.post("http://localhost:8000/chat", json={
    "user_id": "user_001",
    "message": "숄더 밥 헤어스타일의 42포뮬러를 알려주세요",
    "use_rag": True
})

print(response.json()["message"])
```

### 2. 이미지 분석 (URL)
```python
response = requests.post("http://localhost:8000/chat", json={
    "user_id": "user_002", 
    "message": "이 헤어스타일을 분석해주세요",
    "image_url": "https://example.com/hairstyle.jpg",
    "use_rag": True
})
```

### 3. 이미지 업로드
```python
with open("hairstyle.jpg", "rb") as f:
    response = requests.post("http://localhost:8000/upload-image", 
        files={"file": f},
        data={
            "user_id": "user_003",
            "message": "이 스타일의 레이어 구조를 알려주세요"
        }
    )
```

### 4. 스타일 검색
```python
response = requests.get("http://localhost:8000/styles/search", 
    params={"query": "레이어드 컷", "limit": 5}
)
```

## 🧪 테스트

```bash
# 전체 API 테스트
python test_hairgator_api.py

# 특정 기능 테스트
python test_hairgator_api.py --test chat
python test_hairgator_api.py --test image
python test_hairgator_api.py --test search

# 다른 서버 테스트
python test_hairgator_api.py --host production.example.com --port 443 --https
```

## 📁 프로젝트 구조

```
hairgator-system/
├── hairgator_integrated_v5.py    # 메인 애플리케이션
├── requirements_v5.txt           # Python 의존성
├── env_setup_v5.sh              # 환경 변수 템플릿
├── docker-compose.yml           # Docker Compose 설정
├── Dockerfile                   # Docker 이미지
├── nginx.conf                   # Nginx 설정
├── deploy.sh                    # 배포 스크립트
├── test_hairgator_api.py        # API 테스트 스크립트
├── 헤어게이터 스타일 메뉴 텍스트_women_rag_v2.xlsx  # RAG 데이터
├── static/                      # 정적 파일
├── logs/                        # 로그 파일
└── ssl/                         # SSL 인증서
```

## ⚙️ 설정

### 필수 환경 변수
```bash
# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key

# Anthropic Claude API 설정  
ANTHROPIC_API_KEY=your_anthropic_api_key

# Redis 설정
REDIS_URL=redis://localhost:6379

# 서버 설정
HOST=0.0.0.0
PORT=8000
```

### 선택적 설정
```bash
# 환경 설정
ENVIRONMENT=development
DEBUG=true

# 파일 업로드 설정
MAX_FILE_SIZE=10485760
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp

# AI 모델 설정
CLAUDE_MODEL=claude-3-5-sonnet-20241022
OPENAI_MODEL=gpt-4-turbo-preview
```

## 🔧 관리 명령어

### Docker Compose
```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down

# 완전 정리
docker-compose down --volumes --rmi all
```

### 배포 스크립트
```bash
# 전체 배포
./deploy.sh

# 시스템 정리
./deploy.sh cleanup

# 로그 확인
./deploy.sh logs

# 서비스 재시작
./deploy.sh restart

# 상태 확인
./deploy.sh status
```

## 📊 성능 최적화

### Redis 캐싱
- 대화 히스토리 캐싱 (7일 TTL)
- 이미지 분석 결과 캐싱
- RAG 검색 결과 캐싱

### API 최적화
- 비동기 처리 (FastAPI + uvicorn)
- 이미지 크기 자동 조정
- Gzip 압축 (Nginx)

### 보안
- HTTPS 지원 (SSL/TLS)
- API 레이트 리미팅
- 입력 검증 및 샐리타이제이션
- CORS 설정

## 🐛 문제 해결

### 일반적인 문제

**1. Redis 연결 오류**
```bash
# Redis 서버 시작
redis-server --daemonize yes

# 연결 테스트
redis-cli ping
```

**2. API 키 오류**
```bash
# 환경 변수 확인
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# .env 파일 재로드
source .env
```

**3. 이미지 업로드 실패**
```bash
# 파일 크기 확인 (10MB 제한)
# 지원 형식: jpg, jpeg, png, webp
```

**4. Docker 메모리 부족**
```bash
# Docker 리소스 정리
docker system prune -af

# 메모리 사용량 확인
docker stats
```

### 로그 확인
```bash
# 애플리케이션 로그
docker-compose logs hairgator-app

# Nginx 로그
docker-compose logs nginx

# Redis 로그
docker-compose logs redis

# 실시간 로그
docker-compose logs -f
```

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원

- **이슈 리포트**: [GitHub Issues](../../issues)
- **기능 요청**: [GitHub Discussions](../../discussions)
- **보안 문제**: security@example.com

## 🎯 로드맵

### v5.1 (계획)
- [ ] 실시간 WebSocket 지원
- [ ] 다국어 지원 (영어, 일본어)
- [ ] 모바일 앱 연동 API

### v5.2 (계획)
- [ ] 머신러닝 기반 스타일 추천
- [ ] 3D 헤어 모델링 연동
- [ ] AR 가상 피팅 지원

---

**© 2025 Hairgator System. Made with ❤️ by the Hairgator Team.**