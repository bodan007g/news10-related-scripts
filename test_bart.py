from transformers import pipeline

# Initialize a summarization pipeline with a BART model
# Using 'facebook/bart-large-cnn' for summarization
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

text_to_summarize = """
The Orbiter Discovery, commanded by Kevin Kregel, lifted off from Kennedy Space Center at 1:38 p.m. EST on Thursday, marking the 100th space shuttle mission. The seven-member crew, including two Russians, will spend 11 days in orbit, primarily to install a new segment on the International Space Station. This mission is a significant milestone for NASA, demonstrating the longevity and reliability of the space shuttle program. The crew will also conduct several scientific experiments and perform two spacewalks.
"""

# Generate summary
summary = summarizer(text_to_summarize, max_length=50, min_length=25, do_sample=False)

print("Original Text:")
print(text_to_summarize)
print("\nGenerated Summary:")
print(summary[0]['summary_text'])
