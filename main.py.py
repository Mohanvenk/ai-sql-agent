from flask import Flask, request, jsonify, send_file
import sqlite3
import pandas as pd
import google.generativeai as genai
import os
import traceback
import matplotlib.pyplot as plt
import uuid

app = Flask(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("models/gemini-1.5-pro-latest")
DB_PATH = "ecommerce.db"

def get_sql_from_question(question):
    prompt = f"""
    You are an expert SQL assistant for an SQLite database with the following tables:
    - ad_sales(item_id, ad_spend, impressions, clicks)
    - total_sales(item_id, total_sales, total_units_ordered, date)
    - eligibility(item_id, is_eligible)

    Convert this user question into a valid SQL query.

    Question: {question}

    Only return the SQL query. No explanation.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("❌ Gemini API error:", e)
        lower_q = question.lower()
        if "total sales" in lower_q:
            return "SELECT date, SUM(total_sales) as sales FROM total_sales GROUP BY date ORDER BY date;"
        elif "roas" in lower_q:
            return "SELECT (SELECT SUM(total_sales) FROM total_sales) * 1.0 / (SELECT SUM(ad_spend) FROM ad_sales) AS roas;"
        elif "highest cpc" in lower_q:
            return "SELECT item_id, ad_spend * 1.0 / clicks AS cpc FROM ad_sales WHERE clicks > 0 ORDER BY cpc DESC LIMIT 5;"
        else:
            return "SELECT * FROM total_sales LIMIT 5;"

def generate_chart(df, question):
    chart_path = f"chart_{uuid.uuid4().hex}.png"
    try:
        lower_q = question.lower()
        plt.figure(figsize=(8, 4))

        if "total sales" in lower_q and "date" in df.columns:
            plt.plot(df["date"], df["sales"], marker="o")
            plt.title("Total Sales Over Time")
            plt.xlabel("Date")
            plt.ylabel("Sales")

        elif "roas" in lower_q and not df.empty:
            roas_value = df.iloc[0, 0]
            plt.bar(["RoAS"], [roas_value])
            plt.title("Return on Ad Spend (RoAS)")
            plt.ylabel("RoAS")

        elif "cpc" in lower_q and "item_id" in df.columns:
            plt.bar(df["item_id"].astype(str), df["cpc"])
            plt.title("Cost Per Click by Item")
            plt.xlabel("Item ID")
            plt.ylabel("CPC")

        else:
            return None

        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()
        return chart_path
    except Exception as e:
        print("⚠️ Chart error:", e)
        return None

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        questions = data.get("questions")
        if not questions:
            return jsonify({"error": "No questions provided."}), 400

        if isinstance(questions, str):
            questions = [questions]

        results = []
        for q in questions:
            print("📥 Received:", q)
            sql_query = get_sql_from_question(q)
            print("🧠 SQL:", sql_query)
            try:
                conn = sqlite3.connect(DB_PATH)
                df = pd.read_sql_query(sql_query, conn)
                conn.close()

                chart_path = generate_chart(df, q) if not df.empty else None

                results.append({
                    "question": q,
                    "sql_query": sql_query,
                    "answer": df.to_dict(orient="records"),
                    "chart": chart_path
                })
            except Exception as err:
                results.append({
                    "question": q,
                    "sql_query": sql_query,
                    "answer": [],
                    "error": str(err)
                })

        return jsonify({"results": results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/")
def home():
    return "✅ GenAI SQL Agent is running."

@app.route("/chart/<path:filename>")
def serve_chart(filename):
    return send_file(filename, mimetype='image/png')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
