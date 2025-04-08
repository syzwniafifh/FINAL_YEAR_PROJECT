import os
import io
import pandas as pd 
import base64
import pyautogui 
import matplotlib.pyplot  
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file 
from werkzeug.utils import secure_filename
from datetime import datetime
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure key

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

USER_CREDENTIALS = {"admin": "password123"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if username == 'admin' and password == 'password123':  # Ensure correct password
        session['logged_in'] = True
        return redirect(url_for('dashboard'))
    flash("Invalid username or password. Please try again.", "error")
    return redirect(url_for('login_page'))

@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if "logged_in" not in session:
        return redirect(url_for("login_page"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected!", "error")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected!", "error")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            
            # Save file to uploads folder
            file.save(filepath)

            # Store the uploaded file in session
            session["uploaded_file"] = filename  

            flash("File uploaded successfully!", "success")
            return redirect(url_for("dashboard"))

    return render_template("upload.html")


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login_page'))

    # Get the most recent file in the uploads folder
    uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if f.endswith('.csv')]
    
    if uploaded_files:
        latest_file = max(uploaded_files, key=lambda x: os.path.getctime(os.path.join(app.config['UPLOAD_FOLDER'], x)))
        log_file = os.path.join(app.config['UPLOAD_FOLDER'], latest_file)

        df = pd.read_csv(log_file)

        if 'Level' in df.columns:
            info_count = (df['Level'] == 'Information').sum()
            warning_count = (df['Level'] == 'Warning').sum()
            error_count = (df['Level'] == 'Error').sum()
        else:
            info_count = warning_count = error_count = 0
    else:
        info_count = warning_count = error_count = 0

    log_data = {
        "total_logs": info_count + warning_count + error_count,
        "info_count": info_count,
        "warning_count": warning_count,
        "error_count": error_count
    }

    return render_template('dashboard.html', log_data=log_data)



@app.route("/log_management", methods=["GET"])
def log_management():
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))

    uploaded_files = os.listdir(UPLOAD_FOLDER)  # Get all uploaded log files
    filtered_logs = []
    selected_file = request.args.get("file")
    log_level = request.args.get("log_level", "")  # Get selected log level

    if selected_file and selected_file in uploaded_files:
        filepath = os.path.join(UPLOAD_FOLDER, selected_file)
        try:
            df = pd.read_csv(filepath)
            if log_level:  # Filter by log level
                df = df[df["Level"] == log_level]
            filtered_logs = df.to_dict(orient="records")
        except Exception as e:
            flash(f"Error reading log file: {e}")

    return render_template("log_management.html", 
                           uploaded_files=uploaded_files, 
                           log_data=filtered_logs, 
                           selected_file=selected_file,
                           log_level=log_level)  # Pass log level

@app.route("/delete_log/<filename>")
def delete_log(filename):
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        flash("Log file deleted successfully!")

        if session.get("uploaded_file") == filename:
            session.pop("uploaded_file", None)

    return redirect(url_for("log_management"))
 
    

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login_page'))

if __name__ == "__main__":
    app.run(debug=True)
