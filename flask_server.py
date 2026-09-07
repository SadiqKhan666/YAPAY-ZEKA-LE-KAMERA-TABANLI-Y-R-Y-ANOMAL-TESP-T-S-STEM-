import io
import os
import sys
import csv
import sqlite3
import time
import threading
import cv2
import numpy as np
from datetime import timedelta
from functools import wraps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from flask import Flask, jsonify, Response, request, send_from_directory, abort, render_template, redirect, session, url_for, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

import pose_detect

app = Flask(__name__, static_folder='static', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', 'change_this_secret_key')
app.permanent_session_lifetime = timedelta(minutes=30)

DATABASE = os.path.join(os.path.dirname(__file__), 'auth.db')
GAIT_DATABASE = os.path.join(os.path.dirname(__file__), 'gait.db')

patients = [
    {
        'id': 1,
        'name': 'Ali Veli',
        'age': 65,
        'gender': 'Erkek',
        'analyses': []
    },
    {
        'id': 2,
        'name': 'Ayşe Yılmaz',
        'age': 72,
        'gender': 'Kadın',
        'analyses': []
    }
]


def get_gait_db_connection():
    conn = sqlite3.connect(GAIT_DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_gait_db():
    if not os.path.exists(GAIT_DATABASE):
        os.makedirs(os.path.dirname(GAIT_DATABASE), exist_ok=True)

    with get_gait_db_connection() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                right_steps INTEGER,
                left_steps INTEGER,
                total_steps INTEGER,
                status TEXT,
                disease TEXT,
                risk_score REAL,
                symmetry REAL,
                cadence REAL,
                step_time_diff REAL,
                step_height_diff REAL,
                avg_step_time REAL,
                z_variation REAL,
                avg_asymmetry REAL,
                gait_speed REAL,
                ai_prediction TEXT,
                doctor_label TEXT,
                date TEXT,
                confidence REAL,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
            '''
        )
        conn.commit()

    # Seed patients if not already present
    with get_gait_db_connection() as conn:
        for p in patients:
            existing = conn.execute('SELECT id FROM patients WHERE id = ?', (p['id'],)).fetchone()
            if existing is None:
                conn.execute(
                    'INSERT INTO patients (id, name, age, gender) VALUES (?, ?, ?, ?)',
                    (p['id'], p['name'], p['age'], p['gender'])
                )
        conn.commit()


# Initialize gait database as well
init_gait_db()

# Use a shorter auto-training threshold for doctor-approved labels
if hasattr(pose_detect, 'training_pipeline') and pose_detect.training_pipeline:
    pose_detect.training_pipeline.sample_threshold = 20

analysis_thread = None


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    if not os.path.exists(DATABASE):
        os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    with get_db_connection() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'doctor'
            )
            '''
        )
        conn.commit()

        user = conn.execute('SELECT id FROM users WHERE username = ?', ('doctor',)).fetchone()
        if user is None:
            password_hash = generate_password_hash('1234')
            conn.execute(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                ('doctor', password_hash, 'doctor')
            )
            conn.commit()


def get_user(username):
    with get_db_connection() as conn:
        return conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()


# Initialize authentication database and default doctor user.
init_auth_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if 'user' not in session:
            if request.accept_mimetypes.accept_json:
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped_view


@app.route('/patient/<int:patient_id>/view')
@login_required
def patient_view(patient_id):
    """Render a simple patient detail page with analyses and PDF button."""
    patient = next((p for p in patients if p['id'] == patient_id), None)
    if patient is None:
        return abort(404)
    return render_template('patient.html', patient=patient)


@app.route('/report/<int:patient_id>')
@login_required
def generate_report(patient_id):
    """Generate a PDF report for the given patient and return as download."""
    patient = next((p for p in patients if p['id'] == patient_id), None)
    if patient is None:
        return abort(404)

    analyses = patient.get('analyses', [])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("Yürüyüş Analiz Raporu", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Ad: {patient['name']}", styles['Normal']))
    content.append(Paragraph(f"Yaş: {patient['age']}", styles['Normal']))
    content.append(Paragraph(f"Cinsiyet: {patient['gender']}", styles['Normal']))
    content.append(Spacer(1, 12))

    content.append(Paragraph("Analiz Geçmişi:", styles['Heading2']))

    if analyses:
        last = analyses[-1]
        content.append(Spacer(1, 6))
        content.append(Paragraph(f"Son Durum: {last.get('status', '')}", styles['Heading2']))
        if 'Anormal' in str(last.get('status', '')) or 'Anormal' in str(last.get('disease', '')):
            content.append(Paragraph("⚠️ Doktor incelemesi önerilir.", styles['Normal']))
        content.append(Spacer(1, 8))

    for a in analyses:
        # time, right_steps, left_steps, status, disease
        text = f"Tarih: {a.get('time','-')} | Sağ: {a.get('right_steps',0)} | Sol: {a.get('left_steps',0)} | Durum: {a.get('status','-')} | Hastalık: {a.get('disease','-')}"
        content.append(Paragraph(text, styles['Normal']))
        content.append(Spacer(1, 8))

    doc.build(content)
    buffer.seek(0)

    download_name = f"report_{patient_id}.pdf"
    return send_file(buffer, as_attachment=True, download_name=download_name, mimetype='application/pdf')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = get_user(username)

        if user and check_password_hash(user['password_hash'], password):
            session.permanent = True
            session['user'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('panel'))

        error = 'Geçersiz kullanıcı adı veya şifre.'

    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/')
def root():
    if 'user' in session:
        return redirect(url_for('panel'))
    return redirect(url_for('login'))


@app.route('/panel')
@login_required
def panel():
    """Serve the doctor panel static HTML."""
    return send_from_directory('static', 'doctor_panel.html')


@app.route('/dashboard')
@login_required
def dashboard_page():
    total_analyses = sum(len(p['analyses']) for p in patients)
    all_statuses = [analysis['status'] for p in patients for analysis in p['analyses']]
    normal = sum(1 for s in all_statuses if 'Normal' in s)
    abnormal = len(all_statuses) - normal
    return jsonify({
        'patients': len(patients),
        'analyses': total_analyses,
        'normal': normal,
        'abnormal': abnormal,
        'last_updated': time.time()
    })


@app.route('/steps')
@login_required
def steps():
    """Return current left/right foot step counts."""
    return jsonify({
        'right': pose_detect.right_foot_stepper.get_steps(),
        'left': pose_detect.left_foot_stepper.get_steps(),
        'total': min(pose_detect.left_foot_stepper.get_steps(), pose_detect.right_foot_stepper.get_steps()) * 2
    })


@app.route('/status')
@login_required
def status():
    """Return gait classification status."""
    return jsonify({'status': pose_detect.classify_gait()})


@app.route('/patients')
@login_required
def get_patients():
    """Return the patient list with analysis counts."""
    return jsonify(patients)


@app.route('/patient/<int:patient_id>')
@login_required
def get_patient(patient_id):
    """Return detailed patient record."""
    patient = next((p for p in patients if p['id'] == patient_id), None)
    if patient is None:
        return abort(404)
    return jsonify(patient)


def save_analysis_record(patient_id, status=None, disease=None):
    patient = next((p for p in patients if p['id'] == patient_id), None)
    if patient is None:
        return None

    right_steps = pose_detect.right_foot_stepper.get_steps()
    left_steps = pose_detect.left_foot_stepper.get_steps()
    total_steps = min(right_steps, left_steps) * 2
    symmetry = (min(right_steps, left_steps) / max(right_steps, left_steps) * 100) if max(right_steps, left_steps) > 0 else 0
    avg_step_time_value = getattr(pose_detect, 'avg_step_time', 0.0)
    gait_speed_value = getattr(pose_detect, 'gait_speed_m_s', 0.0)
    avg_asymmetry_value = float(np.mean(pose_detect.asimetri_listesi)) if getattr(pose_detect, 'asimetri_listesi', []) else 0.0
    z_variation_value = 0.0
    if hasattr(pose_detect, 'reference_torso_size') and hasattr(pose_detect, 'current_torso_size'):
        try:
            ref = pose_detect.reference_torso_size or 1.0
            z_variation_value = abs(pose_detect.current_torso_size - ref) / ref
        except Exception:
            z_variation_value = 0.0

    analysis = {
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'right_steps': right_steps,
        'left_steps': left_steps,
        'total_steps': total_steps,
        'status': status or pose_detect.classify_gait(),
        'disease': disease or pose_detect.predict_disease(),
        'risk_score': 0,
        'symmetry': round(symmetry, 1),
        'cadence': 0,
        'step_time_diff': 0,
        'step_height_diff': 0,
        'avg_step_time': avg_step_time_value,
        'z_variation': z_variation_value,
        'avg_asymmetry': avg_asymmetry_value,
        'gait_speed': gait_speed_value,
        'ai_prediction': pose_detect.classify_gait(),
        'doctor_label': None,
        'confidence': None
    }

    # Save to in-memory patient list for current session
    patient['analyses'].append(analysis)

    # Persist to gait database
    try:
        with get_gait_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO analyses (
                    patient_id, right_steps, left_steps, total_steps,
                    status, disease, risk_score, symmetry, cadence,
                    step_time_diff, step_height_diff, avg_step_time,
                    z_variation, avg_asymmetry, gait_speed,
                    ai_prediction, doctor_label, date, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    patient_id,
                    analysis['right_steps'],
                    analysis['left_steps'],
                    analysis['total_steps'],
                    analysis['status'],
                    analysis['disease'],
                    analysis['risk_score'],
                    analysis['symmetry'],
                    analysis['cadence'],
                    analysis['step_time_diff'],
                    analysis['step_height_diff'],
                    analysis['avg_step_time'],
                    analysis['z_variation'],
                    analysis['avg_asymmetry'],
                    analysis['gait_speed'],
                    analysis['ai_prediction'],
                    analysis['doctor_label'],
                    analysis['time'],
                    analysis['confidence']
                )
            )
            conn.commit()
            analysis['id'] = cursor.lastrowid
    except Exception as e:
        print(f"✗ DB analysis save error: {e}")

    return analysis


def get_pending_reviews():
    with get_gait_db_connection() as conn:
        rows = conn.execute(
            '''
            SELECT a.id, p.name, a.patient_id, a.status, a.disease,
                   a.ai_prediction, a.doctor_label, a.date, a.confidence,
                   a.right_steps, a.left_steps, a.total_steps,
                   a.symmetry, a.cadence, a.step_time_diff, a.step_height_diff
            FROM analyses a
            JOIN patients p ON a.patient_id = p.id
            WHERE a.doctor_label IS NULL
            ORDER BY a.date DESC
            '''
        ).fetchall()
    return rows


def get_analysis_by_id(analysis_id):
    with get_gait_db_connection() as conn:
        return conn.execute(
            'SELECT * FROM analyses WHERE id = ?',
            (analysis_id,)
        ).fetchone()


def append_analysis_to_dataset(db_row, label):
    # Accept sqlite3.Row or dict-like objects
    if hasattr(db_row, 'keys'):
        dbd = dict(db_row)
    else:
        dbd = db_row

    feature_data = {
        'avg_step_time': dbd.get('avg_step_time', 0.0),
        'step_time_diff': dbd.get('step_time_diff', 0.0),
        'step_height_diff': dbd.get('step_height_diff', 0.0),
        'stride_length': dbd.get('total_steps', 0.0),
        'cadence': dbd.get('cadence', 0.0),
        'symmetry_index': dbd.get('symmetry', 0.0),
        'z_variation': dbd.get('z_variation', 0.0),
        'avg_asymmetry': dbd.get('avg_asymmetry', 0.0),
        'gait_speed': dbd.get('gait_speed', 0.0)
    }

    if hasattr(pose_detect, 'training_pipeline') and pose_detect.training_pipeline:
        pose_detect.training_pipeline.save_analysis(feature_data, label=label)
    else:
        with open('gait_dataset.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                feature_data['avg_step_time'],
                feature_data['step_time_diff'],
                feature_data['step_height_diff'],
                feature_data['stride_length'],
                feature_data['cadence'],
                feature_data['symmetry_index'],
                feature_data['z_variation'],
                label
            ])


