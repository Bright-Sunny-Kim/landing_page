import codecs
with codecs.open('static/js/main.js', 'r', 'utf-8', errors='ignore') as f:
    js = f.read().split('\n')
for i in range(408, 500):
    if i < len(js):
        print(f'{i+1}: {js[i].encode("utf-8")}')
