import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    html = f.read()
idx = html.find('id="partner-history-view"')
if idx != -1:
    print(html[idx-50:idx+100])
