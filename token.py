# Sample text
text = "The cats are running and playing in the garden. They were happier than before."

print("Original Text:\n", text)

# -------------------------------
# 1. Tokenization (Basic)
# -------------------------------
# Convert to lowercase and split by space
tokens = text.lower().replace('.', '').split()

print("\nTokenized Words:\n", tokens)

# -------------------------------
# 2. Stopwords Removal (Manual List)
# -------------------------------
stop_words = {
    "the", "is", "in", "and", "are", "was", "were",
    "they", "than", "before", "a", "an", "of", "to"
}

filtered_words = [word for word in tokens if word not in stop_words]

print("\nAfter Stopword Removal:\n", filtered_words)

# -------------------------------
# 3. Stemming (Simple Rule-Based)
# -------------------------------
def simple_stem(word):
    if word.endswith("ing"):
        return word[:-3]
    elif word.endswith("ed"):
        return word[:-2]
    elif word.endswith("s"):
        return word[:-1]
    return word

stemmed_words = [simple_stem(word) for word in filtered_words]

print("\nAfter Stemming:\n", stemmed_words)

# -------------------------------
# 4. Lemmatization (Very Basic)
# -------------------------------
# Using a small dictionary
lemma_dict = {
    "cats": "cat",
    "running": "run",
    "playing": "play",
    "happier": "happy",
    "better": "good",
    "worse": "bad"
}

lemmatized_words = [lemma_dict.get(word, word) for word in filtered_words]

print("\nAfter Lemmatization:\n", lemmatized_words)

# -------------------------------
# 5. Bag of Words (Manual)
# -------------------------------
# Create vocabulary
vocab = list(set(filtered_words))

# Create BoW vector
bow_vector = []
for word in vocab:
    bow_vector.append(filtered_words.count(word))

print("\nVocabulary:\n", vocab)
print("\nBag of Words Vector:\n", bow_vector)

