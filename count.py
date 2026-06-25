import codecs
with codecs.open('test.html', 'r', 'utf-8', errors='ignore') as f:
    html = f.read()
print('Number of missing items:', html.count('style="font-size: 0.8rem; color: #fca5a5;'))
print('Number of progress bars:', html.count('자료 제출 진척도'))
