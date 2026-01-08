import re
import os
import glob

# Configuration
BOOKS_DIR = r"m:\Sheikh Ahmed\books"
OUTPUT_FILE = r"m:\Sheikh Ahmed\books\stories-of-prophets.html"

def find_input_file():
    try:
        files = os.listdir(BOOKS_DIR)
        for f in files:
            if "قصص الانبياء" in f and f.endswith(".txt"):
                print(f"Found input file: {f}")
                return os.path.join(BOOKS_DIR, f)
    except Exception as e:
        print(f"Error finding file: {e}")
    return None

def parse_prophets_book(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the "Memo" icon which seems to mark episodes
    # The first split might be the book title/intro
    parts = re.split(r'📝', content)
    
    episodes = []
    
    # Process the intro (before first episode) if substantial
    intro_text = parts[0].strip()
    if len(intro_text) > 50:
        episodes.append({
            'title': 'مقدمة الكتاب',
            'content': intro_text,
            'id': 'intro'
        })
    
    # Process each episode
    for i, part in enumerate(parts[1:], 1):
        lines = part.strip().split('\n')
        
        # First line usually contains the Episode Number "إعداد الحلقة الأولى..."
        header_line = lines[0].strip()
        
        # Second line usually contains "عنوان الحلقة: ..."
        # We need to find the title line
        title_line = ""
        body_start_index = 1
        
        for idx, line in enumerate(lines[:5]): # Look in first 5 lines
            if "عنوان الحلقة" in line:
                title_line = line.replace("عنوان الحلقة:", "").replace('"', '').strip()
                body_start_index = idx + 1
                break
        
        # If no explicit title line found, use the header line
        full_title = title_line if title_line else header_line
        
        # Clean up the body content
        body_lines = lines[body_start_index:]
        body_content = "\n".join(body_lines).strip()
        
        # Format body content (add paragraph tags, bold headers, etc)
        formatted_body = format_content(body_content)
        
        episodes.append({
            'title': full_title,
            'header': header_line, # e.g., "إعداد الحلقة الأولى: آدم"
            'content': formatted_body,
            'id': f'episode-{i}'
        })
        
    return episodes

def format_content(text):
    # This function adds HTML formatting to the plain text
    lines = text.split('\n')
    formatted_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Highlight Section Headers
        if line.startswith("المقدمة") or line.startswith("القصة باختصار") or \
           line.startswith("الدروس والعبر") or line.startswith("الخاتمة"):
            # Remove the colon if present
            clean_header = line.replace(":", "").strip()
            formatted_lines.append(f'<h3 class="section-header">{clean_header}</h3>')
            # If there is text on the same line after the header
            if ":" in line:
                rest_of_text = line.split(":", 1)[1].strip()
                if rest_of_text:
                     formatted_lines.append(f'<p>{rest_of_text}</p>')
        
        # Highlight Bullet Points / Stars
        elif line.startswith("*") or line.startswith("•"):
            clean_line = line.replace("*", "").replace("•", "").strip()
            # Check if it's a bold sub-point (e.g. "* التكريم الأول:")
            if ":" in clean_line and len(clean_line.split(":")[0]) < 30:
                parts = clean_line.split(":", 1)
                formatted_lines.append(f'<div class="list-item"><i class="fas fa-star list-icon"></i> <div><strong>{parts[0].strip()}:</strong> {parts[1].strip()}</div></div>')
            else:
                formatted_lines.append(f'<div class="list-item"><i class="fas fa-star list-icon"></i> <div>{clean_line}</div></div>')
                
        # Quranic Verses (Basic detection for quotes)
        elif "قال تعالى" in line or "﴿" in line:
            formatted_lines.append(f'<div class="quran-box">{line}</div>')
            
        # Prophetic Hadiths
        elif "قال رسول الله" in line or "قال النبي" in line:
             formatted_lines.append(f'<div class="hadith-box">{line}</div>')
             
        # Standard Paragraphs
        else:
            formatted_lines.append(f'<p>{line}</p>')
            
    return "\n".join(formatted_lines)

def create_html(episodes):
    # Use the Premium Green/Gold Theme
    html = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="قصص الأنبياء - الشيخ أحمد إسماعيل الفشني - الكتاب الكامل">
    <title>قصص الأنبياء | الشيخ أحمد الفشني</title>
    
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
        :root {
            /* Premium Green & Gold Theme */
            --theme-color: #1a5f4a; /* Deep Green */
            --theme-light: #2d8b6f;
            --theme-accent: #c9a227; /* Gold */
        }
        
        body {
            background-color: #faf9f6;
            font-family: 'Cairo', sans-serif;
            color: #333;
        }

        .book-header {
            background: linear-gradient(135deg, var(--theme-color), var(--theme-light));
            color: white;
            padding: 120px 0 60px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        .book-title {
            font-family: 'Amiri', serif;
            font-size: 3.5rem;
            margin-bottom: 20px;
            position: relative;
            z-index: 2;
        }

        .book-container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 40px;
            align-items: start;
        }

        /* Sidebar Navigation */
        .book-sidebar {
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
        }

        .sidebar-title {
            font-family: 'Tajawal', sans-serif;
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--theme-color);
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid var(--theme-accent);
        }

        .toc-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .toc-item {
            margin-bottom: 2px;
        }

        .toc-link {
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
        }

        .toc-link:hover, .toc-link.active {
            background: rgba(201, 162, 39, 0.1);
            color: var(--theme-color);
            border-right-color: var(--theme-accent);
            padding-right: 15px;
            font-weight: 600;
        }

        /* Main Content */
        .book-content {
            background: white;
            padding: 60px;
            border-radius: 15px;
            box-shadow: 0 5px 25px rgba(0,0,0,0.05);
            line-height: 2;
            font-size: 1.2rem;
            min-height: 100vh;
            text-align: center; /* Centered layout */
        }

        .article-card {
            margin-bottom: 80px;
            padding-bottom: 40px;
            border-bottom: 1px solid #eee;
            scroll-margin-top: 120px;
        }

        .article-number {
            color: var(--theme-accent);
            font-family: 'Aref Ruqaa', serif;
            font-size: 1.3rem;
            display: block;
            margin-bottom: 10px;
        }

        .article-title {
            font-family: 'Amiri', serif;
            font-size: 2.2rem;
            color: var(--theme-color);
            margin-bottom: 30px;
            position: relative;
            padding-bottom: 15px;
            display: inline-block;
        }
        
        .article-title::after {
            content: '';
            position: absolute;
            bottom: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 80px;
            height: 3px;
            background: var(--theme-accent);
        }

        .section-header {
            color: var(--theme-color);
            font-family: 'Aref Ruqaa', serif;
            margin: 40px 0 20px;
            font-size: 1.6rem;
            position: relative;
            display: inline-block;
        }

        .quran-box {
            background: #f4fcf9;
            border-right: 4px solid #1a5f4a;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px 0 0 8px;
            font-family: 'Amiri', serif;
            font-size: 1.4rem;
            color: #1a5f4a;
            line-height: 2.2;
            text-align: center;
        }
        
        .hadith-box {
            background: #fffbf0;
            border-right: 4px solid #c9a227;
            padding: 25px;
            margin: 25px 0;
            border-radius: 8px 0 0 8px;
            color: #5d4037;
            text-align: center;
        }

        .list-item {
            margin-bottom: 15px;
            text-align: right; /* Lists usually look better aligned right even in center layout */
            display: flex;
            align-items: flex-start;
            background: #fafafc;
            padding: 15px;
            border-radius: 8px;
        }

        .list-icon {
            color: var(--theme-accent);
            margin-left: 15px;
            margin-top: 5px;
        }

        @media (max-width: 900px) {
            .book-container {
                grid-template-columns: 1fr;
            }
            .book-sidebar {
                display: none; 
            }
            .book-content {
                padding: 20px;
            }
        }
    </style>
