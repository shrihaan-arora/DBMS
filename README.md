# DBMS
MANAS IS THE BEST

## SkyReserve — Airline Reservation & Flight Operations Database System (MySQL Edition)

An enterprise-grade relational database management application designed to manage core airline operations: flight scheduling, aircraft fleet management, passenger reservations with multivalued contact attributes (1NF), seat allocation with transactional concurrency control, weak-entity baggage tracking, crew rostering with temporal overlap prevention, and operational reporting.

Originally designed for SQLite, this project has been fully migrated to **MySQL (InnoDB)** using `mysql-connector-python` to satisfy university DBMS curriculum requirements.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** (tested and fully compatible with Python 3.14)
- **MySQL Server 8.0+** installed and running locally or remotely

#### Installing / Starting MySQL Server:
- **macOS (Homebrew):**
  ```bash
  brew install mysql
  brew services start mysql
  # Or start manually:
  mysqld_safe &
  ```
- **Ubuntu / Debian Linux:**
  ```bash
  sudo apt update && sudo apt install mysql-server -y
  sudo systemctl start mysql
  ```
- **Windows:**
  - Download and install [MySQL Community Server](https://dev.mysql.com/downloads/installer/).
  - Ensure the MySQL Windows service is started via Services manager or MySQL Workbench.

---

### 2. Environment Configuration

1. Copy the example configuration to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and set your MySQL credentials:
   ```env
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_NAME=skyreserve
   PORT=5001
   ```

---

### 3. Install Dependencies

Install the required Python packages:
```bash
pip install -r requirements.txt
```
*(Dependencies: `Flask>=3.0.0`, `mysql-connector-python>=8.0.0`, `python-dotenv>=1.0.0`)*

---

### 4. Initialize the MySQL Database

Run the database initialization script. This will create the database `skyreserve` if it does not already exist, execute `schema.sql` (creating all 10 tables, constraints, views, and triggers), and load `seed_data.sql`:
```bash
python database.py
```
*Output:*
```
Connecting to MySQL (root@localhost:3306)...
Database 'skyreserve' initialized successfully with schema and seed data.
```

---

### 5. Run the Application

- **Option A (One-Click Start Scripts)**:
  - **macOS / Linux**:
    ```bash
    bash start.sh
    ```
  - **Windows**: Double-click **`start.bat`**
- **Option B (Standard Command Line)**:
  ```bash
  python app.py
  ```
Then open your browser to **`http://localhost:5001`** (or `http://127.0.0.1:5001`).

---

### 6. Run the Verification Test Suite

Verify all 18 functional requirements, constraints, triggers, and views against MySQL:
```bash
python test_suite.py
```

---

## 🗄️ Relational Database Architecture (MySQL InnoDB)

All tables use the **InnoDB** storage engine with strict foreign key integrity, ACID compliance, and check constraints.

### 1. Entity Overview & Normalization

| Entity / Table | Primary Key | Description & Normalization Notes |
|---|---|---|
| **`Aircraft`** | `Aircraft_ID` (`INT AUTO_INCREMENT`) | Fleet inventory (Boeing 787, A320, etc.), total capacity & seat class distribution. |
| **`Flight`** | `Flight_No` (`VARCHAR(20)`) | Route definitions (`Source` & `Destination`, e.g., DEL → BOM). Enforces `CHECK (Source != Destination)`. |
| **`Flight_Schedule`** | `Schedule_ID` (`INT AUTO_INCREMENT`) | Specific temporal occurrences of flights. Enforces `UNIQUE(Aircraft_ID, Date, Departure_Time)` to prevent aircraft double-booking. |
| **`Passenger`** | `Passenger_ID` (`INT AUTO_INCREMENT`) | Passenger demographic, unique email, and unique passport records. |
| **`Passenger_Phone`** | `Phone_ID` (`INT AUTO_INCREMENT`) | **1NF Normalization:** Resolves multivalued phone numbers into a separate 1:N table with `UNIQUE(Passenger_ID, Phone_Number)`. |
| **`Booking`** | `Booking_ID` (`INT AUTO_INCREMENT`) | Resolves M:N relationship between passenger and flight schedule. Tracks seat assignment, class, fare, and lifecycle status (`Confirmed`, `Checked-In`, `Cancelled`). |
| **`Baggage`** | `(Booking_ID, Baggage_Seq_No)` | **Weak Entity:** Composite primary key. Cannot exist independently of a `Booking`. Enforces `ON DELETE CASCADE`. |
| **`Crew`** | `Crew_ID` (`INT AUTO_INCREMENT`) | Pilots, flight engineers, and cabin staff with unique license numbers. |
| **`Crew_Assignment`** | `Assignment_ID` (`INT AUTO_INCREMENT`) | Resolves M:N relationship between crew members and flight schedules with `UNIQUE(Crew_ID, Schedule_ID)`. |
| **`Booking_Audit`** | `Audit_ID` (`INT AUTO_INCREMENT`) | Automated audit trail logging timestamp, action, user, old state JSON, and new state JSON. |

---

### 2. Derived View: `Available_Seats` (FR10)

Calculated on-the-fly dynamically rather than redundantly stored in tables:
```sql
CREATE OR REPLACE VIEW Available_Seats AS
SELECT 
    fs.Schedule_ID,
    f.Flight_No,
    f.Source,
    f.Destination,
    fs.Date,
    fs.Departure_Time,
    fs.Arrival_Time,
    a.Total_Capacity,
    a.Total_Capacity - COALESCE((
        SELECT COUNT(*) FROM Booking b 
        WHERE b.Schedule_ID = fs.Schedule_ID 
        AND b.Booking_Status NOT IN ('Cancelled')
    ), 0) AS Seats_Available,
    fs.Status
FROM Flight_Schedule fs
JOIN Flight f ON fs.Flight_No = f.Flight_No
JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID;
```

---

### 3. MySQL Triggers

The schema implements 4 MySQL triggers utilizing `SIGNAL SQLSTATE '45000'` for transactional aborts:

1. **`prevent_seat_double_booking` (BEFORE INSERT ON Booking)**:
   Rejects duplicate bookings on the same `(Schedule_ID, Seat_No)` for active bookings:
   ```sql
   IF NEW.Seat_No IS NOT NULL AND NEW.Booking_Status IN ('Confirmed', 'Checked-In') THEN
       IF EXISTS (
           SELECT 1 FROM Booking 
           WHERE Schedule_ID = NEW.Schedule_ID 
             AND Seat_No = NEW.Seat_No 
             AND Booking_Status IN ('Confirmed', 'Checked-In')
       ) THEN
           SIGNAL SQLSTATE '45000'
               SET MESSAGE_TEXT = 'Seat already booked for this schedule';
       END IF;
   END IF;
   ```
2. **`prevent_seat_double_booking_update` (BEFORE UPDATE ON Booking)**:
   Guarantees seat conflict checks when seat assignments are modified or passengers change seats.
3. **`booking_after_insert` (AFTER INSERT ON Booking)**:
   Automatically writes an immutable audit record with `JSON_OBJECT(...)` to `Booking_Audit`.
4. **`booking_after_update` (AFTER UPDATE ON Booking)**:
   Captures delta between old values and new values for modifications or cancellations.

---

## 🎯 Requirements Mapping Matrix

| Requirement | Implementation Detail | Location |
|---|---|---|
| **FR1, FR2, FR3** | Flight CRUD, departure/arrival schedules, date/source/destination search & available seats | `/flights`, `/schedules`, `/api/search_flights` |
| **FR4, FR5** | Aircraft fleet management, seating class configuration, overlap prevention | `/aircraft`, `Aircraft_Schedule` unique index |
| **FR6** | Passenger registration with dynamic multivalued phone numbers (1NF) | `/passengers`, `templates/passenger_form.html` |
| **FR7, FR8** | Reservation linking passenger to schedule, seat assignment with real-time API validation | `/bookings/add`, `/api/available_seats/<id>` |
| **FR9, FR10** | Cancellation workflow, auto-recalculation of available seats, refund status tracking | `/bookings/<id>/cancel`, `Available_Seats` view |
| **FR11, FR12** | Baggage weak entity with composite PK, weight limits, excess weight flag (>23kg) | `/bookings/<id>/baggage/add`, `Baggage` table |
| **FR13, FR14** | Crew scheduling, roster management, temporal overlap prevention | `/crew`, `/assignments/add` |
| **FR15-FR18** | Interactive front-end CRUD interfaces, visual indicators, Chart.js analytics | All templates in `/templates` |
| **Flight Search & Booking** | Search by origin, destination, date; live seat counts; instant reservation modal | `/book-flight`, `/book-flight/confirm` |
| **India Flight Map** | Interactive Leaflet.js radar map with curved air corridors, airport hubs, live seats | `/flight-map`, `/api/flight_map_data` |
| **Project Guide & Docs** | Comprehensive technical report: Normalization proofs (1NF-BCNF), DDL schemas, Triggers | `/project-guide` |
| **Direct SQL & Bulk JSON** | Live interactive SQL console with tabular results & Bulk JSON batch insert | `/manual-entry/raw-sql`, `/manual-entry/bulk-json` |

---

## 🔧 Troubleshooting Guide

### 1. `Can't connect to local MySQL server through socket` or `Connection refused`
- **Cause**: MySQL Server service is not running.
- **Solution**:
  - macOS: `brew services start mysql` or `mysql.server start`
  - Linux: `sudo systemctl start mysql`
  - Windows: Start the MySQL service from Windows Services or MySQL Notifier.

### 2. `Access denied for user 'root'@'localhost'`
- **Cause**: Incorrect password or authentication plugin issue.
- **Solution**:
  - Update `DB_PASSWORD` in `.env` with your actual MySQL password.
  - If connecting with blank password, ensure MySQL root has empty password set:
    ```sql
    ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '';
    FLUSH PRIVILEGES;
    ```

### 3. `Table 'skyreserve.Flight' doesn't exist`
- **Cause**: Schema has not been initialized.
- **Solution**: Run `python database.py` to create and populate all tables.

### 4. `Seat already booked for this schedule`
- **Cause**: This is expected! The MySQL trigger `prevent_seat_double_booking` successfully intercepted an attempt to book a seat that is already taken.

---

## 🎓 DBMS Viva & Practical Examination Guide

Use this section to confidently explain and demonstrate the project during your DBMS viva:

### 1. Where and how the MySQL connection is created
- **File**: [`database.py`](file:///Users/SHREEHANARORA/dev/programs/DBMS/SkyReserve/database.py)
- **Function**: `get_db()`
- **Explanation**: Uses `mysql.connector.connect()` with credentials read securely from environment variables (`.env`). It wraps connections in `MySQLConnectionWrapper` and cursors in `MySQLCursorWrapper` using `dictionary=True`, providing dictionary row access (`RowDict`) so column names can be accessed directly as `row['Flight_No']`.

### 2. How Flask routes execute SQL queries
- **File**: [`app.py`](file:///Users/SHREEHANARORA/dev/programs/DBMS/SkyReserve/app.py)
- **Functions**: e.g., `flights()` (lines 67-83), `booking_add()` (lines 542-578)
- **Explanation**: Routes acquire a connection via `db = get_db()`, execute parameterized queries using `%s` placeholders (`db.execute("SELECT * FROM Flight WHERE Source=%s", (source,))`), fetch rows using `.fetchall()` or `.fetchone()`, and ensure connections are closed in `finally` blocks.

### 3. Demonstration of CRUD Operations
- **CREATE (INSERT)**:
  - Passenger registration: `passenger_add()` in `app.py` → `INSERT INTO Passenger (...) VALUES (%s, %s, ...)`
  - Booking creation: `book_flight_confirm()` in `app.py` → `INSERT INTO Booking (...) VALUES (...)`
- **READ (SELECT)**:
  - Flight search: `api_search_flights()` in `app.py` querying the `Available_Seats` view.
  - Revenue analytics: `reports()` in `app.py` with `SUM(Fare)` and `GROUP BY f.Flight_No`.
- **UPDATE**:
  - Seat reallocation: `booking_edit()` in `app.py` → `UPDATE Booking SET Seat_No=%s, Class=%s, Fare=%s WHERE Booking_ID=%s`
- **DELETE**:
  - Flight cancellation: `flight_delete()` in `app.py` → `DELETE FROM Flight WHERE Flight_No=%s` (demonstrates `ON DELETE CASCADE` down to schedules).

### 4. Primary Keys and Foreign Keys Enforcement
- **Primary Keys**: Integer surrogate keys with `AUTO_INCREMENT` (`Passenger_ID`, `Schedule_ID`, `Booking_ID`), natural alphanumeric key on `Flight(Flight_No)`.
- **Foreign Keys**: Defined with `CONSTRAINT fk_... FOREIGN KEY (...) REFERENCES ... ON DELETE CASCADE` on InnoDB.
- **Weak Entity**: `Baggage` table with composite primary key `PRIMARY KEY (Booking_ID, Baggage_Seq_No)` and cascading deletion.

### 5. Joins, Views, Triggers, and Transactions
- **Complex JOIN**: `dashboard()` (lines 41-60 in `app.py`) joins `Flight_Schedule`, `Flight`, and `Aircraft` to display upcoming flights.
- **Dynamic VIEW**: [`schema.sql`](file:///Users/SHREEHANARORA/dev/programs/DBMS/SkyReserve/schema.sql) lines 120-137 (`Available_Seats`) dynamically recalculates seats via a correlated subquery subtracting uncancelled bookings from aircraft capacity.
- **TRIGGERS**:
  - `prevent_seat_double_booking` in [`schema.sql`](file:///Users/SHREEHANARORA/dev/programs/DBMS/SkyReserve/schema.sql) lines 165-180 raising error via `SIGNAL SQLSTATE '45000'`.
  - `booking_after_insert` in [`schema.sql`](file:///Users/SHREEHANARORA/dev/programs/DBMS/SkyReserve/schema.sql) lines 140-155 generating JSON audit trails.
- **TRANSACTIONS**: `book_flight_confirm()` in `app.py` wraps passenger creation, booking insertion, and baggage registration in a single transaction with explicit `db.commit()` and `db.rollback()` on exceptions.
