import codecs
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    text = f.read()
    idx_home = text.find('id="partner-home-view"')
    idx_progress = text.find('progress-section')
    idx_history = text.find('id="partner-history-view"')
    print('Home:', idx_home)
    print('Progress:', idx_progress)
    print('History:', idx_history)
