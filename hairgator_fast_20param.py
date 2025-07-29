from flask import Flask, request, render_template_string, jsonify
import os
import json
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

print("🚀 헤어게이터 서버 시작 중...")
print(f"🔧 환경: {os.getenv('ENVIRONMENT', 'development')}")
print(f"🐍 Python 버전: {os.getenv('PYTHON_VERSION', 'default')}")

# OpenAI 설정 (안전하게)
try:
    from openai import OpenAI
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    if openai_api_key and openai_api_key != '............':
        client = OpenAI(api_key=openai_api_key)
        print("✅ OpenAI API 설정 완료")
        print(f"🤖 사용 모델: {openai_model}")
    else:
        print("⚠️ OpenAI API 키가 설정되지 않음 - 기본 레시피 모드로 실행")
        client = None
        openai_model = None
except Exception as e:
    print(f"⚠️ OpenAI 초기화 오류: {e}")
    client = None
    openai_model = None

# Claude 설정 (현재는 비활성화)
claude_api_key = os.getenv('ANTHROPIC_API_KEY')
claude_model = os.getenv('CLAUDE_MODEL', 'claude-3-sonnet-20240229')

if claude_api_key and claude_api_key != '............':
    print("🔵 Claude API 키 감지됨 (현재 비활성화)")
else:
    print("⚪ Claude API 미설정")

print("=" * 50)

# 헤어 레시피 데이터 (미용사 전용)
HAIR_RECIPES = {
    "컬러링": {
        "keywords": ["컬러", "염색", "애쉬", "브라운", "블론드", "토닝", "탈색"],
        "recipes": [
            "🎨 애쉬 브라운 레시피: 6/1 + 7/1 (1:1) + 6% 옥시",
            "✨ 베이지 블론드: 탈색 후 9/31 + 10/1 (2:1) + 3% 옥시",
            "🌟 그레이 애쉬: 7/1 + 소량의 0/11 + 6% 옥시"
        ]
    },
    "펌": {
        "keywords": ["펌", "파마", "볼륨", "웨이브", "컬"],
        "recipes": [
            "💫 볼륨 펌: 1제 15분 → 2제 10분 (중성화까지)",
            "🌊 웨이브 펌: 콜드 1제 20분 → 2제 15분",
            "🔥 디지털 펌: 열펌 1제 → 건조 → 2제 가열"
        ]
    },
    "트리트먼트": {
        "keywords": ["트리트먼트", "케어", "손상", "영양", "수분"],
        "recipes": [
            "💧 수분 케어: 케라틴 + 히알루론산 (1:1) 15분",
            "🛡️ 단백질 케어: PPT + 아미노산 복합체 20분",
            "✨ 큐티클 케어: 실크 프로틴 + 오일 (2:1)"
        ]
    },
    "스타일링": {
        "keywords": ["스타일링", "드라이", "세팅", "볼륨", "매직"],
        "recipes": [
            "🎯 볼륨 세팅: 무스 + 스프레이 (텐션 드라이)",
            "💨 자연 웨이브: 크림 + 디퓨저 드라이",
            "⚡ 매직 스트레이트: 1제 → 아이론 → 2제"
        ]
    }
}

