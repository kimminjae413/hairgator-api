# Dockerfile for Hairgator System v5.0
# 헤어게이터 시스템 도커 이미지

FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 파일 복사 및 설치
COPY requirements_v5.txt .
RUN pip install --no-cache-dir -r requirements_v5.txt

# 애플리케이션 코드 복사
COPY . .

# 환경 변수 설정
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 포트 노출
EXPOSE 8000

# Redis가 필요하므로 redis-server 설치 (선택사항)
RUN apt-get update && apt-get install -y redis-server

# 시작 스크립트 생성
RUN echo '#!/bin/bash\n\
# Redis 시작 (백그라운드)\n\
redis-server --daemonize yes\n\
\n\
# Python 애플리케이션 시작\n\
python hairgator_integrated_v5.py' > start.sh && \
chmod +x start.sh

# 애플리케이션 시작
CMD ["./start.sh"]

# 또는 uvicorn 직접 실행
# CMD ["uvicorn", "hairgator_integrated_v5:app", "--host", "0.0.0.0", "--port", "8000"]