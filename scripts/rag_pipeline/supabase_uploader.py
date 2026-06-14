import os
from supabase import create_client, Client
from dotenv import load_dotenv

class SupabaseUploader:
    def __init__(self):
        # 환경 변수에서 Supabase 설정 로드
        load_dotenv()
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            print("[Warning] SUPABASE_URL 또는 SUPABASE_KEY가 설정되지 않았습니다.")
            self.supabase = None
        else:
            self.supabase: Client = create_client(url, key)
            
        self.bucket_name = "audit-standards"

    def ensure_bucket_exists(self):
        """기준서 저장용 신규 버킷을 생성합니다."""
        if not self.supabase:
            return
            
        try:
            buckets = self.supabase.storage.list_buckets()
            bucket_names = [b.name for b in buckets]
            
            if self.bucket_name not in bucket_names:
                print(f"[Supabase] '{self.bucket_name}' 버킷을 생성합니다.")
                self.supabase.storage.create_bucket(self.bucket_name, options={"public": False})
            else:
                print(f"[Supabase] '{self.bucket_name}' 버킷이 이미 존재합니다.")
        except Exception as e:
            print(f"[Supabase] 버킷 확인/생성 오류: {e}")

    def upload_file(self, file_path: str, metadata: dict = None, dest_path: str = None):
        """PDF 파일을 버킷에 업로드합니다."""
        if not os.path.exists(file_path):
            print(f"[Supabase] 오류: 파일을 찾을 수 없습니다. ({file_path})")
            return None
            
        filename = os.path.basename(file_path)
        # dest_path가 제공되면 해당 경로로, 아니면 기본 파일명으로 업로드
        storage_path = dest_path if dest_path else filename
        
        try:
            with open(file_path, 'rb') as f:
                # upsert=True 옵션으로 덮어쓰기 허용
                res = self.supabase.storage.from_(self.bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"upsert": "true", "content-type": "application/pdf"}
                )
            print(f"[Supabase] '{storage_path}' 업로드 완료.")
            
            # 메타데이터 테이블에 파일 정보 로깅 (선택 사항)
            if metadata:
                self._save_metadata(storage_path, metadata)
                
            return storage_path
        except Exception as e:
            print(f"[Supabase] 파일 업로드 오류: {e}")
            return None

    def _save_metadata(self, storage_path: str, metadata: dict):
        """업로드된 파일의 메타데이터를 standards_archive 테이블에 저장합니다."""
        try:
            # 원문 파일 링크 URL 생성 (Signed URL 등을 쓸 수도 있음)
            file_url = self.supabase.storage.from_(self.bucket_name).get_public_url(storage_path)
            
            data = {
                "document_name": metadata.get("title"),
                "document_type": metadata.get("type"),
                "file_url": file_url,
                "storage_path": storage_path,
                # 필요시 발효일 등 추가
            }
            
            # standards_archive 테이블에 삽입
            res = self.supabase.table("standards_archive").insert(data).execute()
            print(f"[Supabase] DB 메타데이터 저장 완료: {metadata.get('title')}")
            
        except Exception as e:
            print(f"[Supabase] 메타데이터 저장 오류: {e}")

if __name__ == "__main__":
    import tempfile
    uploader = SupabaseUploader()
    uploader.ensure_bucket_exists()
    
    # 앞선 크롤러 테스트에서 다운받았던 파일 경로
    test_pdf_path = os.path.join(tempfile.gettempdir(), "audit_standards", "K-GAAP_KGAAPSampleTest.pdf")
    
    if os.path.exists(test_pdf_path):
        print(f"\n[테스트] 원문 PDF 파일 업로드 테스트 시작: {test_pdf_path}")
        uploader.upload_file(test_pdf_path, {"title": "K-GAAP 테스트 문서", "type": "K-GAAP"})
        print("[테스트] 업로더 실행 완료.\n")
    else:
        print(f"[에러] 업로드할 테스트 PDF 파일이 없습니다: {test_pdf_path}")
