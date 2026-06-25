import re

with open('templates/company.html', 'r', encoding='utf-8') as f:
    content = f.read()

pattern2 = r'<div class="glass-card dashboard-card master-card" id="partner-history-view" style="display: none;">.*?<div class="glass-card dashboard-card master-card" id="partner-inquiry-view"'

match = re.search(pattern2, content, flags=re.DOTALL)
if match:
    print('Match found!')
else:
    print('No match!')
