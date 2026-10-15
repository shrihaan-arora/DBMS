"""
SkyReserve — Airline Reservation & Flight Operations System
Flask web application with full CRUD, search, and reporting.
"""
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify
)
from database import get_db, init_db
from datetime import datetime
import os, json

app = Flask(__name__)
app.secret_key = "skyreserve_secret_key_2026"

# ─── Initialise DB on first request ────────────────────────────────────────
_db_initialized = False

@app.before_request
def ensure_db():
    global _db_initialized
    if not _db_initialized:
        try:
            db = get_db()
            db.execute("SELECT 1 FROM Flight LIMIT 1")
            db.close()
        except Exception:
            try:
                init_db()
            except Exception as init_err:
                app.logger.warning(f"Database check/init warning: {init_err}")
        _db_initialized = True

# ═══════════════════════════  DASHBOARD  ═══════════════════════════════════
@app.route("/")
def dashboard():
    db = get_db()
    stats = {
        "flights": db.execute("SELECT COUNT(*) c FROM Flight").fetchone()["c"],
        "schedules": db.execute("SELECT COUNT(*) c FROM Flight_Schedule").fetchone()["c"],
        "passengers": db.execute("SELECT COUNT(*) c FROM Passenger").fetchone()["c"],
        "bookings": db.execute("SELECT COUNT(*) c FROM Booking WHERE Booking_Status != 'Cancelled'").fetchone()["c"],
        "aircraft": db.execute("SELECT COUNT(*) c FROM Aircraft").fetchone()["c"],
        "crew": db.execute("SELECT COUNT(*) c FROM Crew").fetchone()["c"],
        "baggage": db.execute("SELECT COUNT(*) c FROM Baggage").fetchone()["c"],
        "assignments": db.execute("SELECT COUNT(*) c FROM Crew_Assignment").fetchone()["c"],
    }
    upcoming = db.execute("""
        SELECT fs.Schedule_ID, f.Flight_No, f.Source, f.Destination,
               fs.Date, fs.Departure_Time, fs.Arrival_Time, fs.Status, fs.Gate,
               a.Model AS Aircraft_Model
        FROM Flight_Schedule fs
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        ORDER BY fs.Date, fs.Departure_Time
        LIMIT 10
    """).fetchall()
    recent_bookings = db.execute("""
        SELECT b.Booking_ID, p.First_Name || ' ' || p.Last_Name AS Passenger,
               f.Flight_No, f.Source, f.Destination, fs.Date,
               b.Seat_No, b.Class, b.Booking_Status, b.Fare
        FROM Booking b
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        ORDER BY b.Booking_Date DESC LIMIT 10
    """).fetchall()
    db.close()
    return render_template("dashboard.html", stats=stats, upcoming=upcoming,
                           recent_bookings=recent_bookings)

# ═══════════════════════════  FLIGHTS  ═════════════════════════════════════
@app.route("/flights")
def flights():
    db = get_db()
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    q = "SELECT * FROM Flight WHERE 1=1"
    params = []
    if source:
        q += " AND Source LIKE ?"
        params.append(f"%{source}%")
    if destination:
        q += " AND Destination LIKE ?"
        params.append(f"%{destination}%")
    q += " ORDER BY Flight_No"
    rows = db.execute(q, params).fetchall()
    db.close()
    return render_template("flights.html", flights=rows, source=source, destination=destination)

