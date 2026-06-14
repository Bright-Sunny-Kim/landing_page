import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Instead of regex with [\s\S], let's use exact line replacement
new_content = []
in_master = False
for line in content.splitlines():
    if "def master_page():" in line:
        in_master = True
        
    if in_master and "files_response = supabase.table('company_files').select('status').execute()" in line:
        # replace with our logic
        new_content.append("            # 전체 파일 가져오기")
        new_content.append("            files_response = supabase.table('company_files').select('company_name, file_url, file_name, status').execute()")
        continue
        
    if in_master and "stats['pending_tasks'] =" in line:
        new_content.append(line)
        # add our partner logic
        new_content.append("""
            # 파트너별 업로드율 계산
            for p in partners:
                p_company = p.get('company')
                p_files = [f for f in all_files if f.get('company_name') == p_company]
                valid_count = sum(1 for f in p_files if f.get('file_url') or (f.get('file_name') and '해당사항없음' in f.get('file_name')))
                rate = int((valid_count / 16.0) * 100)
                if rate > 100: rate = 100
                p['upload_rate'] = rate""")
        continue
        
    if in_master and "def master_detail(company_name):" in line:
        in_master = False

    new_content.append(line)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_content))

print("Updated app.py successfully")
