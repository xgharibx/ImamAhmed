from bs4 import BeautifulSoup
import re

file_path = r'm:\Sheikh Ahmed\books\journey-of-light.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# 1. REMOVE CONTACT INFO
# The contact info starts with a specific paragraph.
start_marker = "الشيخ / أحمد إسماعيل الفشني - من علماء الأزهر الشريف"
found_start = False
trash_chapters = []

# Find the p tag containing the start marker
for p in soup.find_all('p'):
    if start_marker in p.text:
        # found it. This p is likely inside a chapter div.
        parent_chapter = p.find_parent('div', class_='chapter')
        if parent_chapter:
            # We want to remove this p and everything after it in this chapter
            # And remove all subsequent chapters until the end of book-container
            found_start = True
            
            # Remove p and siblings after
            siblings = list(p.next_siblings)
            for s in siblings:
                if s.name: s.decompose()
            p.decompose()
            
            # Identify subsequent chapters to remove
            next_chapter = parent_chapter.find_next_sibling('div', class_='chapter')
            while next_chapter:
                trash_chapters.append(next_chapter)
                next_chapter = next_chapter.find_next_sibling('div', class_='chapter')
            break

for ch in trash_chapters:
    ch.decompose()

# 2. ENHANCE / HIGHLIGHT
# We will iterate through all paragraphs in chapters
chapters = soup.find_all('div', class_='chapter')

for chapter in chapters:
    content_div = chapter.find('div', class_='chapter-content')
    if not content_div: continue
    
    # Work on a copy of children to modify safely
    children = list(content_div.children)
    
    for child in children:
        if child.name != 'p': continue
        text = child.get_text().strip()
        
        # Rule 1: Quran Box
        if '﴿' in text and '﴾' in text:
            # Wrap in quote-box
            wrapper = soup.new_tag('div', **{'class': 'quote-box'})
            child.wrap(wrapper)
            # Add icon
            icon = soup.new_tag('i', **{'class': 'fas fa-quran'})
            wrapper.insert(0, icon)
            
        # Rule 2: Hadith Box / Prophet Quote
        elif 'قال رسول الله' in text or 'يقول ﷺ' in text or 'قال ﷺ' in text:
            wrapper = soup.new_tag('div', **{'class': 'highlight-box'})
            child.wrap(wrapper)
            # Add label
            label = soup.new_tag('strong')
            label.string = "حديث شريف:"
            child.insert(0, label)
            child.insert(1, soup.new_string(" "))

        # Rule 3: Key Questions or Statements (Starting with Why/How)
        elif text.startswith('لِمَاذَا') or text.startswith('كَيْفَ') or text.startswith('مَاذَا'):
             child['class'] = child.get('class', []) + ['question-text']
             # Make it bold
             b = soup.new_tag('strong')
             b.string = text
             child.string = ""
             child.append(b)

        # Rule 4: Numbered lists inside P (If previous script didn't catch them)
        # Only if the whole paragraph is just a list item 1. ...
        elif text and text[0].isdigit() and text[1] == '.':
             # styling
             child['style'] = "font-weight: bold; color: var(--primary-green-dark);"

# 3. Save
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(str(soup))
