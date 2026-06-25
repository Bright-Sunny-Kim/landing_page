import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    text = f.read()

idx_progress = text.find('progress-section')
idx_home = text.find('id="partner-home-view"')
idx_history = text.find('id="partner-history-view"')

print(f'Home: {idx_home}')
print(f'Progress: {idx_progress}')
print(f'History: {idx_history}')
