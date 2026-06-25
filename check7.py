import codecs
import re
with codecs.open('templates/company.html', 'r', 'utf-8', errors='ignore') as f:
    content = f.read()

pattern2 = r'<div class="glass-card dashboard-card master-card" id="partner-history-view".*?<div class="glass-card dashboard-card master-card" id="partner-inquiry-view"'

new_div = '''<div class="glass-card dashboard-card master-card" id="partner-history-view" style="display: block; background-color: red; height: 500px; color: white;">
    <h1 style="color: white; font-size: 50px;">DEBUG RED BOX</h1>
</div>
<div class="glass-card dashboard-card master-card" id="partner-inquiry-view"'''

content = re.sub(pattern2, new_div, content, flags=re.DOTALL)

with codecs.open('templates/company.html', 'w', 'utf-8') as f:
    f.write(content)
print('company.html replaced with red box')
