#!/usr/bin/env python3
"""
setup_database.py
Creates the clinic.db SQLite database with schema and realistic dummy data.
"""

import sqlite3
import random
from datetime import datetime, timedelta
from typing import List, Tuple
import os

# Configuration
DATABASE_PATH = "clinic.db"
NUM_DOCTORS = 15
NUM_PATIENTS = 200
NUM_APPOINTMENTS = 500
NUM_TREATMENTS = 350
NUM_INVOICES = 300

# Realistic data pools
FIRST_NAMES_MALE = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph",
    "Thomas", "Charles", "Christopher", "Daniel", "Matthew", "Anthony", "Mark",
    "Donald", "Steven", "Paul", "Andrew", "Joshua", "Kenneth", "Kevin", "Brian"
]

FIRST_NAMES_FEMALE = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan",
    "Jessica", "Sarah", "Karen", "Lisa", "Nancy", "Betty", "Margaret", "Sandra",
    "Ashley", "Kimberly", "Emily", "Donna", "Michelle", "Dorothy", "Carol", "Amanda"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"
]

SPECIALIZATIONS = ["Dermatology", "Cardiology", "Orthopedics", "General", "Pediatrics"]

DEPARTMENTS = {
    "Dermatology": "Skin Care Department",
    "Cardiology": "Heart & Vascular Department",
    "Orthopedics": "Bone & Joint Department",
    "General": "General Medicine",
    "Pediatrics": "Children's Health Department"
}

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
APPOINTMENT_STATUS_WEIGHTS = [0.15, 0.60, 0.15, 0.10]  # Weighted probabilities

TREATMENT_NAMES = [
    "General Consultation", "Blood Test", "X-Ray", "MRI Scan", "CT Scan",
    "Physical Therapy", "Skin Treatment", "Cardiac Checkup", "Vaccination",
    "Minor Surgery", "Wound Dressing", "Allergy Test", "ECG", "Ultrasound",
    "Dental Cleaning", "Eye Examination", "Hearing Test", "Physiotherapy Session"
]

INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]
INVOICE_STATUS_WEIGHTS = [0.60, 0.25, 0.15]


def create_schema(cursor: sqlite3.Cursor) -> None:
    """Create all database tables."""
    
    # Drop existing tables
    cursor.executescript("""
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS treatments;
        DROP TABLE IF EXISTS appointments;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS patients;
    """)
    
    # Create patients table
    cursor.execute("""
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT CHECK(gender IN ('M', 'F')),
            city TEXT,
            registered_date DATE
        )
    """)
    
    # Create doctors table
    cursor.execute("""
        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        )
    """)
    
    # Create appointments table
    cursor.execute("""
        CREATE TABLE appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT CHECK(status IN ('Scheduled', 'Completed', 'Cancelled', 'No-Show')),
            notes TEXT,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
    """)
    
    # Create treatments table
    cursor.execute("""
        CREATE TABLE treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        )
    """)
    
    # Create invoices table
    cursor.execute("""
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT CHECK(status IN ('Paid', 'Pending', 'Overdue')),
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        )
    """)
    
    print("✓ Schema created successfully")


def generate_phone() -> str:
    """Generate a realistic phone number."""
    return f"({random.randint(200,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}"


def generate_email(first_name: str, last_name: str) -> str:
    """Generate a realistic email address."""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "email.com"]
    separators = [".", "_", ""]
    separator = random.choice(separators)
    number = random.randint(1, 999) if random.random() > 0.5 else ""
    return f"{first_name.lower()}{separator}{last_name.lower()}{number}@{random.choice(domains)}"


def random_date(start_date: datetime, end_date: datetime) -> datetime:
    """Generate a random date between start_date and end_date."""
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)