@app.route('/patient/<int:patient_id>/live')
@login_required
def live_patient(patient_id):
    patient = next((p for p in patients if p['id'] == patient_id), None)
    if patient is None:
        return abort(404)
    return render_template('patient.html', patient=patient)


@app.route('/start_analysis', methods=['POST'])
@login_required
def start_analysis():
    if pose_detect.analysis_running:
        return jsonify({'status': 'already_running'})

    patient_id = request.json.get('patient_id') if request.is_json else None
    try:
        patient_id = int(patient_id)
    except (TypeError, ValueError):
        return jsonify({'error': 'patient_id missing or invalid'}), 400

    pose_detect.analysis_running = True

    def analysis_worker(pid):
        try:
            pose_detect.start_analysis(lambda report: None, display=False)
        finally:
            pose_detect.analysis_running = False
            save_analysis_record(pid)

    global analysis_thread
    analysis_thread = threading.Thread(target=analysis_worker, args=(patient_id,), daemon=True)
    analysis_thread.start()
    return jsonify({'status': 'started'})


@app.route('/stop_analysis', methods=['POST'])
@login_required
def stop_analysis():
    pose_detect.analysis_running = False
    return jsonify({'status': 'stopped'})


@app.route('/analysis_state')
@login_required
def analysis_state():
    return jsonify({
        'analysis_running': bool(pose_detect.analysis_running),
        'status': pose_detect.classify_gait(),
        'right_steps': pose_detect.right_foot_stepper.get_steps(),
        'left_steps': pose_detect.left_foot_stepper.get_steps(),
        'total_steps': min(pose_detect.right_foot_stepper.get_steps(), pose_detect.left_foot_stepper.get_steps()) * 2
    })


