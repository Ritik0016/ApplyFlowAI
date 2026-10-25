# Job Application Automation Tool

Automatically generate tailored, AI-powered job application emails and send them with your resume attached — all from the command line.

**Powered by Google Gemini AI + Gmail SMTP.**

## How It Works

1. **Save your profile once** — name, skills, experience in `profile.json`
2. **Run a command** with the recruiter's email and the target job role
3. **Gemini AI** writes a professional, tailored email body on the fly
4. **The tool sends it** via Gmail with your resume attached
5. **Smart resume picker** — auto-selects the right resume based on the job role

## Features

- **AI-generated emails** — every email is uniquely tailored to the job role
- **Auto resume selection** — maps job keywords to the right resume (e.g., "MERN Developer" → SWE resume, "AI Engineer" → AI resume)
- **Dry-run mode** — preview the email without sending
- **Company targeting** — optional `--company` flag for extra personalization
- **Send confirmation** — always asks before sending
- **Zero templates** — no copy-paste, every email is fresh

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Ritik0016/jobAutomation.git
cd jobAutomation
pip install -r requirements.txt
```

### 2. Set Up Your Profile

```bash
cp profile.example.json profile.json
```

Edit `profile.json` with your real details:

```json
{
    "name": "Your Name",
    "phone": "+91-XXXXXXXXXX",
    "email": "you@gmail.com",
    "linkedin": "https://linkedin.com/in/you",
    "github": "https://github.com/you",
    "skills": ["Python", "React", "Node.js"],
    "experience_summary": "Your experience in 1-2 lines...",
    "achievements": "Key projects and wins...",
    "resumes": {
        "AI Engineer": "resumes/Your_AI_Resume.pdf",
        "Software Engineer": "resumes/Your_SWE_Resume.pdf"
    }
}
```

### 3. Set Up Credentials

```bash
cp .env.example .env
```

Edit `.env` with your keys:

| Variable | Where to Get It |
|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) (free) |
| `SENDER_EMAIL` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | [Google App Passwords](https://myaccount.google.com/apppasswords) (requires 2FA) |

### 4. Add Your Resume(s)

```bash
mkdir resumes
# Copy your PDF resume(s) into the resumes/ folder
# Update the paths in profile.json to match
```

## Usage

### Basic

```bash
python send_application.py recruiter@company.com "MERN Stack Developer"
```

### With Company Name (more tailored)

```bash
python send_application.py hr@google.com "Software Engineer" --company "Google"
```

### Dry Run (preview without sending)

```bash
python send_application.py hr@company.com "Backend Developer" --dry-run
```

### All Options

```
positional arguments:
  receiver_email        Recruiter / HR email address
  job_role              Target job role (e.g., "MERN Stack Developer")

options:
  --company, -c         Company name (optional, for a more tailored email)
  --profile, -p         Path to profile.json (default: ./profile.json)
  --dry-run, -d         Generate & preview email without sending
```

## How Resume Auto-Selection Works

The tool automatically picks the right resume based on keywords in your job role:

| Job Role Contains | Resume Selected |
|---|---|
| ai, machine learning, ml, nlp, llm, data science, deep learning... | **AI Engineer** |
| software, backend, frontend, mern, sde, developer, fullstack... | **Software Engineer** |

If no keyword matches, it falls back to an interactive picker.

## Project Structure

```
jobAutomation/
├── .env.example            # Credentials template (commit this)
├── .env                    # Your real credentials (gitignored)
├── .gitignore
├── profile.example.json    # Profile template (commit this)
├── profile.json            # Your real profile (gitignored)
├── requirements.txt
├── send_application.py     # Main script
├── resumes/                # Your PDF resumes (gitignored)
│   ├── AI_Resume.pdf
│   └── SWE_Resume.pdf
└── README.md
```

## Tech Stack

- **Python 3.10+**
- **Google Gemini AI** (`google-genai`) — email generation
- **Gmail SMTP** — email dispatch
- **python-dotenv** — credential management

## Contributing

PRs welcome! Feel free to add support for more email providers, new resume-matching keywords, or additional AI models.

## License

MIT
