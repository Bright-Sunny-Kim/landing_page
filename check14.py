import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    text = f.read()
    idx1 = text.find('id="partner-history-view"')
    idx2 = text.find('id="partner-inquiry-view"')
    print('Size of history view:', idx2 - idx1)
