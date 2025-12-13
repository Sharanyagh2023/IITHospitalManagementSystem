from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret-key'
app.config['DATABASE'] = 'hospital.db'

def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'doctor', 'patient')),
            email TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            specialization_id INTEGER,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (specialization_id) REFERENCES departments(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            address TEXT,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date DATE NOT NULL,
            appointment_time TIME NOT NULL,
            status TEXT DEFAULT 'Booked' CHECK(status IN ('Booked', 'Completed', 'Cancelled')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            UNIQUE(doctor_id, appointment_date, appointment_time)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            diagnosis TEXT,
            prescription TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS availability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id INTEGER NOT NULL,
            available_date DATE NOT NULL,
            available_time TIME NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            UNIQUE(doctor_id, available_date, available_time)
        )
    ''')
    conn.commit()
    admin_password = generate_password_hash('admin123')  # Default admin password
    cursor.execute('SELECT id FROM users WHERE role = ?', ('admin',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (username, password, role, email)
            VALUES (?, ?, ?, ?)
        ''', ('admin', admin_password, 'admin', 'admin@hospital.com'))
        conn.commit()
        print("Admin user created: username='admin', password='admin123'")
    
    conn.close()
    
def get_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def query_db(query, args=(), one=False):
    conn = get_db()
    cursor = conn.execute(query, args)
    results = cursor.fetchall()
    conn.commit()  # Commit changes (SQLite auto-commits on close, but explicit is better)
    conn.close()
    return (results[0] if results else None) if one else results

