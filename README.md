# NL2SQL Clinic Chatbot

A Natural Language to SQL system built with **Vanna AI 2.0** and **FastAPI**.
Ask questions in plain English and get results from a clinic database — no SQL needed.

## LLM Provider

This project uses **Google Gemini** (`gemini-2.0-flash-exp`) via `GeminiLlmService`.  
Get a free API key at: https://aistudio.google.com/apikey

---

## Project Structure

```
project/
├── setup_database.py   # Creates clinic.db with schema + dummy data
├── vanna_setup.py      # Vanna 2.0 Agent initialization
├── seed_memory.py      # Seeds agent memory with 15 known Q&A pairs
├── main.py             # FastAPI application
├── requirements.txt    # All dependencies
├── README.md           # This file
├── RESULTS.md          # Test results for 20 questions
├── .env                # Environment variables (GOOGLE_API_KEY)
└── clinic.db           # Generated SQLite database
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "— AIML DeveloperCOGNINEST AI"
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv yenv
```

**Activate the virtual environment:**

- **Windows (PowerShell):**
  ```powershell
  yenv\Scripts\activate
  ```

- **Windows (Command Prompt):**
  ```cmd
  yenv\Scripts\activate.bat
  ```

- **macOS/Linux:**
  ```bash
  source yenv/bin/activate
  ```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your-gemini-api-key-here
```

You can get a free key at https://aistudio.google.com/apikey.

### 5. Create the database

```bash
python setup_database.py
```

This creates `clinic.db` and prints a summary:
```
Created 200 patients, 15 doctors, 500 appointments, 287 treatments, 300 invoices
Total billed: $1,585,963.63
Total collected: $1,074,018.34
Outstanding: $511,945.29
```

### 6. Seed agent memory

```bash
python seed_memory.py
```

This pre-loads 15 known correct Q&A pairs so the agent has a head start.

### 7. Start the API server

```bash
uvicorn main:app --port 8000
```

Or to run everything in one shot (as required):

```bash
pip install -r requirements.txt && python setup_database.py && python seed_memory.py && uvicorn main:app --port 8000
```

**Access the API at:** http://localhost:8000

**Interactive API docs:** http://localhost:8000/docs

---

## API Documentation

### POST /chat

Ask a question in plain English.

**Request:**
```json
{
  "question": "Show me the top 5 patients by total spending"
}
```

**Response:**
```json
{
  "message": "Here are the top 5 patients by total spending.",
  "sql_query": "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM patients p JOIN invoices i ON i.patient_id = p.id GROUP BY p.id ORDER BY total_spending DESC LIMIT 5",
  "columns": ["first_name", "last_name", "total_spending"],
  "rows": [
    ["Priya", "Sharma", 7240.5],
    ["Rahul", "Verma", 6890.0],
    ["John", "Doe", 6543.25],
    ["Jane", "Smith", 6102.75],
    ["Michael", "Johnson", 5890.0]
  ],
  "row_count": 5,
  "chart": null,
  "chart_type": null,
  "error": null
}
```

**Example using curl:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"How many patients do we have?\"}"
```

**Example using PowerShell:**
```powershell
Invoke-WebRequest -Uri http://localhost:8000/chat -Method POST -Headers @{"Content-Type"="application/json"} -Body '{"question": "How many patients do we have?"}'
```

---

### GET /health

Check if the API and database are working.

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "agent_memory_items": 15
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### GET /

Basic check that the server is running.

**Response:**
```json
{
  "message": "NL2SQL Clinic API is running. Use POST /chat to ask questions."
}
```

**Example:**
```bash
curl http://localhost:8000/
```

---

## Architecture Overview

```
User Question (plain English)
        |
        v
FastAPI /chat endpoint (main.py)
        |
        v
Input Validation (length, not empty)
        |
        v
Vanna 2.0 Agent (vanna_setup.py)
  - GeminiLlmService (Gemini 2.0 Flash Exp)
  - RunSqlTool → SqliteRunner → clinic.db
  - VisualizeDataTool (Plotly charts)
  - DemoAgentMemory (learns over time)
        |
        v
SQL Validation (SELECT only, no dangerous keywords)
        |
        v
Parse response → JSON returned to user
```

---

## Database Schema

The clinic database has 5 tables:

### **patients**
- `id` (Primary Key)
- `first_name`, `last_name`
- `date_of_birth`, `gender`
- `phone`, `email`
- `address`, `city`, `state`, `zip_code`

### **doctors**
- `id` (Primary Key)
- `first_name`, `last_name`
- `specialization`
- `phone`, `email`

### **appointments**
- `id` (Primary Key)
- `patient_id` (Foreign Key → patients)
- `doctor_id` (Foreign Key → doctors)
- `appointment_date`, `appointment_time`
- `status` (Scheduled, Completed, Cancelled, No-Show)
- `notes`

### **treatments**
- `id` (Primary Key)
- `appointment_id` (Foreign Key → appointments)
- `treatment_name`, `description`
- `cost`

### **invoices**
- `id` (Primary Key)
- `patient_id` (Foreign Key → patients)
- `appointment_id` (Foreign Key → appointments, nullable)
- `invoice_date`, `due_date`
- `total_amount`, `paid_amount`
- `status` (Paid, Pending, Overdue)

---

## Sample Questions You Can Ask

- "How many patients do we have?"
- "Show me the top 5 patients by total spending"
- "Which doctor has the most appointments?"
- "What's the total revenue from completed appointments?"
- "List all overdue invoices"
- "Show me patients from San Jose"
- "How many appointments were cancelled?"
- "What's the average treatment cost?"
- "Show me all cardiologists"
- "Which cities have the most patients?"

---

## Database Summary (After Setup)

```
=======================================================
DATABASE SUMMARY
=======================================================
  Patients       :   200 records
  Doctors        :    15 records
  Appointments   :   500 records
  Treatments     :   287 records
  Invoices       :   300 records

  APPOINTMENT STATUS:
    Completed   : 287
    Scheduled   : 105
    Cancelled   : 74
    No-Show     : 34

  INVOICE STATUS:
    Paid      : 180 invoices  $  939,846.55
    Pending   :  66 invoices  $  360,133.48
    Overdue   :  54 invoices  $  285,983.60

  TOP 5 CITIES BY PATIENT COUNT:
    San Jose            : 33 patients
    Los Angeles         : 30 patients
    San Diego           : 25 patients
    New York            : 21 patients
    Philadelphia        : 18 patients

  REVENUE SUMMARY:
    Total billed   : $1,585,963.63
    Total collected: $1,074,018.34
    Outstanding    : $  511,945.29
=======================================================
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'vanna'`
**Solution:** Make sure you've activated the virtual environment and run `pip install -r requirements.txt`

### Issue: Database not found
**Solution:** Run `python setup_database.py` to create `clinic.db`

### Issue: API returns "Agent not initialized"
**Solution:** Make sure `seed_memory.py` ran successfully before starting the server

### Issue: Google API key errors
**Solution:** 
1. Check that `.env` file exists and contains `GOOGLE_API_KEY=...`
2. Verify the API key is valid at https://aistudio.google.com/apikey
3. Ensure you have quota remaining on your Gemini API account

---
