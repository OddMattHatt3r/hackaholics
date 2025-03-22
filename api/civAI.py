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
    print("Received data:", data)  # Debugging print
    user_message = data.get('message')

    if not user_message:
        print("No message provided in the request.")  # Debugging print
        return jsonify({"error": "No message provided"}), 400

    # Retrieve your assistant
    assistant_id = "asst_8c23L0feKA9FJpQVjvvnKVQA"
    print("Using assistant ID:", assistant_id)  # Debugging print
    thread = client.beta.threads.create()
    print("Created thread with ID:", thread.id)  # Debugging print

    # Send user message to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_message,
    )
    print("Sent user message to thread.")  # Debugging print

    # Run the assistant on that thread
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )
    print("Started assistant run with ID:", run.id)  # Debugging print

    # Wait for the run to complete
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        print("Run status:", run_status.status)  # Debugging print
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            print(f"Run failed with status: {run_status.status}")  # Debugging print
            return jsonify({"error": f"Run {run_status.status}"}), 500
        time.sleep(1)

    # Get assistant's message
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    print("Retrieved messages:", messages)  # Debugging print
    assistant_reply = messages.data[0].content[0].text.value
    print("Assistant reply:", assistant_reply)  # Debugging print

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