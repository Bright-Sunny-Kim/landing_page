import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    text = f.read()
    if 'id="email"' in text:
        print('Yes')
    else:
        print('No')
