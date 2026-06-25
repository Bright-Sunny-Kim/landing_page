import codecs

with codecs.open('app.py', 'r', 'utf-8', errors='ignore') as f:
    content = f.read()

# We need to insert logic at line 690 where `uploaded_files_data = []` starts.
# Wait, let's find `uploaded_files_data = []`
idx = content.find('uploaded_files_data = []')
if idx != -1:
    old_logic = content[idx:content.find('# DB insert only', idx)] # just a rough cut, let's use replace.

# Let's find exactly the block to replace.
search_str = '''    uploaded_files_data = []

    for field_name, label in document_labels.items():
        status = request.form.get(f'{field_name}_status', '미제출')
        files = request.files.getlist(field_name)

        # 항목별 폴더명 분류
        if field_name.startswith('pfile_'):
            year_folder = 'P-File'
        elif field_name == 'finance_inquiry':
            year_folder = 'Ext_F'
        elif field_name == 'partner_inquiry':
            year_folder = 'Ext_C'
        elif 'current' in field_name:
            year_folder = 'Temp/Temp_P'
        else:
            year_folder = 'Temp/Temp_L'

        if status == '제출' and len(files) > 0 and files[0].filename != '':
            for file in files:
                if file.filename != '':
                    uploaded_files_data.append((field_name, label, file, status, year_folder))
        elif status in ['검토중', '해당없음']:
            # DB entry only
            uploaded_files_data.append((field_name, label, None, status, year_folder))'''

new_str = '''    uploaded_files_data = []
    
    # Check if this is the new single-item form from "제출 내역 조회"
    single_category = request.form.get('category')
    if single_category:
        # Determine the selected field_name based on the category
        field_name = None
        if single_category == 'P-File':
            field_name = request.form.get('pfile_doc')
        elif single_category == 'Temp':
            field_name = request.form.get('written_doc')
        elif single_category == 'Ext_F':
            field_name = request.form.get('finance_doc')
        elif single_category == 'Ext_C':
            field_name = request.form.get('partner_doc')
            
        if field_name and field_name in document_labels:
            label = document_labels[field_name]
            files = request.files.getlist('file')
            status = '제출' # The new form implicitly means submitting a file
            
            # Determine year_folder
            if field_name.startswith('pfile_'):
                year_folder = 'P-File'
            elif 'finance' in field_name:
                year_folder = 'Ext_F'
            elif 'partner' in field_name:
                year_folder = 'Ext_C'
            elif 'current' in field_name:
                year_folder = 'Temp/Temp_P'
            else:
                year_folder = 'Temp/Temp_L'
                
            for file in files:
                if file.filename != '':
                    uploaded_files_data.append((field_name, label, file, status, year_folder))
    else:
        # Original mass-upload form logic
        for field_name, label in document_labels.items():
            status = request.form.get(f'{field_name}_status', '미제출')
            files = request.files.getlist(field_name)

            # 항목별 폴더명 분류
            if field_name.startswith('pfile_'):
                year_folder = 'P-File'
            elif field_name == 'finance_inquiry':
                year_folder = 'Ext_F'
            elif field_name == 'partner_inquiry':
                year_folder = 'Ext_C'
            elif 'current' in field_name:
                year_folder = 'Temp/Temp_P'
            else:
                year_folder = 'Temp/Temp_L'

            if status == '제출' and len(files) > 0 and files[0].filename != '':
                for file in files:
                    if file.filename != '':
                        uploaded_files_data.append((field_name, label, file, status, year_folder))
            elif status in ['검토중', '해당없음']:
                # DB entry only
                uploaded_files_data.append((field_name, label, None, status, year_folder))'''

if search_str in content:
    content = content.replace(search_str, new_str)
    with codecs.open('app.py', 'w', 'utf-8') as f:
        f.write(content)
    print("Successfully updated app.py logic")
else:
    print("Could not find the target string in app.py")