def login_required(role=None):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:  # Check if user is logged in
                flash('Please login to access this page', 'error')
                return redirect(url_for('login'))
            if role and session.get('role') != role:  # Check role if specified
                flash('Access denied. Insufficient permissions.', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

if not os.path.exists(app.config['DATABASE']):
    init_db()
else:
    conn = sqlite3.connect(app.config['DATABASE'])
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        init_db()
    conn.close()


@app.route('/')
def index():
    if 'user_id' in session:  # If user is logged in, redirect to dashboard
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
        
        if user and check_password_hash(user['password'], password):  
            session['user_id'] = user['id']  
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        phone = request.form.get('phone')
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        address = request.form.get('address')
        
        existing_user = query_db('SELECT id FROM users WHERE username = ?', (username,), one=True)
        if existing_user:
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        hashed_password = generate_password_hash(password)
        #user
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password, role, email, phone)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hashed_password, 'patient', email, phone))
        user_id = cursor.lastrowid  # Get the ID of the newly created user
        
        #patient
        cursor.execute('''
            INSERT INTO patients (user_id, name, age, gender, address)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, name, age, gender, address))
        conn.commit()
        conn.close()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear all session data
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

 
@app.route('/dashboard')
@login_required()  # Require user to be logged in
def dashboard():
    role = session.get('role')
    
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    elif role == 'patient':
        return redirect(url_for('patient_dashboard'))
    
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
@login_required('admin')  
def admin_dashboard():
    total_doctors = query_db('SELECT COUNT(*) as count FROM doctors WHERE is_active = 1', one=True)['count']
    total_patients = query_db('SELECT COUNT(*) as count FROM patients WHERE is_active = 1', one=True)['count']
    total_appointments = query_db('SELECT COUNT(*) as count FROM appointments', one=True)['count']
    
    recent_appointments = query_db('''
        SELECT a.*, p.name as patient_name, d.name as doctor_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        LIMIT 10
    ''')
    
    return render_template('admin/dashboard.html',
                         total_doctors=total_doctors,
                         total_patients=total_patients,
                         total_appointments=total_appointments,
                         recent_appointments=recent_appointments)

@app.route('/admin/doctors', methods=['GET', 'POST'])
@login_required('admin')
def admin_doctors():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            # Add new doctor
            username = request.form.get('username')
            password = request.form.get('password')
            name = request.form.get('name')
            specialization_id = request.form.get('specialization_id')
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            existing = query_db('SELECT id FROM users WHERE username = ?', (username,), one=True)
            if existing:
                flash('Username already exists', 'error')
            else:
                hashed_password = generate_password_hash(password)
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, password, role, email, phone)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, hashed_password, 'doctor', email, phone))
                user_id = cursor.lastrowid
                cursor.execute('''
                    INSERT INTO doctors (user_id, name, specialization_id)
                    VALUES (?, ?, ?)
                ''', (user_id, name, specialization_id))
                conn.commit()
                conn.close()
                flash('Doctor added successfully', 'success')
        
        elif action == 'update':
            # Update doctor
            doctor_id = request.form.get('doctor_id')
            name = request.form.get('name')
            specialization_id = request.form.get('specialization_id')
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            conn = get_db()
            cursor = conn.cursor()
            doctor = query_db('SELECT user_id FROM doctors WHERE id = ?', (doctor_id,), one=True)
            if doctor:
                cursor.execute('UPDATE doctors SET name = ?, specialization_id = ? WHERE id = ?',
                             (name, specialization_id, doctor_id))
                cursor.execute('UPDATE users SET email = ?, phone = ? WHERE id = ?',
                             (email, phone, doctor['user_id']))
                conn.commit()
            conn.close()
            flash('Doctor updated successfully', 'success')
        
        elif action == 'delete':
            # Deactivate doctor
            doctor_id = request.form.get('doctor_id')
            query_db('UPDATE doctors SET is_active = 0 WHERE id = ?', (doctor_id,))
            flash('Doctor removed successfully', 'success')
        
        return redirect(url_for('admin_doctors'))
    
    # Get doctors
    doctors = query_db('''
        SELECT d.*, u.email, u.phone, dept.name as specialization_name
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        WHERE d.is_active = 1
        ORDER BY d.name
    ''')
    
    #Get all departments
    departments = query_db('SELECT * FROM departments ORDER BY name')
    
    return render_template('admin/doctors.html', doctors=doctors, departments=departments)

@app.route('/admin/appointments')
@login_required('admin')
def admin_appointments():
    appointments = query_db('''
        SELECT a.*, p.name as patient_name, p.id as patient_id,
               d.name as doctor_name, dept.name as specialization
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''')
    
    return render_template('admin/appointments.html', appointments=appointments)

@app.route('/admin/search', methods=['GET', 'POST'])
@login_required('admin')
def admin_search():
    results = None
    search_type = None
    query = None
    
    if request.method == 'POST':
        search_type = request.form.get('search_type')
        query = request.form.get('query')
        
        if search_type == 'patient':
            results = query_db('''
                SELECT p.*, u.email, u.phone
                FROM patients p
                JOIN users u ON p.user_id = u.id
                WHERE p.name LIKE ? OR p.id = ? OR u.email LIKE ? OR u.phone LIKE ?
            ''', (f'%{query}%', query, f'%{query}%', f'%{query}%'))
        
        elif search_type == 'doctor':
            results = query_db('''
                SELECT d.*, dept.name as specialization_name, u.email, u.phone
                FROM doctors d
                JOIN users u ON d.user_id = u.id
                LEFT JOIN departments dept ON d.specialization_id = dept.id
                WHERE d.name LIKE ? OR dept.name LIKE ?
            ''', (f'%{query}%', f'%{query}%'))
        
        elif search_type == 'specialization':
            results = query_db('''
                SELECT * FROM departments WHERE name LIKE ? OR description LIKE ?
            ''', (f'%{query}%', f'%{query}%'))
    
    return render_template('admin/search.html', results=results, search_type=search_type, query=query)

@app.route('/admin/departments', methods=['GET', 'POST'])
@login_required('admin')
def admin_departments():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            name = request.form.get('name')
            description = request.form.get('description')
            query_db('INSERT INTO departments (name, description) VALUES (?, ?)', (name, description))
            flash('Department added successfully', 'success')
        
        elif action == 'update':
            dept_id = request.form.get('dept_id')
            name = request.form.get('name')
            description = request.form.get('description')
            query_db('UPDATE departments SET name = ?, description = ? WHERE id = ?',
                    (name, description, dept_id))
            flash('Department updated successfully', 'success')
        
        elif action == 'delete':
            dept_id = request.form.get('dept_id')
            query_db('DELETE FROM departments WHERE id = ?', (dept_id,))
            flash('Department deleted successfully', 'success')
        
        return redirect(url_for('admin_departments'))
    
    departments = query_db('SELECT * FROM departments ORDER BY name')
    return render_template('admin/departments.html', departments=departments)

# Doctor routes
@app.route('/doctor/dashboard')
@login_required('doctor')
def doctor_dashboard():
    doctor_id = query_db('SELECT id FROM doctors WHERE user_id = ?', (session['user_id'],), one=True)['id']
    today = datetime.now().date()
    
    upcoming_appointments = query_db('''
        SELECT a.*, p.name as patient_name, p.age, p.gender
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.doctor_id = ? AND a.status = 'Booked'
        AND a.appointment_date >= ?
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
        LIMIT 20
    ''', (doctor_id, today))
    
    patients = query_db('''
        SELECT DISTINCT p.*
        FROM patients p
        JOIN appointments a ON p.id = a.patient_id
        WHERE a.doctor_id = ? AND p.is_active = 1
        ORDER BY p.name
    ''', (doctor_id,))
    
    return render_template('doctor/dashboard.html',
                         upcoming_appointments=upcoming_appointments,
                         patients=patients)

@app.route('/doctor/appointments')
@login_required('doctor')
def doctor_appointments():
    doctor_id = query_db('SELECT id FROM doctors WHERE user_id = ?', (session['user_id'],), one=True)['id']
    
    appointments = query_db('''
        SELECT a.*, p.name as patient_name, p.age, p.gender, t.diagnosis, t.prescription, t.notes
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.doctor_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (doctor_id,))
    
    return render_template('doctor/appointments.html', appointments=appointments)

