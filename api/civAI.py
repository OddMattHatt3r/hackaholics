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

    assistant_id = "asst_8c23L0feKA9FJpQVjvvnKVQA"

    # Step 1: Retrieve or create a thread ID
    if 'thread_id' not in session:
        thread = client.beta.threads.create()
        session['thread_id'] = thread.id
        print("Created new thread:", thread.id)
    else:
        thread_id = session['thread_id']
        print("Using existing thread:", thread_id)
        thread = client.beta.threads.retrieve(thread_id)

    # Step 2: Send user message to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message,
    )

    # Step 3: Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    # Step 4: Wait for the assistant to finish
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

    # Step 5: Get the latest assistant message
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_reply = messages.data[0].content[0].text.value

    return jsonify({"response": assistant_reply})

@app.route('/view-file/<path:relpath>')
def view_file(relpath):
    # Get the full absolute path from relative path
    file_path = os.path.abspath(relpath)

    # Security check: ensure the file path is within current working directory
    root_dir = os.getcwd()
    if not file_path.startswith(root_dir):
        abort(403, description="Forbidden: Invalid file path.")

    # Check if the file exists and is a file
    if not os.path.isfile(file_path):
        abort(404, description=f"File not found: {file_path}")

    # Serve the file inline
    try:
        return send_file(file_path, as_attachment=False)
    except Exception as e:
        print(f"Error: {e}")
        abort(500, description="Internal server error.")

    return jsonify({"response": assistant_reply})


if __name__ == '__main__':
    app.run(debug=True)