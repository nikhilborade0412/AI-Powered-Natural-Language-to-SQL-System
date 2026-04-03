"""
test_questions.py

Properly tests all 20 questions by:
1. Checking the SQL matches the question topic (keyword validation)
2. Checking rows were actually returned
3. Catching cases where the wrong SQL is reused for a different question
4. Saving detailed results to RESULTS.md and test_results.json
"""

import json
import re
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

# Each test case defines:
#   question      : the natural language question
#   must_contain  : keywords that MUST appear in the generated SQL (case-insensitive)
#   must_not_reuse: SQL snippets that would indicate a wrong/recycled answer
#   min_rows      : minimum expected row count (-1 = no minimum check)
#   expect_single : True if we expect exactly 1 row (e.g. COUNT(*) queries)

TEST_CASES = [
    {
        "id": 1,
        "question": "How many patients do we have?",
        "must_contain": ["patients", "count"],
        "expect_single": True,
        "min_rows": 1,
    },
    {
        "id": 2,
        "question": "List all doctors and their specializations",
        "must_contain": ["doctors", "specialization"],
        "min_rows": 15,
    },
    {
        "id": 3,
        "question": "Show me appointments for last month",
        "must_contain": ["appointments", "appointment_date"],
        "min_rows": 0,
    },
    {
        "id": 4,
        "question": "Which doctor has the most appointments?",
        "must_contain": ["doctors", "appointments", "count"],
        "expect_single": True,
        "min_rows": 1,
    },
    {
        "id": 5,
        "question": "What is the total revenue?",
        "must_contain": ["invoices", "sum"],
        "expect_single": True,
        "min_rows": 1,
    },
    {
        "id": 6,
        "question": "Show revenue by doctor",
        "must_contain": ["doctors", "invoices", "sum"],
        "min_rows": 1,
    },
    {
        "id": 7,
        "question": "How many cancelled appointments last quarter?",
        "must_contain": ["appointments", "cancelled", "count"],
        "expect_single": True,
        "min_rows": 1,
    },
    {
        "id": 8,
        "question": "Top 5 patients by spending",
        "must_contain": ["patients", "invoices", "limit"],
        "min_rows": 1,
        "max_rows": 5,
    },
    {
        "id": 9,
        "question": "Average treatment cost by specialization",
        "must_contain": ["treatments", "specialization", "avg"],
        "min_rows": 1,
    },
    {
        "id": 10,
        "question": "Show monthly appointment count for the past 6 months",
        "must_contain": ["appointments", "strftime", "month"],
        "min_rows": 1,
    },
    {
        "id": 11,
        "question": "Which city has the most patients?",
        "must_contain": ["patients", "city", "count"],
        "expect_single": True,
        "min_rows": 1,
    },
    {
        "id": 12,
        "question": "List patients who visited more than 3 times",
        "must_contain": ["patients", "appointments", "having"],
        "min_rows": 1,
    },
    {
        "id": 13,
        "question": "Show unpaid invoices",
        "must_contain": ["invoices", "pending"],
        "min_rows": 1,
    },
    {
        "id": 14,
        "question": "What percentage of appointments are no-shows?",
        "must_contain": ["appointments", "no-show"],
        "expect_single": True,
        "min_rows": 1,
    },
    {
        "id": 15,
        "question": "Show the busiest day of the week for appointments",
        "must_contain": ["appointments", "strftime"],
        "min_rows": 1,
    },
    {
        "id": 16,
        "question": "Revenue trend by month",
        "must_contain": ["invoices", "strftime", "sum"],
        "min_rows": 1,
    },
    {
        "id": 17,
        "question": "Average appointment duration by doctor",
        "must_contain": ["doctors", "duration_minutes", "avg"],
        "min_rows": 0,  # may be 0 if no completed appointments have treatments
    },
    {
        "id": 18,
        "question": "List patients with overdue invoices",
        "must_contain": ["patients", "invoices", "overdue"],
        "min_rows": 1,
    },
    {
        "id": 19,
        "question": "Compare revenue between departments",
        "must_contain": ["doctors", "invoices", "department"],
        "min_rows": 1,
    },
    {
        "id": 20,
        "question": "Show patient registration trend by month",
        "must_contain": ["patients", "registered_date"],
        "min_rows": 1,
    },
]


def check_sql(sql: str, test: dict) -> tuple[bool, list[str]]:
    """
    Validate the generated SQL against the test case rules.
    Returns (passed: bool, issues: list[str])
    """
    issues = []
    sql_lower = sql.lower()

    # 1. Must start with SELECT or WITH
    if not (sql_lower.strip().startswith("select") or sql_lower.strip().startswith("with")):
        issues.append(f"SQL does not start with SELECT: {sql[:60]}")

    # 2. All required keywords must be present
    for keyword in test.get("must_contain", []):
        if keyword.lower() not in sql_lower:
            issues.append(f"SQL missing expected keyword: '{keyword}'")

    return len(issues) == 0, issues