@app.route('/add_analysis', methods=['POST'])
@login_required
def add_analysis():
    """Add a new analysis record for a patient."""
    data = request.json
    if not data or 'patient_id' not in data:
        return jsonify({'error': 'patient_id missing'}), 400

    try:
        patient_id = int(data['patient_id'])
    except (TypeError, ValueError):
        return jsonify({'error': 'patient_id invalid'}), 400

    patient = next((p for p in patients if p['id'] == patient_id), None)
    if patient is None:
        return jsonify({'error': 'patient not found'}), 404

    analysis = {
        'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'right_steps': data.get('right', 0),
        'left_steps': data.get('left', 0),
        'status': data.get('status', 'Bilinmiyor'),
        'disease': data.get('disease', 'Bilinmiyor'),
        'risk_score': data.get('risk_score', 0),
        'symmetry': data.get('symmetry', 0),
        'cadence': data.get('cadence', 0),
        'step_time_diff': data.get('step_time_diff', 0),
        'step_height_diff': data.get('step_height_diff', 0),
        'avg_step_time': data.get('avg_step_time', 0),
        'z_variation': data.get('z_variation', 0),
        'avg_asymmetry': data.get('avg_asymmetry', 0),
        'gait_speed': data.get('gait_speed', 0),
        'ai_prediction': data.get('ai_prediction', None),
        'doctor_label': None,
        'confidence': data.get('confidence', None)
    }

    patient['analyses'].append(analysis)
    return jsonify({'status': 'OK', 'analysis': analysis})


