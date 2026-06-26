def fix_app_py():
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open('app.py', 'r', encoding='cp949') as f:
                content = f.read()
        except:
            with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
    if not content.startswith('# -*- coding: utf-8 -*-'):
        content = '# -*- coding: utf-8 -*-\n' + content
        
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Fixed app.py encoding!")

if __name__ == '__main__':
    fix_app_py()
