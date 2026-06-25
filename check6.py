import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    html = f.read()
html = html.replace('id="partner-history-view" style="display: none;"', 'id="partner-history-view" style="display: block; border: 5px solid red; min-height: 200px;"')
with codecs.open('templates/company.html', 'w', 'utf-8') as f:
    f.write(html)
print('company.html updated to show partner-history-view on load')
