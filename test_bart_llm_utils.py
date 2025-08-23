import unittest
from bart_llm_utils import bart_summarize_text, detect_domain_from_link

class TestBartLLMUtils(unittest.TestCase):
    def test_bart_summarize_text(self):
        text = (
            "The Orbiter Discovery, commanded by Kevin Kregel, lifted off from Kennedy Space Center at 1:38 p.m. EST on Thursday, marking the 100th space shuttle mission. "
            "The seven-member crew, including two Russians, will spend 11 days in orbit, primarily to install a new segment on the International Space Station. "
            "This mission is a significant milestone for NASA, demonstrating the longevity and reliability of the space shuttle program. "
            "The crew will also conduct several scientific experiments and perform two spacewalks."
        )
        summary = bart_summarize_text(text, max_length=50, min_length=25)
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)

    def test_detect_domain_from_link(self):
        url_path = "/cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542"
        domain = detect_domain_from_link(url_path)
        self.assertIsInstance(domain, str)
        self.assertIn("Domeniu:", domain)

if __name__ == "__main__":
    unittest.main()
