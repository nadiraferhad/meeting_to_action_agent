from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import re
from datetime import datetime, timedelta
import dateparser
from docx import Document
from PIL import Image
import pytesseract
import os

# ======== Configure Tesseract path (Windows example) ========
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ======== FastAPI app ========
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks = []

class QueryInput(BaseModel):
    question: str

# ======== Helper to read file content ========
async def read_file(file: UploadFile):
    content = await file.read()
    filename = file.filename.lower()

    # DOCX
    if filename.endswith(".docx"):
        with open("temp.docx", "wb") as f:
            f.write(content)
        doc = Document("temp.docx")
        text = "\n".join([p.text for p in doc.paragraphs])
        os.remove("temp.docx")
        return text

    # Images
    elif filename.endswith((".png", ".jpg", ".jpeg")):
        with open("temp_img", "wb") as f:
            f.write(content)
        image = Image.open("temp_img")
        text = pytesseract.image_to_string(image)
        os.remove("temp_img")
        return text

    # Plain text
    else:
        return content.decode('utf-8', errors='ignore')

# ======== Extract tasks endpoint ========
@app.post("/extract/")
async def extract_text(text: str = Form(None), file: UploadFile = File(None)):
    """
    Extract tasks from either raw text (text=...) or uploaded file (file=...).
    """
    global tasks

    # 1️⃣ Get text
    if file:
        text = await read_file(file)
    elif text:
        text = text
    else:
        return {"message": "❌ Please provide text or upload a file."}

    # 2️⃣ Regex for "to" or "will" + task + deadline
    pattern = r"(\b[A-Z][a-z]+\b)\s+(?:to|will)\s+(.*?)\s+by\s*(January|February|March|April|May|June|July|August|September|October|November|December)?\s*(\d{1,2})(?:th|st|nd|rd)?"
    matches = re.findall(pattern, text)

    tasks = []
    for match in matches:
        name = match[0]
        task_desc = match[1].strip()
        month = match[2] if match[2] else "November"
        day = match[3]
        date_str = f"{month} {day}, {datetime.now().year}"
        try:
            deadline = datetime.strptime(date_str, "%B %d, %Y").strftime("%Y-%m-%d")
        except ValueError:
            deadline = datetime.now().strftime("%Y-%m-%d")
        tasks.append({"name": name, "task": task_desc, "deadline": deadline})

    return {"message": "✅ Tasks extracted successfully!", "tasks": tasks}

# ======== Chat query endpoint ========
@app.post("/chat/")
async def chat_query(data: QueryInput):
    global tasks
    question = data.question.lower()

    if not tasks:
        return {"answer": "I don’t have any stored meeting info yet. Please extract the meeting text first."}

    # 1️⃣ List all tasks
    if "list" in question and "task" in question:
        answers = [f"{t['name']}: {t['task']} (Deadline: {t['deadline']})" for t in tasks]
        return {"answer": "\n".join(answers)}

    # 2️⃣ Task info
    for task in tasks:
        name = task["name"].lower()
        if name in question and "task" in question:
            return {"answer": f"{task['name']}'s task is: {task['task']}."}

    # 3️⃣ Deadline info
    for task in tasks:
        name = task["name"].lower()
        deadline = datetime.strptime(task["deadline"], "%Y-%m-%d")
        if name in question and "deadline" in question:
            return {"answer": f"{task['name']}'s deadline is on {deadline.strftime('%B %d, %Y')}."}

    # 4️⃣ Deadline tomorrow
    tomorrow = datetime.now() + timedelta(days=1)
    if "tomorrow" in question:
        matches = [t["name"] for t in tasks if datetime.strptime(t["deadline"], "%Y-%m-%d").date() == tomorrow.date()]
        if matches:
            return {"answer": f"The following people have deadlines tomorrow: {', '.join(matches)}."}

    # 5️⃣ Specific date
    parsed_date = dateparser.parse(question)
    if parsed_date:
        matches = []
        for task in tasks:
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%d")
            if deadline.date() == parsed_date.date():
                matches.append(task["name"])
        if matches:
            return {"answer": f"The people with deadlines on {parsed_date.strftime('%B %d, %Y')} are: {', '.join(matches)}."}

    # 6️⃣ Action keywords
    action_keywords = ["review", "send", "finish", "prepare", "update", "finalize"]
    for task in tasks:
        task_text = task["task"].lower()
        for word in action_keywords:
            if word in question and word in task_text:
                return {"answer": f"{task['name']} is responsible for: {task['task']}."}

    # 7️⃣ Generic deadlines
    if "who" in question and "deadline" in question:
        names = [t["name"] for t in tasks]
        return {"answer": f"The people with deadlines are: {', '.join(names)}."}

    # 8️⃣ Generic info
    for task in tasks:
        name = task["name"].lower()
        if name in question and ("info" in question or "information" in question or "about" in question):
            deadline = datetime.strptime(task["deadline"], "%Y-%m-%d")
            return {"answer": f"{task['name']}'s task is: {task['task']}. Deadline: {deadline.strftime('%B %d, %Y')}."}

    return {"answer": "Sorry, I couldn’t find an answer."}
