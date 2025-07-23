import openai
import os
from dotenv import load_dotenv

# .env 로드
load_dotenv(dotenv_path=".env")

# 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")

# 간단한 테스트 요청
try:
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo-preview",  # 또는 "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "GPT API 작동 중인지 알려줘."}
        ],
        max_tokens=20,
        temperature=0.5
    )
    print("✅ GPT 응답:", response.choices[0].message["content"])
except Exception as e:
    print("❌ 오류 발생:", e)
