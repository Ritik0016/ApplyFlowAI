#!/usr/bin/env python3
"""
Job Application Automation Tool
Generates tailored emails via Gemini AI & sends with resume attached.

Usage:
    python send_application.py <receiver_email> <job_role> [options]

Examples:
    python send_application.py hr@company.com "MERN Stack Developer"
    python send_application.py recruiter@startup.io "AI Engineer" --company "Google"
    python send_application.py hr@firm.com "Backend Developer" --dry-run
"""

import json
import os
import sys
import smtplib
import argparse
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# -- Initialize -------------------------------------------------------
# Force UTF-8 output on Windows to avoid charmap encoding errors
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

# -- Constants --------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_PROFILE = SCRIPT_DIR / "profile.json"

# ANSI color codes (no dependency on colorama needed)
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
WHITE = "\033[97m"
BOLD = "\033[1m"
RESET = "\033[0m"


# -- Helpers ----------------------------------------------------------

def banner():
    """Print a styled startup banner."""
    print()
    print(f"{CYAN}{BOLD}  +----------------------------------------------+")
    print(f"  |   Job Application Automation Tool            |")
    print(f"  |   Powered by Gemini AI                       |")
    print(f"  +----------------------------------------------+{RESET}")
    print()


def info(msg):
    print(f"  {CYAN}[i]{RESET} {msg}")


def success(msg):
    print(f"  {GREEN}[+]{RESET} {msg}")


def warn(msg):
    print(f"  {YELLOW}[!]{RESET} {msg}")


def error(msg):
    print(f"  {RED}[x]{RESET} {msg}")
    sys.exit(1)


def divider(label=""):
    if label:
        print(f"\n  {CYAN}---- {label} {'-' * (40 - len(label))}{RESET}")
    else:
        print(f"  {CYAN}{'-' * 50}{RESET}")


# -- Core Functions ---------------------------------------------------

