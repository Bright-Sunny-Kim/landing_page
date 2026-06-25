import codecs
from bs4 import BeautifulSoup

with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

view = soup.find(id='partner-history-view')
if view:
    with codecs.open('history_view_dump.html', 'w', 'utf-8') as f:
        f.write(view.prettify())
