from transformers import pipeline
from urllib.parse import urlparse

def bart_summarize_text(text, max_length=50, min_length=25):
    """
    Summarize input text using BART (facebook/bart-large-cnn).
    Returns the summary string.
    """
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]['summary_text']

def detect_domain_from_link(url_path):
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
    # Domenii posibile
    candidate_labels = ["economic", "politic", "social", "sport", "tehnologie", "educatie", "sanatate", "cultural", "international"]
    # Folosește zero-shot-classification
    classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    result = classifier(prompt, candidate_labels)
    # Returnează domeniul cu scorul cel mai mare
    return f"Domeniu: {result['labels'][0]} (scor: {result['scores'][0]:.2f})"

if __name__ == "__main__":
    # Example usage
    test_url = "/cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542"
    print("URL:", test_url)
    print("Domeniu detectat:")
    print(detect_domain_from_link(test_url))
