# Hospital Management System (HMS)

A comprehensive web application for managing hospital operations, appointments, and patient care built with Flask, SQLite, and Bootstrap.

## Features

### Admin (Hospital Staff)
- Dashboard with statistics (total doctors, patients, appointments)
- Add, update, and delete doctor profiles
- View and manage all appointments
- Search for patients, doctors, or specializations
- Manage departments/specializations
- Pre-existing admin account (username: `admin`, password: `admin123`)

### Doctor
- Dashboard showing upcoming appointments and patient list
- View all appointments (past and upcoming)
- Mark appointments as completed and record treatment details
- View complete patient treatment history
- Set availability for next 7 days

### Patient
- Register and login
- Search for doctors by specialization or name
- View doctor profiles and availability
- Book, view, and cancel appointments
- View appointment history with diagnosis and prescriptions
- Update profile information

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Frontend**: HTML, CSS, Bootstrap 5, Jinja2 templating
- **Database**: SQLite (created programmatically)

## Installation

1. Install Python 3.7 or higher

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://localhost:5000
```

## Default Login Credentials

- **Admin**: 
  - Username: `admin`
  - Password: `admin123`

## Database

The database (`hospital.db`) is created automatically when you first run the application. All tables are created programmatically - no manual database setup required.

## Project Structure

```
hospitalManagementSystemIITM/
├── app.py                 # Main application file with routes and database setup
├── requirements.txt       # Python dependencies
├── templates/             # Jinja2 HTML templates
│   ├── base.html         # Base template
│   ├── index.html        # Home page
│   ├── login.html        # Login page
│   ├── register.html     # Patient registration
│   ├── admin/            # Admin templates
│   ├── doctor/           # Doctor templates
│   └── patient/          # Patient templates
├── static/               # Static files
│   └── css/
│       └── style.css     # Custom styles
└── hospital.db           # SQLite database (created automatically)
```

## Key Features Implementation

- **Prevent Multiple Appointments**: Database constraint ensures no two appointments at the same date/time for the same doctor
- **Dynamic Status Updates**: Appointment status changes from Booked → Completed → Cancelled
- **Search Functionality**: Admin and patients can search by various criteria
- **Treatment History**: All completed appointments store diagnosis, prescriptions, and notes
- **Role-Based Access**: Each user role has specific permissions and views


## License

This project is created for educational purposes.


