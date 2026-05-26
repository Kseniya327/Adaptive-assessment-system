import re
import spacy
from sklearn.feature_extraction.text import CountVectorizer

nlp = spacy.load("ru_core_news_sm")

def clean_text(text: str) -> str:
    text = re.sub(r'\n\d+\n', '\n', text)
    text = re.sub(r'[^а-яёa-z\s\.\,\?\-\!\(\)]', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def lemmatize_sentence(text: str) -> str:
    doc = nlp(text.lower())
    lemmas = []
    for token in doc:
        if token.is_stop or token.is_punct or len(token.text) < 3:
            continue
        lemma = token.lemma_
        if len(lemma) > 2:
            lemmas.append(lemma)
    return ' '.join(lemmas)

def split_into_sentences(text: str):
    doc = nlp(text)
    sentences = []
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if len(sent_text) > 30:
            lemm_sent = lemmatize_sentence(sent_text)
            if lemm_sent:
                sentences.append(lemm_sent)
    return sentences

def extract_ngrams(sentences, n_range=(2,3), min_freq=2, max_features=200):
    if not sentences:
        return []
    vectorizer = CountVectorizer(ngram_range=n_range, lowercase=False, max_features=max_features)
    X = vectorizer.fit_transform(sentences)
    freqs = X.sum(axis=0).A1
    names = vectorizer.get_feature_names_out()
    return [(name, freq) for name, freq in zip(names, freqs) if freq >= min_freq]