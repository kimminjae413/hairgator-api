#!/bin/bash

echo "🔧 헤어게이터 Render 빌드 시작..."

# 시스템 패키지 업데이트
echo "📦 시스템 의존성 설치..."
apt-get update
apt-get install -y \
    libjpeg-dev \
    libpng-dev \
    libtiff5-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libwebp-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    build-essential

# pip 업그레이드
echo "🔄 pip 업그레이드..."
pip install --upgrade pip setuptools wheel

# Pillow 의존성 먼저 설치
echo "🎨 Pillow 의존성 설치..."
pip install --upgrade setuptools-scm
pip install --no-cache-dir Pillow>=10.2.0

# 나머지 패키지 설치
echo "📚 애플리케이션 의존성 설치..."
pip install --no-cache-dir -r requirements.txt

echo "✅ 빌드 완료!"