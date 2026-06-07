from pathlib import Path

PROMPTS_DIR = Path("prompts")


def load_prompt(prompt_name: str) -> str:
    prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"

    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()