@app.route('/review')
@login_required
def review():
    rows = get_pending_reviews()
    return render_template('review.html', data=rows)


@app.route('/approve', methods=['POST'])
@login_required
def approve():
    analysis_id = request.form.get('id')
    label = request.form.get('label')
    if not analysis_id or not label:
        return redirect(url_for('review'))

    try:
        analysis_id = int(analysis_id)
    except ValueError:
        return redirect(url_for('review'))

    with get_gait_db_connection() as conn:
        conn.execute(
            'UPDATE analyses SET doctor_label = ? WHERE id = ?',
            (label, analysis_id)
        )
        conn.commit()

    db_row = get_analysis_by_id(analysis_id)
    if db_row is not None:
        # Persist approved label into training dataset / pipeline
        append_analysis_to_dataset(db_row, label)

        # Keep in-memory patient list in sync so UI updates immediately
        try:
            patient = next((p for p in patients if p['id'] == db_row['patient_id']), None)
            if patient is not None:
                updated = False
                for a in patient['analyses']:
                    if a.get('id') == analysis_id:
                        a['doctor_label'] = label
                        updated = True
                        break
                if not updated:
                    # Append a lightweight record if the in-memory list didn't contain it
                    patient['analyses'].append({
                        'id': db_row['id'],
                        'time': db_row['date'],
                        'right_steps': db_row['right_steps'],
                        'left_steps': db_row['left_steps'],
                        'total_steps': db_row['total_steps'],
                        'status': db_row['status'],
                        'disease': db_row['disease'],
                        'ai_prediction': db_row['ai_prediction'],
                        'doctor_label': db_row['doctor_label'],
                        'confidence': db_row['confidence']
                    })
        except Exception:
            pass

        # Trigger retraining if the pipeline is available and recommends it
        if hasattr(pose_detect, 'training_pipeline') and pose_detect.training_pipeline:
            if pose_detect.training_pipeline.should_retrain():
                pose_detect.training_pipeline.train_model()

    # If AJAX request, return JSON so client can update UI without full reload
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'ok', 'analysis_id': analysis_id})

    return redirect(url_for('review'))


