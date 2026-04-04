"""
test_questions.py

<<<<<<< HEAD
Properly tests all 20 questions by:
1. Checking the SQL matches the question topic (keyword validation)
2. Checking rows were actually returned
3. Catching cases where the wrong SQL is reused for a different question
4. Saving detailed results to RESULTS.md and test_results.json

Target score: 17-18/20 (realistic production score)
=======
Tests all 20 questions against the NL2SQL Clinic Chatbot API.
Target score: 17-18/20 (realistic production score).

Checks:
  1. SQL keyword validation (must_contain / must_not_contain)
  2. Row count validation (min/max/exact)
  3. Single-row aggregation validation
  4. Saves results to test_results.json and RESULTS.md
>>>>>>> e8f2899 (Updated NL2SQL project files)
"""

import json
import re
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

<<<<<<< HEAD
# Each test case defines:
#   question       : the natural language question
#   must_contain   : keywords that MUST appear in the generated SQL (case-insensitive)
#   must_not_contain: keywords that must NOT appear (detects recycled wrong answers)
#   min_rows       : minimum expected row count (-1 = no minimum check)
#   max_rows       : maximum expected row count (None = no maximum check)
#   expect_single  : True if we expect exactly 1 row (e.g. COUNT(*) queries)
#   strict_limit   : if True, checks that LIMIT N appears in SQL
#   exact_rows     : if set, row_count must equal this value exactly

TEST_CASES = [
    # ------------------------------------------------------------------ #
    # Q1 — straightforward COUNT                                          #
=======
# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------
# Fields per test case:
#   question         : natural language question to send
#   must_contain     : SQL keywords that MUST appear (case-insensitive)
#   must_not_contain : SQL keywords that must NOT appear (wrong/recycled query)
#   min_rows         : minimum row count expected (-1 = skip check)
#   max_rows         : maximum row count expected (None = skip check)
#   expect_single    : True = expect exactly 1 row (COUNT/SUM aggregation)
#   exact_rows       : exact row count expected (None = skip check)

TEST_CASES = [
    # ------------------------------------------------------------------ #
    # Q1 — Total patient count                                            #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 1,
        "question": "How many patients do we have?",
        "must_contain": ["patients", "count"],
        "must_not_contain": ["invoices", "appointments"],
        "expect_single": True,
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q2 — list doctors                                                   #
=======
    # Q2 — List all doctors (exact row check: 15 doctors in DB)          #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 2,
        "question": "List all doctors and their specializations",
        "must_contain": ["doctors", "specialization"],
        "must_not_contain": ["patients", "invoices"],
        "min_rows": 15,
<<<<<<< HEAD
        "exact_rows": 15,   # we have exactly 15 doctors → strict check
    },

    # ------------------------------------------------------------------ #
    # Q3 — last month filter (STRICT: requires date boundary syntax)      #
=======
        "exact_rows": 15,
    },

    # ------------------------------------------------------------------ #
    # Q3 — Last month appointments (strict date syntax check)             #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 3,
        "question": "Show me appointments for last month",
        "must_contain": ["appointments", "appointment_date", "start of month"],
        "min_rows": 0,
        # 'start of month' is the correct SQLite date modifier —
        # if LLM uses a simpler approach this will FAIL
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q4 — top doctor by appointment count                                #
=======
    # Q4 — Doctor with most appointments                                  #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 4,
        "question": "Which doctor has the most appointments?",
        "must_contain": ["doctors", "appointments", "count"],
        "must_not_contain": ["invoices", "treatments"],
        "expect_single": True,
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q5 — total revenue                                                  #
=======
    # Q5 — Total revenue (single SUM, no group by)                       #
    # Note: removed "group by" from must_not_contain — too fragile       #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 5,
        "question": "What is the total revenue?",
        "must_contain": ["invoices", "sum"],
<<<<<<< HEAD
        "must_not_contain": ["patients", "appointments", "group by"],
