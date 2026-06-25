import codecs

with codecs.open('app.py', 'r', 'utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'uploaded_files_data = []' in line:
        insert_idx = i + 1
        break

new_logic = '''
    single_category = request.form.get('category')
    if single_category:
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
            status = '완료'
            
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
'''

# We also need to indent `for field_name, label in document_labels.items():` and everything below it?
# Or just let it run if `uploaded_files_data` is empty?
# If we just do `if not single_category:`, we can indent the old loop.
# It's easier to just do:

new_logic = '''
    single_category = request.form.get('category')
    if single_category:
        field_name = None
        if single_category == 'P-File': field_name = request.form.get('pfile_doc')
        elif single_category == 'Temp': field_name = request.form.get('written_doc')
        elif single_category == 'Ext_F': field_name = request.form.get('finance_doc')
        elif single_category == 'Ext_C': field_name = request.form.get('partner_doc')
        if field_name and field_name in document_labels:
            label = document_labels[field_name]
            files = request.files.getlist('file')
            if field_name.startswith('pfile_'): year_folder = 'P-File'
            elif 'finance' in field_name: year_folder = 'Ext_F'
            elif 'partner' in field_name: year_folder = 'Ext_C'
            elif 'current' in field_name: year_folder = 'Temp/Temp_P'
            else: year_folder = 'Temp/Temp_L'
            for file in files:
                if file.filename != '':
                    uploaded_files_data.append((field_name, label, file, '완료', year_folder))
    else:
'''

# Now indent all lines from insert_idx until `form_type = request.form.get('form_type', '')`
end_idx = insert_idx
for i in range(insert_idx, len(lines)):
    if 'form_type = request.form.get(' in lines[i]:
        end_idx = i
        break

for i in range(insert_idx, end_idx):
    lines[i] = '    ' + lines[i]

lines.insert(insert_idx, new_logic)

with codecs.open('app.py', 'w', 'utf-8') as f:
    f.writelines(lines)
print("app.py updated perfectly!")
