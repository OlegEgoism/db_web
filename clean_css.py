import re
import glob
from bs4 import BeautifulSoup

# Папки с HTML-шаблонами и CSS-файлом
TEMPLATE_DIR = "templates"
CSS_FILE = "static/css/style.css"
CLEANED_CSS_FILE = "static/css/style.css"

# Найти все использованные классы в HTML-файлах
used_classes = set()

for html_file in glob.glob(f"{TEMPLATE_DIR}/**/*.html", recursive=True):
    with open(html_file, "r", encoding="utf-8") as file:
        soup = BeautifulSoup(file, "html.parser")
        for tag in soup.find_all(class_=True):
            used_classes.update(tag.get("class", []))

# Читаем исходный CSS-файл
with open(CSS_FILE, "r", encoding="utf-8") as file:
    css_lines = file.readlines()

# Фильтруем CSS: оставляем только те классы, которые используются
cleaned_css = []
css_block = []
keep_block = False

for line in css_lines:
    class_match = re.match(r"^\s*\.([-_a-zA-Z0-9]+)", line)
    if class_match:
        class_name = class_match.group(1)
        keep_block = class_name in used_classes

    if "{" in line:
        css_block = [line]
    elif "}" in line:
        css_block.append(line)
        if keep_block:
            cleaned_css.extend(css_block)
    else:
        css_block.append(line)

# Записываем очищенный CSS в новый файл
with open(CLEANED_CSS_FILE, "w", encoding="utf-8") as file:
    file.writelines(cleaned_css)

print(f"✅ Очистка завершена! Новый файл: {CLEANED_CSS_FILE}")
