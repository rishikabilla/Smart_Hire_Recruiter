# 🚀 Smart Hire – AI-Powered Recruitment Automation

**Smart Hire** is an intelligent, end-to-end recruitment automation tool that leverages Large Language Models (LLMs) to simplify hiring. It summarizes job descriptions, parses resumes, matches candidates using semantic similarity, and automatically sends interview emails — all through a Flask-based web interface.

---

## Key Features

-  Summarizes job descriptions using **BART**
-  Parses resumes using **Mistral** (via **Ollama**) + **PyMuPDF**
-  Shortlists candidates based on **semantic similarity**
-  Sends personalized interview invitations using **SMTP**
-  Stores shortlisted candidates in a **SQLite database**
-  User-friendly interface built with **Flask**

---

## 🛠️ Technologies Used

| Category        | Tools/Models                         |
|----------------|--------------------------------------|
| Frontend       | Flask (HTML, CSS)                    |
| Backend        | Python                               |
| AI Models      | BART (HuggingFace), Mistral (Ollama) |
| NLP Tools      | spaCy, SentenceTransformer           |
| PDF Parsing    | PyMuPDF                              |
| Email Sender   | smtplib                              |
| Database       | SQLite                               |

## How It Works

1. Recruiter uploads a **job description** and **candidate CVs**.
2. The JD is summarized using **BART**, and each CV is parsed using **Mistral**.
3. Semantic similarity between JD and CV is calculated using **SentenceTransformer**.
4. Candidates above the selected threshold are shortlisted.
5. **Emails are automatically sent** to shortlisted candidates using recruiter credentials.
6. Results are saved in **SQLite** and shown on a dashboard.

**UI**
![image](https://github.com/user-attachments/assets/a3730e9f-6a5f-47fa-8e11-0cc3e873eec0)
**After Shortlisting**
![image](https://github.com/user-attachments/assets/e2388741-e963-47a3-a15f-549fd5fc6c23)
**Mail Received by the shortlisted candidate**
![image](https://github.com/user-attachments/assets/76e78972-078a-4fc0-90b2-e1f02dca984b)