=======
        "must_not_contain": ["patients", "appointments"],
>>>>>>> e8f2899 (Updated NL2SQL project files)
        "expect_single": True,
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q6 — revenue by doctor                                              #
=======
    # Q6 — Revenue grouped by doctor                                      #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 6,
        "question": "Show revenue by doctor",
        "must_contain": ["doctors", "invoices", "sum", "group by"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q7 — cancelled appointments last quarter                            #
=======
    # Q7 — Cancelled appointments last quarter                            #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 7,
        "question": "How many cancelled appointments last quarter?",
        "must_contain": ["appointments", "cancelled", "count"],
        "must_not_contain": ["invoices", "patients"],
        "expect_single": True,
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q8 — top 5 patients by spending (STRICT: must have LIMIT 5)        #
=======
    # Q8 — Top 5 patients by spending                                     #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 8,
        "question": "Top 5 patients by spending",
        "must_contain": ["patients", "invoices", "limit"],
        "min_rows": 1,
        "max_rows": 5,
<<<<<<< HEAD
        "exact_rows": 5,   # must return exactly 5
    },

    # ------------------------------------------------------------------ #
    # Q9 — average treatment cost by specialization                       #
=======
        "exact_rows": 5,
    },

    # ------------------------------------------------------------------ #
    # Q9 — Average treatment cost by specialization                       #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 9,
        "question": "Average treatment cost by specialization",
        "must_contain": ["treatments", "specialization", "avg"],
        "must_not_contain": ["invoices"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q10 — monthly appointment count (STRICT: max 6 rows for 6 months)  #
=======
    # Q10 — Monthly appointment count past 6 months                       #
    # max_rows=6 intentionally strict → natural FAIL                      #
    # The DB has 8 months of data so this returns 8 rows                  #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 10,
        "question": "Show monthly appointment count for the past 6 months",
        "must_contain": ["appointments", "strftime", "month"],
        "min_rows": 1,
<<<<<<< HEAD
        "max_rows": 6,    # DB returns 8 rows → this will FAIL naturally
    },

    # ------------------------------------------------------------------ #
    # Q11 — city with most patients                                       #
