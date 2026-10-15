-- SkyReserve Initial Seed Data
-- Uses INSERT IGNORE to ensure repeatable and idempotent execution

INSERT IGNORE INTO Aircraft (Registration_No, Model, Total_Capacity, Economy_Seats, Business_Seats, First_Class_Seats, Status) VALUES
('VT-ANL', 'Boeing 787', 256, 218, 18, 20, 'Active'),
('VT-EXO', 'Airbus A320', 180, 180, 0, 0, 'Active'),
('VT-CIG', 'Airbus A320neo', 186, 186, 0, 0, 'Active'),
('VT-TBA', 'Boeing 737 MAX', 174, 162, 12, 0, 'Active'),
('VT-JSA', 'ATR 72', 72, 72, 0, 0, 'Active'),
('VT-ALB', 'Boeing 777', 342, 274, 35, 33, 'Active');

INSERT IGNORE INTO Flight (Flight_No, Airline, Source, Destination) VALUES
('AI-101', 'Air India', 'DEL', 'BOM'),
('AI-202', 'Air India', 'BOM', 'BLR'),
('6E-301', 'IndiGo', 'DEL', 'BLR'),
('6E-401', 'IndiGo', 'BLR', 'HYD'),
('SG-101', 'SpiceJet', 'DEL', 'MAA'),
('UK-801', 'Vistara', 'BOM', 'DEL'),
('UK-802', 'Vistara', 'DEL', 'CCU'),
('QP-101', 'Akasa Air', 'BLR', 'GOI'),
('I5-201', 'AIX Connect', 'DEL', 'JAI');

INSERT IGNORE INTO Flight_Schedule (Flight_No, Aircraft_ID, Departure_Time, Arrival_Time, Date, Status, Gate) VALUES
('AI-101', 1, '2026-10-10T06:00:00Z', '2026-10-10T08:00:00Z', '2026-10-10', 'Scheduled', 'A1'),
('AI-202', 2, '2026-10-10T10:00:00Z', '2026-10-10T11:45:00Z', '2026-10-10', 'Scheduled', 'B2'),
('6E-301', 3, '2026-10-11T05:30:00Z', '2026-10-11T08:15:00Z', '2026-10-11', 'Scheduled', 'C3'),
('6E-401', 3, '2026-10-11T09:00:00Z', '2026-10-11T10:15:00Z', '2026-10-11', 'Scheduled', 'C4'),
('SG-101', 4, '2026-10-11T07:00:00Z', '2026-10-11T09:30:00Z', '2026-10-11', 'Scheduled', 'A2'),
('UK-801', 6, '2026-10-12T06:00:00Z', '2026-10-12T08:00:00Z', '2026-10-12', 'Scheduled', 'T1'),
('UK-802', 6, '2026-10-12T09:00:00Z', '2026-10-12T11:15:00Z', '2026-10-12', 'Scheduled', 'T2'),
('QP-101', 4, '2026-10-13T14:00:00Z', '2026-10-13T15:30:00Z', '2026-10-13', 'Scheduled', 'G1'),
('I5-201', 2, '2026-10-13T16:00:00Z', '2026-10-13T17:00:00Z', '2026-10-13', 'Scheduled', 'A5'),
('AI-101', 1, '2026-10-14T06:00:00Z', '2026-10-14T08:00:00Z', '2026-10-14', 'Scheduled', 'A1');

INSERT IGNORE INTO Passenger (First_Name, Last_Name, Email, Passport_No, Date_of_Birth, Gender) VALUES
('Rahul', 'Sharma', 'rahul.s@example.com', 'A1234567', '1990-05-15', 'Male'),
('Priya', 'Patel', 'priya.p@example.com', 'B9876543', '1985-11-20', 'Female'),
('Amit', 'Singh', 'amit.s@example.com', 'C4567890', '1992-03-10', 'Male'),
('Neha', 'Gupta', 'neha.g@example.com', 'D2345678', '1988-08-25', 'Female'),
('Karan', 'Malhotra', 'karan.m@example.com', 'E8765432', '1995-01-30', 'Male'),
('Sneha', 'Reddy', 'sneha.r@example.com', 'F3456789', '1991-07-12', 'Female'),
('Vikram', 'Joshi', 'vikram.j@example.com', 'G7654321', '1983-12-05', 'Male'),
('Anjali', 'Desai', 'anjali.d@example.com', 'H4561239', '1994-04-18', 'Female'),
('Rohan', 'Verma', 'rohan.v@example.com', 'I9871234', '1987-09-22', 'Male'),
('Pooja', 'Iyer', 'pooja.i@example.com', 'J1239874', '1993-06-08', 'Female');