@app.route('/doctor/treatment/<int:appointment_id>', methods=['GET', 'POST'])
@login_required('doctor')
def doctor_treatment(appointment_id):
    doctor_id = query_db('SELECT id FROM doctors WHERE user_id = ?', (session['user_id'],), one=True)['id']
    
    appointment = query_db('''
        SELECT a.*, p.name as patient_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE a.id = ? AND a.doctor_id = ?
    ''', (appointment_id, doctor_id), one=True)
    
    if not appointment:
        flash('Appointment not found', 'error')
        return redirect(url_for('doctor_appointments'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'complete':
            # Mark appointment as completed and add treatment
            diagnosis = request.form.get('diagnosis', '').strip()
            prescription = request.form.get('prescription', '').strip()
            notes = request.form.get('notes', '').strip()
            
            # Ensure required fields are not empty
            if not diagnosis or not prescription:
                flash('Diagnosis and Prescription are required fields', 'error')
                return redirect(url_for('doctor_treatment', appointment_id=appointment_id))
            
            conn = get_db()
            cursor = conn.cursor()
            try:
                # Update appointment status
                cursor.execute('UPDATE appointments SET status = ? WHERE id = ?', ('Completed', appointment_id))
                # Add or update treatment record
                cursor.execute('SELECT id FROM treatments WHERE appointment_id = ?', (appointment_id,))
                existing_treatment = cursor.fetchone()
                if existing_treatment:
                    cursor.execute('''
                        UPDATE treatments SET diagnosis = ?, prescription = ?, notes = ?
                        WHERE appointment_id = ?
                    ''', (diagnosis, prescription, notes, appointment_id))
                else:
                    cursor.execute('''
                        INSERT INTO treatments (appointment_id, diagnosis, prescription, notes)
                        VALUES (?, ?, ?, ?)
                    ''', (appointment_id, diagnosis, prescription, notes))
                conn.commit()
                flash('Treatment recorded successfully', 'success')
            except Exception as e:
                conn.rollback()
                flash('Error saving treatment: ' + str(e), 'error')
            finally:
                conn.close()
            return redirect(url_for('doctor_appointments'))
        
        elif action == 'cancel':
            query_db('UPDATE appointments SET status = ? WHERE id = ?', ('Cancelled', appointment_id))
            flash('Appointment cancelled', 'success')
            return redirect(url_for('doctor_appointments'))
    
    treatment = query_db('SELECT * FROM treatments WHERE appointment_id = ?', (appointment_id,), one=True)
    
    return render_template('doctor/treatment.html', appointment=appointment, treatment=treatment)

@app.route('/doctor/patient-history/<int:patient_id>')
@login_required('doctor')
def doctor_patient_history(patient_id):
    doctor_id = query_db('SELECT id FROM doctors WHERE user_id = ?', (session['user_id'],), one=True)['id']
    patient = query_db('SELECT * FROM patients WHERE id = ?', (patient_id,), one=True)
    history = query_db('''
        SELECT a.*, t.diagnosis, t.prescription, t.notes, t.created_at as treatment_date
        FROM appointments a
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ? AND a.doctor_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (patient_id, doctor_id))
    
    return render_template('doctor/patient_history.html', patient=patient, history=history)

@app.route('/doctor/availability', methods=['GET', 'POST'])
@login_required('doctor')
def doctor_availability():
    doctor_id = query_db('SELECT id FROM doctors WHERE user_id = ?', (session['user_id'],), one=True)['id']
    
    if request.method == 'POST':
        query_db('DELETE FROM availability WHERE doctor_id = ?', (doctor_id,))
        conn = get_db()
        cursor = conn.cursor()
        today = datetime.now().date()
        for day_offset in range(7):
            date = today + timedelta(days=day_offset)
            date_str = date.strftime('%Y-%m-%d')
            
            time_slots = request.form.getlist(f'time_{date_str}')
            for time_slot in time_slots:
                if time_slot:
                    cursor.execute('''
                        INSERT INTO availability (doctor_id, available_date, available_time)
                        VALUES (?, ?, ?)
                    ''', (doctor_id, date_str, time_slot))
        
        conn.commit()
        conn.close()
        flash('Availability updated successfully', 'success')
        return redirect(url_for('doctor_availability'))
    
    availability = query_db('''
        SELECT * FROM availability
        WHERE doctor_id = ? AND available_date >= date('now')
        ORDER BY available_date, available_time
    ''', (doctor_id,))
    
    today = datetime.now().date()
    next_7_days = [(today + timedelta(days=i)) for i in range(7)]
    
    return render_template('doctor/availability.html', availability=availability, next_7_days=next_7_days)

# Patient routes
@app.route('/patient/dashboard')
@login_required('patient')
def patient_dashboard():
    patient_id = query_db('SELECT id FROM patients WHERE user_id = ?', (session['user_id'],), one=True)['id']
    departments = query_db('SELECT * FROM departments ORDER BY name')
    
    today = datetime.now().date()
    upcoming_appointments = query_db('''
        SELECT a.*, d.name as doctor_name, dept.name as specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        WHERE a.patient_id = ? AND a.status = 'Booked' AND a.appointment_date >= ?
        ORDER BY a.appointment_date ASC, a.appointment_time ASC
    ''', (patient_id, today))
    past_appointments = query_db('''
        SELECT a.*, d.name as doctor_name, dept.name as specialization,
               t.diagnosis, t.prescription, t.notes
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ? AND (a.status = 'Completed' OR a.appointment_date < ?)
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
        LIMIT 10
    ''', (patient_id, today))
    
    return render_template('patient/dashboard.html',
                         departments=departments,
                         upcoming_appointments=upcoming_appointments,
                         past_appointments=past_appointments)

@app.route('/patient/profile', methods=['GET', 'POST'])
@login_required('patient')
def patient_profile():
    patient = query_db('''
        SELECT p.*, u.email, u.phone, u.username
        FROM patients p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ?
    ''', (session['user_id'],), one=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        address = request.form.get('address')
        email = request.form.get('email')
        phone = request.form.get('phone')
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE patients SET name = ?, age = ?, gender = ?, address = ?
            WHERE user_id = ?
        ''', (name, age, gender, address, session['user_id']))
        cursor.execute('UPDATE users SET email = ?, phone = ? WHERE id = ?',
                     (email, phone, session['user_id']))
        conn.commit()
        conn.close()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('patient_profile'))
    
    return render_template('patient/profile.html', patient=patient)

@app.route('/patient/search-doctors', methods=['GET', 'POST'])
@login_required('patient')
def patient_search_doctors():
    doctors = None
    specialization_id = request.args.get('specialization_id') or request.form.get('specialization_id')
    search_query = request.args.get('search') or request.form.get('search')
    
    if specialization_id or search_query:
        query = '''
            SELECT d.*, dept.name as specialization_name, u.email, u.phone
            FROM doctors d
            JOIN users u ON d.user_id = u.id
            LEFT JOIN departments dept ON d.specialization_id = dept.id
            WHERE d.is_active = 1
        '''
        params = []
        
        if specialization_id:
            query += ' AND d.specialization_id = ?'
            params.append(specialization_id)
        
        if search_query:
            query += ' AND (d.name LIKE ? OR dept.name LIKE ?)'
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        
        query += ' ORDER BY d.name'
        doctors = query_db(query, tuple(params))
    
    departments = query_db('SELECT * FROM departments ORDER BY name')
    return render_template('patient/search_doctors.html', doctors=doctors, departments=departments)

@app.route('/patient/doctor-profile/<int:doctor_id>')
@login_required('patient')
def patient_doctor_profile(doctor_id):
    doctor = query_db('''
        SELECT d.*, dept.name as specialization_name, dept.description as specialization_desc,
               u.email, u.phone
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        WHERE d.id = ? AND d.is_active = 1
    ''', (doctor_id,), one=True)
    
    if not doctor:
        flash('Doctor not found', 'error')
        return redirect(url_for('patient_search_doctors'))
    today = datetime.now().date()
    availability = query_db('''
        SELECT * FROM availability
        WHERE doctor_id = ? AND available_date >= date('now')
        ORDER BY available_date, available_time
    ''', (doctor_id,))
    
    return render_template('patient/doctor_profile.html', doctor=doctor, availability=availability)

@app.route('/patient/book-appointment', methods=['POST'])
@login_required('patient')
def patient_book_appointment():
    try:
        patient_id = query_db('SELECT id FROM patients WHERE user_id = ?', (session['user_id'],), one=True)['id']
        doctor_id = request.form.get('doctor_id')
        appointment_date = request.form.get('appointment_date')
        appointment_time = request.form.get('appointment_time')
        if not doctor_id or not appointment_date or not appointment_time:
            flash('Please select both date and time for the appointment', 'error')
            return redirect(url_for('patient_doctor_profile', doctor_id=doctor_id))
        existing = query_db('''
            SELECT id FROM appointments
            WHERE doctor_id = ? AND appointment_date = ? AND appointment_time = ? AND status = 'Booked'
        ''', (doctor_id, appointment_date, appointment_time), one=True)
        
        if existing:
            flash('This time slot is already booked. Please choose another time.', 'error')
            return redirect(url_for('patient_doctor_profile', doctor_id=doctor_id))
        available = query_db('''
            SELECT id FROM availability
            WHERE doctor_id = ? AND available_date = ? AND available_time = ?
        ''', (doctor_id, appointment_date, appointment_time), one=True)
        
        if not available:
            flash('This time slot is not available. Please choose from available slots.', 'error')
            return redirect(url_for('patient_doctor_profile', doctor_id=doctor_id))
        
        query_db('''
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status)
            VALUES (?, ?, ?, ?, 'Booked')
        ''', (patient_id, doctor_id, appointment_date, appointment_time))
        
        flash('Appointment booked successfully', 'success')
        return redirect(url_for('patient_dashboard'))
    except Exception as e:
        flash('Error booking appointment: ' + str(e), 'error')
        return redirect(url_for('patient_doctor_profile', doctor_id=request.form.get('doctor_id', '')))

@app.route('/patient/appointments')
@login_required('patient')
def patient_appointments():
    patient_id = query_db('SELECT id FROM patients WHERE user_id = ?', (session['user_id'],), one=True)['id']
    
    appointments = query_db('''
        SELECT a.*, d.name as doctor_name, dept.name as specialization,
               t.diagnosis, t.prescription, t.notes
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (patient_id,))
    
    return render_template('patient/appointments.html', appointments=appointments)

@app.route('/patient/cancel-appointment/<int:appointment_id>')
@login_required('patient')
def patient_cancel_appointment(appointment_id):
    patient_id = query_db('SELECT id FROM patients WHERE user_id = ?', (session['user_id'],), one=True)['id']
    
    appointment = query_db('''
        SELECT * FROM appointments WHERE id = ? AND patient_id = ? AND status = 'Booked'
    ''', (appointment_id, patient_id), one=True)
    
    if not appointment:
        flash('Appointment not found or cannot be cancelled', 'error')
        return redirect(url_for('patient_appointments'))
    
    query_db('UPDATE appointments SET status = ? WHERE id = ?', ('Cancelled', appointment_id))
    flash('Appointment cancelled successfully', 'success')
    return redirect(url_for('patient_appointments'))

@app.route('/patient/history')
@login_required('patient')
def patient_history():
    patient_id = query_db('SELECT id FROM patients WHERE user_id = ?', (session['user_id'],), one=True)['id']
    
    history = query_db('''
        SELECT a.*, d.name as doctor_name, dept.name as specialization,
               t.diagnosis, t.prescription, t.notes, t.created_at as treatment_date
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        LEFT JOIN departments dept ON d.specialization_id = dept.id
        LEFT JOIN treatments t ON a.id = t.appointment_id
        WHERE a.patient_id = ? AND a.status = 'Completed'
        ORDER BY a.appointment_date DESC, a.appointment_time DESC
    ''', (patient_id,))
    
    return render_template('patient/history.html', history=history)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