@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze an uploaded frame and return step/count/status results."""
    if 'frame' not in request.files:
        return jsonify({'error': 'frame field missing'}), 400

    frame_file = request.files['frame']
    npimg = np.frombuffer(frame_file.read(), np.uint8)
    frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({'error': 'invalid image data'}), 400

    result = pose_detect.process_remote_frame(frame)
    disease = pose_detect.predict_disease()
    return jsonify({
        'right': result['right'],
        'left': result['left'],
        'status': result['status'],
        'disease': disease,
        'asymmetry': result.get('asymmetry', 0),
        'right_angle': result.get('right_angle', 0),
        'left_angle': result.get('left_angle', 0)
    })


@app.route('/reset', methods=['POST'])
def reset():
    try:
        pose_detect.left_foot_stepper.reset()
        pose_detect.right_foot_stepper.reset()
        pose_detect.left_stepper.reset()
        pose_detect.right_stepper.reset()
        pose_detect.asimetri_listesi = []
        pose_detect.right_times = []
        pose_detect.left_times = []
        pose_detect.right_heights = []
        pose_detect.left_heights = []
        pose_detect.last_right_time = None
        pose_detect.last_left_time = None
        return jsonify({'status': 'reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/mobile')
def mobile():
    return render_template('mobile.html')


@app.route('/disease')
@login_required
def disease():
    """Return disease prediction from current gait data."""
    return jsonify({
        'disease': pose_detect.predict_disease(),
        'features': pose_detect.get_disease_feature_vector()
    })


def generate_frames():
    """Yield JPEG frames for /video streaming."""
    while True:
        with pose_detect.frame_lock:
            frame = pose_detect.latest_frame
        if frame is None:
            time.sleep(0.05)
            continue

        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            time.sleep(0.05)
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.05)


@app.route('/video')
@login_required
def video():
    """Stream the live camera frames as MJPEG."""
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