def load_profile(profile_path: Path) -> dict:
    """Load the saved profile data from JSON."""
    if not profile_path.exists():
        error(f"Profile not found: {profile_path}\n       Run the tool from the project directory or pass --profile <path>")

    with open(profile_path, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # Validate required fields
    required = ["name", "phone", "email", "linkedin", "skills", "experience_summary"]
    missing = [k for k in required if not profile.get(k)]
    if missing:
        error(f"Profile is missing required fields: {', '.join(missing)}\n       Please fill in profile.json before running.")

    return profile


# -- Resume auto-selection keywords -----------------------------------
# Map resume labels to the job-role keywords that should trigger them.
# Matching is case-insensitive; first match wins.
RESUME_KEYWORDS: dict[str, list[str]] = {
    "AI Engineer": [
        "ai", "artificial intelligence", "machine learning", "ml",
        "deep learning", "data science", "data engineer", "nlp",
        "computer vision", "llm", "generative ai", "langchain",
        "langgraph", "prompt engineer", "ai engineer", "ml engineer",
        "research", "neural",
    ],
    "Software Engineer": [
        "software", "backend", "frontend", "fullstack", "full stack",
        "full-stack", "mern", "mean", "web developer", "web dev",
        "sde", "swe", "software engineer", "software developer",
        "development", "developer", "node", "react", "javascript",
        "python developer", "java developer", "devops", "cloud",
        "intern", "associate",
    ],
}


def select_resume(profile: dict, job_role: str) -> Path:
    """
    Automatically select the best resume based on the job role.
    Falls back to interactive picker if no keyword matches.
    """
    resumes = profile.get("resumes", {})

    if not resumes:
        error("No resumes configured in profile.json.\n       Add a 'resumes' field with label -> path mappings.")

    # Resolve paths relative to the script directory
    resolved = {}
    for label, rel_path in resumes.items():
        full_path = (SCRIPT_DIR / rel_path).resolve()
        resolved[label] = full_path

    # Filter to only existing files
    valid = {label: p for label, p in resolved.items() if p.exists()}
    if not valid:
        error("None of the configured resume files exist:\n" +
              "\n".join(f"       - {label}: {p}" for label, p in resolved.items()))

    if len(valid) == 1:
        label, path = next(iter(valid.items()))
        info(f"Using resume: {WHITE}{BOLD}{label}{RESET} ({path.name})")
        return path

    # -- Auto-select based on job role keywords --
    role_lower = job_role.lower()
    for label, keywords in RESUME_KEYWORDS.items():
        if label not in valid:
            continue
        if any(kw in role_lower for kw in keywords):
            path = valid[label]
            success(f"Auto-selected resume: {WHITE}{BOLD}{label}{RESET} ({path.name})")
            info(f'Matched job role "{job_role}" -> {label}')
            return path

    # -- Fallback: interactive picker --
    warn(f'Could not auto-detect resume for "{job_role}". Please pick manually:')
    choices = list(valid.items())
    for i, (label, path) in enumerate(choices, 1):
        print(f"      {WHITE}{BOLD}{i}.{RESET} {label}  ->  {CYAN}{path.name}{RESET}")

    while True:
        try:
            raw = input(f"\n  {CYAN}?{RESET}  Pick a resume [{1}-{len(choices)}]: ").strip()
            pick = int(raw)
            if 1 <= pick <= len(choices):
                label, path = choices[pick - 1]
                success(f"Selected: {WHITE}{BOLD}{label}{RESET}")
                return path
        except (ValueError, EOFError):
            pass
        warn("Invalid choice. Try again.")


def generate_email(profile: dict, job_role: str, company: str | None = None) -> str:
    """
    Use Gemini AI to generate a tailored, professional email body.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        error("GEMINI_API_KEY not set in .env file.\n       Get one at: https://aistudio.google.com/apikey")

    client = genai.Client(api_key=api_key)

    company_line = f"Target Company: {company}" if company else "Target Company: Not specified (write generically)"

    prompt = textwrap.dedent(f"""\
        You are a top-tier career consultant. Write a concise, compelling cold email
        for a job application. The email must feel human -- professional yet warm, never
        robotic or generic.

        === APPLICANT PROFILE ===
        Name:           {profile['name']}
        Phone:          {profile['phone']}
        Email:          {profile['email']}
        LinkedIn:       {profile['linkedin']}
        GitHub/Portfolio: {profile.get('github', 'N/A')}

        Skills & Stack: {', '.join(profile['skills'])}

        Experience:     {profile['experience_summary']}

        Achievements:   {profile.get('achievements', 'N/A')}

        === TARGET ROLE ===
        Job Role:       {job_role}
        {company_line}

        === RULES ===
        1. Output ONLY the email body text. No subject line, no headers.
        2. Keep it 150-250 words. Respect the reader's time.
        3. Open with a strong hook -- not "I am writing to apply for..."
        4. Highlight the 2-3 most relevant skills/experiences for THIS specific role.
        5. Mention that a resume is attached for detailed background.
        6. End with a clear, confident call-to-action (e.g., happy to discuss on a call).
        7. Sign off with: Name, Phone, LinkedIn, and GitHub (if available).
        8. Plain text only -- no markdown, no bullet points, no special formatting.
        9. If no company is specified, do NOT use placeholder brackets like [Company Name].
           Write the email so it works without naming a specific company.
    """)

    info("Generating tailored email via Gemini AI...")
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=prompt,
    )
    return response.text.strip()


def send_email(
    receiver_email: str,
    subject: str,
    body: str,
    resume_path: Path,
    sender_name: str,
) -> None:
    """Send the email with resume attached via Gmail SMTP."""
    sender_email = os.getenv("SENDER_EMAIL")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or sender_email.startswith("your_"):
        error("SENDER_EMAIL not set in .env file.")
    if not app_password or app_password.startswith("your_"):
        error("GMAIL_APP_PASSWORD not set in .env file.\n       Generate one at: https://myaccount.google.com/apppasswords")

    # Build the email
    msg = MIMEMultipart()
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = receiver_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach resume
    with open(resume_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)

    # Clean up the attachment filename (remove double .pdf if present)
    attach_name = resume_path.name.replace(".pdf.pdf", ".pdf")
    part.add_header("Content-Disposition", f'attachment; filename="{attach_name}"')
    msg.attach(part)

    # Send
    info("Connecting to Gmail SMTP...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())


# -- Main -------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Job Application Automation -- AI-powered email sender",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python send_application.py hr@company.com "MERN Stack Developer"
              python send_application.py recruiter@startup.io "AI Engineer" --company "Google"
              python send_application.py hr@firm.com "Backend Dev" --dry-run
        """),
    )
    parser.add_argument("receiver_email", help="Recruiter / HR email address")
    parser.add_argument("job_role", help='Target job role (e.g., "MERN Stack Developer")')
    parser.add_argument("--company", "-c", default=None, help="Company name (optional, for a more tailored email)")
    parser.add_argument("--profile", "-p", default=str(DEFAULT_PROFILE), help="Path to profile.json")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Generate & preview email without sending")

    args = parser.parse_args()

    banner()

    # -- Step 1: Load profile --
    divider("Loading Profile")
    profile = load_profile(Path(args.profile))
    success(f"Profile loaded for {WHITE}{BOLD}{profile['name']}{RESET}")

    # -- Step 2: Select resume --
    divider("Resume")
    resume_path = select_resume(profile, args.job_role)

    # -- Step 3: Generate email via Gemini --
    divider("AI Email Generation")
    email_body = generate_email(profile, args.job_role, args.company)
    success("Email generated successfully!")

    subject = f"Application for {args.job_role} - {profile['name']}"

    # -- Step 4: Preview --
    divider("Email Preview")
    print(f"  {WHITE}To:      {RESET}{args.receiver_email}")
    print(f"  {WHITE}Subject: {RESET}{subject}")
    print(f"  {WHITE}Resume:  {RESET}{resume_path.name}")
    if args.company:
        print(f"  {WHITE}Company: {RESET}{args.company}")
    print()
    print(f"  {CYAN}{'-' * 50}{RESET}")
    for line in email_body.splitlines():
        print(f"  {line}")
    print(f"  {CYAN}{'-' * 50}{RESET}")

    # -- Step 5: Send or dry-run --
    if args.dry_run:
        print()
        warn("Dry run mode -- email was NOT sent.")
        info("Remove --dry-run to send for real.")
    else:
        divider("Sending Email")
        # Confirm before sending
        try:
            confirm = input(f"\n  {CYAN}?{RESET}  Send this email? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"

        if confirm in ("", "y", "yes"):
            send_email(args.receiver_email, subject, email_body, resume_path, profile["name"])
            print()
            success(f"{GREEN}{BOLD}Email sent successfully to {args.receiver_email}!{RESET}")
        else:
            warn("Aborted -- email was not sent.")

    print()


if __name__ == "__main__":
    main()