@app.route("/flights/add", methods=["GET", "POST"])
def flight_add():
    if request.method == "POST":
        db = get_db()
        redirect_target = request.form.get("redirect_to", "flights")
        try:
            db.execute(
                "INSERT INTO Flight (Flight_No, Airline, Source, Destination) VALUES (?,?,?,?)",
                (request.form["flight_no"].strip().upper(),
                 request.form["airline"].strip(),
                 request.form["source"].strip().upper(),
                 request.form["destination"].strip().upper()),
            )
            db.commit()
            flash("Flight added successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="flights"))
            return redirect(url_for("flights"))
        except Exception as e:
            flash(f"Error adding flight: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="flights"))
    return render_template("flight_form.html", flight=None)

@app.route("/flights/<flight_no>/edit", methods=["GET", "POST"])
def flight_edit(flight_no):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                "UPDATE Flight SET Airline=?, Source=?, Destination=? WHERE Flight_No=?",
                (request.form["airline"].strip(),
                 request.form["source"].strip().upper(),
                 request.form["destination"].strip().upper(),
                 flight_no),
            )
            db.commit()
            flash("Flight updated!", "success")
            return redirect(url_for("flights"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("flight_edit", flight_no=flight_no))
    flight = db.execute("SELECT * FROM Flight WHERE Flight_No=?", (flight_no,)).fetchone()
    db.close()
    if not flight:
        flash("Flight not found.", "warning")
        return redirect(url_for("flights"))
    return render_template("flight_form.html", flight=flight)

@app.route("/flights/<flight_no>/delete", methods=["POST"])
def flight_delete(flight_no):
    db = get_db()
    db.execute("DELETE FROM Flight WHERE Flight_No=?", (flight_no,))
    db.commit()
    db.close()
    flash("Flight deleted.", "success")
    return redirect(url_for("flights"))

# ═══════════════════════════  SCHEDULES  ═══════════════════════════════════
@app.route("/schedules")
def schedules():
    db = get_db()
    date_filter = request.args.get("date", "").strip()
    flight_filter = request.args.get("flight_no", "").strip()
    q = """
        SELECT av.*, a.Model AS Aircraft_Model, a.Registration_No, fs.Gate
        FROM Available_Seats av
        JOIN Flight_Schedule fs ON av.Schedule_ID = fs.Schedule_ID
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        WHERE 1=1
    """
    params = []
    if date_filter:
        q += " AND av.Date = ?"
        params.append(date_filter)
    if flight_filter:
        q += " AND av.Flight_No LIKE ?"
        params.append(f"%{flight_filter}%")
    q += " ORDER BY av.Date, av.Departure_Time"
    rows = db.execute(q, params).fetchall()
    db.close()
    return render_template("schedules.html", schedules=rows, date=date_filter, flight_no=flight_filter)

@app.route("/schedules/add", methods=["GET", "POST"])
def schedule_add():
    db = get_db()
    if request.method == "POST":
        schedule_id = request.form.get("schedule_id", "").strip()
        flight_no = request.form.get("flight_no_manual", "").strip().upper() or request.form.get("flight_no", "").strip().upper()
        aircraft_id = request.form.get("aircraft_id_manual", "").strip() or request.form.get("aircraft_id", "").strip()
        dep_time = request.form.get("departure_time")
        arr_time = request.form.get("arrival_time")
        sched_date = request.form.get("date")
        status = request.form.get("status", "Scheduled")
        gate = request.form.get("gate", "").strip() or None
        redirect_target = request.form.get("redirect_to", "schedules")
        try:
            if not flight_no or not aircraft_id or not sched_date or not dep_time or not arr_time:
                raise ValueError("All schedule date, flight, aircraft, and time fields are required")
            if schedule_id:
                db.execute("""
                    INSERT INTO Flight_Schedule
                    (Schedule_ID, Flight_No, Aircraft_ID, Departure_Time, Arrival_Time, Date, Status, Gate)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (int(schedule_id), flight_no, int(aircraft_id), dep_time, arr_time, sched_date, status, gate))
            else:
                db.execute("""
                    INSERT INTO Flight_Schedule
                    (Flight_No, Aircraft_ID, Departure_Time, Arrival_Time, Date, Status, Gate)
                    VALUES (?,?,?,?,?,?,?)
                """, (flight_no, int(aircraft_id), dep_time, arr_time, sched_date, status, gate))
            db.commit()
            flash("Schedule created successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="schedules"))
            return redirect(url_for("schedules"))
        except Exception as e:
            flash(f"Error creating schedule: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="schedules"))
        return redirect(url_for("schedule_add"))
    flights_list = db.execute("SELECT * FROM Flight ORDER BY Flight_No").fetchall()
    aircraft_list = db.execute("SELECT * FROM Aircraft WHERE Status='Active' ORDER BY Model").fetchall()
    db.close()
    return render_template("schedule_form.html", schedule=None,
                           flights=flights_list, aircraft=aircraft_list)

@app.route("/schedules/<int:sid>/edit", methods=["GET", "POST"])
def schedule_edit(sid):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute("""
                UPDATE Flight_Schedule
                SET Flight_No=?, Aircraft_ID=?, Departure_Time=?, Arrival_Time=?,
                    Date=?, Status=?, Gate=?
                WHERE Schedule_ID=?
            """, (
                request.form["flight_no"],
                request.form["aircraft_id"],
                request.form["departure_time"],
                request.form["arrival_time"],
                request.form["date"],
                request.form.get("status", "Scheduled"),
                request.form.get("gate", "").strip() or None,
                sid,
            ))
            db.commit()
            flash("Schedule updated!", "success")
            return redirect(url_for("schedules"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("schedule_edit", sid=sid))
    schedule = db.execute("SELECT * FROM Flight_Schedule WHERE Schedule_ID=?", (sid,)).fetchone()
    flights_list = db.execute("SELECT * FROM Flight ORDER BY Flight_No").fetchall()
    aircraft_list = db.execute("SELECT * FROM Aircraft WHERE Status='Active' ORDER BY Model").fetchall()
    db.close()
    if not schedule:
        flash("Schedule not found.", "warning")
        return redirect(url_for("schedules"))
    return render_template("schedule_form.html", schedule=schedule,
                           flights=flights_list, aircraft=aircraft_list)

@app.route("/schedules/<int:sid>/delete", methods=["POST"])
def schedule_delete(sid):
    db = get_db()
    db.execute("DELETE FROM Flight_Schedule WHERE Schedule_ID=?", (sid,))
    db.commit()
    db.close()
    flash("Schedule deleted.", "success")
    return redirect(url_for("schedules"))

# ═══════════════════════════  AIRCRAFT  ════════════════════════════════════
@app.route("/aircraft")
def aircraft_list():
    db = get_db()
    rows = db.execute("SELECT * FROM Aircraft ORDER BY Model").fetchall()
    db.close()
    return render_template("aircraft.html", aircraft=rows)

@app.route("/aircraft/add", methods=["GET", "POST"])
def aircraft_add():
    if request.method == "POST":
        db = get_db()
        redirect_target = request.form.get("redirect_to", "aircraft_list")
        aid = request.form.get("aircraft_id", "").strip()
        try:
            reg_no = request.form["registration_no"].strip().upper()
            model = request.form["model"].strip()
            total_cap = int(request.form["total_capacity"])
            eco = int(request.form.get("economy_seats", 0))
            biz = int(request.form.get("business_seats", 0))
            first = int(request.form.get("first_class_seats", 0))
            status = request.form.get("status", "Active")
            if aid:
                db.execute("""
                    INSERT INTO Aircraft
                    (Aircraft_ID, Registration_No, Model, Total_Capacity, Economy_Seats, Business_Seats, First_Class_Seats, Status)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (int(aid), reg_no, model, total_cap, eco, biz, first, status))
            else:
                db.execute("""
                    INSERT INTO Aircraft
                    (Registration_No, Model, Total_Capacity, Economy_Seats, Business_Seats, First_Class_Seats, Status)
                    VALUES (?,?,?,?,?,?,?)
                """, (reg_no, model, total_cap, eco, biz, first, status))
            db.commit()
            flash("Aircraft added successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="aircraft"))
            return redirect(url_for("aircraft_list"))
        except Exception as e:
            flash(f"Error adding aircraft: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="aircraft"))
    return render_template("aircraft_form.html", aircraft=None)

@app.route("/aircraft/<int:aid>/edit", methods=["GET", "POST"])
def aircraft_edit(aid):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute("""
                UPDATE Aircraft
                SET Registration_No=?, Model=?, Total_Capacity=?,
                    Economy_Seats=?, Business_Seats=?, First_Class_Seats=?, Status=?
                WHERE Aircraft_ID=?
            """, (
                request.form["registration_no"].strip().upper(),
                request.form["model"].strip(),
                int(request.form["total_capacity"]),
                int(request.form.get("economy_seats", 0)),
                int(request.form.get("business_seats", 0)),
                int(request.form.get("first_class_seats", 0)),
                request.form.get("status", "Active"),
                aid,
            ))
            db.commit()
            flash("Aircraft updated!", "success")
            return redirect(url_for("aircraft_list"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("aircraft_edit", aid=aid))
    ac = db.execute("SELECT * FROM Aircraft WHERE Aircraft_ID=?", (aid,)).fetchone()
    db.close()
    if not ac:
        flash("Aircraft not found.", "warning")
        return redirect(url_for("aircraft_list"))
    return render_template("aircraft_form.html", aircraft=ac)

@app.route("/aircraft/<int:aid>/delete", methods=["POST"])
def aircraft_delete(aid):
    db = get_db()
    try:
        db.execute("DELETE FROM Aircraft WHERE Aircraft_ID=?", (aid,))
        db.commit()
        flash("Aircraft deleted.", "success")
    except Exception as e:
        flash(f"Cannot delete: {e}", "danger")
    finally:
        db.close()
    return redirect(url_for("aircraft_list"))

# ═══════════════════════════  PASSENGERS  ══════════════════════════════════
@app.route("/passengers")
def passengers():
    db = get_db()
    search = request.args.get("search", "").strip()
    q = """
        SELECT p.*, GROUP_CONCAT(pp.Phone_Number, ', ') AS Phones
        FROM Passenger p
        LEFT JOIN Passenger_Phone pp ON p.Passenger_ID = pp.Passenger_ID
        WHERE 1=1
    """
    params = []
    if search:
        q += " AND (p.First_Name LIKE ? OR p.Last_Name LIKE ? OR p.Passport_No LIKE ? OR p.Email LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s])
    q += " GROUP BY p.Passenger_ID ORDER BY p.Last_Name, p.First_Name"
    rows = db.execute(q, params).fetchall()
    db.close()
    return render_template("passengers.html", passengers=rows, search=search)

@app.route("/passengers/add", methods=["GET", "POST"])
def passenger_add():
    if request.method == "POST":
        db = get_db()
        redirect_target = request.form.get("redirect_to", "passengers")
        pid_manual = request.form.get("passenger_id", "").strip()
        try:
            first_name = request.form["first_name"].strip()
            last_name = request.form["last_name"].strip()
            email = request.form.get("email", "").strip() or None
            passport = request.form.get("passport_no", "").strip() or None
            dob = request.form.get("dob", "").strip() or None
            gender = request.form.get("gender") or None
            addr = request.form.get("address", "").strip() or None

            if pid_manual:
                pid = int(pid_manual)
                db.execute(
                    """INSERT INTO Passenger
                       (Passenger_ID, First_Name, Last_Name, Email, Passport_No, Date_of_Birth, Gender, Address)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (pid, first_name, last_name, email, passport, dob, gender, addr)
                )
            else:
                cur = db.execute(
                    """INSERT INTO Passenger
                       (First_Name, Last_Name, Email, Passport_No, Date_of_Birth, Gender, Address)
                       VALUES (?,?,?,?,?,?,?)""",
                    (first_name, last_name, email, passport, dob, gender, addr)
                )
                pid = cur.lastrowid

            # Insert phone numbers (from dynamic list or single input)
            phones = request.form.getlist("phone_number")
            phone_types = request.form.getlist("phone_type")
            for ph, pt in zip(phones, phone_types):
                ph = ph.strip()
                if ph:
                    db.execute(
                        "INSERT INTO Passenger_Phone (Passenger_ID, Phone_Number, Phone_Type) VALUES (?,?,?)",
                        (pid, ph, pt or "Mobile"),
                    )
            manual_single_phone = request.form.get("single_phone_number", "").strip()
            if manual_single_phone:
                db.execute(
                    "INSERT INTO Passenger_Phone (Passenger_ID, Phone_Number, Phone_Type) VALUES (?,?,?)",
                    (pid, manual_single_phone, request.form.get("single_phone_type", "Mobile")),
                )
            db.commit()
            flash("Passenger registered successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="passengers"))
            return redirect(url_for("passengers"))
        except Exception as e:
            flash(f"Error registering passenger: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="passengers"))
    return render_template("passenger_form.html", passenger=None, phones=[])

@app.route("/passengers/<int:pid>")
def passenger_detail(pid):
    db = get_db()
    p = db.execute("SELECT * FROM Passenger WHERE Passenger_ID=?", (pid,)).fetchone()
    if not p:
        db.close()
        flash("Passenger not found.", "warning")
        return redirect(url_for("passengers"))
    phones = db.execute("SELECT * FROM Passenger_Phone WHERE Passenger_ID=?", (pid,)).fetchall()
    bookings = db.execute("""
        SELECT b.*, f.Flight_No, f.Source, f.Destination, fs.Date,
               fs.Departure_Time, fs.Arrival_Time
        FROM Booking b
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        WHERE b.Passenger_ID = ?
        ORDER BY fs.Date DESC
    """, (pid,)).fetchall()
    db.close()
    return render_template("passenger_detail.html", passenger=p, phones=phones, bookings=bookings)

@app.route("/passengers/<int:pid>/edit", methods=["GET", "POST"])
def passenger_edit(pid):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute("""
                UPDATE Passenger SET First_Name=?, Last_Name=?, Email=?,
                       Passport_No=?, Date_of_Birth=?, Gender=?, Address=?
                WHERE Passenger_ID=?
            """, (
                request.form["first_name"].strip(),
                request.form["last_name"].strip(),
                request.form.get("email", "").strip() or None,
                request.form.get("passport_no", "").strip() or None,
                request.form.get("dob", "").strip() or None,
                request.form.get("gender") or None,
                request.form.get("address", "").strip() or None,
                pid,
            ))
            # Replace phone numbers
            db.execute("DELETE FROM Passenger_Phone WHERE Passenger_ID=?", (pid,))
            phones = request.form.getlist("phone_number")
            phone_types = request.form.getlist("phone_type")
            for ph, pt in zip(phones, phone_types):
                ph = ph.strip()
                if ph:
                    db.execute(
                        "INSERT INTO Passenger_Phone (Passenger_ID, Phone_Number, Phone_Type) VALUES (?,?,?)",
                        (pid, ph, pt),
                    )
            db.commit()
            flash("Passenger updated!", "success")
            return redirect(url_for("passenger_detail", pid=pid))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("passenger_edit", pid=pid))
    p = db.execute("SELECT * FROM Passenger WHERE Passenger_ID=?", (pid,)).fetchone()
    phones = db.execute("SELECT * FROM Passenger_Phone WHERE Passenger_ID=?", (pid,)).fetchall()
    db.close()
    if not p:
        flash("Passenger not found.", "warning")
        return redirect(url_for("passengers"))
    return render_template("passenger_form.html", passenger=p, phones=phones)

@app.route("/passengers/<int:pid>/delete", methods=["POST"])
def passenger_delete(pid):
    db = get_db()
    db.execute("DELETE FROM Passenger WHERE Passenger_ID=?", (pid,))
    db.commit()
    db.close()
    flash("Passenger deleted.", "success")
    return redirect(url_for("passengers"))

# ═══════════════════════════  BOOKINGS  ════════════════════════════════════
@app.route("/bookings")
def bookings():
    db = get_db()
    status_filter = request.args.get("status", "").strip()
    q = """
        SELECT b.*, p.First_Name || ' ' || p.Last_Name AS Passenger,
               f.Flight_No, f.Source, f.Destination, fs.Date,
               fs.Departure_Time
        FROM Booking b
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        WHERE 1=1
    """
    params = []
    if status_filter:
        q += " AND b.Booking_Status = ?"
        params.append(status_filter)
    q += " ORDER BY b.Booking_Date DESC"
    rows = db.execute(q, params).fetchall()
    db.close()
    return render_template("bookings.html", bookings=rows, status=status_filter)

@app.route("/bookings/add", methods=["GET", "POST"])
def booking_add():
    db = get_db()
    if request.method == "POST":
        redirect_target = request.form.get("redirect_to", "bookings")
        bid_manual = request.form.get("booking_id", "").strip()
        pax_id = request.form.get("passenger_id_manual", "").strip() or request.form.get("passenger_id", "").strip()
        sched_id = request.form.get("schedule_id_manual", "").strip() or request.form.get("schedule_id", "").strip()
        seat_no = request.form.get("seat_no", "").strip() or None
        travel_class = request.form.get("class", "Economy")
        fare = float(request.form.get("fare", 0))
        status = request.form.get("booking_status", "Confirmed")
        try:
            if not pax_id or not sched_id:
                raise ValueError("Both Passenger ID and Flight Schedule ID are required.")
            if bid_manual:
                db.execute("""
                    INSERT INTO Booking (Booking_ID, Passenger_ID, Schedule_ID, Seat_No, Class, Fare, Booking_Status)
                    VALUES (?,?,?,?,?,?,?)
                """, (int(bid_manual), int(pax_id), int(sched_id), seat_no, travel_class, fare, status))
            else:
                db.execute("""
                    INSERT INTO Booking (Passenger_ID, Schedule_ID, Seat_No, Class, Fare, Booking_Status)
                    VALUES (?,?,?,?,?,?)
                """, (int(pax_id), int(sched_id), seat_no, travel_class, fare, status))
            db.commit()
            flash("Booking created successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="bookings"))
            return redirect(url_for("bookings"))
        except Exception as e:
            flash(f"Error creating booking: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="bookings"))
        return redirect(url_for("booking_add"))
    pax_list = db.execute("SELECT * FROM Passenger ORDER BY Last_Name").fetchall()
    sched_list = db.execute("""
        SELECT av.*, a.Model AS Aircraft_Model
        FROM Available_Seats av
        JOIN Flight_Schedule fs ON av.Schedule_ID = fs.Schedule_ID
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        WHERE av.Status != 'Cancelled' AND av.Seats_Available > 0
        ORDER BY av.Date, av.Departure_Time
    """).fetchall()
    db.close()
    return render_template("booking_form.html", booking=None,
                           passengers=pax_list, schedules=sched_list)

@app.route("/bookings/<int:bid>")
def booking_detail(bid):
    db = get_db()
    b = db.execute("""
        SELECT b.*, p.First_Name || ' ' || p.Last_Name AS Passenger, p.Passenger_ID AS PID,
               f.Flight_No, f.Source, f.Destination, fs.Date,
               fs.Departure_Time, fs.Arrival_Time, a.Model AS Aircraft_Model
        FROM Booking b
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        WHERE b.Booking_ID = ?
    """, (bid,)).fetchone()
    if not b:
        db.close()
        flash("Booking not found.", "warning")
        return redirect(url_for("bookings"))
    baggage = db.execute("SELECT * FROM Baggage WHERE Booking_ID=? ORDER BY Baggage_Seq_No", (bid,)).fetchall()
    audit = db.execute("SELECT * FROM Booking_Audit WHERE Booking_ID=? ORDER BY Changed_At DESC", (bid,)).fetchall()
    db.close()
    return render_template("booking_detail.html", booking=b, baggage=baggage, audit=audit)

@app.route("/bookings/<int:bid>/edit", methods=["GET", "POST"])
def booking_edit(bid):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute("""
                UPDATE Booking SET Seat_No=?, Class=?, Fare=?
                WHERE Booking_ID=? AND Booking_Status NOT IN ('Cancelled')
            """, (
                request.form.get("seat_no", "").strip() or None,
                request.form["class"],
                float(request.form["fare"]),
                bid,
            ))
            db.commit()
            flash("Booking updated!", "success")
            return redirect(url_for("booking_detail", bid=bid))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("booking_edit", bid=bid))
    booking = db.execute("""
        SELECT b.*, f.Flight_No, f.Source, f.Destination, fs.Date
        FROM Booking b
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        WHERE b.Booking_ID = ?
    """, (bid,)).fetchone()
    db.close()
    if not booking:
        flash("Booking not found.", "warning")
        return redirect(url_for("bookings"))
    return render_template("booking_edit.html", booking=booking)

@app.route("/bookings/<int:bid>/cancel", methods=["POST"])
def booking_cancel(bid):
    db = get_db()
    now = datetime.now().isoformat()
    db.execute("""
        UPDATE Booking SET Booking_Status='Cancelled',
               Cancellation_Date=?, Refund_Status='Pending'
        WHERE Booking_ID=? AND Booking_Status NOT IN ('Cancelled')
    """, (now, bid))
    db.commit()
    db.close()
    flash("Booking cancelled. Refund is pending.", "success")
    return redirect(url_for("booking_detail", bid=bid))

# ═══════════════════════════  BAGGAGE  ═════════════════════════════════════
@app.route("/baggage")
def baggage_list():
    db = get_db()
    tag_search = request.args.get("tag", "").strip()
    type_filter = request.args.get("type", "").strip()
    booking_id = request.args.get("booking_id", "").strip()
    q = """
        SELECT bg.*, b.Seat_No, b.Class, b.Booking_Status,
               p.Passenger_ID, p.First_Name || ' ' || p.Last_Name AS Passenger_Name,
               fs.Flight_No, fs.Date, fs.Departure_Time
        FROM Baggage bg
        JOIN Booking b ON bg.Booking_ID = b.Booking_ID
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        WHERE 1=1
    """
    params = []
    if tag_search:
        q += " AND bg.Tag_No LIKE ?"
        params.append(f"%{tag_search}%")
    if type_filter:
        q += " AND bg.Type = ?"
        params.append(type_filter)
    if booking_id:
        q += " AND bg.Booking_ID = ?"
        params.append(booking_id)
    q += " ORDER BY bg.Booking_ID DESC, bg.Baggage_Seq_No ASC"
    rows = db.execute(q, params).fetchall()
    active_bookings = db.execute("""
        SELECT b.Booking_ID, p.First_Name || ' ' || p.Last_Name AS Passenger,
               fs.Flight_No, fs.Date
        FROM Booking b
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        WHERE b.Booking_Status != 'Cancelled'
        ORDER BY b.Booking_ID DESC
    """).fetchall()
    db.close()
    return render_template("baggage.html", baggage=rows, bookings=active_bookings,
                           tag=tag_search, type=type_filter, booking_id=booking_id)

@app.route("/baggage/add", methods=["GET", "POST"])
def baggage_add_standalone():
    db = get_db()
    if request.method == "POST":
        redirect_target = request.form.get("redirect_to", "baggage_list")
        booking_id = request.form.get("booking_id_manual", "").strip() or request.form.get("booking_id", "").strip()
        seq_manual = request.form.get("baggage_seq_no", "").strip()
        tag_no = request.form.get("tag_no", "").strip()
        weight = request.form.get("weight", "").strip()
        bg_type = request.form.get("type", "Checked")
        try:
            if not booking_id or not tag_no or not weight:
                raise ValueError("Booking ID, Tag Number, and Weight are required.")
            bid = int(booking_id)
            if seq_manual:
                seq_no = int(seq_manual)
            else:
                row = db.execute(
                    "SELECT COALESCE(MAX(Baggage_Seq_No),0)+1 AS next_seq FROM Baggage WHERE Booking_ID=?",
                    (bid,)
                ).fetchone()
                seq_no = row["next_seq"]
            db.execute("""
                INSERT INTO Baggage (Booking_ID, Baggage_Seq_No, Weight, Tag_No, Type)
                VALUES (?,?,?,?,?)
            """, (bid, seq_no, float(weight), tag_no, bg_type))
            db.commit()
            flash("Baggage record added successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="baggage"))
            return redirect(url_for("baggage_list"))
        except Exception as e:
            flash(f"Error adding baggage: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="baggage"))
        return redirect(url_for("baggage_add_standalone"))
    active_bookings = db.execute("""
        SELECT b.Booking_ID, p.First_Name || ' ' || p.Last_Name AS Passenger,
               fs.Flight_No, fs.Date, b.Class
        FROM Booking b
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        WHERE b.Booking_Status != 'Cancelled'
        ORDER BY b.Booking_ID DESC
    """).fetchall()
    db.close()
    return render_template("baggage_standalone_form.html", bookings=active_bookings)

@app.route("/bookings/<int:bid>/baggage/add", methods=["GET", "POST"])
def baggage_add(bid):
    db = get_db()
    if request.method == "POST":
        try:
            # Get next sequence number
            seq_manual = request.form.get("baggage_seq_no", "").strip()
            if seq_manual:
                next_seq = int(seq_manual)
            else:
                row = db.execute(
                    "SELECT COALESCE(MAX(Baggage_Seq_No),0)+1 AS next_seq FROM Baggage WHERE Booking_ID=?",
                    (bid,)
                ).fetchone()
                next_seq = row["next_seq"]
            db.execute("""
                INSERT INTO Baggage (Booking_ID, Baggage_Seq_No, Weight, Tag_No, Type)
                VALUES (?,?,?,?,?)
            """, (
                bid, next_seq,
                float(request.form["weight"]),
                request.form["tag_no"].strip(),
                request.form.get("type", "Checked"),
            ))
            db.commit()
            flash("Baggage added!", "success")
            return redirect(url_for("booking_detail", bid=bid))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("baggage_add", bid=bid))
    booking = db.execute("SELECT * FROM Booking WHERE Booking_ID=?", (bid,)).fetchone()
    db.close()
    if not booking:
        flash("Booking not found.", "warning")
        return redirect(url_for("bookings"))
    return render_template("baggage_form.html", booking=booking)

@app.route("/baggage/<int:bid>/<int:seq>/delete", methods=["POST"])
def baggage_delete(bid, seq):
    db = get_db()
    db.execute("DELETE FROM Baggage WHERE Booking_ID=? AND Baggage_Seq_No=?", (bid, seq))
    db.commit()
    db.close()
    flash("Baggage removed.", "success")
    return redirect(url_for("booking_detail", bid=bid))

# ═══════════════════════════  CREW  ════════════════════════════════════════
@app.route("/crew")
def crew_list():
    db = get_db()
    rows = db.execute("SELECT * FROM Crew ORDER BY Role, Last_Name").fetchall()
    db.close()
    return render_template("crew.html", crew=rows)

@app.route("/crew/add", methods=["GET", "POST"])
def crew_add():
    if request.method == "POST":
        db = get_db()
        redirect_target = request.form.get("redirect_to", "crew_list")
        cid_manual = request.form.get("crew_id", "").strip()
        first_name = request.form["first_name"].strip()
        last_name = request.form["last_name"].strip()
        role = request.form["role"]
        license_no = request.form.get("license_no", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        status = request.form.get("status", "Active")
        try:
            if cid_manual:
                db.execute("""
                    INSERT INTO Crew (Crew_ID, First_Name, Last_Name, Role, License_No, Phone, Email, Status)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (int(cid_manual), first_name, last_name, role, license_no, phone, email, status))
            else:
                db.execute("""
                    INSERT INTO Crew (First_Name, Last_Name, Role, License_No, Phone, Email, Status)
                    VALUES (?,?,?,?,?,?,?)
                """, (first_name, last_name, role, license_no, phone, email, status))
            db.commit()
            flash("Crew member added successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="crew"))
            return redirect(url_for("crew_list"))
        except Exception as e:
            flash(f"Error adding crew member: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="crew"))
    return render_template("crew_form.html", crew_member=None)

@app.route("/crew/<int:cid>")
def crew_detail(cid):
    db = get_db()
    c = db.execute("SELECT * FROM Crew WHERE Crew_ID=?", (cid,)).fetchone()
    if not c:
        db.close()
        flash("Crew member not found.", "warning")
        return redirect(url_for("crew_list"))
    assignments = db.execute("""
        SELECT ca.Assignment_ID, fs.Schedule_ID, f.Flight_No, f.Source, f.Destination,
               fs.Date, fs.Departure_Time, fs.Arrival_Time
        FROM Crew_Assignment ca
        JOIN Flight_Schedule fs ON ca.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        WHERE ca.Crew_ID = ?
        ORDER BY fs.Date DESC
    """, (cid,)).fetchall()
    db.close()
    return render_template("crew_detail.html", crew_member=c, assignments=assignments)

@app.route("/crew/<int:cid>/edit", methods=["GET", "POST"])
def crew_edit(cid):
    db = get_db()
    if request.method == "POST":
        try:
            db.execute("""
                UPDATE Crew SET First_Name=?, Last_Name=?, Role=?,
                       License_No=?, Phone=?, Email=?, Status=?
                WHERE Crew_ID=?
            """, (
                request.form["first_name"].strip(),
                request.form["last_name"].strip(),
                request.form["role"],
                request.form.get("license_no", "").strip() or None,
                request.form.get("phone", "").strip() or None,
                request.form.get("email", "").strip() or None,
                request.form.get("status", "Active"),
                cid,
            ))
            db.commit()
            flash("Crew member updated!", "success")
            return redirect(url_for("crew_detail", cid=cid))
        except Exception as e:
            flash(f"Error: {e}", "danger")
        finally:
            db.close()
        return redirect(url_for("crew_edit", cid=cid))
    c = db.execute("SELECT * FROM Crew WHERE Crew_ID=?", (cid,)).fetchone()
    db.close()
    if not c:
        flash("Crew member not found.", "warning")
        return redirect(url_for("crew_list"))
    return render_template("crew_form.html", crew_member=c)

@app.route("/crew/<int:cid>/delete", methods=["POST"])
def crew_delete(cid):
    db = get_db()
    db.execute("DELETE FROM Crew WHERE Crew_ID=?", (cid,))
    db.commit()
    db.close()
    flash("Crew member deleted.", "success")
    return redirect(url_for("crew_list"))

# ═══════════════════════════  CREW ASSIGNMENTS  ════════════════════════════
@app.route("/assignments")
def assignments():
    db = get_db()
    rows = db.execute("""
        SELECT ca.Assignment_ID, c.Crew_ID,
               c.First_Name || ' ' || c.Last_Name AS Crew_Name, c.Role,
               f.Flight_No, f.Source, f.Destination, fs.Date,
               fs.Departure_Time, fs.Schedule_ID
        FROM Crew_Assignment ca
        JOIN Crew c ON ca.Crew_ID = c.Crew_ID
        JOIN Flight_Schedule fs ON ca.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        ORDER BY fs.Date, fs.Departure_Time
    """).fetchall()
    db.close()
    return render_template("assignments.html", assignments=rows)

@app.route("/assignments/add", methods=["GET", "POST"])
def assignment_add():
    db = get_db()
    if request.method == "POST":
        redirect_target = request.form.get("redirect_to", "assignments")
        aid_manual = request.form.get("assignment_id", "").strip()
        crew_id = request.form.get("crew_id_manual", "").strip() or request.form.get("crew_id", "").strip()
        schedule_id = request.form.get("schedule_id_manual", "").strip() or request.form.get("schedule_id", "").strip()
        try:
            if not crew_id or not schedule_id:
                raise ValueError("Both Crew ID and Schedule ID are required.")
            cid = int(crew_id)
            sid = int(schedule_id)
            # Check for overlap: same crew, same date, overlapping times
            new_sched = db.execute("SELECT * FROM Flight_Schedule WHERE Schedule_ID=?", (sid,)).fetchone()
            if new_sched:
                overlap = db.execute("""
                    SELECT 1 FROM Crew_Assignment ca
                    JOIN Flight_Schedule fs ON ca.Schedule_ID = fs.Schedule_ID
                    WHERE ca.Crew_ID = ? AND fs.Date = ?
                      AND fs.Departure_Time < ? AND fs.Arrival_Time > ?
                """, (cid, new_sched["Date"],
                      new_sched["Arrival_Time"], new_sched["Departure_Time"])).fetchone()
                if overlap:
                    flash("Overlap conflict (FR14): Crew member has an overlapping assignment on this date/time!", "danger")
                    db.close()
                    if redirect_target == "manual_entry":
                        return redirect(url_for("manual_entry", tab="assignments"))
                    return redirect(url_for("assignment_add"))
            if aid_manual:
                db.execute(
                    "INSERT INTO Crew_Assignment (Assignment_ID, Crew_ID, Schedule_ID) VALUES (?,?,?)",
                    (int(aid_manual), cid, sid),
                )
            else:
                db.execute(
                    "INSERT INTO Crew_Assignment (Crew_ID, Schedule_ID) VALUES (?,?)",
                    (cid, sid),
                )
            db.commit()
            flash("Crew assignment created successfully!", "success")
            if redirect_target == "manual_entry":
                return redirect(url_for("manual_entry", tab="assignments"))
            return redirect(url_for("assignments"))
        except Exception as e:
            flash(f"Error creating assignment: {e}", "danger")
        finally:
            db.close()
        if redirect_target == "manual_entry":
            return redirect(url_for("manual_entry", tab="assignments"))
        return redirect(url_for("assignment_add"))
    crew = db.execute("SELECT * FROM Crew WHERE Status='Active' ORDER BY Last_Name").fetchall()
    scheds = db.execute("""
        SELECT fs.Schedule_ID, f.Flight_No, f.Source, f.Destination, fs.Date,
               fs.Departure_Time
        FROM Flight_Schedule fs JOIN Flight f ON fs.Flight_No = f.Flight_No
        WHERE fs.Status != 'Cancelled'
        ORDER BY fs.Date, fs.Departure_Time
    """).fetchall()
    db.close()
    return render_template("assignment_form.html", crew=crew, schedules=scheds)

@app.route("/assignments/<int:aid>/delete", methods=["POST"])
def assignment_delete(aid):
    db = get_db()
    db.execute("DELETE FROM Crew_Assignment WHERE Assignment_ID=?", (aid,))
    db.commit()
    db.close()
    flash("Assignment removed.", "success")
    return redirect(url_for("assignments"))

# ═══════════════════════════  REPORTS  ═════════════════════════════════════
@app.route("/reports")
def reports():
    db = get_db()
    # Booking status breakdown
    status_counts = db.execute("""
        SELECT Booking_Status, COUNT(*) AS cnt FROM Booking GROUP BY Booking_Status
    """).fetchall()
    # Revenue by flight
    revenue = db.execute("""
        SELECT f.Flight_No, f.Source, f.Destination, SUM(b.Fare) AS Total_Revenue,
               COUNT(*) AS Booking_Count
        FROM Booking b
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON fs.Flight_No = f.Flight_No
        WHERE b.Booking_Status != 'Cancelled'
        GROUP BY f.Flight_No ORDER BY Total_Revenue DESC
    """).fetchall()
    # Recent audit log
    audit = db.execute("""
        SELECT ba.*, b.Seat_No, p.First_Name || ' ' || p.Last_Name AS Passenger
        FROM Booking_Audit ba
        LEFT JOIN Booking b ON ba.Booking_ID = b.Booking_ID
        LEFT JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        ORDER BY ba.Changed_At DESC LIMIT 30
    """).fetchall()
    # Class breakdown
    class_counts = db.execute("""
        SELECT Class, COUNT(*) AS cnt FROM Booking
        WHERE Booking_Status != 'Cancelled' GROUP BY Class
    """).fetchall()
    db.close()
    return render_template("reports.html", status_counts=status_counts,
                           revenue=revenue, audit=audit, class_counts=class_counts)

# ═══════════════════════════  JSON APIs  ═══════════════════════════════════
@app.route("/api/search_flights")
def api_search_flights():
    db = get_db()
    source = request.args.get("source", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()
    q = "SELECT * FROM Available_Seats WHERE Status != 'Cancelled'"
    params = []
    if source:
        q += " AND Source LIKE ?"
        params.append(f"%{source}%")
    if destination:
        q += " AND Destination LIKE ?"
        params.append(f"%{destination}%")
    if date:
        q += " AND Date = ?"
        params.append(date)
    q += " ORDER BY Date, Departure_Time"
    rows = db.execute(q, params).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/available_seats/<int:schedule_id>")
def api_available_seats(schedule_id):
    db = get_db()
    row = db.execute("SELECT * FROM Available_Seats WHERE Schedule_ID=?", (schedule_id,)).fetchone()
    db.close()
    if row:
        return jsonify(dict(row))
    return jsonify({"error": "Schedule not found"}), 404


# ═══════════════════════════  INDIAN AIRPORTS METADATA  ════════════════════
INDIAN_AIRPORTS = {
    "DEL": {"code": "DEL", "city": "Delhi", "name": "Indira Gandhi International Airport", "lat": 28.5562, "lng": 77.1000, "hub": True},
    "BOM": {"code": "BOM", "city": "Mumbai", "name": "Chhatrapati Shivaji Maharaj International Airport", "lat": 19.0896, "lng": 72.8656, "hub": True},
    "BLR": {"code": "BLR", "city": "Bengaluru", "name": "Kempegowda International Airport", "lat": 13.1986, "lng": 77.7066, "hub": True},
    "MAA": {"code": "MAA", "city": "Chennai", "name": "Chennai International Airport", "lat": 12.9941, "lng": 80.1709, "hub": True},
    "HYD": {"code": "HYD", "city": "Hyderabad", "name": "Rajiv Gandhi International Airport", "lat": 17.2403, "lng": 78.4294, "hub": True},
    "CCU": {"code": "CCU", "city": "Kolkata", "name": "Netaji Subhash Chandra Bose International Airport", "lat": 22.6547, "lng": 88.4467, "hub": True},
    "GOI": {"code": "GOI", "city": "Goa", "name": "Dabolim / Manohar International Airport", "lat": 15.3800, "lng": 73.8314, "hub": False},
    "JAI": {"code": "JAI", "city": "Jaipur", "name": "Jaipur International Airport", "lat": 26.8242, "lng": 75.8122, "hub": False},
    "PNQ": {"code": "PNQ", "city": "Pune", "name": "Pune International Airport", "lat": 18.5821, "lng": 73.9197, "hub": False},
    "AMD": {"code": "AMD", "city": "Ahmedabad", "name": "Sardar Vallabhbhai Patel International Airport", "lat": 23.0734, "lng": 72.6347, "hub": False},
    "COK": {"code": "COK", "city": "Kochi", "name": "Cochin International Airport", "lat": 10.1518, "lng": 76.3930, "hub": False},
    "GAU": {"code": "GAU", "city": "Guwahati", "name": "Lokpriya Gopinath Bordoloi International Airport", "lat": 26.1061, "lng": 91.5859, "hub": False},
    "LKO": {"code": "LKO", "city": "Lucknow", "name": "Chaudhary Charan Singh International Airport", "lat": 26.7606, "lng": 80.8893, "hub": False},
    "IXC": {"code": "IXC", "city": "Chandigarh", "name": "Shaheed Bhagat Singh International Airport", "lat": 30.6735, "lng": 76.7885, "hub": False},
    "TRV": {"code": "TRV", "city": "Trivandrum", "name": "Thiruvananthapuram International Airport", "lat": 8.4821, "lng": 76.9200, "hub": False},
    "BBI": {"code": "BBI", "city": "Bhubaneswar", "name": "Biju Patnaik International Airport", "lat": 20.2444, "lng": 85.8178, "hub": False},
    "PAT": {"code": "PAT", "city": "Patna", "name": "Jayprakash Narayan International Airport", "lat": 25.5913, "lng": 85.0880, "hub": False},
    "SXR": {"code": "SXR", "city": "Srinagar", "name": "Sheikh ul-Alam International Airport", "lat": 33.9871, "lng": 74.7741, "hub": False},
    "VNS": {"code": "VNS", "city": "Varanasi", "name": "Lal Bahadur Shastri International Airport", "lat": 25.4524, "lng": 82.8593, "hub": False},
    "ATQ": {"code": "ATQ", "city": "Amritsar", "name": "Sri Guru Ram Dass Jee International Airport", "lat": 31.7096, "lng": 74.7973, "hub": False}
}


# ═══════════════════════════  BOOK FLIGHT SEARCH & BOOKING  ════════════════
@app.route("/book-flight")
def book_flight():
    source = request.args.get("source", "").strip().upper()
    destination = request.args.get("destination", "").strip().upper()
    date = request.args.get("date", "").strip()
    travel_class = request.args.get("class", "Economy").strip()

    db = get_db()
    # Distinct airports from DB
    db_sources = [r["Source"] for r in db.execute("SELECT DISTINCT Source FROM Flight ORDER BY Source").fetchall()]
    db_dests = [r["Destination"] for r in db.execute("SELECT DISTINCT Destination FROM Flight ORDER BY Destination").fetchall()]
    all_codes = sorted(list(set(db_sources + db_dests + list(INDIAN_AIRPORTS.keys()))))
    airports_list = []
    for code in all_codes:
        meta = INDIAN_AIRPORTS.get(code, {"city": code, "name": f"{code} Airport"})
        airports_list.append({"code": code, "city": meta["city"], "name": meta["name"]})

    # Passengers for quick select
    passengers = db.execute("SELECT Passenger_ID, First_Name, Last_Name, Passport_No, Email FROM Passenger ORDER BY First_Name").fetchall()

    # Query available flights
    q = """
        SELECT av.*, fs.Gate, a.Model AS Aircraft_Model,
               a.Economy_Seats, a.Business_Seats, a.First_Class_Seats,
               f.Airline
        FROM Available_Seats av
        JOIN Flight_Schedule fs ON av.Schedule_ID = fs.Schedule_ID
        JOIN Flight f ON av.Flight_No = f.Flight_No
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        WHERE av.Status != 'Cancelled' AND av.Seats_Available > 0
    """
    params = []
    if source:
        q += " AND av.Source = ?"
        params.append(source)
    if destination:
        q += " AND av.Destination = ?"
        params.append(destination)
    if date:
        q += " AND av.Date = ?"
        params.append(date)

    q += " ORDER BY av.Date, av.Departure_Time"
    matching_flights = [dict(r) for r in db.execute(q, params).fetchall()]

    # If date was specified but no direct date match, find alternative upcoming dates for this route
    alternative_flights = []
    if date and len(matching_flights) == 0 and source and destination:
        alt_q = """
            SELECT av.*, fs.Gate, a.Model AS Aircraft_Model,
                   f.Airline
            FROM Available_Seats av
            JOIN Flight_Schedule fs ON av.Schedule_ID = fs.Schedule_ID
            JOIN Flight f ON av.Flight_No = f.Flight_No
            JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
            WHERE av.Status != 'Cancelled' AND av.Seats_Available > 0
              AND av.Source = ? AND av.Destination = ?
            ORDER BY av.Date, av.Departure_Time
            LIMIT 5
        """
        alternative_flights = [dict(r) for r in db.execute(alt_q, (source, destination)).fetchall()]

    db.close()
    return render_template("book_flight.html",
                           source=source, destination=destination, date=date,
                           travel_class=travel_class,
                           airports=airports_list,
                           passengers=passengers,
                           flights=matching_flights,
                           alternative_flights=alternative_flights)


@app.route("/book-flight/confirm", methods=["POST"])
def book_flight_confirm():
    db = get_db()
    try:
        schedule_id = int(request.form.get("schedule_id"))
        pax_choice = request.form.get("pax_choice", "existing")
        travel_class = request.form.get("class", "Economy")
        fare = float(request.form.get("fare", 4999.0))
        seat_no = request.form.get("seat_no", "").strip().upper()
        
        # Determine passenger ID
        if pax_choice == "new":
            fname = request.form.get("first_name", "").strip()
            lname = request.form.get("last_name", "").strip()
            email = request.form.get("email", "").strip()
            passport = request.form.get("passport_no", "").strip().upper()
            phone = request.form.get("phone_number", "").strip()
            phone_type = request.form.get("phone_type", "Mobile")
            if not fname or not lname or not passport:
                raise ValueError("First Name, Last Name, and Passport Number are required for passenger registration.")
            
            cur = db.cursor()
            cur.execute("INSERT INTO Passenger (First_Name, Last_Name, Email, Passport_No) VALUES (?, ?, ?, ?)",
                        (fname, lname, email, passport))
            passenger_id = cur.lastrowid
            if phone:
                cur.execute("INSERT INTO Passenger_Phone (Passenger_ID, Phone_Number, Phone_Type) VALUES (?, ?, ?)",
                            (passenger_id, phone, phone_type))
        else:
            passenger_id = int(request.form.get("passenger_id"))

        # If seat number is empty, auto-assign next available seat
        if not seat_no:
            taken_seats = [r["Seat_No"] for r in db.execute(
                "SELECT Seat_No FROM Booking WHERE Schedule_ID = ? AND Booking_Status != 'Cancelled' AND Seat_No IS NOT NULL",
                (schedule_id,)
            ).fetchall()]
            for row_idx in range(1, 35):
                for col in ['A', 'B', 'C', 'D', 'E', 'F']:
                    cand = f"{row_idx}{col}"
                    if cand not in taken_seats:
                        seat_no = cand
                        break
                if seat_no:
                    break
        
        # Insert Booking (trigger prevent_seat_double_booking validates seat conflict!)
        cur = db.cursor()
        cur.execute("""
            INSERT INTO Booking (Passenger_ID, Schedule_ID, Seat_No, Class, Fare, Booking_Status)
            VALUES (?, ?, ?, ?, ?, 'Confirmed')
        """, (passenger_id, schedule_id, seat_no, travel_class, fare))
        booking_id = cur.lastrowid

        # Optional baggage check-in during booking
        baggage_weight = request.form.get("baggage_weight", "").strip()
        if baggage_weight:
            weight = float(baggage_weight)
            baggage_type = request.form.get("baggage_type", "Checked").strip()
            if baggage_type not in ["Checked", "Cabin", "Special"]:
                baggage_type = "Checked"
            tag_no = f"BG-{booking_id}-01"
            cur.execute("""
                INSERT INTO Baggage (Booking_ID, Baggage_Seq_No, Tag_No, Weight, Type)
                VALUES (?, 1, ?, ?, ?)
            """, (booking_id, tag_no, weight, baggage_type))

        db.commit()
        flash(f"🎉 Reservation Successful! Ticket #{booking_id} issued for Seat {seat_no} ({travel_class}).", "success")
        return redirect(url_for("booking_detail", bid=booking_id))
    except Exception as e:
        db.rollback()
        flash(f"Booking Error: {e}", "danger")
        return redirect(url_for("book_flight",
                                source=request.form.get("source", ""),
                                destination=request.form.get("destination", ""),
                                date=request.form.get("date", "")))
    finally:
        db.close()


# ═══════════════════════════  INDIA FLIGHT MAP  ════════════════════════════
@app.route("/flight-map")
def flight_map():
    db = get_db()
    flights_data = db.execute("""
        SELECT f.Flight_No, f.Airline, f.Source, f.Destination,
               fs.Schedule_ID, fs.Date, fs.Departure_Time, fs.Arrival_Time, fs.Status, fs.Gate,
               a.Model AS Aircraft_Model, a.Total_Capacity,
               av.Seats_Available
        FROM Flight f
        JOIN Flight_Schedule fs ON f.Flight_No = fs.Flight_No
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        JOIN Available_Seats av ON fs.Schedule_ID = av.Schedule_ID
        WHERE fs.Status != 'Cancelled'
        ORDER BY f.Flight_No, fs.Date
    """).fetchall()
    db.close()
    return render_template("flight_map.html", flights=[dict(r) for r in flights_data], airports=INDIAN_AIRPORTS)


@app.route("/api/flight_map_data")
def api_flight_map_data():
    db = get_db()
    flights = db.execute("""
        SELECT f.Flight_No, f.Airline, f.Source, f.Destination,
               fs.Schedule_ID, fs.Date, fs.Departure_Time, fs.Arrival_Time, fs.Status, fs.Gate,
               a.Model AS Aircraft_Model, a.Total_Capacity,
               av.Seats_Available
        FROM Flight f
        JOIN Flight_Schedule fs ON f.Flight_No = fs.Flight_No
        JOIN Aircraft a ON fs.Aircraft_ID = a.Aircraft_ID
        JOIN Available_Seats av ON fs.Schedule_ID = av.Schedule_ID
        WHERE fs.Status != 'Cancelled'
    """).fetchall()
    
    airport_stats = {}
    for code, meta in INDIAN_AIRPORTS.items():
        airport_stats[code] = {
            "code": code,
            "city": meta["city"],
            "name": meta["name"],
            "lat": meta["lat"],
            "lng": meta["lng"],
            "hub": meta["hub"],
            "departures": 0,
            "arrivals": 0
        }
    
    routes_list = []
    for f in flights:
        src = f["Source"]
        dst = f["Destination"]
        if src in airport_stats:
            airport_stats[src]["departures"] += 1
        if dst in airport_stats:
            airport_stats[dst]["arrivals"] += 1
        
        src_coords = [airport_stats[src]["lat"], airport_stats[src]["lng"]] if src in airport_stats else None
        dst_coords = [airport_stats[dst]["lat"], airport_stats[dst]["lng"]] if dst in airport_stats else None
        
        routes_list.append({
            "flight_no": f["Flight_No"],
            "airline": f["Airline"],
            "source": src,
            "destination": dst,
            "source_coords": src_coords,
            "dest_coords": dst_coords,
            "schedule_id": f["Schedule_ID"],
            "date": f["Date"],
            "departure_time": f["Departure_Time"],
            "arrival_time": f["Arrival_Time"],
            "aircraft": f["Aircraft_Model"],
            "seats_available": f["Seats_Available"],
            "total_capacity": f["Total_Capacity"],
            "status": f["Status"],
            "gate": f["Gate"]
        })

    db.close()
    return jsonify({
        "airports": airport_stats,
        "routes": routes_list,
        "total_active_flights": len(routes_list),
        "total_airports": len(airport_stats)
    })


# ═══════════════════════════  PROJECT GUIDE & ARCHITECTURE DOCS  ════════════
@app.route("/project-guide")
def project_guide():
    return render_template("project_guide.html")



# ═══════════════════════════  MANUAL DATA INPUT CONSOLE  ═══════════════════
@app.route("/manual-entry")
def manual_entry():
    tab = request.args.get("tab", "flights")
    db = get_db()
    flights = db.execute("SELECT Flight_No, Airline, Source, Destination FROM Flight ORDER BY Flight_No").fetchall()
    aircraft = db.execute("SELECT Aircraft_ID, Registration_No, Model, Total_Capacity FROM Aircraft ORDER BY Aircraft_ID").fetchall()
    passengers = db.execute("SELECT Passenger_ID, First_Name, Last_Name, Passport_No FROM Passenger ORDER BY Passenger_ID").fetchall()
    schedules = db.execute("""
        SELECT fs.Schedule_ID, fs.Flight_No, fs.Date, fs.Departure_Time, f.Source, f.Destination
        FROM Flight_Schedule fs JOIN Flight f ON fs.Flight_No = f.Flight_No
        ORDER BY fs.Date DESC, fs.Departure_Time
    """).fetchall()
    bookings = db.execute("""
        SELECT b.Booking_ID, p.First_Name || ' ' || p.Last_Name AS Passenger,
               fs.Flight_No, fs.Date, b.Class
        FROM Booking b
        JOIN Passenger p ON b.Passenger_ID = p.Passenger_ID
        JOIN Flight_Schedule fs ON b.Schedule_ID = fs.Schedule_ID
        WHERE b.Booking_Status != 'Cancelled'
        ORDER BY b.Booking_ID DESC LIMIT 30
    """).fetchall()
    crew = db.execute("SELECT Crew_ID, First_Name, Last_Name, Role FROM Crew ORDER BY Crew_ID").fetchall()
    counts = {
        "flights": len(flights),
        "schedules": len(schedules),
        "aircraft": len(aircraft),
        "passengers": len(passengers),
        "bookings": db.execute("SELECT COUNT(*) c FROM Booking").fetchone()["c"],
        "baggage": db.execute("SELECT COUNT(*) c FROM Baggage").fetchone()["c"],
        "crew": len(crew),
        "assignments": db.execute("SELECT COUNT(*) c FROM Crew_Assignment").fetchone()["c"],
    }
    db.close()
    return render_template("manual_entry.html", current_tab=tab,
                           flights=flights, aircraft=aircraft, passengers=passengers,
                           schedules=schedules, bookings=bookings, crew=crew, counts=counts)

@app.route("/manual-entry/raw-sql", methods=["POST"])
def manual_entry_sql():
    sql = request.form.get("sql_query", "").strip()
    if not sql:
        flash("Please enter a SQL query", "warning")
        return redirect(url_for("manual_entry", tab="sql"))
    
    # Security restrictions: Prevent administrative/destructive server operations
    prohibited_ops = ["DROP DATABASE", "CREATE USER", "ALTER USER", "DROP USER", "GRANT", "REVOKE", "SHUTDOWN"]
    sql_upper = sql.upper()
    for op in prohibited_ops:
        if op in sql_upper:
            flash(f"Security Alert: Operation '{op}' is restricted in the web console.", "danger")
            return redirect(url_for("manual_entry", tab="sql"))

    db = get_db()
    try:
        cur = db.cursor()
        statements = [s.strip() for s in sql.split(";") if s.strip()]
        result_rows = []
        headers = []
        is_select = False
        
        for stmt in statements:
            stmt_upper = stmt.upper()
            if (stmt_upper.startswith("SELECT") or stmt_upper.startswith("SHOW") or 
                stmt_upper.startswith("DESCRIBE") or stmt_upper.startswith("EXPLAIN") or 
                stmt_upper.startswith("PRAGMA")):
                res = cur.execute(stmt)
                if cur.description:
                    headers = [d[0] for d in cur.description]
                    raw_rows = res.fetchall()
                    result_rows = [list(r.values()) if isinstance(r, dict) else list(r) for r in raw_rows]
                is_select = True
            else:
                cur.execute(stmt)
        
        db.commit()
        if is_select:
            flash(f"SQL executed successfully! Returned {len(result_rows)} row(s).", "success")
            db.close()
            return render_template("manual_sql_result.html", sql=sql, headers=headers, rows=result_rows)
        else:
            flash("SQL statement(s) executed and committed successfully!", "success")
    except Exception as e:
        db.rollback()
        flash(f"SQL Execution Error: {e}", "danger")
    finally:
        db.close()
    return redirect(url_for("manual_entry", tab="sql"))

@app.route("/manual-entry/bulk-json", methods=["POST"])
def manual_entry_bulk_json():
    table = request.form.get("table_name", "").strip()
    json_data = request.form.get("json_content", "").strip()
    try:
        data = json.loads(json_data)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or len(data) == 0:
            raise ValueError("Expected a JSON array of objects or a single JSON object")
        
        valid_tables = ["Flight", "Flight_Schedule", "Aircraft", "Passenger", "Passenger_Phone", "Booking", "Baggage", "Crew", "Crew_Assignment"]
        matched_table = next((t for t in valid_tables if t.lower() == table.lower()), None)
        if not matched_table:
            raise ValueError(f"Invalid table '{table}'. Must be one of: {', '.join(valid_tables)}")
        
        db = get_db()
        inserted_count = 0
        for item in data:
            cols = list(item.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            col_names = ", ".join(cols)
            vals = [item[c] for c in cols]
            db.execute(f"INSERT INTO {matched_table} ({col_names}) VALUES ({placeholders})", vals)
            inserted_count += 1
        db.commit()
        db.close()
        flash(f"Successfully inserted {inserted_count} record(s) into {matched_table}!", "success")
    except Exception as e:
        flash(f"Bulk JSON Import Error: {e}", "danger")
    return redirect(url_for("manual_entry", tab="bulk"))

# ═══════════════════════════  RUN  ═════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="127.0.0.1", port=port)