# HTML 템플릿
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#667eea">
    <title>헤어게이터 - AI 헤어케어 진단</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
        }
        
        /* 입력 필드만 텍스트 선택 허용 */
        input, textarea {
            -webkit-user-select: text;
            -moz-user-select: text;
            -ms-user-select: text;
            user-select: text;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #f8f9ff 0%, #e8f0fe 50%, #f1f8ff 100%);
            min-height: 100vh;
            min-height: -webkit-fill-available;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: fixed;
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
        }
        
        html {
            height: -webkit-fill-available;
        }
        
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 500px;
            height: 100vh;
            height: -webkit-fill-available;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            position: relative;
        }
        
        /* 모바일에서 더 자연스러운 크기 */
        @media (max-width: 768px) {
            body {
                align-items: stretch;
            }
            
            .container {
                width: 100%;
                height: 100%;
                border-radius: 0;
                max-width: none;
                margin: 0;
            }
            
            .input-container {
                padding: 10px 12px;
                padding-bottom: 10px;
            }
            
            /* 키보드 활성화 시 브라우저 UI 완전 숨김 */
            .keyboard-active {
                height: 100vh;
                overflow: hidden;
            }
            
            .keyboard-active .input-container {
                padding-bottom: 6px;
                position: fixed;
                bottom: 0;
            }
            
            /* iOS Safari 하단 바 숨김 */
            .keyboard-active body {
                padding-bottom: 0;
            }
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px 30px;
            text-align: center;
            position: relative;
            box-shadow: 0 2px 15px rgba(102, 126, 234, 0.15);
        }
        
        .logo {
            width: 60px;
            height: 60px;
            background: linear-gradient(45deg, #ff6b9d, #c44569);
            border-radius: 16px;
            margin: 0 auto 15px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: 800;
            color: white;
            position: relative;
            z-index: 1;
            box-shadow: 0 4px 15px rgba(255, 107, 157, 0.3);
        }
        
        .header h1 {
            font-size: 1.8rem;
            margin-bottom: 8px;
            font-weight: 700;
            position: relative;
            z-index: 1;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 0.9rem;
            position: relative;
            z-index: 1;
            font-weight: 500;
        }
        
        .chat-container {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #fafafa;
            -webkit-overflow-scrolling: touch;
            scroll-behavior: smooth;
        }
        
        .message {
            margin-bottom: 15px;
            padding: 12px 18px;
            border-radius: 18px;
            max-width: 80%;
            word-wrap: break-word;
        }
        
        .user-message {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            margin-left: auto;
            text-align: right;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
        }
        
        .bot-message {
            background: white;
            color: #333;
            margin-right: auto;
            border: 1px solid #f0f0f0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            position: relative;
        }
        
        .bot-message::before {
            content: 'H';
            position: absolute;
            top: -10px;
            left: 15px;
            background: linear-gradient(45deg, #ff6b9d, #c44569);
            width: 28px;
            height: 28px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            font-weight: 800;
            color: white;
            border: 3px solid white;
            box-shadow: 0 2px 8px rgba(255, 107, 157, 0.3);
        }
        
        .input-container {
            padding: 12px 16px;
            background: white;
            border-top: 1px solid #e9ecef;
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        }
        
        /* 키보드 활성화 시 하단 메뉴 완전 숨김 */
        .keyboard-active .input-container {
            padding-bottom: 8px;
            transform: translateY(0);
        }
        
        /* 채팅 컨테이너에 하단 여백 추가 (입력창 공간 확보) */
        .chat-container {
            padding-bottom: 80px; /* 입력창 높이만큼 여백 */
        }
        
        .input-group {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        
        .input-field {
            flex: 1;
            padding: 12px 18px;
            border: 2px solid #e9ecef;
            border-radius: 25px;
            font-size: 16px; /* iOS 확대 방지 */
            outline: none;
            transition: border-color 0.3s;
            background: white;
            -webkit-appearance: none;
            resize: none;
            min-height: 44px; /* 터치 타겟 최소 크기 */
        }
        
        .input-field:focus {
            border-color: #667eea;
            -webkit-appearance: none;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.12);
        }
        
        /* iOS Safari 키보드 대응 */
        @supports (-webkit-touch-callout: none) {
            .input-field:focus {
                transform: translateZ(0);
                -webkit-transform: translateZ(0);
            }
        }
        
        .send-btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.2s;
            min-height: 44px; /* 터치 타겟 최소 크기 */
            min-width: 44px;
            display: flex;
            align-items: center;
            justify-content: center;
            -webkit-tap-highlight-color: transparent;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.25);
        }
        
        .send-btn:hover, .send-btn:active {
            background: linear-gradient(135deg, #5a67d8, #667eea);
            transform: scale(0.98);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.35);
        }
        
        .send-btn:disabled {
            background: #6c757d;
            cursor: not-allowed;
            transform: none;
        }
        
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            color: #6c757d;
        }
        
        .status {
            text-align: center;
            padding: 10px;
            font-size: 0.9rem;
            color: white;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-bottom: 1px solid rgba(255,255,255,0.15);
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status">
            ✨ 미용사 전용 헤어 레시피 서비스 - 온라인
        </div>
        
        <div class="header">
            <div class="logo">H</div>
            <h1>헤어게이터</h1>
            <p>전문 미용사를 위한 헤어 레시피 챗봇</p>
        </div>
        
        <div class="chat-container" id="chatContainer">
            <div class="message bot-message">
                안녕하세요! 헤어게이터입니다 ✨<br>
                미용사님을 위한 전문 헤어 레시피를 제공해드려요!<br>
                <br>
                <strong>🎨 질문 예시:</strong><br>
                • "애쉬 브라운 컬러 레시피 알려주세요"<br>
                • "손상모발 트리트먼트 방법"<br>
                • "볼륨 펌 약제 비율"<br>
                • "탈색 후 토닝 레시피"<br>
                <br>
                <em>💡 전문 미용사만을 위한 정확한 시술 정보를 제공합니다</em>
            </div>
        </div>
        
        <div class="loading" id="loading">
            💭 헤어게이터가 생각 중이에요...
        </div>
        
        <div class="input-container">
            <div class="input-group">
                <input type="text" id="userInput" class="input-field" 
                       placeholder="헤어 레시피나 시술 방법을 물어보세요..." 
                       onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()" class="send-btn" id="sendBtn">전송</button>
            </div>
        </div>
    </div>

    <script>
        // 키보드 대응 (iOS/Android) - ChatGPT 스타일
        let initialViewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
        let isKeyboardActive = false;
        
        function handleViewportChange() {
            if (window.visualViewport) {
                const currentHeight = window.visualViewport.height;
                const heightDiff = initialViewportHeight - currentHeight;
                
                if (heightDiff > 150) { // 키보드가 올라왔을 때
                    isKeyboardActive = true;
                    document.documentElement.classList.add('keyboard-active');
                    document.body.classList.add('keyboard-active');
                    
                    // 키보드 높이만큼 입력창 위치 조정
                    const inputContainer = document.querySelector('.input-container');
                    if (inputContainer) {
                        inputContainer.style.bottom = '0px';
                        inputContainer.style.position = 'fixed';
                    }
                    
                    // 뷰포트 크기에 맞춰 컨테이너 조정
                    const container = document.querySelector('.container');
                    if (container) {
                        container.style.height = currentHeight + 'px';
                    }
                    
                } else { // 키보드가 내려갔을 때
                    isKeyboardActive = false;
                    document.documentElement.classList.remove('keyboard-active');
                    document.body.classList.remove('keyboard-active');
                    
                    // 원래 상태로 복원
                    const inputContainer = document.querySelector('.input-container');
                    if (inputContainer) {
                        inputContainer.style.bottom = '0px';
                        inputContainer.style.position = 'fixed';
                    }
                    
                    const container = document.querySelector('.container');
                    if (container) {
                        container.style.height = '100vh';
                    }
                }
            }
        }
        
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', handleViewportChange);
        }
        
        // 화면 확대/축소 방지
        document.addEventListener('touchstart', function(e) {
            if (e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });
        
        let lastTouchEnd = 0;
        document.addEventListener('touchend', function(e) {
            const now = (new Date()).getTime();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
        
        function addMessage(message, isUser) {
            const chatContainer = document.getElementById('chatContainer');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
            messageDiv.innerHTML = message;
            chatContainer.appendChild(messageDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

        function handleKeyPress(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }
        
        // 입력 필드 포커스 시 ChatGPT 스타일 동작
        const inputField = document.getElementById('userInput');
        
        inputField.addEventListener('focus', function() {
            // 포커스 시 스크롤을 하단으로
            setTimeout(() => {
                window.scrollTo(0, document.body.scrollHeight);
                
                // 키보드 올라온 상태에서 입력창을 키보드 바로 위로
                if (window.visualViewport) {
                    const currentHeight = window.visualViewport.height;
                    const heightDiff = initialViewportHeight - currentHeight;
                    
                    if (heightDiff > 150) {
                        // 입력창이 키보드에 가려지지 않도록 조정
                        const inputContainer = document.querySelector('.input-container');
                        if (inputContainer) {
                            inputContainer.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'end' 
                            });
                        }
                    }
                }
            }, 100);
        });
        
        // 입력 필드 블러 시 상태 정리
        inputField.addEventListener('blur', function() {
            setTimeout(() => {
                if (!isKeyboardActive) {
                    document.documentElement.classList.remove('keyboard-active');
                    document.body.classList.remove('keyboard-active');
                }
            }, 200);
        });
        
        // 브라우저 크기 변경 시에도 대응
        window.addEventListener('resize', handleViewportChange);

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const sendBtn = document.getElementById('sendBtn');
            const loading = document.getElementById('loading');
            
            const message = input.value.trim();
            if (!message) return;
            
            // 사용자 메시지 표시
            addMessage(message, true);
            input.value = '';
            
            // 로딩 표시
            sendBtn.disabled = true;
            loading.style.display = 'block';
            
            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        timestamp: new Date().toISOString()
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                addMessage(data.response, false);
                
            } catch (error) {
                console.error('Error:', error);
                addMessage('죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요. 🙏', false);
            } finally {
                sendBtn.disabled = false;
                loading.style.display = 'none';
            }
        }
    </script>
</body>
</html>
'''

def analyze_hair_query(message):
    """미용사 전용 헤어 레시피 분석"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['컬러', '염색', '애쉬', '브라운', '블론드', '토닝', '탈색']):
        return "컬러링", HAIR_RECIPES["컬러링"]["recipes"]
    elif any(word in message_lower for word in ['펌', '파마', '볼륨', '웨이브', '컬']):
        return "펌", HAIR_RECIPES["펌"]["recipes"]
    elif any(word in message_lower for word in ['트리트먼트', '케어', '손상', '영양', '수분']):
        return "트리트먼트", HAIR_RECIPES["트리트먼트"]["recipes"]
    elif any(word in message_lower for word in ['스타일링', '드라이', '세팅', '매직']):
        return "스타일링", HAIR_RECIPES["스타일링"]["recipes"]
    else:
        return "일반상담", [
            "🎨 컬러링 레시피를 원하시면 '애쉬 브라운' 등을 말씀해주세요",
            "💫 펜 레시피는 '볼륨 펌' 등으로 문의하세요",
            "💧 트리트먼트는 '손상모발 케어' 등으로 질문해주세요"
        ]

def get_openai_response(message, recipe_type, recipes):
    """OpenAI API를 통한 미용사 전용 응답 생성"""
    # API 키 체크
    if not client:
        return f"""
        <strong>🦎 {recipe_type} 기본 레시피</strong><br><br>
        
        <strong>📋 추천 레시피:</strong><br>
        {'<br>'.join([f'{recipe}' for recipe in recipes])}<br><br>
        
        <strong>⚠️ 주의사항:</strong><br>
        • 패치 테스트 필수<br>
        • 모발 상태 확인 후 시술<br>
        • 시술 시간 준수<br><br>
        
        <strong>💡 AI 기능:</strong><br>
        OpenAI API 연결 시 더 상세한 조언을 받을 수 있어요!
        """
    
    try:
        # 모델 설정
        model_to_use = openai_model or 'gpt-3.5-turbo'
        
        # 전문적인 프롬프트
        prompt = f"""
당신은 20년 경력의 전문 헤어 디자이너이자 컬러리스트입니다.

미용사 질문: "{message}"
카테고리: {recipe_type}
기본 레시피: {', '.join(recipes)}

다음 조건으로 전문적인 답변을 해주세요:

1. 🎯 구체적인 시술 방법 (단계별)
2. 📊 정확한 약제 비율과 시간
3. ⚠️ 주의사항과 트러블슈팅
4. 💡 프로 팁 (현장에서만 알 수 있는)
5. 🚫 일반인 사용 금지 명시

답변은 HTML 형식으로 200자 내외, 이모지 적절히 사용.
반드시 "전문 미용사 전용" 강조하세요.
        """
        
        # OpenAI API 호출
        response = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": "당신은 전문 미용사를 위한 헤어 기술 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7,
            top_p=0.9
        )
        
        ai_response = response.choices[0].message.content
        
        # 응답 검증 및 포맷팅
        if len(ai_response.strip()) < 50:
            raise Exception("응답이 너무 짧습니다")
            
        return ai_response
        
    except Exception as e:
        logger.error(f"OpenAI API 오류: {e}")
        
        # 폴백 응답 (더 전문적으로)
        return f"""
        <strong>🦎 {recipe_type} 전문 레시피</strong><br><br>
        
        <strong>📋 시술 가이드:</strong><br>
        {'<br>'.join([f'• {recipe}' for recipe in recipes])}<br><br>
        
        <strong>⚠️ 전문 미용사 전용 정보:</strong><br>
        • 고객 모발 진단 후 시술 진행<br>
        • 패치 테스트 24시간 전 실시<br>
        • 시술 중 모발 상태 지속 체크<br><br>
        
        <strong>🔧 시스템 정보:</strong><br>
        API 연결 오류: {str(e)[:50]}...<br>
        기본 레시피로 제공됩니다.
        """
        
    except KeyError as e:
        logger.error(f"환경변수 오류: {e}")
        return f"""
        <strong>⚠️ 시스템 설정 오류</strong><br><br>
        환경변수가 올바르게 설정되지 않았습니다.<br>
        관리자에게 문의해주세요.<br><br>
        <strong>오류:</strong> {str(e)}
        """

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'error': '메시지가 비어있습니다.'}), 400
        
        logger.info(f"미용사 질문: {message}")
        
        # 헤어 레시피 분석
        recipe_type, recipes = analyze_hair_query(message)
        
        # AI 응답 생성
        response = get_openai_response(message, recipe_type, recipes)
        
        logger.info(f"레시피 제공 완료: {recipe_type}")
        
        return jsonify({
            'response': response,
            'recipe_type': recipe_type,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"채팅 처리 오류: {e}")
        return jsonify({
            'response': '죄송합니다. 일시적인 오류가 발생했습니다. 다시 시도해주세요. 🙏',
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """서버 상태 및 환경변수 체크"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'openai_available': bool(client),
        'openai_model': openai_model,
        'claude_available': bool(claude_api_key and claude_api_key != '............'),
        'claude_model': claude_model if claude_api_key else None,
        'python_version': os.getenv('PYTHON_VERSION', 'default'),
        'port': os.getenv('PORT', '5000')
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 헤어게이터 서버 최종 시작!")
    print(f"📍 포트: {port}")
    print(f"🔑 OpenAI: {'✅ 연결됨' if client else '❌ 미연결'}")
    print(f"🤖 모델: {openai_model or '기본 레시피 모드'}")
    print(f"🔵 Claude: {'✅ 준비됨' if claude_api_key and claude_api_key != '............' else '❌ 미설정'}")
    print(f"🌐 환경: {os.getenv('ENVIRONMENT', 'development')}")
    print("=" * 50)
    print("💡 테스트 질문: '애쉬 브라운 레시피 알려주세요'")
    print("🎯 URL: https://여러분의도메인.onrender.com/health (상태 확인)")
    print("=" * 50)
    
    # Render 환경에서는 반드시 0.0.0.0으로 바인딩
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=(os.getenv('ENVIRONMENT') != 'production')
    )
