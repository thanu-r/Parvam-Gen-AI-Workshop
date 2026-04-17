import re
from collections import Counter


def tokenize_text(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return [token for token in text.split() if token]


def sentence_split(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def build_keyword_scores(text: str, stopwords: set[str] | None = None) -> Counter:
    if stopwords is None:
        stopwords = {
            "the", "and", "is", "in", "it", "of", "to", "a", "an", "that", "this",
            "for", "on", "with", "as", "by", "at", "from", "or", "be", "are",
            "was", "were", "has", "have", "had", "not", "but", "if", "they", "their",
        }
    tokens = tokenize_text(text)
    keywords = [token for token in tokens if token not in stopwords]
    return Counter(keywords)


def score_sentence(sentence: str, keyword_scores: Counter) -> int:
    tokens = tokenize_text(sentence)
    return sum(keyword_scores[token] for token in tokens)


def summarize_text(text: str, stopwords: set[str] | None = None) -> str:
    sentences = sentence_split(text)
    if not sentences:
        return ""
    keyword_scores = build_keyword_scores(text, stopwords)
    scored = [(score_sentence(sentence, keyword_scores), idx, sentence) for idx, sentence in enumerate(sentences)]
    top_score, _, top_sentence = max(scored)
    return top_sentence


def main() -> None:
    example_text = (
        "Natural language processing makes it possible for computers to understand human language. "
        "A simple summarizer can use keyword frequency to identify the most important sentence. "
        "This method works best for short passages and extracts the sentence with the highest score. "
        "More advanced systems use neural networks and semantic understanding." 
    )

    summary = summarize_text(example_text)
    print("Original text:\n")
    print(example_text)
    print("\nMost important sentence:\n")
    print(summary)


if __name__ == "__main__":
    main()
