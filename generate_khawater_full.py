import re
import os
import glob

# Configuration
BOOKS_DIR = r"m:\Sheikh Ahmed\books"
OUTPUT_FILE = r"m:\Sheikh Ahmed\books\khawater-success-path.html"

def find_input_file():
    # Find file starting with specific arabic chars
    try:
        files = os.listdir(BOOKS_DIR)
        for f in files:
            if "خَوَاطِرُ" in f and f.endswith(".txt"):
                print(f"Found input file: {f}")
                return os.path.join(BOOKS_DIR, f)
    except Exception as e:
        print(f"Error finding file: {e}")
    return None

def create_html_content(articles):
    # HTML generation logic
    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="خواطر على درب النجاح والتزكية - الشيخ أحمد إسماعيل الفشني - النسخة الكاملة">
    <title>خواطر على درب النجاح والتزكية | الشيخ أحمد الفشني</title>
    
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=Cairo:wght@300;400;500;600;700&family=Tajawal:wght@400;500;700&family=Aref+Ruqaa:wght@400;700&display=swap" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    
    <!-- AOS Animation -->
    <link href="https://unpkg.com/aos@2.3.1/dist/aos.css" rel="stylesheet">
    
    <!-- Styles -->
    <link rel="stylesheet" href="../style.css">
    
    <style>
        :root {{
            /* Updated to match site standard colors */
            --theme-color: #1a5f4a; /* Deep Green */
            --theme-light: #2d8b6f;
            --theme-accent: #c9a227; /* Gold */
        }}
        
        body {{
            background-color: #faf9f6;
            font-family: 'Cairo', sans-serif;
            color: #333;
        }}

        .book-header {{
            background: linear-gradient(135deg, var(--theme-color), var(--theme-light));
            color: white;
            padding: 120px 0 60px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}

        .book-title {{
            font-family: 'Amiri', serif;
            font-size: 3.5rem;
            margin-bottom: 20px;
            position: relative;
            z-index: 2;
        }}

        .book-container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 40px;
            align-items: start;
        }}

        /* Sidebar Navigation */
        .book-sidebar {{
            position: sticky;
            top: 100px;
            max-height: calc(100vh - 140px);
            overflow-y: auto;
            background: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            scrollbar-width: thin;
            scrollbar-color: var(--theme-accent) #eee;
        }}

        .sidebar-title {{
            font-family: 'Tajawal', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--theme-color);
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--theme-accent);
        }}

        .toc-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        .toc-item {{
            margin-bottom: 2px;
        }}

        .toc-link {{
            display: block;
            padding: 8px 12px;
            color: #555;
            border-radius: 6px;
            transition: all 0.3s ease;
            font-size: 0.95rem;
            border-right: 3px solid transparent;
            text-decoration: none;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .toc-link:hover, .toc-link.active {{
            background: rgba(230, 126, 34, 0.1);
            color: var(--theme-color);
            border-right-color: var(--theme-accent);
            padding-right: 15px;
            font-weight: 600;
        }}

        .toc-section-header {{
            font-weight: bold;
            color: var(--theme-color);
            background: #f1f2f6;
            padding: 10px 15px;
            margin: 15px 0 5px;
            font-size: 1rem;
            border-radius: 5px;
            font-family: 'Amiri', serif;
            border-right: 4px solid var(--theme-accent);
        }}

        /* Main Content */
        .book-content {{
            background: white;
            padding: 60px;
            border-radius: 15px;
            box-shadow: 0 5px 25px rgba(0,0,0,0.05);
            line-height: 2;
            font-size: 1.2rem;
            min-height: 100vh;
            text-align: center; /* Center text */
        }}

        .article-card {{
            margin-bottom: 80px;
            padding-bottom: 40px;
            border-bottom: 1px solid #eee;
            scroll-margin-top: 120px;
        }}

        .article-number {{
            color: var(--theme-accent);
            font-family: 'Aref Ruqaa', serif;
            font-size: 1.5rem;
            display: block;
            margin-bottom: 10px;
        }}

        .article-title {{
            font-family: 'Amiri', serif;
            font-size: 2.2rem;
            color: var(--theme-color);
            margin-bottom: 30px;
            position: relative;
            padding-bottom: 15px;
            display: inline-block; /* For centering */
        }}
        
        .article-title::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 3px;
            background: var(--theme-accent);
            opacity: 1;
        }}

        .section-separator {{
            text-align: center;
            margin: 100px 0 60px;
            position: relative;
        }}
        
        .section-separator span {{
            background: var(--theme-color);
            color: white;
            padding: 15px 40px;
            border-radius: 50px;
            font-family: 'tajawal', sans-serif;
            font-weight: bold;
            font-size: 1.6rem;
            position: relative;
            z-index: 1;
            box-shadow: 0 4px 15px rgba(44, 62, 80, 0.3);
            display: inline-block;
        }}
        
        .section-separator::before {{
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            width: 100%;
            height: 2px;
            background: #eee;
            z-index: 0;
        }}

        .quran-box {{
            background: #f4fcf9;
            border-right: 4px solid #1a5f4a;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px 0 0 8px;
            font-family: 'Amiri', serif;
            font-size: 1.4rem;
            color: #1a5f4a;
            line-height: 2.2;
        }}
        
        .hadith-box {{
            background: #fffbf0;
            border-right: 4px solid #c9a227;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px 0 0 8px;
            color: #5d4037;
            font-style: normal;
        }}
        
        .poetry-box {{
            background: #f8f9fa;
            border: 1px dashed #bbc1c7;
            padding: 30px;
            margin: 30px 0;
            text-align: center;
            font-family: 'Amiri', serif;
            font-weight: bold;
            font-size: 1.3rem;
            color: #34495e;
            line-height: 2.4;
        }}
        
        .list-item {{
            margin-right: 20px; 
            margin-bottom: 12px; 
            display: flex; 
            align-items: flex-start;
        }}
        
        .list-icon {{
            color: var(--theme-accent);
            margin-left: 10px;
            font-size: 0.8em; 
            margin-top: 10px;
        }}

        @media (max-width: 900px) {{
            .book-container {{
                grid-template-columns: 1fr;
            }}
            .book-sidebar {{
                display: none; 
            }}
            .book-content {{
                padding: 20px;
            }}
            .book-title {{
                font-size: 2rem;
            }}
            .section-separator span {{
                font-size: 1.2rem;
                padding: 10px 20px;
            }}
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <header class="book-header">
        <div class="container">
            <h1 class="book-title" data-aos="fade-down">خواطر على درب النجاح والتزكية</h1>
            <p data-aos="fade-up" data-aos-delay="200" style="font-size: 1.2rem;">بقلم فضيلة الشيخ أحمد إسماعيل الفشني</p>
            <a href="../books.html" class="btn btn-light" style="margin-top: 20px; display: inline-block; padding: 10px 30px; background:white; color:var(--theme-color); border-radius: 30px; text-decoration: none; font-weight: bold; transition: all 0.3s; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                <i class="fas fa-arrow-right"></i> عودة للمكتبة
            </a>
        </div>
    </header>

    <div class="book-container">
        <!-- Sidebar TOC -->
        <aside class="book-sidebar">
            <div class="sidebar-title"><i class="fas fa-list"></i> فهرس الموضـوعات</div>
            <ul class="toc-list">
                {generate_toc_html(articles)}
            </ul>
        </aside>

        <!-- Main Content -->
        <main class="book-content">
            {generate_body_html(articles)}
        </main>
    </div>

    <!-- Scripts -->
    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script>
        AOS.init();
        
        // Active TOC link on scroll
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    document.querySelectorAll('.toc-link').forEach(link => link.classList.remove('active'));
                    const id = entry.target.getAttribute('id');
                    const link = document.querySelector(`.toc-link[href="#${{id}}"]`);
                    if (link) link.classList.add('active');
                    
                    // Scroll TOC to active element
                     if (link) {{
                        link.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                    }}
                }}
            }});
        }}, {{ threshold: 0.1, rootMargin: "-100px 0px -60% 0px" }});

        document.querySelectorAll('.article-card').forEach((section) => {{
            observer.observe(section);
        }});
    </script>
