import anthropic
import os

# Set your API key here (for security, consider using environment variables)
API_KEY = os.getenv("ANTHROPIC_API_KEY")

def main():
    client = anthropic.Anthropic(api_key=API_KEY)

    print("Welcome to the Claude Chatbot! Type 'exit' or 'quit' to end the conversation.")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye!")
            break

        try:
            message = client.messages.create(
                model="claude-3-sonnet-20240229",  # You can change to other models like claude-3-haiku
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": user_input}
                ]
            )
            response = message.content[0].text
            print(f"Claude: {response}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()