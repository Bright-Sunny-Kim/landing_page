import codecs
with codecs.open('static/js/main.js', 'r', 'utf-8', errors='ignore') as f:
    lines = f.readlines()
for i in range(630, 680):
    if i < len(lines):
        print(f'{i+1}: {lines[i].strip()}')