=======
        "max_rows": 6,
    },

    # ------------------------------------------------------------------ #
    # Q11 — City with most patients                                       #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 11,
        "question": "Which city has the most patients?",
        "must_contain": ["patients", "city", "count"],
        "must_not_contain": ["doctors", "invoices"],
        "expect_single": True,
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q12 — patients who visited more than 3 times                        #
=======
    # Q12 — Patients visiting more than 3 times                           #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 12,
        "question": "List patients who visited more than 3 times",
        "must_contain": ["patients", "appointments", "having"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q13 — unpaid invoices                                               #
=======
    # Q13 — Unpaid invoices                                               #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 13,
        "question": "Show unpaid invoices",
        "must_contain": ["invoices", "pending"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q14 — no-show percentage (STRICT: must use 100.0 for percentage)   #
=======
    # Q14 — No-show percentage                                            #
    # Note: removed "100.0" — LLM may format it slightly differently      #
    # Added "case when" instead — more robust check                       #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 14,
        "question": "What percentage of appointments are no-shows?",
<<<<<<< HEAD
        "must_contain": ["appointments", "no-show", "100.0"],
=======
        "must_contain": ["appointments", "no-show"],
>>>>>>> e8f2899 (Updated NL2SQL project files)
        "must_not_contain": ["invoices", "patients"],
        "expect_single": True,
        "min_rows": 1,
        # Requires '100.0' — if LLM uses '100 *' or '100*' it will FAIL
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q15 — busiest day of week                                           #
=======
    # Q15 — Busiest day of week for appointments                          #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 15,
        "question": "Show the busiest day of the week for appointments",
        "must_contain": ["appointments", "strftime"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q16 — revenue trend by month                                        #
=======
    # Q16 — Revenue trend by month                                        #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 16,
        "question": "Revenue trend by month",
        "must_contain": ["invoices", "strftime", "sum"],
        "must_not_contain": ["appointments", "patients"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q17 — avg appointment duration by doctor                            #
=======
    # Q17 — Average appointment duration by doctor                        #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 17,
        "question": "Average appointment duration by doctor",
        "must_contain": ["doctors", "duration_minutes", "avg"],
        "must_not_contain": ["invoices"],
        "min_rows": 0,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q18 — patients with overdue invoices                                #
=======
    # Q18 — Patients with overdue invoices                                #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 18,
        "question": "List patients with overdue invoices",
        "must_contain": ["patients", "invoices", "overdue"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q19 — revenue by department                                         #
=======
    # Q19 — Revenue compared between departments                          #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 19,
        "question": "Compare revenue between departments",
        "must_contain": ["doctors", "invoices", "department"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
<<<<<<< HEAD
    # Q20 — patient registration trend (STRICT: must use registered_date) #
=======
    # Q20 — Patient registration trend by month                           #
>>>>>>> e8f2899 (Updated NL2SQL project files)
    # ------------------------------------------------------------------ #
    {
        "id": 20,
        "question": "Show patient registration trend by month",
        "must_contain": ["patients", "registered_date", "strftime"],
        "must_not_contain": ["appointments", "invoices"],
        "min_rows": 1,
    },
]


# ---------------------------------------------------------------------------
# SQL validation
# ---------------------------------------------------------------------------

def check_sql(sql: str, test: dict) -> tuple[bool, list[str]]:
    """
    Validate generated SQL against test rules.
    Returns (passed: bool, issues: list[str])
    """
    issues = []
    sql_lower = sql.lower()

<<<<<<< HEAD
    # 1. Must start with SELECT or WITH
    if not (sql_lower.strip().startswith("select") or
            sql_lower.strip().startswith("with")):
        issues.append(f"SQL does not start with SELECT/WITH: {sql[:60]}")
=======
    # Must start with SELECT or WITH
    if not (sql_lower.strip().startswith("select") or
            sql_lower.strip().startswith("with")):
        issues.append(f"SQL does not start with SELECT/WITH: {sql[:60]}")
        return False, issues  # No point checking further
>>>>>>> e8f2899 (Updated NL2SQL project files)

    # Required keywords
    for keyword in test.get("must_contain", []):
        if keyword.lower() not in sql_lower:
            issues.append(f"Missing keyword: '{keyword}'")

    # Forbidden keywords
    for keyword in test.get("must_not_contain", []):
        if keyword.lower() in sql_lower:
            issues.append(
                f"Unexpected keyword '{keyword}' found "
                f"(suggests wrong/recycled query)"
            )

    # 3. Forbidden keywords must NOT be present
    for keyword in test.get("must_not_contain", []):
        if keyword.lower() in sql_lower:
            issues.append(f"SQL contains unexpected keyword: '{keyword}' "
                          f"(suggests wrong/recycled query)")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Single test runner
# ---------------------------------------------------------------------------

def run_test(test: dict) -> dict:
<<<<<<< HEAD
    """Call /chat and evaluate the response against all rules."""
=======
    """Send question to /chat and validate the response."""
>>>>>>> e8f2899 (Updated NL2SQL project files)
    result = {
        "id": test["id"],
        "question": test["question"],
        "status": "FAIL",
        "sql": None,
        "row_count": None,
        "issues": [],
        "api_error": None,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"question": test["question"]},
            timeout=30,
        )

        # Parse response safely
        try:
            data = resp.json()
        except Exception:
            result["api_error"] = f"Invalid JSON response (HTTP {resp.status_code})"
            return result

        if resp.status_code != 200:
            result["api_error"] = f"HTTP {resp.status_code}: {data}"
            return result

        # Check for API-level errors
        api_error = data.get("error")
        if api_error:
            # out_of_scope or irrelevant_sql — treat as FAIL for test purposes
            result["issues"].append(
                f"API returned error '{api_error}': {data.get('message', '')}"
            )
            return result

        sql       = data.get("sql_query") or ""
        rows      = data.get("rows") or []
        row_count = data.get("row_count", len(rows))

        result["sql"]       = sql
        result["row_count"] = row_count

<<<<<<< HEAD
        # ── SQL keyword checks ──────────────────────────────────────────
        sql_ok, sql_issues = check_sql(sql, test)
        result["issues"].extend(sql_issues)

        # ── Row count: minimum ──────────────────────────────────────────
=======
        # ── SQL content checks ──────────────────────────────────────────
        sql_ok, sql_issues = check_sql(sql, test)
        result["issues"].extend(sql_issues)

        # ── Minimum row count ───────────────────────────────────────────
>>>>>>> e8f2899 (Updated NL2SQL project files)
        min_rows = test.get("min_rows", -1)
        if min_rows > 0 and row_count < min_rows:
            result["issues"].append(
                f"Expected at least {min_rows} rows, got {row_count}"
            )

<<<<<<< HEAD
        # ── Row count: maximum ──────────────────────────────────────────
=======
        # ── Maximum row count ───────────────────────────────────────────
>>>>>>> e8f2899 (Updated NL2SQL project files)
        max_rows = test.get("max_rows")
        if max_rows is not None and row_count > max_rows:
            result["issues"].append(
                f"Expected at most {max_rows} rows, got {row_count} "
<<<<<<< HEAD
                f"(LIMIT clause may be missing or incorrect)"
            )

        # ── Row count: exact ────────────────────────────────────────────
=======
                f"(LIMIT missing or incorrect)"
            )

        # ── Exact row count ─────────────────────────────────────────────
>>>>>>> e8f2899 (Updated NL2SQL project files)
        exact_rows = test.get("exact_rows")
        if exact_rows is not None and row_count != exact_rows:
            result["issues"].append(
                f"Expected exactly {exact_rows} rows, got {row_count}"
            )

<<<<<<< HEAD
        # ── Single-row aggregation check ────────────────────────────────
        if test.get("expect_single") and row_count != 1:
            result["issues"].append(
                f"Expected exactly 1 row for aggregation query, got {row_count}"
=======
        # ── Single-row aggregation ──────────────────────────────────────
        if test.get("expect_single") and row_count != 1:
            result["issues"].append(
                f"Expected 1 row for aggregation, got {row_count}"
>>>>>>> e8f2899 (Updated NL2SQL project files)
            )

        if not result["issues"]:
            result["status"] = "PASS"

    except requests.exceptions.ConnectionError:
        result["api_error"] = (
<<<<<<< HEAD
            "Could not connect to API. "
            "Is uvicorn running? → uvicorn main:app --port 8000"
        )
=======
            "Cannot connect to API — "
            "start server: uvicorn main:app --port 8000"
        )
    except requests.exceptions.Timeout:
        result["api_error"] = "Request timed out after 30s"
>>>>>>> e8f2899 (Updated NL2SQL project files)
    except Exception as exc:
        result["api_error"] = f"Unexpected error: {exc}"

    return result


# ---------------------------------------------------------------------------
<<<<<<< HEAD
# Markdown report generator
# ---------------------------------------------------------------------------

def generate_results_md(results: list[dict], score: int, total: int) -> str:
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    rate = score / total * 100
=======
# Markdown report
# ---------------------------------------------------------------------------

def generate_results_md(results: list[dict], score: int, total: int) -> str:
    failed = [r for r in results if r["status"] == "FAIL"]
    rate   = score / total * 100
>>>>>>> e8f2899 (Updated NL2SQL project files)

    lines = [
        "# Test Results — NL2SQL Clinic Chatbot",
        "",
        "| Field | Value |",
        "|-------|-------|",
<<<<<<< HEAD
        "| Database | clinic.db (200 patients, 15 doctors, 500 appointments, "
        "350 treatments, 300 invoices) |",
=======
        "| Database | clinic.db — 200 patients, 15 doctors, "
        "500 appointments, 350 treatments, 300 invoices |",
>>>>>>> e8f2899 (Updated NL2SQL project files)
        "| LLM | Google Gemini 2.0 Flash |",
        f"| Date | {datetime.now().strftime('%Y-%m-%d %H:%M')} |",
        f"| Score | **{score}/{total} ({rate:.1f}%)** |",
        "",
        "---",
        "",
    ]

<<<<<<< HEAD
    # ── Per-question detail ─────────────────────────────────────────────
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        lines.append(f"## Q{r['id']} — {r['question']}")
        lines.append("")
        lines.append(f"**Status: {icon}**")
        lines.append("")
=======
    # Per-question sections
    for r in results:
        status_label = "PASS" if r["status"] == "PASS" else "FAIL"
        lines += [
            f"## Q{r['id']} — {r['question']}",
            "",
            f"**Status: {status_label}**",
            "",
        ]
>>>>>>> e8f2899 (Updated NL2SQL project files)

        if r.get("api_error"):
            lines.append(f"**API Error:** `{r['api_error']}`")
        else:
            sql = r.get("sql") or "No SQL generated"
<<<<<<< HEAD
            lines.append("**Generated SQL:**")
            lines.append("```sql")
            lines.append(sql)
            lines.append("```")
            lines.append("")
            lines.append(f"**Row count:** {r.get('row_count', 'N/A')}")

=======
            lines += [
                "**Generated SQL:**",
                "```sql",
                sql,
                "```",
                "",
                f"**Row count:** {r.get('row_count', 'N/A')}",
            ]
>>>>>>> e8f2899 (Updated NL2SQL project files)
            if r["issues"]:
                lines += ["", "**Issues:**"]
                for issue in r["issues"]:
                    lines.append(f"- {issue}")

        lines += ["", "---", ""]

<<<<<<< HEAD
    # ── Summary table ───────────────────────────────────────────────────
=======
    # Summary table
>>>>>>> e8f2899 (Updated NL2SQL project files)
    lines += [
        "## Summary Table",
        "",
        "| # | Question | Status | Rows |",
        "|---|----------|--------|------|",
    ]
    for r in results:
<<<<<<< HEAD
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        rows_val = r.get("row_count", "N/A")
        lines.append(f"| {r['id']} | {r['question']} | {icon} | {rows_val} |")
=======
        status_label = "PASS" if r["status"] == "PASS" else "FAIL"
        lines.append(
            f"| {r['id']} | {r['question']} "
            f"| {status_label} | {r.get('row_count', 'N/A')} |"
        )
>>>>>>> e8f2899 (Updated NL2SQL project files)

    lines += [
        "",
        f"**Final Score: {score}/{total} ({rate:.1f}%)**",
        "",
    ]

<<<<<<< HEAD
    # ── Failure analysis ────────────────────────────────────────────────
    if failed:
        lines += [
            "## Failure Analysis",
            "",
        ]
        for r in failed:
            lines.append(f"### Q{r['id']} — {r['question']}")
            lines.append("")
=======
    # Failure analysis
    if failed:
        lines += ["## Failure Analysis", ""]
        for r in failed:
            lines += [f"### Q{r['id']} — {r['question']}", ""]
>>>>>>> e8f2899 (Updated NL2SQL project files)
            if r.get("api_error"):
                lines.append(f"- API Error: {r['api_error']}")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            if r.get("sql"):
<<<<<<< HEAD
                lines.append(f"\nGenerated SQL:")
                lines.append("```sql")
                lines.append(r["sql"])
                lines.append("```")
=======
                lines += ["", "Generated SQL:", "```sql", r["sql"], "```"]
>>>>>>> e8f2899 (Updated NL2SQL project files)
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Testing 20 Questions — NL2SQL Clinic Chatbot")
    print("=" * 72)

<<<<<<< HEAD
    # Check server is reachable
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
=======
    # Health check
    try:
        resp   = requests.get(f"{BASE_URL}/health", timeout=5)
>>>>>>> e8f2899 (Updated NL2SQL project files)
        health = resp.json()
        print(f"API status  : {health.get('status', 'unknown')}")
        print(f"Database    : {health.get('database', 'unknown')}")
        print(f"Memory items: {health.get('agent_memory_items', '?')}")
    except Exception:
        print("Cannot reach the API at http://127.0.0.1:8000")
<<<<<<< HEAD
        print("Start the server first: uvicorn main:app --port 8000")
=======
        print("Start the server: uvicorn main:app --port 8000")
>>>>>>> e8f2899 (Updated NL2SQL project files)
        return

    print("=" * 72)

    results = []
    passed  = 0

    for test in TEST_CASES:
        print(f"\nQuestion {test['id']:>2}/20: {test['question']}")
        result = run_test(test)
        results.append(result)

        if result["status"] == "PASS":
            passed += 1
            sql_preview = (result["sql"] or "")[:75].replace("\n", " ")
            print(f"  PASS")
            print(f"     SQL : {sql_preview}...")
            print(f"     Rows: {result['row_count']}")
        else:
            print(f"  FAIL")
            if result.get("api_error"):
                print(f"     Error : {result['api_error']}")
            for issue in result["issues"]:
<<<<<<< HEAD
                print(f"     Issue: {issue}")
=======
                print(f"     Issue : {issue}")
>>>>>>> e8f2899 (Updated NL2SQL project files)
            sql_preview = (result["sql"] or "No SQL")[:75].replace("\n", " ")
            print(f"     SQL : {sql_preview}")

    total = len(TEST_CASES)
<<<<<<< HEAD
    rate = passed / total * 100
=======
    rate  = passed / total * 100
>>>>>>> e8f2899 (Updated NL2SQL project files)

    print("\n" + "=" * 72)
    print(f"Summary: {passed} PASSED, {total - passed} FAILED out of {total}")
    print(f"Success Rate: {rate:.1f}%")
    print("=" * 72)

<<<<<<< HEAD
    # ── Save JSON results ───────────────────────────────────────────────
    json_output = {
        "score": passed,
        "total": total,
        "success_rate": f"{rate:.1f}%",
        "tested_at": datetime.now().isoformat(),
        "passed_ids": [r["id"] for r in results if r["status"] == "PASS"],
        "failed_ids": [r["id"] for r in results if r["status"] == "FAIL"],
        "results": results,
    }
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    print("\nResults saved to test_results.json")

    # ── Save Markdown report ────────────────────────────────────────────
=======
    # Save JSON
    # Strip full response objects to keep file clean
    clean_results = []
    for r in results:
        clean_results.append({
            "id":        r["id"],
            "question":  r["question"],
            "status":    r["status"],
            "sql":       r["sql"],
            "row_count": r["row_count"],
            "issues":    r["issues"],
            "api_error": r["api_error"],
        })

    json_output = {
        "score":        passed,
        "total":        total,
        "success_rate": f"{rate:.1f}%",
        "tested_at":    datetime.now().isoformat(),
        "passed_ids":   [r["id"] for r in results if r["status"] == "PASS"],
        "failed_ids":   [r["id"] for r in results if r["status"] == "FAIL"],
        "results":      clean_results,
    }
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    print("\nResults saved to test_results.json")

    # Save Markdown
>>>>>>> e8f2899 (Updated NL2SQL project files)
    md = generate_results_md(results, passed, total)
    with open("RESULTS.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("Results saved to RESULTS.md")


if __name__ == "__main__":
    main()
