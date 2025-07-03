import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Optional
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from style_codes import style_code_to_name

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")
llm = ChatOpenAI(model="gpt-4o")
db = Chroma(persist_directory="./hairgator_chroma_db_v2", embedding_function=embedding_model)

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=""""
당신은 HairGator라는 AI 기반의 전문 헤어 디자이너입니다.

질문에 응답할 때 다음 원칙을 지키세요:
1. 말투는 전문가답게, 설명은 정확하게.
2. 파라미터나 수치는 괄호로 쉽게 설명하세요.
3. 질문이 스타일 전체일 경우:
   - 스타일 요약
   - 컷 순서
   - 주요 파라미터
   - 관리 팁

<참고 정보>
{context}

<질문>
{question}
"""
)

def extract_vision_parameters(image_url: str) -> str:
    vision_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": "이 이미지를 HairGator 파라미터 체계로 분석해줘. Length, Axis, Direction, Cut Shape 등 30개 파라미터 중 가능한 것들을 JSON으로 출력해줘."}
            ]}
        ],
        max_tokens=500
    )
    return vision_response.choices[0].message.content.strip()

def process_hairgator_request(text: Optional[str], image_url: Optional[str]):
    vision_summary = ""
    if image_url:
        try:
            vision_summary = extract_vision_parameters(image_url)
        except Exception as e:
            vision_summary = f"[Vision 분석 실패: {e}]"

    question = ""
    if text and vision_summary:
        question = f"아래는 이미지 분석 결과입니다: {vision_summary}\n\n사용자 질문: {text}"
    elif vision_summary:
        question = f"이 이미지를 기반으로 스타일을 분석하고 추천해주세요. 분석 결과: {vision_summary}"
    elif text:
        question = text
    else:
        return {"error": "text 또는 image_url 중 하나는 필요합니다."}

    retriever = db.as_retriever(search_kwargs={"k": 10})
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        chain_type="stuff",
        chain_type_kwargs={"prompt": prompt_template}
    )
    response = qa_chain.invoke({"query": question})

    seen = set()
    style_refs = []
    for doc in response["source_documents"]:
        code = doc.metadata.get("style_code")
        if code and code not in seen:
            seen.add(code)
            style_refs.append({
                "style_code": code,
                "style_name": style_code_to_name.get(code, code),
                "chunk_type": doc.metadata.get("chunk_type"),
                "content": doc.page_content
            })

    return {
        "question": question,
        "result": response["result"],
        "reference_styles": style_refs
    }
