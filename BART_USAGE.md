# BART LLM Usage in This Project

This project uses Facebook's BART language model via HuggingFace's `transformers` library for two main tasks, implemented in `bart_llm_utils.py`:

## 1. Zero-Shot Classification

We use the BART model (`facebook/bart-large-mnli`) to automatically detect the domain/context of an article title or URL. This is done using HuggingFace's `zero-shot-classification` pipeline, which allows the model to choose the most appropriate label from a predefined list (e.g., "economic", "politic", "social", etc.) even if the label does not appear explicitly in the text.

**Implemented in:** `bart_llm_utils.py` as `detect_domain_from_link`

**Example:**
```python
from bart_llm_utils import detect_domain_from_link
url_path = "/cati-bani-a-dat-romania-in-republica-moldova-de-ce-sunt-ascunse-cifrele-5334542"
print(detect_domain_from_link(url_path))
```

## 2. Summarization

The BART model (`facebook/bart-large-cnn`) is used for text summarization. The `bart_summarize_text` function in `bart_llm_utils.py` generates a short summary of the input text.

**Implemented in:** `bart_llm_utils.py` as `bart_summarize_text`

**Example:**
```python
from bart_llm_utils import bart_summarize_text
text = "The Orbiter Discovery, commanded by Kevin Kregel, lifted off ..."
print(bart_summarize_text(text, max_length=50, min_length=25))
```

## Why BART?
- BART is a powerful sequence-to-sequence model suitable for both classification and summarization tasks.
- Zero-shot classification allows us to infer context without explicit keywords.
- Summarization helps generate human-readable explanations from short or noisy input.

## Requirements
- `transformers` library (install with `pip install transformers`)
- Pretrained BART models (downloaded automatically by HuggingFace)

## Testing

Unit tests for both functions are provided in `test_bart_llm_utils.py`.

### How to run the tests

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```
2. Run the unit tests with:
   ```bash
   python3 test_bart_llm_utils.py
   ```

## See Also
- `bart_llm_utils.py` for the main implementation
- `test_bart_llm_utils.py` for unit tests
- HuggingFace documentation: https://huggingface.co/docs/transformers
