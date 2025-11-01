from openai import OpenAI

# Configuration
TOKENROUTER_URL = "http://api.qhchina.org/v1"  # TokenRouter endpoint
TEAM_TOKEN = "tmrjNjPGuASJxGJ6TNE8bVJuyqbUeaxvlXr5DkbnHhQ"  # Replace with your actual team token

# Create OpenAI client pointing to TokenRouter
client = OpenAI(
    api_key=TEAM_TOKEN,  # Your team token
    base_url=TOKENROUTER_URL  # TokenRouter endpoint
)

def simple_chat(message: str) -> str:
    """Simple chat example."""
    response = client.chat.completions.create(
        model="GPT-5-nano",
        messages=[
            {"role": "user", "content": message}
        ]
    )
    return response.choices[0].message.content

print("🤖 TokenRouter with OpenAI Client\n")

# Example 1: Simple question
print("Example 1: Simple question")
print("-" * 50)
question = "What is the capital of France?"
print(f"Q: {question}")
answer = simple_chat(question)
print(f"A: {answer}\n")

