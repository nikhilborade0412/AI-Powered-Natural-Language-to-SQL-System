"""
seed_memory.py

Pre-seeds the agent memory with 20 known-good question → SQL pairs.
Run AFTER setup_database.py and BEFORE starting the API server.

    python seed_memory.py
"""

from vanna_setup import get_agent

QA_PAIRS = [
    # ── Patients ──────────────────────────────────────────────────────────
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients"
    },
    {
        "question": "List all patients from New York",
        "sql": (
            "SELECT first_name, last_name, email, phone "
            "FROM patients WHERE city = 'New York'"
        )
    },
    {
        "question": "How many male and female patients do we have?",
        "sql": "SELECT gender, COUNT(*) AS count FROM patients GROUP BY gender"
    },
    {
        "question": "Which city has the most patients?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count FROM patients "
            "GROUP BY city ORDER BY patient_count DESC LIMIT 1"
        )
    },

    # ── Doctors ───────────────────────────────────────────────────────────
    {
        "question": "List all doctors and their specializations",
        "sql": "SELECT name, specialization, department FROM doctors ORDER BY specialization"
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": (
            "SELECT d.name, COUNT(a.id) AS total_appointments "
            "FROM doctors d "
            "JOIN appointments a ON a.doctor_id = d.id "
            "GROUP BY d.id ORDER BY total_appointments DESC LIMIT 1"
        )
    },
    {
        "question": "How many doctors are in each specialization?",
        "sql": (
            "SELECT specialization, COUNT(*) AS doctor_count "
            "FROM doctors GROUP BY specialization ORDER BY doctor_count DESC"
        )
    },

    # ── Appointments ──────────────────────────────────────────────────────
    {
        "question": "Show me appointments for last month",
        "sql": (
            "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, "
            "a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE strftime('%Y-%m', a.appointment_date) = "
            "strftime('%Y-%m', date('now', '-1 month'))"
        )
    },
    {
        "question": "How many cancelled appointments do we have?",
        "sql": "SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled'"
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": (
            "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS total "
            "FROM appointments "
            "WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month ORDER BY month"
        )
    },

    # ── Financial ─────────────────────────────────────────────────────────
    {
        "question": "What is the total revenue?",
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices WHERE status = 'Paid'"
    },
    {
        "question": "Show revenue by doctor",
        "sql": (
            "SELECT d.name, SUM(i.total_amount) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.name ORDER BY total_revenue DESC"
        )
    },
    {
        "question": "Show unpaid invoices",
        "sql": (
            "SELECT p.first_name, p.last_name, i.total_amount, i.paid_amount, "
            "i.status, i.invoice_date "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.invoice_date DESC"
        )
    },
    {
        "question": "Average treatment cost by specialization",
        "sql": (
            "SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost "
            "FROM treatments t "
            "JOIN appointments a ON a.id = t.appointment_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.specialization ORDER BY avg_cost DESC"
        )
    },
    {
        "question": "Top 5 patients by spending",
        "sql": (
            "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
            "FROM patients p "
            "JOIN invoices i ON i.patient_id = p.id "
            "GROUP BY p.id ORDER BY total_spending DESC LIMIT 5"
        )
    },
    {
        "question": "List patients who visited more than 3 times",
        "sql": (
            "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count "
            "FROM patients p "
            "JOIN appointments a ON a.patient_id = p.id "
            "GROUP BY p.id HAVING visit_count > 3 ORDER BY visit_count DESC"
        )
    },
    {
        "question": "What percentage of appointments are no-shows?",
        "sql": (
            "SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) "
            "/ COUNT(*), 2) AS no_show_percentage FROM appointments"
        )
    },
    {
        "question": "Show the busiest day of the week for appointments",
        "sql": (
            "SELECT strftime('%w', appointment_date) AS day_of_week, "
            "COUNT(*) AS total FROM appointments "
            "GROUP BY day_of_week ORDER BY total DESC LIMIT 1"
        )
    },
    {
        "question": "Revenue trend by month",
        "sql": (
            "SELECT strftime('%Y-%m', invoice_date) AS month, "
            "SUM(total_amount) AS revenue "
            "FROM invoices GROUP BY month ORDER BY month"
        )
    },
    {
        "question": "Compare revenue between departments",
        "sql": (
            "SELECT d.department, SUM(i.total_amount) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.department ORDER BY total_revenue DESC"
        )
    },
]


def seed_memory():
    print("Seeding agent memory with Q&A pairs...")
    print("-" * 50)

    agent = get_agent()
    seeded = 0

    for i, pair in enumerate(QA_PAIRS):
        try:
            agent.add_training_data(pair["question"], pair["sql"])
            print(f"  [{i + 1:>2}] Added: {pair['question'][:55]}...")
            seeded += 1
        except Exception as exc:
            print(f"  [{i + 1:>2}] Warning: {pair['question'][:45]} — {exc}")

    print("-" * 50)
    print(f"✓ Seeded {seeded} new Q&A pairs")
    print(f"✓ Total memory items: {agent.get_memory_count()}")
    print("\n✅ Memory seeding complete!")


if __name__ == "__main__":
    seed_memory()