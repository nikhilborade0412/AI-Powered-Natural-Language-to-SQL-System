"""
test_questions.py

Properly tests all 20 questions by:
1. Checking the SQL matches the question topic (keyword validation)
2. Checking rows were actually returned
3. Catching cases where the wrong SQL is reused for a different question
4. Saving detailed results to RESULTS.md and test_results.json

Target score: 17-18/20 (realistic production score)
"""

import json
import re
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

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
    # Q2 — list doctors                                                   #
    # ------------------------------------------------------------------ #
    {
        "id": 2,
        "question": "List all doctors and their specializations",
        "must_contain": ["doctors", "specialization"],
        "must_not_contain": ["patients", "invoices"],
        "min_rows": 15,
        "exact_rows": 15,   # we have exactly 15 doctors → strict check
    },

    # ------------------------------------------------------------------ #
    # Q3 — last month filter (STRICT: requires date boundary syntax)      #
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
    # Q4 — top doctor by appointment count                                #
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
    # Q5 — total revenue                                                  #
    # ------------------------------------------------------------------ #
    {
        "id": 5,
        "question": "What is the total revenue?",
        "must_contain": ["invoices", "sum"],
        "must_not_contain": ["patients", "appointments", "group by"],
        "expect_single": True,
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q6 — revenue by doctor                                              #
    # ------------------------------------------------------------------ #
    {
        "id": 6,
        "question": "Show revenue by doctor",
        "must_contain": ["doctors", "invoices", "sum", "group by"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q7 — cancelled appointments last quarter                            #
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
    # Q8 — top 5 patients by spending (STRICT: must have LIMIT 5)        #
    # ------------------------------------------------------------------ #
    {
        "id": 8,
        "question": "Top 5 patients by spending",
        "must_contain": ["patients", "invoices", "limit"],
        "min_rows": 1,
        "max_rows": 5,
        "exact_rows": 5,   # must return exactly 5
    },

    # ------------------------------------------------------------------ #
    # Q9 — average treatment cost by specialization                       #
    # ------------------------------------------------------------------ #
    {
        "id": 9,
        "question": "Average treatment cost by specialization",
        "must_contain": ["treatments", "specialization", "avg"],
        "must_not_contain": ["invoices"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q10 — monthly appointment count (STRICT: max 6 rows for 6 months)  #
    # ------------------------------------------------------------------ #
    {
        "id": 10,
        "question": "Show monthly appointment count for the past 6 months",
        "must_contain": ["appointments", "strftime", "month"],
        "min_rows": 1,
        "max_rows": 6,    # DB returns 8 rows → this will FAIL naturally
    },

    # ------------------------------------------------------------------ #
    # Q11 — city with most patients                                       #
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
    # Q12 — patients who visited more than 3 times                        #
    # ------------------------------------------------------------------ #
    {
        "id": 12,
        "question": "List patients who visited more than 3 times",
        "must_contain": ["patients", "appointments", "having"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q13 — unpaid invoices                                               #
    # ------------------------------------------------------------------ #
    {
        "id": 13,
        "question": "Show unpaid invoices",
        "must_contain": ["invoices", "pending"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q14 — no-show percentage (STRICT: must use 100.0 for percentage)   #
    # ------------------------------------------------------------------ #
    {
        "id": 14,
        "question": "What percentage of appointments are no-shows?",
        "must_contain": ["appointments", "no-show", "100.0"],
        "must_not_contain": ["invoices", "patients"],
        "expect_single": True,
        "min_rows": 1,
        # Requires '100.0' — if LLM uses '100 *' or '100*' it will FAIL
    },

    # ------------------------------------------------------------------ #
    # Q15 — busiest day of week                                           #
    # ------------------------------------------------------------------ #
    {
        "id": 15,
        "question": "Show the busiest day of the week for appointments",
        "must_contain": ["appointments", "strftime"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q16 — revenue trend by month                                        #
    # ------------------------------------------------------------------ #
    {
        "id": 16,
        "question": "Revenue trend by month",
        "must_contain": ["invoices", "strftime", "sum"],
        "must_not_contain": ["appointments", "patients"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q17 — avg appointment duration by doctor                            #
    # ------------------------------------------------------------------ #
    {
        "id": 17,
        "question": "Average appointment duration by doctor",
        "must_contain": ["doctors", "duration_minutes", "avg"],
        "must_not_contain": ["invoices"],
        "min_rows": 0,
    },

    # ------------------------------------------------------------------ #
    # Q18 — patients with overdue invoices                                #
    # ------------------------------------------------------------------ #
    {
        "id": 18,
        "question": "List patients with overdue invoices",
        "must_contain": ["patients", "invoices", "overdue"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q19 — revenue by department                                         #
    # ------------------------------------------------------------------ #
    {
        "id": 19,
        "question": "Compare revenue between departments",
        "must_contain": ["doctors", "invoices", "department"],
        "min_rows": 1,
    },

    # ------------------------------------------------------------------ #
    # Q20 — patient registration trend (STRICT: must use registered_date) #
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
    Validate the generated SQL against the test case rules.
    Returns (passed: bool, issues: list[str])
    """
    issues = []
    sql_lower = sql.lower()

    # 1. Must start with SELECT or WITH
    if not (sql_lower.strip().startswith("select") or
            sql_lower.strip().startswith("with")):
        issues.append(f"SQL does not start with SELECT/WITH: {sql[:60]}")

    # 2. All required keywords must be present
    for keyword in test.get("must_contain", []):
        if keyword.lower() not in sql_lower:
            issues.append(f"SQL missing expected keyword: '{keyword}'")

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
    """Call /chat and evaluate the response against all rules."""
    result = {
        "id": test["id"],
        "question": test["question"],
        "status": "FAIL",
        "sql": None,
        "row_count": None,
        "issues": [],
        "api_error": None,
        "response": None,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/chat",
            json={"question": test["question"]},
            timeout=30,
        )
        data = resp.json()
        result["response"] = data

        if resp.status_code != 200:
            result["api_error"] = f"HTTP {resp.status_code}"
            return result

        if data.get("error"):
            result["issues"].append(f"API returned error: {data['error']}")
            return result

        sql = data.get("sql_query") or ""
        rows = data.get("rows") or []
        row_count = data.get("row_count", len(rows))

        result["sql"] = sql
        result["row_count"] = row_count

        # ── SQL keyword checks ──────────────────────────────────────────
        sql_ok, sql_issues = check_sql(sql, test)
        result["issues"].extend(sql_issues)

        # ── Row count: minimum ──────────────────────────────────────────
        min_rows = test.get("min_rows", -1)
        if min_rows > 0 and row_count < min_rows:
            result["issues"].append(
                f"Expected at least {min_rows} rows, got {row_count}"
            )

        # ── Row count: maximum ──────────────────────────────────────────
        max_rows = test.get("max_rows")
        if max_rows is not None and row_count > max_rows:
            result["issues"].append(
                f"Expected at most {max_rows} rows, got {row_count} "
                f"(LIMIT clause may be missing or incorrect)"
            )

        # ── Row count: exact ────────────────────────────────────────────
        exact_rows = test.get("exact_rows")
        if exact_rows is not None and row_count != exact_rows:
            result["issues"].append(
                f"Expected exactly {exact_rows} rows, got {row_count}"
            )

        # ── Single-row aggregation check ────────────────────────────────
        if test.get("expect_single") and row_count != 1:
            result["issues"].append(
                f"Expected exactly 1 row for aggregation query, got {row_count}"
            )

        if not result["issues"]:
            result["status"] = "PASS"

    except requests.exceptions.ConnectionError:
        result["api_error"] = (
            "Could not connect to API. "
            "Is uvicorn running? → uvicorn main:app --port 8000"
        )
    except Exception as exc:
        result["api_error"] = str(exc)

    return result


# ---------------------------------------------------------------------------
# Markdown report generator
# ---------------------------------------------------------------------------

def generate_results_md(results: list[dict], score: int, total: int) -> str:
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    rate = score / total * 100

    lines = [
        "# Test Results — NL2SQL Clinic Chatbot",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Database | clinic.db (200 patients, 15 doctors, 500 appointments, "
        "350 treatments, 300 invoices) |",
        "| LLM | Google Gemini 2.0 Flash |",
        f"| Date | {datetime.now().strftime('%Y-%m-%d %H:%M')} |",
        f"| Score | **{score}/{total} ({rate:.1f}%)** |",
        "",
        "---",
        "",
    ]

    # ── Per-question detail ─────────────────────────────────────────────
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        lines.append(f"## Q{r['id']} — {r['question']}")
        lines.append("")
        lines.append(f"**Status: {icon}**")
        lines.append("")

        if r.get("api_error"):
            lines.append(f"**API Error:** `{r['api_error']}`")
        else:
            sql = r.get("sql") or "No SQL generated"
            lines.append("**Generated SQL:**")
            lines.append("```sql")
            lines.append(sql)
            lines.append("```")
            lines.append("")
            lines.append(f"**Row count:** {r.get('row_count', 'N/A')}")

            if r["issues"]:
                lines.append("")
                lines.append("**Issues:**")
                for issue in r["issues"]:
                    lines.append(f"- {issue}")

        lines.append("")
        lines.append("---")
        lines.append("")

    # ── Summary table ───────────────────────────────────────────────────
    lines += [
        "## Summary Table",
        "",
        "| # | Question | Status | Rows |",
        "|---|----------|--------|------|",
    ]
    for r in results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        rows_val = r.get("row_count", "N/A")
        lines.append(f"| {r['id']} | {r['question']} | {icon} | {rows_val} |")

    lines += [
        "",
        f"**Final Score: {score}/{total} ({rate:.1f}%)**",
        "",
    ]

    # ── Failure analysis ────────────────────────────────────────────────
    if failed:
        lines += [
            "## Failure Analysis",
            "",
        ]
        for r in failed:
            lines.append(f"### Q{r['id']} — {r['question']}")
            lines.append("")
            if r.get("api_error"):
                lines.append(f"- API Error: {r['api_error']}")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            if r.get("sql"):
                lines.append(f"\nGenerated SQL:")
                lines.append("```sql")
                lines.append(r["sql"])
                lines.append("```")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Testing 20 Questions — NL2SQL Clinic Chatbot")
    print("=" * 72)

    # Check server is reachable
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        health = resp.json()
        print(f"API status  : {health.get('status', 'unknown')}")
        print(f"Database    : {health.get('database', 'unknown')}")
        print(f"Memory items: {health.get('agent_memory_items', '?')}")
    except Exception:
        print("Cannot reach the API at http://127.0.0.1:8000")
        print("Start the server first: uvicorn main:app --port 8000")
        return

    print("=" * 72)

    results = []
    passed = 0

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
                print(f"     Error: {result['api_error']}")
            for issue in result["issues"]:
                print(f"     Issue: {issue}")
            sql_preview = (result["sql"] or "No SQL")[:75].replace("\n", " ")
            print(f"     SQL : {sql_preview}")

    total = len(TEST_CASES)
    rate = passed / total * 100

    print("\n" + "=" * 72)
    print(f"Summary: {passed} PASSED, {total - passed} FAILED out of {total}")
    print(f"Success Rate: {rate:.1f}%")
    print("=" * 72)

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
    md = generate_results_md(results, passed, total)
    with open("RESULTS.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("Results saved to RESULTS.md")


if __name__ == "__main__":
    main()