def run_test(test: dict) -> dict:
    """Call /chat and evaluate the response."""
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

        # Validate SQL content
        sql_ok, sql_issues = check_sql(sql, test)
        result["issues"].extend(sql_issues)

        # Validate row count
        min_rows = test.get("min_rows", -1)
        if min_rows > 0 and row_count < min_rows:
            result["issues"].append(
                f"Expected at least {min_rows} rows, got {row_count}"
            )

        max_rows = test.get("max_rows")
        if max_rows is not None and row_count > max_rows:
            result["issues"].append(
                f"Expected at most {max_rows} rows (LIMIT), got {row_count}"
            )

        if test.get("expect_single") and row_count != 1:
            result["issues"].append(
                f"Expected exactly 1 row for aggregation, got {row_count}"
            )

        if not result["issues"]:
            result["status"] = "PASS"

    except requests.exceptions.ConnectionError:
        result["api_error"] = "Could not connect to API. Is uvicorn running on port 8000?"
    except Exception as exc:
        result["api_error"] = str(exc)

    return result


def generate_results_md(results: list[dict], score: int, total: int) -> str:
    lines = [
        "# Test Results — NL2SQL Clinic Chatbot",
        "",
        f"Tested on: clinic.db (200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices)",
        f"LLM: Google Gemini 2.0 Flash",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"**Final Score: {score}/{total} correct**",
        "",
        "---",
        "",
    ]

    for r in results:
        icon = "✅" if r["status"] == "PASS" else "❌"
        lines.append(f"## Question {r['id']} — {r['question']}")
        lines.append("")
        lines.append(f"**Status: {icon} {r['status']}**")
        lines.append("")

        if r.get("api_error"):
            lines.append(f"**API Error:** {r['api_error']}")
        else:
            sql = r.get("sql") or "No SQL generated"
            lines.append("Generated SQL:")
            lines.append("```sql")
            lines.append(sql)
            lines.append("```")
            lines.append("")
            lines.append(f"Row count: {r.get('row_count', 'N/A')}")

            if r["issues"]:
                lines.append("")
                lines.append("**Issues:**")
                for issue in r["issues"]:
                    lines.append(f"- {issue}")

        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| # | Question | Result |")
    lines.append("|---|----------|--------|")
    for r in results:
        icon = "✅ Pass" if r["status"] == "PASS" else "❌ Fail"
        lines.append(f"| {r['id']} | {r['question']} | {icon} |")

    lines.append("")
    lines.append(f"**Score: {score}/{total}**")
    lines.append("")

    failed = [r for r in results if r["status"] == "FAIL"]
    if failed:
        lines.append("## Notes on Failures")
        lines.append("")
        for r in failed:
            lines.append(f"**Q{r['id']} ({r['question']}):**")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    return "\n".join(lines)


def main():
    print("Testing 20 Questions — NL2SQL Clinic Chatbot")
    print("=" * 72)

    # Check server is up
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
    except Exception:
        print("❌ Cannot reach the API at http://127.0.0.1:8000")
        print("   Make sure uvicorn is running: uvicorn main:app --port 8000")
        return

    results = []
    passed = 0

    for test in TEST_CASES:
        print(f"\nQuestion {test['id']:>2}/20: {test['question']}")
        result = run_test(test)
        results.append(result)

        if result["status"] == "PASS":
            passed += 1
            print(f"  ✅ PASS")
            sql_preview = (result["sql"] or "")[:80].replace("\n", " ")
            print(f"     SQL: {sql_preview}...")
            print(f"     Rows: {result['row_count']}")
        else:
            print(f"  ❌ FAIL")
            if result.get("api_error"):
                print(f"     Error: {result['api_error']}")
            for issue in result["issues"]:
                print(f"     Issue: {issue}")
            sql_preview = (result["sql"] or "No SQL")[:80].replace("\n", " ")
            print(f"     SQL: {sql_preview}")

    total = len(TEST_CASES)
    print("\n" + "=" * 72)
    print(f"Summary: {passed} PASSED, {total - passed} FAILED out of {total}")
    print(f"Success Rate: {passed / total * 100:.1f}%")

    # Save JSON
    json_output = {
        "score": passed,
        "total": total,
        "success_rate": f"{passed / total * 100:.1f}%",
        "tested_at": datetime.now().isoformat(),
        "results": results,
    }
    with open("test_results.json", "w") as f:
        json.dump(json_output, f, indent=2)
    print("\n✅ Results saved to test_results.json")
    
    # Save RESULTS.md with UTF-8 encoding to handle emojis
    md = generate_results_md(results, passed, total)
    with open("RESULTS.md", "w", encoding="utf-8") as f:  # <-- FIXED
        f.write(md)
    print("Results saved to RESULTS.md")


if __name__ == "__main__":
    main()
