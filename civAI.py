from flask import Flask, render_template, redirect, url_for, request, abort,jsonify,session,flash,Response,send_file,make_response, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = "HACKAHOLICS1234"

@app.route('/')
def home():
    return render_template('/templates/index.html')

if __name__ == '__main__':
    app.run(debug=True)