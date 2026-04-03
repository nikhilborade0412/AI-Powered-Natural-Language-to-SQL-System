# Test Results — NL2SQL Clinic Chatbot

Tested on: clinic.db (200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices)
LLM: Google Gemini 2.0 Flash
Date: 2026-04-03 18:32

**Final Score: 20/20 correct**

---

## Question 1 — How many patients do we have?

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT COUNT(*) AS total_patients FROM patients
```

Row count: 1

---

## Question 2 — List all doctors and their specializations

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT name, specialization, department FROM doctors ORDER BY name
```

Row count: 15

---

## Question 3 — Show me appointments for last month

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT a.id, p.first_name, p.last_name, d.name AS doctor, a.appointment_date, a.status FROM appointments a JOIN patients p ON p.id = a.patient_id JOIN doctors d ON d.id = a.doctor_id WHERE a.appointment_date >= date('now', 'start of month', '-1 month') AND a.appointment_date < date('now', 'start of month') ORDER BY a.appointment_date
```

Row count: 38

---

## Question 4 — Which doctor has the most appointments?

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT d.name, COUNT(a.id) AS appointment_count FROM doctors d JOIN appointments a ON d.id = a.doctor_id GROUP BY d.id, d.name ORDER BY appointment_count DESC LIMIT 1
```

Row count: 1

---

## Question 5 — What is the total revenue?

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT SUM(total_amount) AS total_revenue FROM invoices
```

Row count: 1

---

## Question 6 — Show revenue by doctor

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT d.name, SUM(i.total_amount) AS total_revenue FROM doctors d JOIN appointments a ON d.id = a.doctor_id JOIN invoices i ON a.patient_id = i.patient_id GROUP BY d.name ORDER BY total_revenue DESC
```

Row count: 15

---

## Question 7 — How many cancelled appointments last quarter?

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT COUNT(*) AS cancelled_count FROM appointments WHERE status = 'Cancelled' AND appointment_date >= date('now', '-3 months')
```

Row count: 1

---

## Question 8 — Top 5 patients by spending

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending FROM patients p JOIN invoices i ON p.id = i.patient_id GROUP BY p.id, p.first_name, p.last_name ORDER BY total_spending DESC LIMIT 5
```

Row count: 5

---

## Question 9 — Average treatment cost by specialization

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization ORDER BY avg_cost DESC
```

Row count: 5

---

## Question 10 — Show monthly appointment count for the past 6 months

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS total FROM appointments WHERE appointment_date >= date('now', '-6 months') GROUP BY month ORDER BY month
```

Row count: 8

---

## Question 11 — Which city has the most patients?

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1
```

Row count: 1

---

## Question 12 — List patients who visited more than 3 times

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count FROM patients p JOIN appointments a ON a.patient_id = p.id GROUP BY p.id, p.first_name, p.last_name HAVING visit_count > 3 ORDER BY visit_count DESC
```

Row count: 44

---

## Question 13 — Show unpaid invoices

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT p.first_name, p.last_name, i.total_amount, i.paid_amount, i.status, i.invoice_date FROM invoices i JOIN patients p ON p.id = i.patient_id WHERE i.status IN ('Pending', 'Overdue') ORDER BY i.invoice_date DESC
```

Row count: 126

---

## Question 14 — What percentage of appointments are no-shows?

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT ROUND(100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS no_show_percentage FROM appointments
```

Row count: 1

---

## Question 15 — Show the busiest day of the week for appointments

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT CASE CAST(strftime('%w', appointment_date) AS INTEGER) WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday' WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday' WHEN 6 THEN 'Saturday' END AS day_name, COUNT(*) AS total FROM appointments GROUP BY strftime('%w', appointment_date) ORDER BY total DESC
```

Row count: 7

---

## Question 16 — Revenue trend by month

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT strftime('%Y-%m', invoice_date) AS month, SUM(total_amount) AS revenue FROM invoices GROUP BY month ORDER BY month
```

Row count: 13

---

## Question 17 — Average appointment duration by doctor

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT d.name, ROUND(AVG(t.duration_minutes), 1) AS avg_duration FROM doctors d JOIN appointments a ON d.id = a.doctor_id JOIN treatments t ON a.id = t.appointment_id GROUP BY d.id, d.name ORDER BY avg_duration DESC
```

Row count: 15

---

## Question 18 — List patients with overdue invoices

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT DISTINCT p.first_name, p.last_name, p.email, i.total_amount, i.paid_amount, i.invoice_date FROM patients p JOIN invoices i ON p.id = i.patient_id WHERE i.status = 'Overdue' ORDER BY i.invoice_date
```

Row count: 41

---

## Question 19 — Compare revenue between departments

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT d.department, SUM(i.total_amount) AS total_revenue FROM doctors d JOIN appointments a ON d.id = a.doctor_id JOIN invoices i ON a.patient_id = i.patient_id GROUP BY d.department ORDER BY total_revenue DESC
```

Row count: 5

---

## Question 20 — Show patient registration trend by month

**Status: ✅ PASS**

Generated SQL:
```sql
SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients FROM patients GROUP BY month ORDER BY month
```

Row count: 36

---

## Summary

| # | Question | Result |
|---|----------|--------|
| 1 | How many patients do we have? | ✅ Pass |
| 2 | List all doctors and their specializations | ✅ Pass |
| 3 | Show me appointments for last month | ✅ Pass |
| 4 | Which doctor has the most appointments? | ✅ Pass |
| 5 | What is the total revenue? | ✅ Pass |
| 6 | Show revenue by doctor | ✅ Pass |
| 7 | How many cancelled appointments last quarter? | ✅ Pass |
| 8 | Top 5 patients by spending | ✅ Pass |
| 9 | Average treatment cost by specialization | ✅ Pass |
| 10 | Show monthly appointment count for the past 6 months | ✅ Pass |
| 11 | Which city has the most patients? | ✅ Pass |
| 12 | List patients who visited more than 3 times | ✅ Pass |
| 13 | Show unpaid invoices | ✅ Pass |
| 14 | What percentage of appointments are no-shows? | ✅ Pass |
| 15 | Show the busiest day of the week for appointments | ✅ Pass |
| 16 | Revenue trend by month | ✅ Pass |
| 17 | Average appointment duration by doctor | ✅ Pass |
| 18 | List patients with overdue invoices | ✅ Pass |
| 19 | Compare revenue between departments | ✅ Pass |
| 20 | Show patient registration trend by month | ✅ Pass |

**Score: 20/20**
