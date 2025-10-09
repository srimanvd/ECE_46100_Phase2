import pytest
from run import classify_url

@pytest.mark.parametrize("u,cat", [
    ("https://huggingface.co/datasets/squad", "DATASET"),
    ("https://huggingface.co/bert-base-uncased", "MODEL"),
    ("https://github.com/pytorch/pytorch", "CODE"),
    ("https://gitlab.com/user/repo", "CODE"),
    ("", "CODE"),
    ("  https://HUGGINGFACE.CO/bert-base-uncased  ", "MODEL"),
])
def test_classify_url_more(u, cat):
    assert classify_url(u) == cat