</body>
</html>"""
    return html_content

def generate_toc_html(articles):
    html = ""
    for item in articles:
        if item['type'] == 'section':
             html += f'<li class="toc-section-header">{item["title"]}</li>'
        else:
            html += f'<li class="toc-item"><a href="#article-{item["id"]}" class="toc-link">{item["title"]}</a></li>'
    return html

def generate_body_html(articles):
    html = ""
    for item in articles:
        if item['type'] == 'section':
            html += f"""
            <div class="section-separator" data-aos="fade-up">
                <span>{item['title']}</span>
            </div>
            """
        elif item['type'] == 'article':
            content_html = process_content(item['content'])
            html += f"""
            <article id="article-{item['id']}" class="article-card" data-aos="fade-up">
                <span class="article-number">{item['number']}</span>
                <h2 class="article-title">{item['title']}</h2>
                <div class="article-body">
                    {content_html}
                </div>
            </article>
            """
    return html

def process_content(text):
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        line = line.strip()
        if not line: 
            continue 
        
        if "﴿" in line and "﴾" in line:
            return_line = f'<div class="quran-box">{line}</div>'
        elif ("قال رسول الله" in line or "صلى الله عليه وسلم" in line) and ("«" in line or '"' in line) and len(line) < 400:
             return_line = f'<div class="hadith-box"><i class="fas fa-quote-right" style="color:#c9a227; margin-left:10px;"></i>{line}</div>'
        elif "***" in line:
             parts = line.split("***")
             if len(parts) == 2:
                return_line = f'<div class="poetry-box">{parts[0].strip()} &nbsp;&nbsp;***&nbsp;&nbsp; {parts[1].strip()}</div>'
             else:
                return_line = f'<div class="poetry-box">{line}</div>'
        elif len(line) < 100 and (".." in line and line.count(".") > 3) or (line.count("   ") > 1):
             # Try to catch informal poetry styling
             return_line = f'<div class="poetry-box">{line}</div>'
        elif line.startswith("*") or line.startswith("-"):
            return_line = f'<div class="list-item"><i class="fas fa-check-circle list-icon"></i><span>{line[1:]}</span></div>'
        else:
            return_line = f'<p>{line}</p>'
            
        processed_lines.append(return_line)
        
    return "".join(processed_lines)

def parse_file(filepath):
    print(f"Reading file: {{filepath}}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    items = []
    
    # 1. Intro
    intro_start = content.find("المُقَدِّمَة")
    if intro_start != -1:
        first_marker_match = re.search(r'(البَابُ|الفصل|\d+\.)', content[intro_start+10:])
        if first_marker_match:
            intro_end = intro_start + 10 + first_marker_match.start()
            intro_text = content[intro_start:intro_end]
            items.append({
                'type': 'article',
                'id': 'intro',
                'number': 'مقدمة الكتاب',
                'title': 'المقدمة',
                'content': intro_text.replace("المُقَدِّمَة", "").strip()
            })
    
    section_pattern = re.compile(r'^(البَابُ|الفصل)\s+.*$')
    article_pattern = re.compile(r'^(\d+)\.\s+(.*)$')
    
    lines = content.split('\n')
    current_article = None
    current_content = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        
        if "المُقَدِّمَة" in line:
            continue
            
        sec_match = section_pattern.match(line)
        art_match = article_pattern.match(line)
        
        if sec_match:
            if current_article:
                current_article['content'] = "\n".join(current_content)
                items.append(current_article)
                current_article = None
                current_content = []
            
            items.append({
                'type': 'section',
                'title': line
            })
            
        elif art_match:
            if current_article:
                current_article['content'] = "\n".join(current_content)
                items.append(current_article)
            
            current_article = {
                'type': 'article',
                'id': art_match.group(1),
                'number': f'خاطرة {art_match.group(1)}',
                'title': art_match.group(2),
                'content': ''
            }
            current_content = []
            
        else:
            if current_article:
                current_content.append(line)
                
    if current_article:
        current_article['content'] = "\n".join(current_content)
        items.append(current_article)
        
    return items

def main():
    input_file_path = find_input_file()
    if not input_file_path:
        print("Error: Input file starting with 'خواطر' not found in books directory")
        return

    print("Parsing file...")
    articles = parse_file(input_file_path)
    print(f"Found {{len(articles)}} items.")
    
    print("Generating HTML...")
    html = create_html_content(articles)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Done! Created {{OUTPUT_FILE}}")

if __name__ == "__main__":
    main()
