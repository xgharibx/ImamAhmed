import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BooksSectionDisabledTests(unittest.TestCase):
    def test_books_landing_page_shows_soon_without_book_cards(self):
        page = (ROOT / "books.html").read_text(encoding="utf-8")

        self.assertIn("قريبا", page)
        self.assertIn('name="robots" content="noindex, nofollow, noarchive"', page)
        self.assertIn('rel="canonical" href="https://ahmedelfashny.com/books.html"', page)
        self.assertNotIn('class="book-card"', page)
        self.assertNotIn("اقرأ الكتاب", page)

    def test_direct_book_page_contains_no_book_text(self):
        page = (ROOT / "books" / "how-they-lived-how-we-live.html").read_text(encoding="utf-8")

        self.assertIn("قريبا", page)
        self.assertNotIn("خواطر على درب النجاح والتزكية", page)
        self.assertNotIn("تحميل PDF", page)

    def test_direct_book_placeholder_keeps_the_full_site_shell(self):
        page = (ROOT / "books" / "how-they-lived-how-we-live.html").read_text(encoding="utf-8")

        for href in ("../about.html", "../videos.html", "../contact.html"):
            self.assertIn(f'href="{href}"', page)
        self.assertIn('<footer id="footer" class="footer">', page)
        self.assertIn(".page-header-custom {", page)
        self.assertIn("background: var(--gradient-green);", page)
        self.assertIn("padding: 100px 0 60px;", page)

    def test_article_pages_in_books_folder_remain_available(self):
        page = (ROOT / "books" / "article-b4eee344173279b2.html").read_text(encoding="utf-8")

        self.assertIn('data-article-id="article-b4eee344173279b2"', page)
        self.assertIn("تحميل PDF", page)


if __name__ == "__main__":
    unittest.main()