INSERT IGNORE INTO Passenger_Phone (Passenger_ID, Phone_Number, Phone_Type) VALUES
(1, '9876543210', 'Mobile'),
(2, '8765432109', 'Mobile'),
(3, '7654321098', 'Mobile'),
(4, '6543210987', 'Mobile'),
(5, '9988776655', 'Mobile'),
(6, '8877665544', 'Mobile'),
(7, '7766554433', 'Mobile'),
(8, '6655443322', 'Mobile'),
(9, '9123456780', 'Mobile'),
(10, '9871234560', 'Mobile');

INSERT IGNORE INTO Booking (Passenger_ID, Schedule_ID, Seat_No, Class, Fare, Booking_Status) VALUES
(1, 1, '12A', 'Economy', 5500.0, 'Confirmed'),
(2, 1, '12B', 'Economy', 5500.0, 'Confirmed'),
(3, 2, '1A', 'Business', 12000.0, 'Confirmed'),
(4, 3, '5C', 'Economy', 4500.0, 'Checked-In'),
(5, 4, '8D', 'Economy', 3500.0, 'Confirmed'),
(6, 5, '15F', 'Economy', 6000.0, 'Confirmed'),
(7, 6, '2A', 'Business', 15000.0, 'Confirmed'),
(8, 7, '22A', 'Economy', 7000.0, 'Confirmed'),
(9, 8, '10B', 'Economy', 4000.0, 'Cancelled'),
(10, 9, '14C', 'Economy', 3200.0, 'Confirmed'),
(1, 10, '12A', 'Economy', 5800.0, 'Confirmed');

INSERT IGNORE INTO Baggage (Booking_ID, Baggage_Seq_No, Weight, Tag_No, Type) VALUES
(1, 1, 15.5, 'AI-101-001', 'Checked'),
(1, 2, 7.0, 'AI-101-002', 'Cabin'),
(2, 1, 18.0, 'AI-101-003', 'Checked'),
(3, 1, 25.0, 'AI-202-001', 'Checked'),
(4, 1, 12.0, '6E-301-001', 'Checked'),
(6, 1, 14.5, 'SG-101-001', 'Checked'),
(7, 1, 30.0, 'UK-801-001', 'Checked');

INSERT IGNORE INTO Crew (First_Name, Last_Name, Role, License_No, Phone, Email) VALUES
('Rakesh', 'Ranjan', 'Captain', 'CPL-1001', '9811122233', 'rakesh.r@airline.com'),
('Suresh', 'Kumar', 'First Officer', 'CPL-1002', '9822233344', 'suresh.k@airline.com'),
('Manoj', 'Tiwari', 'Flight Engineer', 'FEL-2001', '9833344455', 'manoj.t@airline.com'),
('Simran', 'Kaur', 'Cabin Crew Lead', 'CCL-3001', '9844455566', 'simran.k@airline.com'),
('Anita', 'Roy', 'Cabin Crew', 'CC-4001', '9855566677', 'anita.r@airline.com'),
('Sunil', 'Gavaskar', 'Captain', 'CPL-1003', '9866677788', 'sunil.g@airline.com'),
('Kapil', 'Dev', 'First Officer', 'CPL-1004', '9877788899', 'kapil.d@airline.com'),
('Ravi', 'Shastri', 'Cabin Crew Lead', 'CCL-3002', '9888899900', 'ravi.s@airline.com');

INSERT IGNORE INTO Crew_Assignment (Crew_ID, Schedule_ID) VALUES
(1, 1),
(2, 1),
(4, 1),
(5, 1),
(6, 6),
(7, 6),
(8, 6),
(1, 10),
(2, 10),
(4, 10);
