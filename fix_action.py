import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    text = f.read()
text = text.replace('action="/company/{{ company_name }}/upload"', 'action="/company/{{ company_name }}"')
with codecs.open('templates/company.html', 'w', 'utf-8') as f:
    f.write(text)
print('Fixed action URL')
