import os
import fitz
import re
import requests
import spacy
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from nltk.tokenize import sent_tokenize
from transformers import pipeline
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

#Setting up the models
spacy_model = spacy.load("en_core_web_sm")
summarizer_model = pipeline("summarization", model="facebook/bart-large-cnn")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

#Required inputs
job_role=input("Enter Job Role:")
jd_file = "job_description.txt"
cv_folder = "CVs"
skill_score=int(input("Enter 1 if you need only highly skilled candidates and 2 for both moderate and highly skilled"))
recruiter_email = "rg.resumeparser@gmail.com"
recruiter_pass = "ldgz rslx uyoo ufml"

#Summarizer agent
def summarize_jd(jd_text):
    summary = summarizer_model(jd_text, max_length=150, min_length=40, do_sample=False)[0]['summary_text']
    return summary

#Resume parser agent
def parse_resume(cv_path):
    with fitz.open(cv_path) as doc:
        text = "".join(page.get_text() for page in doc)
    clean_text = re.sub(r"\s+", " ", text.strip())
    sentences = sent_tokenize(clean_text)
    resume_text = " ".join(sentences)
    prompt = f"""
You are a professional resume parser and evaluator. 
Given the resume below, perform the following tasks:
1. Write a professional and concise paragraph summarizing the candidate's qualifications, technical skills, work experience, certifications, and project experience. This summary should be suitable for comparing against a job description.
2. Extract the candidate's full name.
3. Extract the candidate's email address.
Return the output in the following format:
Summary: <one-paragraph summary here>
Name: <candidate name here>
Email: <candidate email here
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

#Email dispatcher agent
def send_email(name, email,job_role):
    subject = f"Interview Invitation for {name.title()}"
    body = f"""Dear {name},\n\nWe are pleased to inform you that you have been shortlisted for the position of {job_role} at our organization. After reviewing your resume, we were impressed by your background, skill set, and the projects you've undertaken.We believe that your experience and passion align well with our team's goals, and we would love to learn more about your potential contributions.\n\n
\nShould you have any questions in the meantime, feel free to contact us.\nLooking forward to speaking with you soon.\nBest regards,  
\nRecruitment Team
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

#the main logic (Shortlister agent)
if __name__ == "__main__":
    with open(jd_file, "r", encoding="utf-8") as f:
        jd_text = f.read()

    jd_summary = summarize_jd(jd_text)
    jd_embedding = embedding_model.encode([jd_summary])[0]
    shortlisted = []
    for file in os.listdir(cv_folder):
        if file.endswith(".pdf"):
            path = os.path.join(cv_folder, file)
            parsed_cv, email, name = parse_resume(path)
            print(f"Comparing {name} CV with summarized JD")
            if not email:
                print(f"Skipped {file} (no email found)")
                continue
            cv_embedding = embedding_model.encode([parsed_cv])[0]
            score = cosine_similarity([jd_embedding], [cv_embedding])[0][0]
            def compare(cmp_score):
                if score >= cmp_score:
                    print(f"Shortlisted: {name} | {email}")
                    if send_email(name, email,job_role):
                        shortlisted.append({"name": name, "email": email})
            if skill_score==1:
                compare(0.7)
            else:
                compare(0.4)
                

    print("\n📋 Final Shortlisted Candidates:")
    for i, cand in enumerate(shortlisted, 1):
        print(f"{i}. {cand['name']} | {cand['email']}")
