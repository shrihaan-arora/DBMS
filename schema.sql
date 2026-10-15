-- SkyReserve MySQL Database Schema
-- Compatible with MySQL 8.0+

SET FOREIGN_KEY_CHECKS = 0;

DROP VIEW IF EXISTS Available_Seats;
DROP TRIGGER IF EXISTS booking_after_insert;
DROP TRIGGER IF EXISTS booking_after_update;
DROP TRIGGER IF EXISTS prevent_seat_double_booking;
DROP TRIGGER IF EXISTS prevent_seat_double_booking_update;

DROP TABLE IF EXISTS Booking_Audit;
DROP TABLE IF EXISTS Baggage;
DROP TABLE IF EXISTS Booking;
DROP TABLE IF EXISTS Crew_Assignment;
DROP TABLE IF EXISTS Crew;
DROP TABLE IF EXISTS Passenger_Phone;
DROP TABLE IF EXISTS Passenger;
DROP TABLE IF EXISTS Flight_Schedule;
DROP TABLE IF EXISTS Flight;
DROP TABLE IF EXISTS Aircraft;

SET FOREIGN_KEY_CHECKS = 1;

-- 1. Aircraft Table
CREATE TABLE Aircraft (
    Aircraft_ID INT NOT NULL AUTO_INCREMENT,
    Registration_No VARCHAR(50) NOT NULL,
    Model VARCHAR(100) NOT NULL,
    Total_Capacity INT NOT NULL,
    Economy_Seats INT NOT NULL DEFAULT 0,
    Business_Seats INT NOT NULL DEFAULT 0,
    First_Class_Seats INT NOT NULL DEFAULT 0,
    Status VARCHAR(20) DEFAULT 'Active',
    PRIMARY KEY (Aircraft_ID),
    UNIQUE KEY uq_aircraft_reg (Registration_No),
    CONSTRAINT chk_aircraft_capacity CHECK (Total_Capacity > 0),
    CONSTRAINT chk_aircraft_status CHECK (Status IN ('Active', 'Maintenance', 'Retired'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Flight Table
CREATE TABLE Flight (
    Flight_No VARCHAR(20) NOT NULL,
    Airline VARCHAR(100) NOT NULL,
    Source VARCHAR(100) NOT NULL,
    Destination VARCHAR(100) NOT NULL,
    PRIMARY KEY (Flight_No),
    CONSTRAINT chk_flight_route CHECK (Source != Destination)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Flight_Schedule Table
CREATE TABLE Flight_Schedule (
    Schedule_ID INT NOT NULL AUTO_INCREMENT,
    Flight_No VARCHAR(20) NOT NULL,
    Aircraft_ID INT NOT NULL,
    Departure_Time VARCHAR(30) NOT NULL,
    Arrival_Time VARCHAR(30) NOT NULL,
    Date VARCHAR(20) NOT NULL,
    Status VARCHAR(20) DEFAULT 'Scheduled',
    Gate VARCHAR(20),
    PRIMARY KEY (Schedule_ID),
    UNIQUE KEY uq_schedule_slot (Aircraft_ID, Date, Departure_Time),
    CONSTRAINT chk_schedule_status CHECK (Status IN ('Scheduled', 'On-Time', 'Delayed', 'Cancelled', 'Completed')),
    CONSTRAINT fk_schedule_flight FOREIGN KEY (Flight_No) REFERENCES Flight(Flight_No) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_schedule_aircraft FOREIGN KEY (Aircraft_ID) REFERENCES Aircraft(Aircraft_ID) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Passenger Table
CREATE TABLE Passenger (
    Passenger_ID INT NOT NULL AUTO_INCREMENT,
    First_Name VARCHAR(100) NOT NULL,
    Last_Name VARCHAR(100) NOT NULL,
    Email VARCHAR(255),
    Passport_No VARCHAR(50),
    Date_of_Birth VARCHAR(20),
    Gender VARCHAR(20),
    Address TEXT,
    Created_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (Passenger_ID),
    UNIQUE KEY uq_passenger_email (Email),
    UNIQUE KEY uq_passenger_passport (Passport_No),
    CONSTRAINT chk_passenger_gender CHECK (Gender IN ('Male', 'Female', 'Other') OR Gender IS NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Passenger_Phone Table (Multivalued Attribute / 1NF)
CREATE TABLE Passenger_Phone (
    Phone_ID INT NOT NULL AUTO_INCREMENT,
    Passenger_ID INT NOT NULL,
    Phone_Number VARCHAR(50) NOT NULL,
    Phone_Type VARCHAR(20) DEFAULT 'Mobile',
    PRIMARY KEY (Phone_ID),
    UNIQUE KEY uq_passenger_phone (Passenger_ID, Phone_Number),
    CONSTRAINT chk_phone_type CHECK (Phone_Type IN ('Mobile', 'Home', 'Work')),
    CONSTRAINT fk_phone_passenger FOREIGN KEY (Passenger_ID) REFERENCES Passenger(Passenger_ID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Booking Table
CREATE TABLE Booking (
    Booking_ID INT NOT NULL AUTO_INCREMENT,
    Passenger_ID INT NOT NULL,
    Schedule_ID INT NOT NULL,
    Seat_No VARCHAR(20),
    Class VARCHAR(20) NOT NULL,
    Fare DECIMAL(10, 2) NOT NULL,
    Booking_Status VARCHAR(20) DEFAULT 'Confirmed',
    Booking_Date DATETIME DEFAULT CURRENT_TIMESTAMP,
    Cancellation_Date VARCHAR(50),
    Refund_Status VARCHAR(20),
    PRIMARY KEY (Booking_ID),
    CONSTRAINT chk_booking_class CHECK (Class IN ('Economy', 'Business', 'First')),
    CONSTRAINT chk_booking_fare CHECK (Fare >= 0),
    CONSTRAINT chk_booking_status CHECK (Booking_Status IN ('Confirmed', 'Cancelled', 'Checked-In', 'Completed')),
    CONSTRAINT chk_booking_refund CHECK (Refund_Status IN ('Pending', 'Processed', 'Denied') OR Refund_Status IS NULL),
    CONSTRAINT fk_booking_passenger FOREIGN KEY (Passenger_ID) REFERENCES Passenger(Passenger_ID) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_booking_schedule FOREIGN KEY (Schedule_ID) REFERENCES Flight_Schedule(Schedule_ID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Baggage Table (Weak Entity identified by Booking_ID and Baggage_Seq_No)
CREATE TABLE Baggage (
    Booking_ID INT NOT NULL,
    Baggage_Seq_No INT NOT NULL,
    Weight DECIMAL(6, 2) NOT NULL,
    Tag_No VARCHAR(50) NOT NULL,
    Type VARCHAR(20) DEFAULT 'Checked',
    PRIMARY KEY (Booking_ID, Baggage_Seq_No),
    UNIQUE KEY uq_baggage_tag (Tag_No),
    CONSTRAINT chk_baggage_weight CHECK (Weight > 0),
    CONSTRAINT chk_baggage_type CHECK (Type IN ('Checked', 'Cabin', 'Special')),
    CONSTRAINT fk_baggage_booking FOREIGN KEY (Booking_ID) REFERENCES Booking(Booking_ID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Crew Table
CREATE TABLE Crew (
    Crew_ID INT NOT NULL AUTO_INCREMENT,
    First_Name VARCHAR(100) NOT NULL,
    Last_Name VARCHAR(100) NOT NULL,
    Role VARCHAR(50) NOT NULL,
    License_No VARCHAR(50),
    Phone VARCHAR(50),
    Email VARCHAR(255),
    Status VARCHAR(20) DEFAULT 'Active',
    PRIMARY KEY (Crew_ID),
    UNIQUE KEY uq_crew_license (License_No),
    UNIQUE KEY uq_crew_email (Email),
    CONSTRAINT chk_crew_role CHECK (Role IN ('Captain', 'First Officer', 'Flight Engineer', 'Cabin Crew Lead', 'Cabin Crew')),
    CONSTRAINT chk_crew_status CHECK (Status IN ('Active', 'On Leave', 'Retired'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Crew_Assignment Table (M:N Relationship between Crew and Flight_Schedule)
CREATE TABLE Crew_Assignment (
    Assignment_ID INT NOT NULL AUTO_INCREMENT,
    Crew_ID INT NOT NULL,
    Schedule_ID INT NOT NULL,
    PRIMARY KEY (Assignment_ID),
    UNIQUE KEY uq_crew_schedule (Crew_ID, Schedule_ID),
    CONSTRAINT fk_assignment_crew FOREIGN KEY (Crew_ID) REFERENCES Crew(Crew_ID) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_assignment_schedule FOREIGN KEY (Schedule_ID) REFERENCES Flight_Schedule(Schedule_ID) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Booking_Audit Table
CREATE TABLE Booking_Audit (
    Audit_ID INT NOT NULL AUTO_INCREMENT,
    Booking_ID INT,
    Action VARCHAR(50) NOT NULL,
    Old_Values TEXT,
    New_Values TEXT,
    Changed_At DATETIME DEFAULT CURRENT_TIMESTAMP,
    Changed_By VARCHAR(100) DEFAULT 'system',
    PRIMARY KEY (Audit_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Available_Seats View
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

-- 12. Triggers
DELIMITER //

CREATE TRIGGER booking_after_insert
AFTER INSERT ON Booking
FOR EACH ROW
BEGIN
    INSERT INTO Booking_Audit (Booking_ID, Action, New_Values)
    VALUES (
        NEW.Booking_ID,
        'CREATED',
        JSON_OBJECT(
            'Passenger_ID', NEW.Passenger_ID,
            'Schedule_ID', NEW.Schedule_ID,
            'Seat_No', NEW.Seat_No,
            'Class', NEW.Class,
            'Fare', NEW.Fare,
            'Booking_Status', NEW.Booking_Status
        )
    );
END//

CREATE TRIGGER booking_after_update
AFTER UPDATE ON Booking
FOR EACH ROW
BEGIN
    INSERT INTO Booking_Audit (Booking_ID, Action, Old_Values, New_Values)
    VALUES (
        NEW.Booking_ID,
        'MODIFIED',
        JSON_OBJECT(
            'Seat_No', OLD.Seat_No,
            'Class', OLD.Class,
            'Booking_Status', OLD.Booking_Status,
            'Refund_Status', OLD.Refund_Status
        ),
        JSON_OBJECT(
            'Seat_No', NEW.Seat_No,
            'Class', NEW.Class,
            'Booking_Status', NEW.Booking_Status,
            'Refund_Status', NEW.Refund_Status
        )
    );
END//

CREATE TRIGGER prevent_seat_double_booking
BEFORE INSERT ON Booking
FOR EACH ROW
BEGIN
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
END//

CREATE TRIGGER prevent_seat_double_booking_update
BEFORE UPDATE ON Booking
FOR EACH ROW
BEGIN
    IF NEW.Seat_No IS NOT NULL AND NEW.Booking_Status IN ('Confirmed', 'Checked-In') THEN
        IF EXISTS (
            SELECT 1 FROM Booking 
            WHERE Schedule_ID = NEW.Schedule_ID 
              AND Seat_No = NEW.Seat_No 
              AND Booking_Status IN ('Confirmed', 'Checked-In')
              AND Booking_ID != NEW.Booking_ID
        ) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Seat already booked for this schedule';
        END IF;
    END IF;
END//

DELIMITER ;