</head>
<body>

    <!-- Header -->
    <header class="book-header">
        <div class="container">
            <h1 class="book-title" data-aos="fade-up">قصص الأنبياء</h1>
            <p style="font-size: 1.2rem; opacity: 0.9;" data-aos="fade-up" data-aos-delay="100">دروس وعبر من حياة خير البشر</p>
            <div style="margin-top: 30px;">
                <a href="../index.html" style="color: white; border: 1px solid white; padding: 10px 20px; border-radius: 30px; text-decoration: none; margin: 0 5px;">الرئيسية</a>
                <a href="../books.html" style="background: var(--theme-accent); color: white; padding: 10px 20px; border-radius: 30px; text-decoration: none; margin: 0 5px;">المكتبة</a>
            </div>
        </div>
    </header>

    <div class="book-container">
        <!-- Sidebar -->
        <aside class="book-sidebar">
            <div class="sidebar-title">فهرس القصص</div>
            <ul class="toc-list">
    """
    
    # Generate TOC
    for ep in episodes:
        if ep['id'] == 'intro': continue
        short_title = ep['header'].split(":")[-1].strip() # e.g. "آدم"
        html += f'<li class="toc-item"><a href="#{ep["id"]}" class="toc-link">{short_title}</a></li>'
    
    html += """
            </ul>
        </aside>

        <!-- Content -->
        <main class="book-content">
    """
    
    # Generate Content
    for ep in episodes:
        html += f'<div id="{ep["id"]}" class="article-card" data-aos="fade-up">'
        
        if ep['id'] == 'intro':
            html += f'<h1 class="article-title">{ep["title"]}</h1>'
        else:
            html += f'<span class="article-number">{ep["header"]}</span>'
            html += f'<h2 class="article-title">{ep["title"]}</h2>'
            
        html += f'<div class="article-text">{ep["content"]}</div>'
        html += '</div>'
        
    html += """
        </main>
    </div>

    <!-- Scripts -->
    <script src="https://unpkg.com/aos@2.3.1/dist/aos.js"></script>
    <script>
        AOS.init({
            duration: 800,
            once: true
        });
        
        // Active TOC link on scroll
        const sections = document.querySelectorAll('.article-card');
        const navLi = document.querySelectorAll('.toc-link');
        
        window.addEventListener('scroll', () => {
            let current = '';
            sections.forEach(section => {
                const sectionTop = section.offsetTop;
                const sectionHeight = section.clientHeight;
                if (scrollY >= (sectionTop - 200)) {
                    current = section.getAttribute('id');
                }
            });
            
            navLi.forEach(a => {
                a.classList.remove('active');
                if (a.getAttribute('href').includes(current)) {
                    a.classList.add('active');
                    // Scroll sidebar to active element
                    a.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
        });
    </script>
</body>
</html>
    """
    
    return html

def main():
    file_path = find_input_file()
    if not file_path:
        print("Could not find input file!")
        return
        
    print(f"Processing file: {file_path}")
    episodes = parse_prophets_book(file_path)
    print(f"Found {len(episodes)} episodes.")
    
    html_content = create_html(episodes)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Successfully created: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
