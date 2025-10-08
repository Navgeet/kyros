from openai import OpenAI

# Modify OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "EMPTY"
openai_api_base = "http://localhost:8000/v1"

client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

models = client.models.list()
model = models.data[0].id

messages = [{"role": "user", "content": "9.11 and 9.8, which is greater?"}]
# For granite, add: `extra_body={"chat_template_kwargs": {"thinking": True}}`
stream = client.chat.completions.create(model=model,
                                        messages=messages,
                                        stream=True)

print("client: Start streaming chat completions...")
printed_reasoning_content = False
printed_content = False

for chunk in stream:
    reasoning_content = None
    content = None
    # Check the content is reasoning_content or content
    if hasattr(chunk.choices[0].delta, "reasoning_content"):
        reasoning_content = chunk.choices[0].delta.reasoning_content
    elif hasattr(chunk.choices[0].delta, "content"):
        content = chunk.choices[0].delta.content

    if reasoning_content is not None:
        if not printed_reasoning_content:
            printed_reasoning_content = True
            print("reasoning_content:", end="", flush=True)
        print(reasoning_content, end="", flush=True)
    elif content is not None:
        if not printed_content:
            printed_content = True
            print("\ncontent:", end="", flush=True)
        # Extract and print the content
        print(content, end="", flush=True)
