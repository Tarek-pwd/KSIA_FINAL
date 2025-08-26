import openai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initial system prompt
messages = [
    {
        "role": "system",
        "content": "You are a helpful assistant that takes a user query, which was executed by another model via a SQL statement. You should reason using both the query and the result of the executed SQL query."
    }
]

# Function to ask GPT-4o and stream its response
def reason_openai(user_query):
    messages = [
    {
        "role": "system",
        "content": " DO NOT MAKE ASSUMPTIONS FROM YOUR HEAD . todays date is  28th July 2025 You are a helpful assistant that takes a user query, which was executed by another model via a SQL statement. You should reason using both the query and the result of the executed SQL query."
    }
]

    # Add user message to the conversation
    messages.append({"role": "user", "content": user_query})
    # Call OpenAI with streaming enabled
    response = openai.chat.completions.create(
        model="gpt-4-turbo",
        messages=messages,
        stream=True  # This enables token-by-token streaming
    )

    print("Assistant:", end=" ", flush=True)

    # Stream the output token-by-token
    for chunk in response:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()  # newline


