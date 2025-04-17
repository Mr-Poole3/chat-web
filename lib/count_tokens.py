import os
from pathlib import Path

from transformers import GPT2TokenizerFast

_cur_dir = os.path.split(os.path.abspath(__file__))[0]
_root_dir = Path(os.path.split(_cur_dir)[0])

gpt_tokenizer = GPT2TokenizerFast.from_pretrained(str(_root_dir / "models" / "gpt2"))


def get_gpt_token_count(text: str):
    if not text:
        return 0
    tokens = gpt_tokenizer.tokenize(text)
    return len(tokens)


if __name__ == "__main__":
    test = "abcdefghijklmn"
    print(get_gpt_token_count(test))
