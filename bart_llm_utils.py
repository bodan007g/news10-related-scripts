try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

from urllib.parse import urlparse

def bart_summarize_text(text, max_length=50, min_length=25):
    """
    Summarize input text using BART (facebook/bart-large-cnn).
    Returns the summary string. Falls back to truncated text if BART is unavailable.
    """
    if not TRANSFORMERS_AVAILABLE:
        # Fallback: return first few sentences as summary
        sentences = text.split('.')[:3]
        return '. '.join(sentences).strip() + '.' if sentences else text[:200]
    
    try:
        summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
        summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        print(f"BART summarization failed: {e}")
        # Fallback: return first few sentences as summary
        sentences = text.split('.')[:3]
        return '. '.join(sentences).strip() + '.' if sentences else text[:200]

def detect_domain_from_link(url_path):
    """
    Given a URL path (e.g. /cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542),
    extract keywords and use BART to generate a context summary.
    Falls back to keyword-based classification if BART is unavailable.
    """
    # Remove leading/trailing slashes and split by hyphens
    parts = url_path.strip("/").split("-")
    # Remove numeric parts (e.g. IDs)
    words = [p for p in parts if not p.isdigit() and p]
    # Create a prompt sentence
    prompt = " ".join(words).lower()
    
    # Fallback keyword-based classification if BART is unavailable
    if not TRANSFORMERS_AVAILABLE:
        # Simple keyword-based domain detection
        domain_keywords = {
            'economic': ['bani', 'economie', 'buget', 'taxa', 'pib', 'afaceri', 'business', 'profit', 'investitie'],
            'politic': ['guvern', 'parlament', 'alegeri', 'presedinte', 'ministru', 'politica', 'partidul'],
            'social': ['social', 'comunitate', 'societate', 'familie', 'oameni', 'populatie'],
            'sport': ['fotbal', 'sport', 'campionat', 'echipa', 'jucator', 'meci'],
            'tehnologie': ['tehnologie', 'internet', 'calculator', 'software', 'app', 'digital'],
            'sanatate': ['sanatate', 'medical', 'doctor', 'spital', 'tratament', 'medicina'],
            'educatie': ['educatie', 'scolar', 'universitate', 'elev', 'student', 'invatamant'],
            'cultural': ['cultura', 'arte', 'muzica', 'film', 'teatru', 'literatura'],
            'international': ['international', 'mondial', 'europa', 'sua', 'rusia', 'china']
        }
        
        for domain, keywords in domain_keywords.items():
            if any(keyword in prompt for keyword in keywords):
                return f"Domeniu: {domain} (scor: 0.75)"
        
        return "Domeniu: general (scor: 0.50)"
    
    try:
        # Domenii posibile
        candidate_labels = ["economic", "politic", "social", "sport", "tehnologie", "educatie", "sanatate", "cultural", "international"]
        # Folosește zero-shot-classification
        classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        result = classifier(prompt, candidate_labels)
        # Returnează domeniul cu scorul cel mai mare
        return f"Domeniu: {result['labels'][0]} (scor: {result['scores'][0]:.2f})"
    except Exception as e:
        print(f"BART classification failed: {e}")
        return "Domeniu: general (scor: 0.50)"

if __name__ == "__main__":
    # Example usage
    test_url = "/cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542"
    print("URL:", test_url)
    print("Domeniu detectat:")
    print(detect_domain_from_link(test_url))
