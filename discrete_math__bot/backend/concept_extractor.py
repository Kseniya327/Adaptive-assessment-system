import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from .stop_phrases import STOP_PHRASES

# Загрузка модели spaCy (должна быть установлена)
try:
    nlp = spacy.load("ru_core_news_sm")
except OSError:
    raise RuntimeError("Модель ru_core_news_sm не найдена. Установите: python -m spacy download ru_core_news_sm")

# Разрешённые части речи (существительные, прилагательные, причастия)
ALLOWED_POS = {'NOUN', 'ADJ', 'PART'}

def is_valid_ngram(ngram):
    """Проверяет, состоит ли n-грамма из разрешённых частей речи."""
    doc = nlp(ngram)
    for token in doc:
        if token.pos_ not in ALLOWED_POS:
            return False
    return True

def is_stop_phrase(phrase):
    phrase_lower = phrase.lower()
    for stop in STOP_PHRASES:
        if stop in phrase_lower or phrase_lower in stop:
            return True
    return False

def cluster_concepts(concepts_list, threshold=0.65):
    """Группирует похожие концепты на основе символьных n-грамм."""
    if len(concepts_list) < 2:
        return {c: [c] for c in concepts_list}
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(2,4))
    X = vectorizer.fit_transform(concepts_list)
    cos_sim = (X * X.T).toarray()
    used = set()
    clusters = []
    for i in range(len(concepts_list)):
        if i in used:
            continue
        cluster = [concepts_list[i]]
        used.add(i)
        for j in range(i+1, len(concepts_list)):
            if j not in used and cos_sim[i,j] > threshold:
                cluster.append(concepts_list[j])
                used.add(j)
        clusters.append(cluster)
    result = {}
    for cl in clusters:
        canonical = min(cl, key=len)
        result[canonical] = cl
    return result

def filter_concepts(ngrams, min_len=5, forbid_digits=True):
    """Фильтрует n-граммы по длине, цифрам, стоп-фразам и частям речи."""
    filtered = []
    for ng, freq in ngrams:
        if len(ng) < min_len:
            continue
        if forbid_digits and any(c.isdigit() for c in ng):
            continue
        if is_stop_phrase(ng):
            continue
        if not is_valid_ngram(ng):
            continue
        filtered.append(ng)
    return filtered