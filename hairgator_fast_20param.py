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

# OpenAI 설정 (안전하게)
try:
    import openai
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if openai_api_key:
        openai.api_key = openai_api_key
        print("✅ OpenAI API 설정 완료")
    else:
        print("⚠️ OpenAI API 키가 없습니다 - 테스트 모드로 실행")
except Exception as e:
    print(f"⚠️ OpenAI 초기화 오류: {e}")
    openai = None

# 간단한 헤어 진단 데이터
HAIR_SOLUTIONS = {
    "탈모": ["미녹시딜 사용", "모발이식 상담", "영양제 복용", "스트레스 관리"],
    "지성모발": ["순한 샴푸 사용", "주 2-3회 세발", "기름기 제거 제품"],
    "건성모발": ["보습 트리트먼트", "오일 케어", "부드러운 샴푸"],
    "비듬": ["항진균 샴푸", "스케일링", "피부과 상담"],
    "모발손상": ["단백질 트리트먼트", "열 보호제", "정기적 컷팅"]
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
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            min-height: -webkit-fill-available;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
            position: fixed;
            width: 100%;
            height: 100%;
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
            .container {
                width: 100%;
                height: 100%;
                border-radius: 0;
                max-width: none;
            }
        }
        
        .header {
            background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2rem;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 1rem;
        }
        
        .chat-container {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
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
            background: #007bff;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        
        .bot-message {
            background: white;
            color: #333;
            margin-right: auto;
            border: 1px solid #e9ecef;
        }
        
        .input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e9ecef;
            padding-bottom: calc(20px + env(safe-area-inset-bottom));
            position: relative;
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
            border-color: #007bff;
            -webkit-appearance: none;
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
            background: #007bff;
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
        }
        
        .send-btn:hover, .send-btn:active {
            background: #0056b3;
            transform: scale(0.98);
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
            color: #28a745;
            background: #d4edda;
            border-bottom: 1px solid #c3e6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status">
            ✅ 서버 연결됨 - 기본 헤어 진단 서비스 제공 중
        </div>
        
        <div class="header">
            <h1>🦎 헤어게이터</h1>
            <p>AI 헤어케어 전문가가 도와드려요!</p>
        </div>
        
        <div class="chat-container" id="chatContainer">
            <div class="message bot-message">
                안녕하세요! 헤어게이터입니다 🦎✨<br>
                어떤 헤어 고민이 있으신가요?<br>
                <br>
                <strong>질문 예시:</strong><br>
                • "머리가 많이 빠져요"<br>
                • "머리가 너무 기름져요"<br>
                • "비듬이 심해요"<br>
                • "모발이 손상됐어요"
            </div>
        </div>
        
        <div class="loading" id="loading">
            💭 헤어게이터가 생각 중이에요...
        </div>
        
        <div class="input-container">
            <div class="input-group">
                <input type="text" id="userInput" class="input-field" 
                       placeholder="헤어 고민을 말씀해주세요..." 
                       onkeypress="handleKeyPress(event)">
                <button onclick="sendMessage()" class="send-btn" id="sendBtn">전송</button>
            </div>
        </div>
    </div>

    <script>
        // 키보드 대응 (iOS/Android)
        let initialViewportHeight = window.visualViewport ? window.visualViewport.height : window.innerHeight;
        
        function handleViewportChange() {
            if (window.visualViewport) {
                const currentHeight = window.visualViewport.height;
                const heightDiff = initialViewportHeight - currentHeight;
                
                if (heightDiff > 150) { // 키보드가 올라왔을 때
                    document.body.style.height = currentHeight + 'px';
                    document.querySelector('.container').style.height = currentHeight + 'px';
                } else { // 키보드가 내려갔을 때
                    document.body.style.height = '100vh';
                    document.querySelector('.container').style.height = '100vh';
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
        
        // 입력 필드 포커스 시 스크롤 조정
        document.getElementById('userInput').addEventListener('focus', function() {
            setTimeout(() => {
                this.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        });

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

def analyze_hair_concern(message):
    """간단한 키워드 기반 헤어 진단"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['탈모', '빠짐', '빠져', '빠지', '모발', '대머리']):
        return "탈모", HAIR_SOLUTIONS["탈모"]
    elif any(word in message_lower for word in ['기름', '지성', '끈적', '번들']):
        return "지성모발", HAIR_SOLUTIONS["지성모발"]
    elif any(word in message_lower for word in ['건조', '건성', '푸석', '거칠']):
        return "건성모발", HAIR_SOLUTIONS["건성모발"]
    elif any(word in message_lower for word in ['비듬', '각질', '가려']):
        return "비듬", HAIR_SOLUTIONS["비듬"]
    elif any(word in message_lower for word in ['손상', '끊어', '갈라', '트리트먼트']):
        return "모발손상", HAIR_SOLUTIONS["모발손상"]
    else:
        return "일반상담", ["규칙적인 헤어케어", "전문가 상담", "적절한 제품 사용"]

def get_openai_response(message, hair_type, solutions):
    """OpenAI API를 통한 응답 생성 (안전 처리)"""
    if not openai or not openai.api_key:
        return f"""
        <strong>🦎 {hair_type} 진단 결과</strong><br><br>
        
        <strong>추천 솔루션:</strong><br>
        {'<br>'.join([f'• {sol}' for sol in solutions])}<br><br>
        
        <strong>💡 추가 팁:</strong><br>
        전문가와 상담하시는 것을 권장드려요!
        """
    
    try:
        prompt = f"""
        사용자의 헤어 고민: {message}
        진단된 문제: {hair_type}
        추천 솔루션: {', '.join(solutions)}
        
        헤어케어 전문가로서 친근하고 도움이 되는 조언을 200자 이내로 제공해주세요.
        이모지를 적절히 사용하고, 구체적이고 실용적인 팁을 포함해주세요.
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"OpenAI API 오류: {e}")
        return f"""
        <strong>🦎 {hair_type} 진단 결과</strong><br><br>
        
        <strong>추천 솔루션:</strong><br>
        {'<br>'.join([f'• {sol}' for sol in solutions])}<br><br>
        
        <strong>💡 추가 팁:</strong><br>
        규칙적인 관리와 전문가 상담을 권장드려요!
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
        
        logger.info(f"사용자 메시지: {message}")
        
        # 헤어 고민 분석
        hair_type, solutions = analyze_hair_concern(message)
        
        # AI 응답 생성
        response = get_openai_response(message, hair_type, solutions)
        
        logger.info(f"응답 생성 완료: {hair_type}")
        
        return jsonify({
            'response': response,
            'hair_type': hair_type,
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
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'openai_available': bool(openai and openai.api_key)
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 헤어게이터 서버 시작!")
    print(f"📍 포트: {port}")
    print(f"🔑 OpenAI API: {'✅ 연결됨' if openai and openai.api_key else '❌ 미연결'}")
    print(f"🌐 서버 모드: {'Production' if os.environ.get('FLASK_ENV') == 'production' else 'Development'}")
    
    # Render 환경에서는 반드시 0.0.0.0으로 바인딩
    app.run(host='0.0.0.0', port=port, debug=False)
