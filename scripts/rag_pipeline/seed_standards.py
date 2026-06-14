import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# 환경 변수 및 임포트 경로 로드
load_dotenv()

# landing_page 경로를 sys.path에 추가하여 audit_engine을 임포트
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from audit_engine import K_GAAP_CORPUS
    print("성공: K_GAAP_CORPUS 데이터를 가져왔습니다.")
except ImportError:
    # Fallback 코퍼스 데이터 직접 정의 (만약 임포트 실패 시)
    K_GAAP_CORPUS = [
        {
            "standard_no": "제6장 금융자산",
            "paragraph_no": "문단 6.17",
            "title": "수취채권의 손상(대손)평가",
            "content": "보고기간말 현재 수취채권의 회수가능성을 평가하여 대손충당금을 설정하여야 한다. 대손충당금은 과거의 대손경험률 및 채권의 연령 등을 고려하여 합리적이고 객관적인 기준에 따라 산정하여야 하며, 회수가 불확실한 채권에 대해서는 개별적으로 손상 여부를 검토하여 대손예상액을 충당금으로 계상하여야 한다."
        },
        {
            "standard_no": "제7장 재고자산",
            "paragraph_no": "문단 7.15",
            "title": "재고자산의 저가법 적용",
            "content": "재고자산은 취득원가와 시가 중 낮은 금액으로 측정한다. 시가가 취득원가보다 하락한 경우에는 저가법을 적용하여 평가손실을 인식하며, 이는 재고자산의 장부금액에서 직접 차감하거나 평가충당금 계정으로 표시하고 매출원가에 가산한다. 순실현가능가치의 하락 요인에는 물리적 손상, 진부화, 판매가격의 하락 등이 포함된다."
        },
        {
            "standard_no": "제10장 유형자산",
            "paragraph_no": "문단 10.33",
            "title": "유형자산의 감가상각 내용연수 및 상각방법",
            "content": "유형자산의 감가상각대상금액은 자산의 내용연수에 걸쳐 체계적인 방법으로 배분하여야 한다. 감가상각방법은 자산의 경제적 효익이 소멸되는 형태를 반영하여야 하며, 소멸 형태를 신뢰성 있게 결정할 수 없는 경우에는 정액법을 적용한다. 내용연수나 상각방법에 대한 재검토 결과 추정치가 변경되는 경우에는 회계추정의 변경으로 처리한다."
        },
        {
            "standard_no": "제10장 유형자산",
            "paragraph_no": "문단 10.38",
            "title": "유형자산의 손상차손 인식",
            "content": "유형자산의 진부화, 시장가치의 급격한 하락 등으로 인하여 자산의 회수가능액이 장부금액에 미달할 가능성이 있는 경우에는 손상 징후 여부를 검토하여야 한다. 자산의 회수가능액이 장부금액에 미달하는 경우, 장부금액을 회수가능액으로 감소시키고 그 감액분을 손상차손으로 당기손익에 반영한다."
        },
        {
            "standard_no": "제16장 수익",
            "paragraph_no": "문단 16.12",
            "title": "재화의 판매에 대한 수익인식기준",
            "content": "재화의 판매로 인한 수익은 다음 조건이 모두 충족될 때 인식한다. 1) 재화의 소유에 따른 유의적인 위험과 보상이 구매자에게 이전됨, 2) 판매자는 판매된 재화에 대하여 통상적으로 행사하는 정도의 관리나 효과적인 통제를 할 수 없음, 3) 수익금액을 신뢰성 있게 측정할 수 있음, 4) 경제적효익의 유입가능성이 매우 높음, 5) 거래와 관련하여 발생했거나 발생할 원가를 신뢰성 있게 측정할 수 있음."
        },
        {
            "standard_no": "제16장 수익",
            "paragraph_no": "문단 16.18",
            "title": "용역의 제공에 대한 수익인식기준",
            "content": "용역의 제공으로 인한 수익은 보고기간말 현재 거래의 진행률에 따라 수익을 인식한다. 진행률은 수행한 용역에 대한 측정, 총예정원가 대비 누적발생원가 비율 등 합리적인 방법으로 계산한다. 거래의 결과를 신뢰성 있게 추정할 수 없는 경우에는 회수 가능한 발생원가의 범위 내에서만 수익을 인식한다."
        },
        {
            "standard_no": "제21장 외화환산",
            "paragraph_no": "문단 21.7",
            "title": "보고기간말 화폐성 외화자산·부채의 환산",
            "content": "보고기간말 현재의 화폐성 외화자산 및 외화부채는 보고기간말 현재의 마감환율로 환산하여야 한다. 환산 과정에서 발생하는 외화환산손익은 당기손익으로 인식하며, 비화폐성 외화자산 및 부채는 취득일의 역사적 환율로 환산하는 것을 원칙으로 한다."
        }
    ]

# Supabase 설정
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key or url == "YOUR_SUPABASE_PROJECT_URL_HERE":
    print("오류: .env 파일에 올바른 SUPABASE_URL 및 SUPABASE_KEY가 누락되었습니다.")
    sys.exit(1)

supabase: Client = create_client(url, key)

def seed_database():
    # 1. 임베딩 모델 로딩
    print("Sentence-Transformers 모델을 로드 중입니다 (all-MiniLM-L6-v2)...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('all-MiniLM-L6-v2')
        print("모델 로드 성공!")
    except ImportError:
        print("오류: sentence-transformers 패키지가 아직 설치되지 않았습니다. 설치를 대기해 주세요.")
        return

    # 2. 기존 DB 데이터 청소 (안전한 갱신)
    print("기존 K-GAAP 기준서 테이블을 비우는 중...")
    try:
        supabase.table("k_gaap_standards").delete().neq("id", 0).execute()
        print("기존 데이터 제거 성공.")
    except Exception as clean_err:
        print(f"테이블 청소 경고 (테이블이 아직 없거나 권한 부족일 수 있음): {clean_err}")
        print("계속해서 업서트를 시도합니다.")

    # 3. 기준서 코퍼스 임베딩 및 업로드
    print("기준서 임베딩 적재 시작...")
    
    insert_records = []
    for idx, item in enumerate(K_GAAP_CORPUS, 1):
        text_to_embed = f"{item['standard_no']} {item['paragraph_no']} {item['title']} {item['content']}"
        print(f"[{idx}/{len(K_GAAP_CORPUS)}] 임베딩 생성 중: {item['standard_no']} - {item['paragraph_no']}")
        
        # 384차원 임베딩 벡터 리스트 생성
        embedding_vec = model.encode(text_to_embed).tolist()
        
        record = {
            "standard_no": item["standard_no"],
            "paragraph_no": item["paragraph_no"],
            "title": item["title"],
            "content": item["content"],
            "embedding": embedding_vec
        }
        insert_records.append(record)

    # 4. Supabase DB 일괄 삽입
    try:
        response = supabase.table("k_gaap_standards").insert(insert_records).execute()
        print(f"성공: 총 {len(insert_records)}개의 K-GAAP 기준서 임베딩이 Supabase pgvector DB에 성공적으로 적재되었습니다!")
    except Exception as e:
        print(f"데이터베이스 적재 중 오류 발생: {e}")
        print("참고: Supabase SQL Editor를 통해 supabase_schema.sql DDL 스크립트를 먼저 실행하셨는지 확인해 주세요.")

if __name__ == "__main__":
    seed_database()
