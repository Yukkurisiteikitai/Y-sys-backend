# test_sample.py
from lm_studio_rag.classifier import ContentClassifier
from lm_studio_rag.storage import RAGStorage

def test_classifier():
    clf = ContentClassifier()
    # no training: heuristics only
    print(clf.classify("昨日、映画を見に行きました"))   # -> experience
    print(clf.classify("私は内向的だ"))               # -> personality

def test_storage():
    s = RAGStorage()
    s.save_personality_data("私は猫が好きです", {"note":"test"})
    s.save_experience_data("昨日は寿司屋に行った", {"note":"test"})
    res = s.search_similar("猫 好き", category="personality")
    print("search:", res)

if __name__ == "__main__":
    test_classifier()
    test_storage()
