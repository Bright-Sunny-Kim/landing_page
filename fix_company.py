import os

def fix_company():
    path = r"C:\Users\CLAUD\landing_page\templates\company.html"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find and remove the extra closing div
    to_remove = "</div> <!-- Close partner-history-view -->\n"
    if to_remove in content:
        content = content.replace(to_remove, "<!-- Close partner-history-view removed -->\n")
    else:
        to_remove = "</div> <!-- Close partner-history-view -->"
        content = content.replace(to_remove, "<!-- Close partner-history-view removed -->")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    fix_company()