def insert_doctors(cursor: sqlite3.Cursor) -> List[int]:
    """Insert doctors and return their IDs."""
    doctor_ids = []
    
    # Ensure at least 3 doctors per specialization
    doctors_per_spec = NUM_DOCTORS // len(SPECIALIZATIONS)
    
    for i, spec in enumerate(SPECIALIZATIONS):
        for j in range(doctors_per_spec):
            first_name = random.choice(FIRST_NAMES_MALE + FIRST_NAMES_FEMALE)
            last_name = random.choice(LAST_NAMES)
            name = f"Dr. {first_name} {last_name}"
            department = DEPARTMENTS[spec]
            phone = generate_phone()
            
            cursor.execute("""
                INSERT INTO doctors (name, specialization, department, phone)
                VALUES (?, ?, ?, ?)
            """, (name, spec, department, phone))
            doctor_ids.append(cursor.lastrowid)
    
    print(f"✓ Inserted {len(doctor_ids)} doctors")
    return doctor_ids


def insert_patients(cursor: sqlite3.Cursor) -> List[int]:
    """Insert patients and return their IDs."""
    patient_ids = []
    today = datetime.now()
    
    for i in range(NUM_PATIENTS):
        gender = random.choice(["M", "F"])
        first_name = random.choice(FIRST_NAMES_MALE if gender == "M" else FIRST_NAMES_FEMALE)
        last_name = random.choice(LAST_NAMES)
        
        # Some patients don't have email or phone (NULL values)
        email = generate_email(first_name, last_name) if random.random() > 0.1 else None
        phone = generate_phone() if random.random() > 0.15 else None
        
        # Age between 1 and 90
        age_days = random.randint(365, 365 * 90)
        date_of_birth = (today - timedelta(days=age_days)).strftime("%Y-%m-%d")
        
        city = random.choice(CITIES)
        
        # Registration date within the last 3 years
        registered_date = random_date(
            today - timedelta(days=365*3),
            today
        ).strftime("%Y-%m-%d")
        
        cursor.execute("""
            INSERT INTO patients (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date))
        patient_ids.append(cursor.lastrowid)
    
    print(f"✓ Inserted {len(patient_ids)} patients")
    return patient_ids


def insert_appointments(cursor: sqlite3.Cursor, patient_ids: List[int], doctor_ids: List[int]) -> List[Tuple[int, str]]:
    """Insert appointments and return list of (appointment_id, status)."""
    appointments = []
    today = datetime.now()
    
    # Create a distribution where some patients have many appointments
    # 20% of patients will have 50% of appointments (frequent visitors)
    frequent_patients = random.sample(patient_ids, k=int(len(patient_ids) * 0.2))
    
    # Similarly, some doctors are busier
    busy_doctors = random.sample(doctor_ids, k=int(len(doctor_ids) * 0.3))
    
    notes_samples = [
        "Regular checkup", "Follow-up visit", "Initial consultation",
        "Referred by GP", "Emergency visit", "Routine screening",
        None, None, None  # Some NULL notes
    ]
    
    for i in range(NUM_APPOINTMENTS):
        # 50% chance to pick from frequent patients
        if random.random() < 0.5 and frequent_patients:
            patient_id = random.choice(frequent_patients)
        else:
            patient_id = random.choice(patient_ids)
        
        # 60% chance to pick from busy doctors
        if random.random() < 0.6 and busy_doctors:
            doctor_id = random.choice(busy_doctors)
        else:
            doctor_id = random.choice(doctor_ids)
        
        # Appointment date within the last 12 months
        appointment_date = random_date(
            today - timedelta(days=365),
            today + timedelta(days=30)  # Some future appointments
        )
        
        # Status based on whether appointment is in past or future
        if appointment_date > today:
            status = "Scheduled"
        else:
            status = random.choices(
                APPOINTMENT_STATUSES,
                weights=APPOINTMENT_STATUS_WEIGHTS
            )[0]
        
        notes = random.choice(notes_samples)
        
        cursor.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (patient_id, doctor_id, appointment_date.strftime("%Y-%m-%d %H:%M:%S"), status, notes))
        
        appointments.append((cursor.lastrowid, status))
    
    print(f"✓ Inserted {len(appointments)} appointments")
    return appointments


def insert_treatments(cursor: sqlite3.Cursor, appointments: List[Tuple[int, str]]) -> int:
    """Insert treatments for completed appointments."""
    treatment_count = 0
    
    # Get completed appointments
    completed_appointments = [apt_id for apt_id, status in appointments if status == "Completed"]
    
    # Randomly select appointments to have treatments
    appointments_with_treatments = random.sample(
        completed_appointments,
        k=min(NUM_TREATMENTS, len(completed_appointments))
    )
    
    for appointment_id in appointments_with_treatments:
        treatment_name = random.choice(TREATMENT_NAMES)
        cost = round(random.uniform(50, 5000), 2)
        duration_minutes = random.choice([15, 30, 45, 60, 90, 120])
        
        cursor.execute("""
            INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)
            VALUES (?, ?, ?, ?)
        """, (appointment_id, treatment_name, cost, duration_minutes))
        treatment_count += 1
    
    print(f"✓ Inserted {treatment_count} treatments")
    return treatment_count


def insert_invoices(cursor: sqlite3.Cursor, patient_ids: List[int]) -> int:
    """Insert invoices for patients."""
    invoice_count = 0
    today = datetime.now()
    
    # Select patients who will have invoices
    patients_with_invoices = random.sample(
        patient_ids,
        k=min(NUM_INVOICES, len(patient_ids))
    )
    
    # Some patients have multiple invoices
    for _ in range(NUM_INVOICES):
        patient_id = random.choice(patients_with_invoices)
        
        invoice_date = random_date(
            today - timedelta(days=365),
            today
        ).strftime("%Y-%m-%d")
        
        total_amount = round(random.uniform(100, 10000), 2)
        
        status = random.choices(
            INVOICE_STATUSES,
            weights=INVOICE_STATUS_WEIGHTS
        )[0]
        
        if status == "Paid":
            paid_amount = total_amount
        elif status == "Pending":
            paid_amount = round(random.uniform(0, total_amount * 0.5), 2)
        else:  # Overdue
            paid_amount = round(random.uniform(0, total_amount * 0.3), 2)
        
        cursor.execute("""
            INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)
            VALUES (?, ?, ?, ?, ?)
        """, (patient_id, invoice_date, total_amount, paid_amount, status))
        invoice_count += 1
    
    print(f"✓ Inserted {invoice_count} invoices")
    return invoice_count


def print_summary(cursor: sqlite3.Cursor) -> None:
    """Print a summary of the database contents."""
    print("\n" + "="*50)
    print("DATABASE SUMMARY")
    print("="*50)
    
    tables = ["patients", "doctors", "appointments", "treatments", "invoices"]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  {table.capitalize()}: {count} records")
    
    # Additional statistics
    print("\nAPPOINTMENT STATUS DISTRIBUTION:")
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM appointments 
        GROUP BY status 
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]}")
    
    print("\nINVOICE STATUS DISTRIBUTION:")
    cursor.execute("""
        SELECT status, COUNT(*) as count, ROUND(SUM(total_amount), 2) as total
        FROM invoices 
        GROUP BY status 
        ORDER BY total DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} invoices (${row[2]:,.2f} total)")
    
    print("\nPATIENTS BY CITY:")
    cursor.execute("""
        SELECT city, COUNT(*) as count 
        FROM patients 
        GROUP BY city 
        ORDER BY count DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} patients")
    
    print("="*50)


def main():
    """Main function to set up the database."""
    # Remove existing database
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"✓ Removed existing {DATABASE_PATH}")
    
    # Connect to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print(f"\nCreating database: {DATABASE_PATH}")
    print("-" * 50)
    
    try:
        # Create schema
        create_schema(cursor)
        
        # Insert data
        doctor_ids = insert_doctors(cursor)
        patient_ids = insert_patients(cursor)
        appointments = insert_appointments(cursor, patient_ids, doctor_ids)
        insert_treatments(cursor, appointments)
        insert_invoices(cursor, patient_ids)
        
        # Commit changes
        conn.commit()
        
        # Print summary
        print_summary(cursor)
        
        print(f"\n✅ Database '{DATABASE_PATH}' created successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error creating database: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()