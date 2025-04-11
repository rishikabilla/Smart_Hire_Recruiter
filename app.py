from flask import Flask, render_template, request, redirect, url_for, session
import os
import fitz
import re
import requests
import spacy
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from nltk.tokenize import sent_tokenize
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Folders
UPLOAD_FOLDER = 'uploads'
CV_FOLDER = os.path.join(UPLOAD_FOLDER, 'CVs')
os.makedirs(CV_FOLDER, exist_ok=True)

# Load models
spacy_model = spacy.load("en_core_web_sm")
summarizer_model = pipeline("summarization", model="facebook/bart-large-cnn")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# SQLite setup
def init_db():
    conn = sqlite3.connect("shortlisted.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            score REAL,
            resume_file TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(name, email, score, file):
    conn = sqlite3.connect("shortlisted.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO candidates (name, email, score, resume_file) VALUES (?, ?, ?, ?)",
                   (name, email, score, file))
    conn.commit()
    conn.close()

# Resume parser
def parse_resume(cv_path):
    with fitz.open(cv_path) as doc:
        text = "".join(page.get_text() for page in doc)
    clean_text = re.sub(r"\s+", " ", text.strip())
    sentences = sent_tokenize(clean_text)
    resume_text = " ".join(sentences)

    prompt = f"""
You are a professional resume analyzer.

Your task is to:
1. Write a clear, professional paragraph summarizing the candidate’s qualifications, technical skills, relevant experience, certifications, and key projects.
2. Extract the candidate’s full name.
3. Extract the candidate’s email address.

Use the following output format exactly:
Summary:
<summary here>

Name: <candidate's name>
Email: <candidate's email>
Resume:
{resume_text}
"""

    response = requests.post("http://localhost:11434/api/generate", json={
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    })
    answer = response.json()["response"]
    summary_match = re.search(r"Summary:\s*(.*?)\n(?:Name:|$)", answer, re.DOTALL)
    name_match = re.search(r"Name:\s*(.*)", answer)
    email_match = re.search(r"Email:\s*([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", answer)

    cv_summary = summary_match.group(1).strip() if summary_match else "Summary not found"
    name = name_match.group(1).strip() if name_match else "Name not found"
    email = email_match.group(1).strip() if email_match else "Email not found"
    
    return cv_summary, email, name

# Email dispatcher
def send_email(name, email, job_role, recruiter_email, recruiter_pass):
    subject = f"Interview Invitation for {name.title()}"
    body = f"""Dear {name},

We are pleased to inform you that you have been shortlisted for the position of {job_role} at our organization. After reviewing your resume, we were impressed by your background, skill set, and the projects you've undertaken.

We believe that your experience and passion align well with our team's goals, and we would love to learn more about your potential contributions.

Should you have any questions in the meantime, feel free to contact us.

Looking forward to speaking with you soon.

Best regards,  
Recruitment Team
"""

    msg = MIMEMultipart()
    msg["From"] = recruiter_email
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(recruiter_email, recruiter_pass)
            server.sendmail(recruiter_email, email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send email to {email}: {e}")
        return False

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['job_title'] = request.form.get('job_title')
        session['recruiter_email'] = request.form.get('recruiter_email')
        session['recruiter_pass'] = request.form.get('recruiter_pass')
        session['skill_score'] = int(request.form.get('skill_score'))

        jd_file = request.files['jd_file']
        jd_path = os.path.join(UPLOAD_FOLDER, 'jd.txt')
        jd_file.save(jd_path)

        cv_files = request.files.getlist('cv_files')
        for file in cv_files:
            file.save(os.path.join(CV_FOLDER, file.filename))

        return redirect(url_for('shortlist'))

    return render_template('index.html')

@app.route('/shortlist')
def shortlist():
    job_title = session.get('job_title')
    recruiter_email = session.get('recruiter_email')
    recruiter_pass = session.get('recruiter_pass')
    skill_score = session.get('skill_score')

    with open(os.path.join(UPLOAD_FOLDER, 'jd.txt'), "r", encoding="utf-8") as f:
        jd_text = f.read()

    jd_summary = summarizer_model(jd_text, max_length=150, min_length=40, do_sample=False)[0]['summary_text']
    jd_embedding = embedding_model.encode([jd_summary])[0]

    shortlisted = []

    for file in os.listdir(CV_FOLDER):
        if file.endswith(".pdf"):
            path = os.path.join(CV_FOLDER, file)
            parsed_cv, email, name = parse_resume(path)
            if email == "Email not found":
                continue
            cv_embedding = embedding_model.encode([parsed_cv])[0]
            score = cosine_similarity([jd_embedding], [cv_embedding])[0][0]
            threshold = 0.7 if skill_score == 1 else 0.4
            if score >= threshold:
                if send_email(name, email, job_title, recruiter_email, recruiter_pass):
                    save_to_db(name, email, score, file)
                    shortlisted.append({"name": name, "email": email, "score": score, "resume": file})

    return render_template("results.html", candidates=shortlisted)

if __name__ == '__main__':
    init_db()
    app.run(host='127.0.0.1', port=5050)

