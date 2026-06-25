import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    text = f.read()
    idx = text.find('id="partner-inquiry-view"')
    if idx != -1:
        print(text[max(0, idx-50):idx+150])
