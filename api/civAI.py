from flask import Flask, render_template, redirect, url_for, request, abort,jsonify,session,flash,Response,send_file,make_response, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from openai import OpenAI
from dotenv import load_dotenv
import base64
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

@app.route('/assistant', methods=['GET', 'POST'])
def assistant():
    if request.method == 'GET':
        return render_template('assistant.html')




@app.route('/chatbot', methods=['POST'])
def chatbot():
    # Retrieve the text message from the form data.
    message = request.form.get('message')
    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Retrieve all uploaded files.
    uploaded_files = []
    for key in request.files:
        file_obj = request.files.get(key)
        if file_obj:
            uploaded_files.append(file_obj)

    # Separate files into document files and image files.
    # Adjust the supported extensions as needed.
    document_extensions = {'.pdf', '.txt', '.docx'}
    image_extensions = {'.jpg', '.jpeg', '.png'}

    document_files = []
    image_files = []

    for file_obj in uploaded_files:
        filename = file_obj.filename.lower()
        if any(filename.endswith(ext) for ext in image_extensions):
            image_files.append(file_obj)
        else:
            document_files.append(file_obj)

    thread_reply = None
    file_counts_dict = None

    # --- Process Document Files ---
    if document_files:
        # Create a vector store called "User Uploads".
        vector_store = client.vector_stores.create(name="User Uploads")

        # Prepare file tuples (filename, file stream) for the vector store upload.
        file_tuples = []
        for file_obj in document_files:
            file_obj.stream.seek(0)
            file_tuples.append((file_obj.filename, file_obj.stream))

        # Upload the files and wait for the file batch to complete.
        file_batch = client.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_tuples
        )
        print("File batch status:", file_batch.status)
        print("File counts:", file_batch.file_counts)

        # Prepare attachments by re-uploading only supported document files.
        attachments = []
        for file_obj in document_files:
            filename = file_obj.filename.lower()
            if not any(filename.endswith(ext) for ext in document_extensions):
                print(f"Skipping unsupported file type: {filename}")
                continue
            file_obj.stream.seek(0)
            message_file = client.files.create(
                file=(file_obj.filename, file_obj.stream),
                purpose="user_data"
            )
            attachments.append({
                "file_id": message_file.id,
                "tools": [{"type": "file_search"}, {"type": "code_interpreter"}]
            })

        if not attachments:
            return jsonify({"error": "No supported document file types uploaded for file search."}), 400

        # Create a thread with the user's message and attached document files.
        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": message,
                    "attachments": attachments
                }
            ]
        )
        print("Created thread with id:", thread.id)

        # Run the assistant for the document-based thread.
        assistant_id = "asst_8c23L0feKA9FJpQVjvvnKVQA"
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant_id
        )
        # Poll until the run completes.
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

        # Retrieve the assistant's reply from the thread.
        messages_obj = client.beta.threads.messages.list(thread_id=thread.id)
        thread_reply = messages_obj.data[0].content[0].text.value

        # Convert file_batch.file_counts to a dictionary for JSON serialization.
        file_counts_dict = vars(file_batch.file_counts)

    # --- Process Image Files ---
    image_reply = None
    if image_files:
        image_messages = []
        # Process each image file by encoding it as Base64.
        for file_obj in image_files:
            file_obj.stream.seek(0)
            base64_image = base64.b64encode(file_obj.stream.read()).decode("utf-8")
            # Determine MIME type based on file extension.
            ext = file_obj.filename.lower().split('.')[-1]
            if ext in ["jpg", "jpeg"]:
                mime = "image/jpeg"
            elif ext == "png":
                mime = "image/png"
            else:
                mime = "application/octet-stream"
            image_messages.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime};base64,{base64_image}"
                }
            })

        # Build the content payload with the text message and image messages.
        text_message = {"type": "text", "text": message}
        image_content = [text_message] + image_messages

        # Call the GPT-4O completions endpoint with the image content.
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": image_content
                }
            ],
        )
        image_reply = completion.choices[0].message.content

    # --- Return Response ---
    # If only document files were processed (i.e. no images), return the thread reply.
    if document_files and not image_files:
        return jsonify({
            "assistant_reply": thread_reply,
            "file_counts": file_counts_dict,
        })
    # If only images were processed.
    elif image_files and not document_files:
        return jsonify({
            "assistant_reply": image_reply,
        })
    # If both were provided, return both replies.
    else:
        return jsonify({
            "thread_reply": thread_reply,
            "image_reply": image_reply,
            "file_counts": file_counts_dict,
        })


def upload_and_poll_file_batch(vector_store_id, file_streams):
    """
    Upload files to the vector store and wait until the file batch upload is complete.
    This uses the SDK's built-in upload_and_poll method.
    """
    # This method both uploads and polls until the batch is complete.
    file_batch = client.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store_id,
        files=file_streams
    )
    return file_batch

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