import unittest
from utils import get_html_content, strip_irrelevant_html_tags

class TestUtils(unittest.TestCase):
    def test_strip_irrelevant_html_tags_removes_script_and_style(self):
        html = '''<html><head><style>body{}</style></head><body><script>var x=1;</script><noscript>no js</noscript><iframe src="foo"></iframe><p>Hello World!</p></body></html>'''
        cleaned = strip_irrelevant_html_tags(html)
        self.assertNotIn('<script>', cleaned)
        self.assertNotIn('<style>', cleaned)
        self.assertNotIn('<noscript>', cleaned)
        self.assertNotIn('<iframe', cleaned)
        self.assertIn('Hello World!', cleaned)

    def test_strip_irrelevant_html_tags_removes_empty_tags(self):
        html = '<div></div><span id="x"></span><p>Text</p>'
        cleaned = strip_irrelevant_html_tags(html)
        self.assertNotIn('<div></div>', cleaned)
        self.assertIn('<span id="x"></span>', cleaned)
        self.assertIn('Text', cleaned)

    def test_strip_irrelevant_html_tags_strips_attributes_except_id_and_class(self):
        html = '<p id="pid" class="c" style="color:red" data-x="1">Text</p>'
        cleaned = strip_irrelevant_html_tags(html)
        self.assertIn('id="pid"', cleaned)
        self.assertIn('class="c"', cleaned)
        self.assertNotIn('style=', cleaned)
        self.assertNotIn('data-x=', cleaned)
        self.assertIn('Text', cleaned)

    def test_strip_irrelevant_html_tags_keeps_text(self):
        html = '<html><body><p>Text</p></body></html>'
        cleaned = strip_irrelevant_html_tags(html)
        self.assertIn('Text', cleaned)

    # Note: get_html_content requires network, so only a basic test
    def test_get_html_content_fetches_html(self):
        # This test will only work if example.com is reachable
        html = get_html_content('https://example.com')
        self.assertIn('<html', html)
        self.assertIn('Example Domain', html)

if __name__ == '__main__':
    unittest.main()
