from transformers import pipeline
from urllib.parse import urlparse

def summarize_link_context(url_path):
    """
    Given a URL path (e.g. /cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542),
    extract keywords and use BART to generate a context summary.
    """
    # Remove leading/trailing slashes and split by hyphens
    parts = url_path.strip("/").split("-")
    # Remove numeric parts (e.g. IDs)
    words = [p for p in parts if not p.isdigit() and p]
    # Create a prompt sentence
    prompt = " ".join(words)
    prompt_text = f"This article is about: {prompt}"
    # Summarize with BART
    bart_summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = bart_summarizer(prompt_text, max_length=60, min_length=20, do_sample=False)
    return summary[0]['summary_text']

if __name__ == "__main__":
    # Example usage
    test_url = "/cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542"
    print("URL:", test_url)
    print("Context summary:")
    print(summarize_link_context(test_url))
