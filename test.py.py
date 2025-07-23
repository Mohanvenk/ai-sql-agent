import requests

def ask_question():
    print("🤖 Welcome to the GenAI SQL Agent!")
    print("Type your question below (or type 'exit' to quit):")

    url = "http://127.0.0.1:5000/ask"

    while True:
        question = input("🧑 You: ").strip()
        if not question:
            print("⚠️ Please type a valid question.")
            continue
        if question.lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break

        try:
            response = requests.post(url, json={"questions": [question]})
            data = response.json()

            if "results" not in data:
                print("❌ Error:", data.get("error", "Unknown error"))
                continue

            result = data["results"][0]

            print("\n✅ AI Response")
            print("🧠 SQL      :", result.get("sql_query", "N/A"))

            if result.get("error"):
                print("❌ Error    :", result["error"])
            elif result["answer"]:
                print("📊 Answer:")
                for row in result["answer"]:
                    print("   -", " | ".join(f"{k}: {v}" for k, v in row.items()))
            else:
                print("⚠️ No data returned.")

            if result.get("chart"):
                print(f"\n📈 Chart saved as: {result['chart']}")
                print("🖼️ You can view it manually by opening the image file.")

            print("-" * 50)

        except Exception as e:
            print("❌ Failed to connect or parse response:", e)

if __name__ == "__main__":
    ask_question()
