from flask import Flask, render_template, redirect, url_for, request, abort,jsonify,session,flash,Response,send_file,make_response, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from openai import OpenAI
from dotenv import load_dotenv
import time

import os
load_dotenv()

# Ensure the API key is set via environment variable or directly
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("The OPENAI_API_KEY environment variable is not set.")
client = OpenAI(api_key=api_key)

app = Flask(__name__)
app.config['SECRET_KEY'] = "HACKAHOLICS1234"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if request.method == 'GET':
        return render_template('chat.html')


@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get('message')

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Retrieve your assistant
    assistant_id = "asst_8c23L0feKA9FJpQVjvvnKVQA"
    thread = client.beta.threads.create()

    # Send user message to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message,
    )

    # Run the assistant on that thread
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    # Wait for the run to complete
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            return jsonify({"error": f"Run {run_status.status}"}), 500
        time.sleep(1)

    # Get assistant's message
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_reply = messages.data[0].content[0].text.value

    return jsonify({"response": assistant_reply})
if __name__ == '__main__':
    app.run(debug=True)