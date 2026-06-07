from tools.llm import get_llm

llm = get_llm()

response = llm.invoke(
    "Reply with only the word SUCCESS"
)

print(response.content)