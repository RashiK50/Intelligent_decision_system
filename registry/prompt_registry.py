import json


with open(
    "prompts/prompts.json",
    "r",
    encoding="utf-8"
) as f:

    PROMPTS = json.load(f)


def get_prompt(prompt_name: str):

    prompt_data = PROMPTS[prompt_name]

    active_version = prompt_data["active_version"]

    return prompt_data["versions"][active_version]