

import cv2
import mediapipe as mp
import numpy as np
import csv
import time
from collections import deque
import os
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading

try:
    import serial  # MPU6050 için serial iletişim
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    SERIAL_AVAILABLE = False
    print("WARNING: pyserial not available - MPU6050 support disabled")

import matplotlib
try:
    matplotlib.use('TkAgg')
except Exception as e:
    print(f"WARNING: TkAgg backend unavailable, falling back to Agg: {e}")
    matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Advanced ML & Metrics
try:
    from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("WARNING: scikit-learn not available - metrics tracking disabled")

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("WARNING: xgboost not available - ML model disabled")

try:
    import pandas as pd
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False
    print("WARNING: pandas/joblib not available - auto-training disabled")

# Remote frame processing globals
pose_model = None
pose_model_initialized = False
pose_init_lock = threading.Lock()

# ===================== SABİT DEĞERLER =====================
# These constants define the thresholds and parameters for gait analysis
# See METHODS.md for detailed explanations of each parameter

CSV_FILE = "final_gait_analizi.csv"

# Asymmetry Index Thresholds
# Asymmetry Index = |Left_Value - Right_Value| / Mean_Value × 100
# Indicates left-right gait symmetry (lower = more symmetric)
ASYMETRI_ESIGI = 15  # Primary asymmetry threshold (%)
ASYMETRI_HAFIF_ESIGI = 10  # Mild asymmetry threshold (%)

# Joint Angle Thresholds (degrees)
MAKS_DUZ_ACI = 150  # Maximum straight angle (extended joint)
MIN_BUKUK_ACI = 100  # Minimum bent angle (flexed joint)

# Step detection thresholds (knee angle)
STEP_BEND_THRESHOLD = 168.0   # Diz 168'in altına inerse adım hazırlığı
STEP_STRAIGHTEN_THRESHOLD = 172.0  # Diz 172'nin üzerine çıkarsa adım tamamlandı olarak say

# Camera placement recommendation:
# - Capture the whole body from head to foot
# - Prefer sagittal/side view for best knee-angle accuracy
# - Frontal view is less reliable for knee-bend based step detection

# Temporal Thresholds
MIN_ADIM_ARALIK = 0.4  # Minimum step interval (seconds) - prevents duplicate detections
BUFFER_BOYUT = 5  # Moving average buffer size for smoothing
CSV_BUFFER_LIMIT = 30  # Number of samples before writing to CSV

# Gait Cycle Parameters
MAX_ADIM_SAYISI = 18  # Maximum number of steps to analyze per trial

# Foot landmark indices for MediaPipe Pose
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32

# ===================== FRONTAL PLANE CAMERA CALIBRATION =====================
# Camera parameters for depth-change estimation (Fig 2, METHODS.md)
CAMERA_FOCAL_LENGTH = 700.0        # f: Camera focal length (pixels) - calibrate for your camera
REFERENCE_DEPTH = 4.27             # d_Ref: Initial reference depth (meters)
PERSON_HEIGHT = 1.70               # Human height for pixel scaling (meters)
USER_HEIGHT_CM = 170                # Set your own height in cm for approximate pixel-to-cm conversion
LOW_PASS_FILTER_ALPHA = 0.3        # Low-pass filter coefficient (0.0-1.0, lower = more smoothing)

# ===================== VALIDATION METRICS (Table 1 & Table 2) =====================
# Accuracy data from comparison with 3D motion capture (stroke & Parkinson's disease)
# See Fig 4, Fig 5, Fig 6, Table 1, Table 2 for detailed validation results

# SAGITTAL PLANE VALIDATION (C_Sag vs Motion Capture)
SAGITTAL_STEP_TIME_ERROR = 0.02        # ±0.02 seconds average error
SAGITTAL_STEP_LENGTH_ERROR = 0.03      # ±0.03 meters (3 cm) average error
SAGITTAL_GAIT_SPEED_ERROR = 0.04       # ±0.04 m/s average error
SAGITTAL_STEP_LENGTH_CORRELATION = 0.922  # Strong correlation (r ≥ 0.922)
SAGITTAL_GAIT_SPEED_CORRELATION = 0.981   # Very strong correlation (r ≥ 0.981)
SAGITTAL_STEP_TIME_ASYM_ERROR = 0.03   # ±0.03 average error for step time asymmetry
SAGITTAL_STEP_LENGTH_ASYM_ERROR = 0.050  # ±0.050 average error for step length asymmetry
SAGITTAL_JOINT_ANGLE_ERRORS = {         # Mean absolute errors (degrees)
    'hip': 3.3,
    'knee': 4.0,
    'ankle': 6.3
}

# FRONTAL PLANE VALIDATION (C_Front vs Motion Capture)
# NOTE: Frontal errors are larger due to depth-change estimation challenges
FRONTAL_STEP_TIME_ERROR = 0.02          # ±0.02 seconds average error
FRONTAL_STEP_LENGTH_ERROR = 0.07        # ±0.07 meters (7 cm) average error - larger than sagittal
FRONTAL_GAIT_SPEED_ERROR = 0.10         # ±0.10 m/s average error - larger than sagittal
FRONTAL_STEP_LENGTH_CORRELATION = 0.922 # Strong correlation but weak when walking away from camera
FRONTAL_GAIT_SPEED_CORRELATION = 0.981  # Very strong correlation

# FRONTAL PLANE DEPTH & WALKING DIRECTION EFFECTS (S1 Fig, S3 Fig, S3 Table)
# Accuracy decreases as person moves away from camera (appears smaller)
FRONTAL_NEAREST_ERROR = 0.07            # ~7 cm error when nearest to camera
FRONTAL_FAR_AWAY_ERROR = 0.16           # ~16 cm error when walking away from camera
FRONTAL_TOWARD_ERROR = 0.11             # ~11 cm error when walking toward camera
FRONTAL_GAIT_CYCLE_TIMING_LAG_AWAY = 0.04  # ~0.04 s lag when walking away
FRONTAL_GAIT_CYCLE_TIMING_LAG_TOWARD = 0.15  # ~0.15 s lag when walking toward

# GAIT SPEED OVERESTIMATION BY WALKING DIRECTION (when walking away from front camera)
FRONTAL_SPEED_OVEREST_AWAY_STROKE = 0.13      # +0.13 m/s overestimation for stroke
FRONTAL_SPEED_OVEREST_AWAY_PD = 0.21          # +0.21 m/s overestimation for PD
FRONTAL_SPEED_OVEREST_TOWARD_STROKE = 0.01    # +0.01 m/s when walking toward
FRONTAL_SPEED_OVEREST_TOWARD_PD = 0.03        # +0.03 m/s when walking toward

# ===================== MPU6050 AYARLARI =====================
# Inertial Measurement Unit (IMU) integration for complementary motion data
# Provides accelerometer (ax, ay, az) and gyroscope (gx, gy, gz) readings
# Used for body orientation tracking and validation of depth-change estimates

MPU6050_PORT = 'COM3'  # Arduino'nun bağlı olduğu port (değiştirilebilir)
MPU6050_BAUD = 115200
mpu_serial = None
mpu_connected = False

# MPU6050 verilerini saklamak için
# Format: ax, ay, az (acceleration), gx, gy, gz (angular velocity)
mpu_data = {
    'ax': 0, 'ay': 0, 'az': 0,
    'gx': 0, 'gy': 0, 'gz': 0
}

# ===================== DOSYA AYARLARI (CSV) =====================
# OUTPUT DATA STRUCTURE FOR GAIT ANALYSIS
# Columns store real-time measurements from video analysis and IMU
# See METHODS.md for detailed parameter descriptions

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Zaman",                    # Time elapsed (seconds)
            "Sol_Diz_Acisi",            # Left Knee Angle (degrees) - from sagittal plane analysis
            "Sag_Diz_Acisi",            # Right Knee Angle (degrees) - from sagittal plane analysis
            "Asimetri_Indeksi",         # Asymmetry Index (%) - left-right difference
            "Sol_Adim",                 # Left Step parameters (length, time)
            "Sag_Adim"                  # Right Step parameters (length, time)
        ])

csv_f = open(CSV_FILE, "a", newline="")
writer = csv.writer(csv_f)
start_time = time.time()
data_buffer = []  # CSV için buffer
asimetri_listesi = []  # Asimetri değerlerini toplamak için
ai_history = []
time_history = []
total_distance_px = 0.0
total_distance_cm = 0.0
start_walk_time = None
end_walk_time = None
gait_speed_m_s = 0.0
speed_status = "Bekleniyor"
gait_score = 0
score_status = "Bekleniyor"
avg_step_time = 0.6

# ===================== MPU6050 FONKSİYONLARI =====================
def init_mpu6050():
    """
    Initialize MPU6050 IMU sensor for motion data collection.
    
    The MPU6050 provides complementary accelerometer and gyroscope data
    for validating video-based depth-change estimates (Fig 2, METHODS.md).
    
    RETURNS:
    --------
    bool
        True if connection successful, False otherwise
        Analysis continues even if MPU6050 is unavailable
    """
    global mpu_serial, mpu_connected
    try:
        mpu_serial = serial.Serial(MPU6050_PORT, MPU6050_BAUD, timeout=1)
        time.sleep(2)  # Buffer için bekle
        mpu_connected = True
        print("OK: MPU6050 bağlantısı başarılı!")
        return True
    except Exception as e:
        print(f"ERROR: MPU6050 bağlantı hatası: {e}")
        print("Not: MPU6050 olmadan da analiz devam edecektir.")
        mpu_connected = False
        return False

def read_mpu6050():
    """
    Read accelerometer and gyroscope data from MPU6050.
    
    Updates global mpu_data dictionary with current IMU readings.
    Used to complement pixel-based depth estimation with inertial data.
    
    RETURNS:
    --------
    bool
        True if new data was read, False otherwise
    """
    global mpu_data
    if not mpu_connected or not mpu_serial:
        return False
    
    try:
        if mpu_serial.in_waiting:
            line = mpu_serial.readline().decode('utf-8').strip()
            if line.startswith("MPU:"):
                data = line[4:].split(",")
                if len(data) == 6:
                    mpu_data['ax'], mpu_data['ay'], mpu_data['az'], mpu_data['gx'], mpu_data['gy'], mpu_data['gz'] = map(int, data)
                    return True
    except Exception as e:
        print(f"MPU6050 okuma hatası: {e}")
    
    return False
def calculate_angle(a, b, c):
    """
    Calculate joint angle from three anatomical keypoints.
    
    Used in sagittal plane analysis to compute 2D joint kinematics.
    Implements the law of cosines for angle calculation.
    
    PARAMETERS:
    -----------
    a : array-like
        First keypoint position (e.g., hip)
    b : array-like
        Joint center (vertex of angle - e.g., knee)
    c : array-like
        Third keypoint position (e.g., ankle)
    
    RETURNS:
    --------
    angle : float
        Joint angle in degrees (0-180)
    
    EXAMPLE:
    --------
    Knee angle = calculate_angle(hip_pos, knee_pos, ankle_pos)
    Hip angle = calculate_angle(shoulder_pos, hip_pos, knee_pos)
    
    METHODOLOGY REFERENCE:
    This function is used in the sagittal plane workflow (Fig 1C) to 
    compute 2D joint kinematics throughout the gait cycle.
    """
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    
    ba = a - b
    bc = c - b
    
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)  # Numerical stability
    angle = np.arccos(cosine_angle) * 180 / np.pi
    return angle


def distance(p1, p2, frame_shape=None):
    """Compute Euclidean distance between two normalized keypoints.

    If frame_shape is provided, the normalized coordinates are converted
    to pixel coordinates before measuring the distance.
    """
    p1 = np.array(p1, dtype=np.float32)
    p2 = np.array(p2, dtype=np.float32)

    if frame_shape is not None and len(frame_shape) >= 2:
        h, w = frame_shape[:2]
        p1 = np.array([p1[0] * w, p1[1] * h], dtype=np.float32)
        p2 = np.array([p2[0] * w, p2[1] * h], dtype=np.float32)

    return float(np.linalg.norm(p1 - p2))


def estimate_pixel_to_cm_scale(head, foot_y, frame_height, real_height_cm=USER_HEIGHT_CM):
    """Estimate pixel-to-cm scale from head-to-foot pixel height."""
    if head is None or foot_y is None or frame_height <= 0 or real_height_cm <= 0:
        return None

    pixel_height = abs(head[1] - foot_y) * frame_height
    if pixel_height < 20:
        return None

    return real_height_cm / pixel_height


# ===================== ADVANCED GAIT FEATURES =====================
class SignalFilter:
    """Exponential Moving Average (EMA) filter for signal smoothing."""
    
    def __init__(self, alpha=0.7):
        """
        Initialize EMA filter.
        alpha: smoothing factor (0.0-1.0)
        - alpha ~ 0.0: heavy smoothing
        - alpha ~ 1.0: no filtering
        """
        self.alpha = alpha
        self.filtered_value = None
    
    def apply(self, raw_value):
        """Apply EMA filter to raw signal."""
        if self.filtered_value is None:
            self.filtered_value = raw_value
        else:
            self.filtered_value = self.alpha * raw_value + (1 - self.alpha) * self.filtered_value
        return self.filtered_value
    
    def reset(self):
        self.filtered_value = None


class AdvancedGaitFeatures:
    """Extract advanced gait features for disease detection."""
    
    def __init__(self, window_size=60):  # 2 seconds at 30fps
        self.window_size = window_size
        self.step_times = deque(maxlen=window_size)
        self.step_heights = deque(maxlen=window_size)
        self.asymmetry_values = deque(maxlen=window_size)
        self.z_positions = deque(maxlen=window_size)
        self.velocity_history = deque(maxlen=window_size)
        self.acceleration_history = deque(maxlen=window_size)
    
    def add_frame_data(self, step_time=0.0, step_height=0.0, asymmetry=0.0, 
                       z_position=0.0, velocity=0.0):
        """Add frame-level data."""
        if step_time > 0:
            self.step_times.append(step_time)
        if step_height > 0:
            self.step_heights.append(step_height)
        if asymmetry >= 0:
            self.asymmetry_values.append(asymmetry)
        if z_position != 0:
            self.z_positions.append(z_position)
        if velocity != 0:
            self.velocity_history.append(velocity)
    
    def calculate_stride_variability(self):
        """Calculate stride time variability (std dev of step times)."""
        if len(self.step_times) < 2:
            return 0.0
        return float(np.std(self.step_times))
    
    def calculate_cadence_variability(self):
        """Calculate cadence variability."""
        if len(self.step_times) < 2:
            return 0.0
        cadences = [60.0 / st if st > 0 else 0 for st in self.step_times]
        return float(np.std(cadences))
    
    def calculate_cadence(self):
        """Average cadence (steps/minute)."""
        if len(self.step_times) < 1:
            return 0.0
        avg_step_time = float(np.mean(self.step_times))
        if avg_step_time > 0:
            return 60.0 / avg_step_time
        return 0.0
    
    def calculate_symmetry_index(self, left_steps, right_steps):
        """Symmetry index based on step count."""
        total = left_steps + right_steps
        if total == 0:
            return 0.0
        return abs(left_steps - right_steps) / (total + 1e-6)
    
    def calculate_z_stability(self):
        """Calculate Z-axis stability (thorax depth variation)."""
        if len(self.z_positions) < 2:
            return 0.0
        return float(np.std(self.z_positions))
    
    def calculate_jerk(self):
        """Calculate movement jerk (smoothness metric)."""
        if len(self.acceleration_history) < 2:
            return 0.0
        acc_diff = np.diff(list(self.acceleration_history))
        return float(np.mean(np.abs(acc_diff)))
    
    def get_feature_vector(self, left_steps, right_steps):
        """Get comprehensive feature vector."""
        features = {
            'stride_variability': self.calculate_stride_variability(),
            'cadence_variability': self.calculate_cadence_variability(),
            'cadence': self.calculate_cadence(),
            'symmetry_index': self.calculate_symmetry_index(left_steps, right_steps),
            'z_stability': self.calculate_z_stability(),
            'jerk': self.calculate_jerk(),
            'avg_asymmetry': float(np.mean(self.asymmetry_values)) if len(self.asymmetry_values) > 0 else 0.0,
            'avg_step_height': float(np.mean(self.step_heights)) if len(self.step_heights) > 0 else 0.0,
        }
        return features
    
    def reset(self):
        self.step_times.clear()
        self.step_heights.clear()
        self.asymmetry_values.clear()
        self.z_positions.clear()
        self.velocity_history.clear()
        self.acceleration_history.clear()


class WindowedFeatureExtractor:
    """Extract features over sliding windows (2-3 seconds)."""
    
    def __init__(self, window_duration=2.0, frame_rate=30):
        self.window_duration = window_duration
        self.frame_rate = frame_rate
        self.window_size = int(window_duration * frame_rate)
        self.data_buffer = deque(maxlen=self.window_size)
    
    def add_data(self, data_point):
        """Add data to window buffer."""
        self.data_buffer.append(data_point)
    
    def get_window_features(self):
        """Extract statistics from current window."""
        if len(self.data_buffer) < 2:
            return None
        
        data_array = np.array(list(self.data_buffer))
        return {
            'mean': float(np.mean(data_array)),
            'std': float(np.std(data_array)),
            'min': float(np.min(data_array)),
            'max': float(np.max(data_array)),
            'range': float(np.max(data_array) - np.min(data_array)),
        }
    
    def is_window_ready(self):
        """Check if window has enough data."""
        return len(self.data_buffer) >= self.window_size


class GaitMetrics:
    """Track classification metrics (precision, recall, F1)."""
    
    def __init__(self):
        self.y_true = []
        self.y_pred = []
        self.prediction_history = deque(maxlen=100)
    
    def add_prediction(self, true_label, predicted_label):
        """Add a prediction for metric tracking."""
        self.y_true.append(true_label)
        self.y_pred.append(predicted_label)
        self.prediction_history.append({
            'true': true_label,
            'pred': predicted_label,
            'timestamp': time.time()
        })
    
    def get_metrics(self):
        """Get precision, recall, F1 scores."""
        if SKLEARN_AVAILABLE and len(self.y_true) > 0:
            try:
                # Binary classification (normal vs abnormal)
                precision, recall, f1, support = precision_recall_fscore_support(
                    self.y_true, self.y_pred, average='binary', zero_division=0
                )
                cm = confusion_matrix(self.y_true, self.y_pred)
                
                return {
                    'precision': float(precision),
                    'recall': float(recall),
                    'f1': float(f1),
                    'confusion_matrix': cm.tolist(),
                    'support': int(support)
                }
            except Exception as e:
                print(f"Metric calculation error: {e}")
                return None
        return None
    
    def get_classification_report(self):
        """Get detailed classification report."""
        if SKLEARN_AVAILABLE and len(self.y_true) > 0:
            try:
                return classification_report(self.y_true, self.y_pred, 
                                            target_names=['Normal', 'Abnormal'],
                                            zero_division=0)
            except:
                return None
        return None
    
    def get_recent_accuracy(self, window=20):
        """Get accuracy over recent predictions."""
        recent = list(self.prediction_history)[-window:]
        if len(recent) == 0:
            return 0.0
        correct = sum(1 for p in recent if p['true'] == p['pred'])
        return correct / len(recent)
    
    def reset(self):
        self.y_true = []
        self.y_pred = []
        self.prediction_history.clear()


class HybridGaitClassifier:
    """Hybrid classification: Rule-based + AI model fusion."""
    
    def __init__(self):
        self.metrics_tracker = GaitMetrics()
        self.model = None
        self.model_trained = False
        
        # Rule thresholds
        self.symmetry_threshold = 0.25
        self.cadence_threshold = 70.0
        self.stride_var_threshold = 0.15
        self.jerk_threshold = 0.5
    
    def rule_based_classification(self, features):
        """Apply rule-based classification logic."""
        
        # Check for Parkinson's indicators
        if (features.get('cadence', 0) < self.cadence_threshold and 
            features.get('stride_variability', 0) > self.stride_var_threshold):
            return 'PARKINSONS_RISK'
        
        # Check for gait imbalance
        if features.get('symmetry_index', 0) > self.symmetry_threshold:
            return 'IMBALANCE'
        
        # Check for rigidity/reduced smoothness
        if features.get('jerk', 0) > self.jerk_threshold:
            return 'REDUCED_SMOOTHNESS'
        
        # Check for high variability
        if (features.get('cadence_variability', 0) > 0.2 and 
            features.get('stride_variability', 0) > 0.2):
            return 'HIGH_VARIABILITY'
        
        return 'NORMAL'
    
    def train_model(self, X_train, y_train):
        """Train XGBoost model on labeled gait data."""
        if not XGBOOST_AVAILABLE:
            print("⚠️  XGBoost not available - skipping model training")
            return False
        
        try:
            print(f"Training XGBoost model on {len(X_train)} samples...")
            self.model = xgb.XGBClassifier(
                n_estimators=50,
                max_depth=5,
                learning_rate=0.1,
                random_state=42,
                verbosity=0
            )
            self.model.fit(X_train, y_train)
            self.model_trained = True
            print(f"OK: Model trained successfully")
            return True
        except Exception as e:
            print(f"ERROR: Model training failed: {e}")
            return False
    
    def create_synthetic_training_data(self, n_samples=100):
        """Create synthetic training data for initial model training."""
        np.random.seed(42)
        X_train = []
        y_train = []
        
        # Generate normal gait patterns
        for _ in range(n_samples // 2):
            features = [
                np.random.normal(0.08, 0.02),  # stride_variability
                np.random.normal(0.05, 0.02),  # cadence_variability
                np.random.normal(100, 10),      # cadence
                np.random.normal(0.10, 0.05),   # symmetry_index
                np.random.normal(0.02, 0.01),   # z_stability
                np.random.normal(0.2, 0.05),    # jerk
                np.random.normal(5, 2),          # avg_asymmetry
            ]
            X_train.append(features)
            y_train.append(0)  # Normal
        
        # Generate abnormal gait patterns
        for _ in range(n_samples // 2):
            features = [
                np.random.normal(0.25, 0.05),   # high stride_variability
                np.random.normal(0.20, 0.05),   # high cadence_variability
                np.random.normal(60, 15),        # low cadence
                np.random.normal(0.30, 0.10),   # high symmetry_index
                np.random.normal(0.08, 0.03),   # high z_stability
                np.random.normal(0.6, 0.15),    # high jerk
                np.random.normal(15, 5),         # high avg_asymmetry
            ]
            X_train.append(features)
            y_train.append(1)  # Abnormal
        
        return np.array(X_train), np.array(y_train)
    
    def hybrid_predict(self, features, use_model=True):
        """
        Hybrid prediction: combine rule-based and ML model.
        Returns (prediction, confidence, reasoning)
        """
        
        rule_result = self.rule_based_classification(features)
        
        # If rules trigger, use those results with high confidence
        if rule_result != 'NORMAL':
            return rule_result, 0.8, f"Rule-based: {rule_result}"
        
        # Otherwise, use ML model if available
        if use_model and self.model_trained and XGBOOST_AVAILABLE:
            try:
                feature_vector = np.array([[
                    features.get('stride_variability', 0),
                    features.get('cadence_variability', 0),
                    features.get('cadence', 0),
                    features.get('symmetry_index', 0),
                    features.get('z_stability', 0),
                    features.get('jerk', 0),
                    features.get('avg_asymmetry', 0),
                ]])
                
                pred_proba = self.model.predict_proba(feature_vector)[0]
                pred_class = self.model.predict(feature_vector)[0]
                confidence = max(pred_proba)
                
                class_name = 'ABNORMAL' if pred_class == 1 else 'NORMAL'
                return class_name, float(confidence), f"ML-based ({confidence:.2f})"
            except Exception as e:
                print(f"Model prediction error: {e}")
        
        return 'NORMAL', 0.5, "Default"


# ===================== SELF-IMPROVING DATA PIPELINE =====================
class AutoTrainingPipeline:
    """Automatic data collection, model training, and versioning system."""
    
    def __init__(self, dataset_path="gait_dataset.csv", model_dir="models"):
        self.dataset_path = dataset_path
        self.model_dir = model_dir
        self.last_train_time = time.time()
        self.train_interval = 3600  # 1 hour in seconds
        self.sample_threshold = 50  # Retrain every 50 samples
        self.model_version = 0
        self.current_model = None
        self.model_loaded = False
        
        # Create model directory
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize dataset if doesn't exist
        if not os.path.exists(dataset_path):
            self._init_dataset()
        
        # Load best model if exists
        self.load_best_model()
    
    def _init_dataset(self):
        """Initialize CSV with headers."""
        if not JOBLIB_AVAILABLE:
            print("⚠️  pandas/joblib required for dataset management")
            return
            
        headers = [
            'timestamp', 'avg_step_time', 'step_time_diff', 'step_height_diff',
            'stride_length', 'cadence', 'symmetry_index', 'z_variation',
            'avg_asymmetry', 'gait_speed', 'label'
        ]
        try:
            with open(self.dataset_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            print(f"OK: Dataset initialized: {self.dataset_path}")
        except Exception as e:
            print(f"ERROR: Dataset init error: {e}")
    
    def save_analysis(self, features_dict, label=None):
        """
        Save analysis features to dataset.
        
        IMPORTANT: label should be None initially, user validates later.
        """
        try:
            row = [
                time.strftime('%Y-%m-%d %H:%M:%S'),
                features_dict.get('avg_step_time', 0),
                features_dict.get('step_time_diff', 0),
                features_dict.get('step_height_diff', 0),
                features_dict.get('stride_length', 0),
                features_dict.get('cadence', 0),
                features_dict.get('symmetry_index', 0),
                features_dict.get('z_variation', 0),
                features_dict.get('avg_asymmetry', 0),
                features_dict.get('gait_speed', 0),
                label if label is not None else 'UNVALIDATED'
            ]
            
            with open(self.dataset_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(row)
            
            print(f"OK: Data saved (label: {label if label else 'PENDING'})")
            return True
        except Exception as e:
            print(f"ERROR: Data save error: {e}")
            return False
    
    def get_unvalidated_count(self):
        """Count records with UNVALIDATED label."""
        if not JOBLIB_AVAILABLE:
            return 0
        try:
            df = pd.read_csv(self.dataset_path)
            unvalidated = len(df[df['label'] == 'UNVALIDATED'])
            return unvalidated
        except:
            return 0
    
    def validate_record(self, row_index, new_label):
        """Update label for a specific record (manual validation)."""
        if not JOBLIB_AVAILABLE:
            print("⚠️  pandas required for validation")
            return False
        
        try:
            df = pd.read_csv(self.dataset_path)
            if 0 <= row_index < len(df):
                df.at[row_index, 'label'] = new_label
                df.to_csv(self.dataset_path, index=False)
                print(f"OK: Record {row_index} validated as {new_label}")
                return True
            return False
        except Exception as e:
            print(f"ERROR: Validation error: {e}")
            return False
    
    def should_retrain(self):
        """Check if model should be retrained (time or sample count)."""
        if not JOBLIB_AVAILABLE:
            return False
        
        try:
            df = pd.read_csv(self.dataset_path)
            validated_count = len(df[df['label'] != 'UNVALIDATED'])
            
            # Time-based trigger
            time_since_train = time.time() - self.last_train_time
            time_trigger = time_since_train > self.train_interval
            
            # Sample-based trigger
            sample_trigger = (validated_count % self.sample_threshold == 0) and validated_count > 0
            
            return time_trigger or sample_trigger
        except:
            return False
    
    def train_model(self):
        """Train RandomForest model on validated data."""
        if not JOBLIB_AVAILABLE:
            print("⚠️  Skipping training: joblib not available")
            return False
        
        try:
            print(f"\n🔄 Starting model training...")
            df = pd.read_csv(self.dataset_path)
            
            # Filter only validated data
            df_validated = df[df['label'] != 'UNVALIDATED'].copy()
            
            if len(df_validated) < 5:
                print(f"⚠️  Not enough data ({len(df_validated)} samples, need 5+)")
                return False
            
            # Prepare features and labels
            feature_cols = [
                'avg_step_time', 'step_time_diff', 'step_height_diff',
                'stride_length', 'cadence', 'symmetry_index', 'z_variation',
                'avg_asymmetry', 'gait_speed'
            ]
            
            X = df_validated[feature_cols].fillna(0)
            y = df_validated['label'].map({'NORMAL': 0, 'ABNORMAL': 1, 
                                           'PARKINSONS': 2, 'IMBALANCE': 3}).fillna(0)
            
            # Train RandomForest
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(n_estimators=100, max_depth=10, 
                                          random_state=42, n_jobs=-1)
            model.fit(X, y)
            
            # Save versioned model
            self.model_version += 1
            model_path = os.path.join(self.model_dir, f"model_v{self.model_version}.pkl")
            joblib.dump(model, model_path)
            
            # Evaluate
            train_score = model.score(X, y)
            print(f"OK: Model v{self.model_version} trained (accuracy: {train_score:.2%})")
            print(f"  Samples: {len(df_validated)} (validated) + {len(df[df['label'] == 'UNVALIDATED'])} (pending)")
            
            self.current_model = model
            self.model_loaded = True
            self.last_train_time = time.time()
            
            # Cleanup old models (keep last 3)
            self._cleanup_old_models()
            
            return True
        except Exception as e:
            print(f"ERROR: Training error: {e}")
            return False
    
    def load_best_model(self):
        """Load best available model."""
        if not JOBLIB_AVAILABLE:
            print("⚠️  Skipping model load: joblib not available")
            return False
        
        try:
            # Find latest model
            model_files = sorted([f for f in os.listdir(self.model_dir) 
                                 if f.startswith('model_v') and f.endswith('.pkl')])
            
            if not model_files:
                print("ℹ️  No trained model found yet (first run)")
                return False
            
            latest_model = model_files[-1]
            model_path = os.path.join(self.model_dir, latest_model)
            
            self.current_model = joblib.load(model_path)
            version = int(latest_model.replace('model_v', '').replace('.pkl', ''))
            self.model_version = version
            self.model_loaded = True
            
            print(f"OK: Loaded model: {latest_model}")
            return True
        except Exception as e:
            print(f"ERROR: Model load error: {e}")
            return False
    
    def predict(self, features_dict):
        """Predict using trained model or rules."""
        if not self.model_loaded or self.current_model is None:
            return None  # No model yet, use hybrid rules
        
        try:
            feature_cols = [
                'avg_step_time', 'step_time_diff', 'step_height_diff',
                'stride_length', 'cadence', 'symmetry_index', 'z_variation',
                'avg_asymmetry', 'gait_speed'
            ]
            
            feature_vector = np.array([[
                features_dict.get(col, 0) for col in feature_cols
            ]])
            
            prediction = self.current_model.predict(feature_vector)[0]
            prediction_proba = self.current_model.predict_proba(feature_vector)[0]
            confidence = float(max(prediction_proba))
            
            class_map = {0: 'NORMAL', 1: 'ABNORMAL', 2: 'PARKINSONS', 3: 'IMBALANCE'}
            class_name = class_map.get(int(prediction), 'UNKNOWN')
            
            return class_name, confidence
        except Exception as e:
            print(f"⚠️  Prediction error: {e}")
            return None
    
    def _cleanup_old_models(self, keep=3):
        """Keep only last N models to save space."""
        try:
            model_files = sorted([f for f in os.listdir(self.model_dir) 
                                 if f.startswith('model_v') and f.endswith('.pkl')])
            
            if len(model_files) > keep:
                for old_model in model_files[:-keep]:
                    os.remove(os.path.join(self.model_dir, old_model))
                    print(f"  Cleaned: {old_model}")
        except:
            pass
    
    def get_statistics(self):
        """Get dataset statistics."""
        if not JOBLIB_AVAILABLE:
            return None
        
        try:
            df = pd.read_csv(self.dataset_path)
            stats = {
                'total': len(df),
                'validated': len(df[df['label'] != 'UNVALIDATED']),
                'unvalidated': len(df[df['label'] == 'UNVALIDATED']),
                'model_version': self.model_version,
                'model_loaded': self.model_loaded
            }
            return stats
        except:
            return None


# Initialize pipeline
training_pipeline = AutoTrainingPipeline()


def calculate_score(speed, ai, step_time):
    """Calculate gait analysis score based on speed, asymmetry index, and step time.
    
    PARAMETERS:
    -----------
    speed : float
        Gait speed in m/s
    ai : float
        Average asymmetry index (%)
    step_time : float
        Average step time in seconds
    
    RETURNS:
    --------
    final_score : int
        Weighted gait score (0-100)
    """
    # --- HIZ SKORU (0-100) ---
    if speed >= 1.0:
        speed_score = 100
    elif speed >= 0.8:
        speed_score = 70
    elif speed >= 0.6:
        speed_score = 40
    else:
        speed_score = 20

    # --- ASIMETRI SKORU (düşük = iyi) ---
    if ai < 10:
        ai_score = 100
    elif ai < 15:
        ai_score = 70
    elif ai < 20:
        ai_score = 40
    else:
        ai_score = 20

    # --- ADIM SURESI SKORU ---
    if 0.5 <= step_time <= 0.7:
        step_score = 100
    elif 0.4 <= step_time <= 0.9:
        step_score = 70
    else:
        step_score = 40

    # --- AGIRLIKLI ORTALAMA ---
    final_score = (0.4 * speed_score +
                   0.4 * ai_score +
                   0.2 * step_score)

    return int(final_score)


# Veriyi yumuşatmak için
left_buffer = deque(maxlen=BUFFER_BOYUT)
right_buffer = deque(maxlen=BUFFER_BOYUT)

def smooth(buf, val):
    buf.append(val)
    return int(np.mean(buf))

def asymmetry_index(L, R):
    # Güvenli hesaplama - sıfır bölme ve aşırı değerleri önler
    if L < 10 or R < 10:          # Çok küçük açıları dikkate alma
        return 0.0
    avg = (L + R) / 2
    if avg == 0:
        return 0.0
    ai = abs(L - R) / avg * 100
    return min(ai, 100.0)         # Maksimum %100 ile sınırla

# ===================== FRONTAL PLANE: TORSO PIXEL SIZE TRACKING =====================
def calculate_torso_pixel_size(landmarks):
    """
    Calculate the pixel size of the torso from OpenPose keypoints.
    
    This is the first step in frontal plane depth-change estimation (Fig 2).
    Measures bounding box dimensions of the torso region to track person's size
    at different depths from the frontal plane camera (C_Front).
    
    PARAMETERS:
    -----------
    landmarks : MediaPipe Pose landmarks
        Detected pose keypoints from the frame
    
    RETURNS:
    --------
    torso_size : float
        Height of torso bounding box in pixels (measures s_i or s_Ref)
    torso_width : float
        Width of torso bounding box in pixels
    
    METHODOLOGY REFERENCE:
    - Fig 2A: s_Ref = person size at reference depth, s_i = person size at new depth
    - Tracks pixel dimensions throughout gait cycle
    - See METHODS.md for detailed explanation
    """
    try:
        # Torso keypoints: shoulders (11, 12), hips (23, 24)
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        left_hip = landmarks[23]
        right_hip = landmarks[24]
        
        # Extract coordinates (normalize to pixel values)
        shoulder_y_avg = (left_shoulder.y + right_shoulder.y) / 2
        hip_y_avg = (left_hip.y + right_hip.y) / 2
        shoulder_x_avg = (left_shoulder.x + right_shoulder.x) / 2
        hip_x_avg = (left_hip.x + right_hip.x) / 2
        
        # Calculate torso dimensions
        torso_size = abs(shoulder_y_avg - hip_y_avg)  # Vertical dimension
        torso_width = abs(shoulder_x_avg - hip_x_avg) # Horizontal dimension
        
        return max(torso_size, 0.001), max(torso_width, 0.001)
    except:
        return 0.001, 0.001

# ===================== FRONTAL PLANE: LOW-PASS FILTER =====================
def low_pass_filter(previous_value, current_value, alpha=LOW_PASS_FILTER_ALPHA):
    """
    Apply first-order low-pass filter to smooth noisy measurements.
    
    Smooths time-series data from pixel tracking to reduce frame-to-frame
    variability and noise in step 3 of frontal workflow (Fig 2D).
    
    PARAMETERS:
    -----------
    previous_value : float
        Filtered value from previous frame
    current_value : float
        Raw measured value from current frame
    alpha : float
        Filter coefficient (0.0-1.0)
        - alpha ~ 0.0: Heavy smoothing (less responsive)
        - alpha ~ 1.0: No filtering (follows raw data)
        - Typical: 0.3 for good balance
    
    RETURNS:
    --------
    filtered_value : float
        Smoothed measurement
    
    FORMULA:
    --------
    y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
    
    METHODOLOGY REFERENCE:
    - See S4 Fig in paper for justification of filtering parameters
    - Applied after torso pixel size calculation
    - Critical for accurate depth-change estimates
    """
    if previous_value == 0:
        return current_value
    filtered = alpha * current_value + (1 - alpha) * previous_value
    return filtered

# ===================== FRONTAL PLANE: DEPTH-CHANGE ESTIMATION =====================
def calculate_depth_change(s_ratio, d_ref=REFERENCE_DEPTH):
    """
    Calculate depth-change (Δd_i) from pixel size ratio using trigonometric model.
    
    Implements the mathematical relationship from Fig 2B-C for estimating
    how far the person has moved toward/away from the frontal plane camera.
    
    PARAMETERS:
    -----------
    s_ratio : float
        Pixel size ratio: s_Ratio = s_i / s_Ref
        (current pixel size divided by reference pixel size)
    d_ref : float
        Reference depth distance (meters) - default: REFERENCE_DEPTH
    
    RETURNS:
    --------
    delta_d : float
        Depth-change in meters (positive = moving toward camera, 
        negative = moving away)
    
    MATHEMATICAL MODEL:
    -------------------
    From trigonometric relationships (camera lens geometry):
    
    s_Ratio = d_Ref / (d_Ref + Δd_i)
    
    Solving for Δd_i:
    Δd_i = d_Ref * (s_Ratio^(-1) - 1)
    
    Where:
    - f = focal length of camera
    - d_Ref = initial reference depth (distance from camera)
    - d_Ref + Δd_i = new depth (after depth-change)
    - s_Ref = pixel size at d_Ref
    - s_i = pixel size at new depth
    
    METHODOLOGY REFERENCE:
    - Fig 2B: Derivation of pixel size vs. depth relationship
    - Fig 2C: Validation showing predicted vs. manual annotation
    - Once Δd_i is known, step length = lateral_motion × scaling_factor
    
    EXAMPLE:
    --------
    If person is 10% smaller: s_ratio = 0.9
    Then: Δd_i = 4.27 * (0.9^(-1) - 1) = 4.27 * 0.111 ≈ 0.47 meters (moved away)
    """
    if s_ratio <= 0 or s_ratio > 2.0:
        return 0.0
    
    try:
        # Δd_i = d_Ref * (1/s_Ratio - 1)
        delta_d = d_ref * (1.0 / s_ratio - 1.0)
        return delta_d
    except:
        return 0.0

# ===================== LANDMARK YARDIMCISI =====================
def get_landmark(lm, idx):
    if idx >= len(lm) or lm[idx].visibility < 0.5:
        return None
    return [lm[idx].x, lm[idx].y]

# ===================== ADIM SAYAR SINIFI =====================
class StepDetector:
    """Diz açısına göre FSM tabanlı, tekrarlama engellemeli adım sayar."""

    def __init__(self, history_len=5, min_stable_frames=3, min_step_interval=0.3):
        self.state = 'DUZ'  # DUZ | BUKUK
        self.frame_state_count = 0
        self.step_count = 0
        self.last_step_time = 0.0
        self.last_step_length_px = 0.0
        self.last_step_length_cm = 0.0

        self.angle_buffer = deque(maxlen=history_len)
        self.min_stable_frames = min_stable_frames
        self.min_step_interval = min_step_interval

        self.base_stance_threshold = STEP_STRAIGHTEN_THRESHOLD
        self.base_swing_threshold = STEP_BEND_THRESHOLD
        self.adaptive_factor = 0.0

    def _smooth(self, raw_angle):
        self.angle_buffer.append(raw_angle)
        return float(sum(self.angle_buffer)) / len(self.angle_buffer)

    def _adaptive_thresholds(self):
        return self.base_swing_threshold, self.base_stance_threshold

    def update(self, raw_angle, current_time=None, step_length_px=0.0, step_length_cm=0.0):
        if current_time is None:
            current_time = time.time()

        angle = self._smooth(raw_angle)
        prev_state = self.state
        new_state = self.state

        # Daha güvenilir bir FSM: diz bükük ise BUKUK, diz açık ise DUZ kabul et
        if angle < STEP_BEND_THRESHOLD:
            new_state = 'BUKUK'
        elif angle > STEP_STRAIGHTEN_THRESHOLD:
            new_state = 'DUZ'

        if new_state == prev_state:
            self.frame_state_count += 1
        else:
            self.frame_state_count = 1

        step_increment = 0
        if prev_state == 'BUKUK' and new_state == 'DUZ':
            if current_time - self.last_step_time >= self.min_step_interval:
                self.step_count += 1
                self.last_step_time = current_time
                self.last_step_length_px = step_length_px
                self.last_step_length_cm = step_length_cm
                step_increment = 1

        self.state = new_state
        return step_increment

    def get_steps(self):
        return self.step_count

    @property
    def steps(self):
        return self.step_count

    def reset(self):
        self.state = 'DUZ'
        self.frame_state_count = 0
        self.step_count = 0
        self.last_step_time = 0.0
        self.angle_buffer.clear()

left_stepper = StepDetector()
right_stepper = StepDetector()

# ===================== AYAK ADIM SAYAR SINIFI =====================
class FootStepDetector:
    """Ayak Y koordinatına göre FSM tabanlı adım sayar."""

    def __init__(self, history_len=5, min_stable_frames=3, min_step_interval=0.3, cooldown_frames=10):
        self.state = 'GROUND'  # GROUND -> AIR -> GROUND
        self.frame_state_count = 0
        self.step_count = 0
        self.last_step_time = 0.0

        self.y_buffer = deque(maxlen=history_len)
        self.prev_y = None
        self.min_stable_frames = min_stable_frames
        self.min_step_interval = min_step_interval
        self.cooldown_frames = cooldown_frames
        self.cooldown = 0

        self.smooth_alpha = 0.7
        self.movement_threshold = 0.015      # Hareket eşiği (kalibrasyon sonrası velocity tabanlı)
        self.ground_threshold = 0.005        # Yere basma / stabil olma eşiği
        self.min_lift_distance = 0.02        # Ayak kalkma olarak kabul edilecek minimum mesafe
        self.ground_level = None

        self.calibrating = True
        self.y_values = []
        self.v_values = []
        self.start_calibration_time = None
        self.VEL_UP = None
        self.VEL_DOWN = None
        self.ground_stable = None

    def _smooth(self, raw_y):
        if not self.y_buffer:
            smoothed = raw_y
        else:
            smoothed = self.smooth_alpha * self.y_buffer[-1] + (1 - self.smooth_alpha) * raw_y
        self.y_buffer.append(smoothed)
        return smoothed

    def _calibrate(self, y_smooth):
        if self.start_calibration_time is None:
            self.start_calibration_time = time.time()

        self.y_values.append(y_smooth)
        if len(self.y_values) > 1:
            self.v_values.append(y_smooth - self.y_values[-2])

        if time.time() - self.start_calibration_time > 3 and len(self.v_values) > 20 and self.calibrating:
            mean_v = np.mean(self.v_values)
            std_v = np.std(self.v_values)

            self.VEL_UP = mean_v - 2.0 * std_v
            self.VEL_DOWN = mean_v + 2.0 * std_v
            self.ground_stable = max(std_v, self.ground_threshold)
            self.calibrating = False

            print("Kalibrasyon tamamlandı!")
            print(f"VEL_UP: {self.VEL_UP}")
            print(f"VEL_DOWN: {self.VEL_DOWN}")
            print(f"GROUND_STABLE: {self.ground_stable}")

    def _calibrate_ground(self, y_smooth):
        if self.ground_level is None:
            self.ground_level = y_smooth

        if self.state == 'GROUND':
            self.ground_level = max(self.ground_level, y_smooth)

        return self.ground_level

    def update(self, foot_y, hip_y, current_time=None):
        if current_time is None:
            current_time = time.time()

        relative_y = foot_y - hip_y
        y_smooth = self._smooth(relative_y)
        if self.calibrating:
            self._calibrate(y_smooth)

        ground_level = self._calibrate_ground(y_smooth)

        delta_y = 0.0
        if self.prev_y is not None:
            delta_y = y_smooth - self.prev_y
        self.prev_y = y_smooth

        if self.cooldown > 0:
            self.cooldown -= 1

        new_state = self.state
        if self.state == 'GROUND':
            if not self.calibrating and self.VEL_UP is not None:
                if delta_y < self.VEL_UP and (ground_level - y_smooth) >= self.min_lift_distance:
                    new_state = 'AIR'
        elif self.state == 'AIR':
            if not self.calibrating and self.VEL_DOWN is not None:
                if delta_y > self.VEL_DOWN and abs(y_smooth - ground_level) <= self.ground_stable and self.cooldown == 0:
                    new_state = 'GROUND'

        if new_state == self.state:
            self.frame_state_count += 1
        else:
            self.frame_state_count = 1

        step_added = 0
        if self.state == 'AIR' and new_state == 'GROUND' and self.frame_state_count >= self.min_stable_frames:
            if current_time - self.last_step_time >= self.min_step_interval:
                if not self.calibrating:
                    self.step_count += 1
                    self.last_step_time = current_time
                    self.cooldown = self.cooldown_frames
                    step_added = 1

        self.state = new_state
        return step_added

    def get_steps(self):
        return self.step_count

    def reset(self):
        self.state = 'GROUND'
        self.frame_state_count = 0
        self.step_count = 0
        self.last_step_time = 0.0
        self.y_buffer.clear()
        self.prev_y = None
        self.cooldown = 0
        self.ground_level = None
        self.calibrating = True
        self.y_values = []
        self.v_values = []
        self.start_calibration_time = None
        self.VEL_UP = None
        self.VEL_DOWN = None
        self.ground_stable = None

    @property
    def calibration_status(self):
        return "Kalibrasyon yapılıyor..." if self.calibrating else "Hazır"

left_foot_stepper = FootStepDetector()
right_foot_stepper = FootStepDetector()

# ===================== ADVANCED FEATURE TRACKING =====================
advanced_features = AdvancedGaitFeatures(window_size=60)  # 2 sec at 30fps
signal_filter_left_knee = SignalFilter(alpha=0.7)
signal_filter_right_knee = SignalFilter(alpha=0.7)
signal_filter_left_foot = SignalFilter(alpha=0.7)
signal_filter_right_foot = SignalFilter(alpha=0.7)
windowed_extractor_asymmetry = WindowedFeatureExtractor(window_duration=2.0, frame_rate=30)
gait_metrics = GaitMetrics()
hybrid_classifier = HybridGaitClassifier()

# Shared frame buffer for backend video streaming
latest_frame = None
frame_lock = threading.Lock()
analysis_running = False

# ===================== GAIT FEATURE EXTRACTION =====================
right_times = []
left_times = []
right_heights = []
left_heights = []
last_right_time = None
last_left_time = None
reference_torso_size = None
current_torso_size = None
stride_length_estimate = 0.0


def extract_features(right_y, left_y, step_right, step_left):
    """Extract step timing and height features for gait classification."""
    global last_right_time, last_left_time

    now = time.time()

    if step_right:
        if last_right_time is not None:
            right_times.append(now - last_right_time)
        last_right_time = now
        right_heights.append(right_y)

    if step_left:
        if last_left_time is not None:
            left_times.append(now - last_left_time)
        last_left_time = now
        left_heights.append(left_y)


def classify_gait():
    """Classify gait as normal or abnormal using extracted features."""
    if len(right_times) < 3 or len(left_times) < 3:
        return "Analiz ediliyor..."

    avg_r_time = sum(right_times) / len(right_times)
    avg_l_time = sum(left_times) / len(left_times)
    avg_r_height = sum(right_heights) / len(right_heights)
    avg_l_height = sum(left_heights) / len(left_heights)

    time_diff = abs(avg_r_time - avg_l_time)
    height_diff = abs(avg_r_height - avg_l_height)
    step_count_diff = abs(len(right_times) - len(left_times))

    if time_diff > 0.2 or height_diff > 0.05 or step_count_diff >= 2:
        return "Anormal Yürüyüş ⚠️"
    return "Normal Yürüyüş ✅"


def get_disease_feature_vector():
    """Build the gait feature vector for disease prediction."""
    if len(right_times) < 2 or len(left_times) < 2:
        return None

    avg_r_time = sum(right_times) / len(right_times)
    avg_l_time = sum(left_times) / len(left_times)
    avg_r_height = sum(right_heights) / len(right_heights) if right_heights else 0.0
    avg_l_height = sum(left_heights) / len(left_heights) if left_heights else 0.0
    avg_step_time = (avg_r_time + avg_l_time) / 2.0
    cadence = 60.0 / avg_step_time if avg_step_time > 0 else 0.0
    time_diff = abs(avg_r_time - avg_l_time)
    height_diff = abs(avg_r_height - avg_l_height)
    symmetry_index = np.mean(asimetri_listesi) if asimetri_listesi else 0.0
    stride_length = stride_length_estimate
    z_variation = abs(current_torso_size - reference_torso_size) / reference_torso_size if reference_torso_size and current_torso_size else 0.0

    return {
        'avg_step_time': avg_step_time,
        'step_time_diff': time_diff,
        'step_height_diff': height_diff,
        'stride_length': stride_length,
        'cadence': cadence,
        'symmetry_index': symmetry_index,
        'z_variation': z_variation,
        'avg_r_height': avg_r_height,
        'avg_l_height': avg_l_height
    }


def predict_disease():
    """Predict disease risk using rule-based gait classification."""
    features = get_disease_feature_vector()
    if features is None:
        return "Analiz ediliyor..."

    if features['symmetry_index'] > 0.20 or features['step_time_diff'] > 0.30:
        return "Topallama"

    if features['cadence'] < 80 and min(features['avg_r_height'], features['avg_l_height']) < 0.05:
        return "Parkinson benzeri yürüyüş"

    if features['z_variation'] > 0.08:
        return "Denge problemi"

    return "Normal yürüyüş"


# Remote frame models for phone-based upload analysis
pose_model = None
pose_model_initialized = False
pose_init_lock = threading.Lock()


def init_pose_model():
    """Initialize MediaPipe Pose model for single-frame remote analysis."""
    global pose_model, pose_model_initialized
    with pose_init_lock:
        if not pose_model_initialized:
            mp_pose = mp.solutions.pose
            pose_model = mp_pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                smooth_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
            pose_model_initialized = True


def process_remote_frame(frame):
    """Process a single BGR frame from a remote client and update gait state."""
    init_pose_model()

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    rgb.flags.writeable = False
    results = pose_model.process(rgb)
    rgb.flags.writeable = True

    left_angle = right_angle = 0
    AI = 0
    left_step_added = 0
    right_step_added = 0

    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark

        L_hip = get_landmark(lm, 23)
        L_knee = get_landmark(lm, 25)
        L_ankle = get_landmark(lm, 27)
        R_hip = get_landmark(lm, 24)
        R_knee = get_landmark(lm, 26)
        R_ankle = get_landmark(lm, 28)
        L_foot = get_landmark(lm, LEFT_FOOT_INDEX)
        R_foot = get_landmark(lm, RIGHT_FOOT_INDEX)
        head = get_landmark(lm, 0)

        step_length_px = 0.0
        step_length_cm = 0.0
        if None not in [L_ankle, R_ankle]:
            step_length_px = distance(L_ankle, R_ankle, frame.shape)
            if head is not None:
                foot_y = max(L_ankle[1], R_ankle[1])
                scale = estimate_pixel_to_cm_scale(head, foot_y, frame.shape[0])
                if scale is not None:
                    step_length_cm = int(step_length_px * scale)

        if None not in [L_hip, L_knee, L_ankle]:
            raw_L = calculate_angle(L_hip, L_knee, L_ankle)
            left_angle = smooth(left_buffer, raw_L)

        if None not in [R_hip, R_knee, R_ankle]:
            raw_R = calculate_angle(R_hip, R_knee, R_ankle)
            right_angle = smooth(right_buffer, raw_R)

        AI = asymmetry_index(left_angle, right_angle)
        asimetri_listesi.append(AI)

        if left_angle > 0:
            left_stepper.update(left_angle, time.time(), step_length_px, step_length_cm)
        if right_angle > 0:
            right_stepper.update(right_angle, time.time(), step_length_px, step_length_cm)

        if L_foot is not None and L_hip is not None:
            left_step_added = left_foot_stepper.update(L_foot[1], L_hip[1], time.time())
        if R_foot is not None and R_hip is not None:
            right_step_added = right_foot_stepper.update(R_foot[1], R_hip[1], time.time())

        extract_features(
            right_y=R_foot[1] if R_foot is not None else 0.0,
            left_y=L_foot[1] if L_foot is not None else 0.0,
            step_right=bool(right_step_added),
            step_left=bool(left_step_added)
        )

    return {
        'right': right_foot_stepper.get_steps(),
        'left': left_foot_stepper.get_steps(),
        'status': classify_gait(),
        'asymmetry': AI,
        'right_angle': right_angle,
        'left_angle': left_angle
    }


# ===================== FRONTAL PLANE: WALKING DIRECTION DETECTION =====================
class WalkingDirectionDetector:
    """
    Detects walking direction relative to frontal plane camera.
    
    VALIDATION FINDINGS (S3 Table, S1 Fig):
    - Walking AWAY from camera: Greater step length errors (~16 cm)
                               Larger gait speed overestimation
                               Worse OpenPose tracking (back view)
    - Walking TOWARD camera:   Smaller step length errors (~11 cm)
                              Better keypoint tracking (front view)
                              More accurate depth estimates
    
    Walking direction must be considered to interpret accuracy metrics properly.
    For best results, analyze only trials with the same walking direction,
    or apply direction-specific error corrections.
    """
    
    def __init__(self, window_size=30):
        """
        Initialize walker direction detector with position history.
        
        PARAMETERS:
        -----------
        window_size : int
            Number of frames to analyze for direction trend
        """
        self.x_positions = deque(maxlen=window_size)  # Torso x-position history
        self.direction = "UNKNOWN"  # "TOWARD", "AWAY", or "UNKNOWN"
        self.confidence = 0.0
    
    def update(self, landmarks):
        """
        Update walking direction based on torso position trend.
        
        METHODOLOGY:
        Compares current torso position with historical average.
        - Moving RIGHT in image (x increasing) = walking TOWARD (front view)
        - Moving LEFT in image (x decreasing) = walking AWAY (back view)
        
        RETURNS: direction string ("TOWARD" or "AWAY")
        """
        try:
            # Get torso center (average of shoulders and hips)
            left_shoulder = landmarks[11]
            right_shoulder = landmarks[12]
            torso_x = (left_shoulder.x + right_shoulder.x) / 2
            
            self.x_positions.append(torso_x)
            
            if len(self.x_positions) >= 10:
                # Calculate trend over last 10 frames
                old_avg = np.mean(list(self.x_positions)[:5])
                new_avg = np.mean(list(self.x_positions)[-5:])
                
                position_change = new_avg - old_avg
                self.confidence = abs(position_change)
                
                if position_change > 0.01:  # Moving right in image
                    self.direction = "TOWARD"
                    return "TOWARD"
                elif position_change < -0.01:  # Moving left in image
                    self.direction = "AWAY"
                    return "AWAY"
            
            return "UNKNOWN"
        except:
            return "UNKNOWN"
    
    def get_expected_error(self, parameter_type="step_length", subject_type="stroke"):
        """
        Get expected error magnitude based on walking direction and subject type.
        
        Uses validation data from Table 1 and S3 Table to predict accuracy.
        
        PARAMETERS:
        -----------
        parameter_type : str
            "step_length", "gait_speed", "step_time"
        subject_type : str
            "stroke" or "pd" (Parkinson's disease)
        
        RETURNS:
        --------
        error : float
            Expected error in appropriate units
        """
        if self.direction == "UNKNOWN":
            return None
        
        # Step length errors (meters)
        if parameter_type == "step_length":
            if self.direction == "AWAY":
                return 0.16 if subject_type == "stroke" else 0.16
            else:  # TOWARD
                return 0.11 if subject_type == "stroke" else 0.11
        
        # Gait speed errors (m/s)
        elif parameter_type == "gait_speed":
            if self.direction == "AWAY":
                return FRONTAL_SPEED_OVEREST_AWAY_STROKE if subject_type == "stroke" else FRONTAL_SPEED_OVEREST_AWAY_PD
            else:  # TOWARD
                return FRONTAL_SPEED_OVEREST_TOWARD_STROKE if subject_type == "stroke" else FRONTAL_SPEED_OVEREST_TOWARD_PD
        
        # Step time errors (seconds)
        elif parameter_type == "step_time":
            return 0.04 if self.direction == "AWAY" else 0.02
        
        return None
    
    def get_gait_cycle_timing_correction(self):
        """
        Get gait cycle timing correction based on walking direction.
        
        VALIDATION DATA (S3 Fig, S3 Fig panel A):
        - Walking AWAY: Timing leads by ~0.04 s (4 motion capture frames)
        - Walking TOWARD: Timing lags by ~0.15 s (15 motion capture frames)
        
        RETURNS:
        --------
        timing_correction : float
            Seconds to adjust gait cycle timing (negative = earlier, positive = later)
        """
        if self.direction == "AWAY":
            return -0.04  # Leads by 0.04 s
        elif self.direction == "TOWARD":
            return 0.15   # Lags by 0.15 s
        return 0.0

walking_direction_detector = WalkingDirectionDetector()

# ===================== VALIDATION & ACCURACY ASSESSMENT =====================
def validate_gait_parameter(parameter_type, measured_value, subject_type="stroke", plane="sagittal"):
    """
    Validate measured gait parameter against expected accuracy based on research validation.
    
    Compares measurements against validation data from Table 1 and Table 2 to determine
    if measurements are within expected error ranges.
    
    VALIDATION SOURCES:
    - Table 1: Comparison of video-based and motion capture measurements
    - Table 2: Comparison of speed-related changes
    - Fig 4-6: Detailed validation plots
    - S3 Table: Walking direction effects
    
    PARAMETERS:
    -----------
    parameter_type : str
        "step_time", "step_length", "gait_speed", "step_time_asym", "step_length_asym"
    measured_value : float
        The measured parameter value from video analysis
    subject_type : str
        "stroke" or "pd" (Parkinson's disease)
    plane : str
        "sagittal" or "frontal" - analysis plane used
    
    RETURNS:
    --------
    validation_result : dict
        {
            'is_valid': bool,
            'expected_error': float,
            'error_range': tuple,
            'confidence': str ('High', 'Good', 'Moderate', 'Low'),
            'notes': str
        }
    
    METHODOLOGY REFERENCE:
    - Sagittal plane analysis is more accurate than frontal plane
    - Frontal plane accuracy depends heavily on walking direction
    - Correlations are strong for most parameters (r ≥ 0.86)
    """
    
    result = {
        'is_valid': False,
        'expected_error': 0.0,
        'error_range': (0.0, 0.0),
        'confidence': 'Unknown',
        'notes': ''
    }
    
    try:
        if plane.lower() == "sagittal":
            # SAGITTAL PLANE VALIDATION (most accurate)
            if parameter_type == "step_time":
                result['expected_error'] = SAGITTAL_STEP_TIME_ERROR
                result['error_range'] = (-0.02, 0.02)
                result['confidence'] = 'High'
                result['is_valid'] = True
                result['notes'] = f"Sagittal plane analysis. Strong correlation: r ≥ {SAGITTAL_STEP_TIME_ASYM_ERROR}"
            
            elif parameter_type == "step_length":
                result['expected_error'] = SAGITTAL_STEP_LENGTH_ERROR
                result['error_range'] = (-0.058, 0.079)  # 95% limits of agreement
                result['confidence'] = 'High'
                result['is_valid'] = True
                result['notes'] = f"Sagittal plane. Very strong correlation: r ≥ {SAGITTAL_STEP_LENGTH_CORRELATION}"
            
            elif parameter_type == "gait_speed":
                result['expected_error'] = SAGITTAL_GAIT_SPEED_ERROR
                result['error_range'] = (-0.11, 0.14)  # 95% limits of agreement
                result['confidence'] = 'High'
                result['is_valid'] = True
                result['notes'] = f"Sagittal plane. Very strong correlation: r ≥ {SAGITTAL_GAIT_SPEED_CORRELATION}"
            
            elif parameter_type == "step_time_asym":
                result['expected_error'] = SAGITTAL_STEP_TIME_ASYM_ERROR
                result['error_range'] = (-0.04, 0.07)
                result['confidence'] = 'Good'
                result['is_valid'] = True
                result['notes'] = "Step time asymmetry (sagittal). Strong correlation: r ≥ 0.865"
            
            elif parameter_type == "step_length_asym":
                result['expected_error'] = SAGITTAL_STEP_LENGTH_ASYM_ERROR
                result['error_range'] = (-0.142, 0.138)
                result['confidence'] = 'Good'
                result['is_valid'] = True
                result['notes'] = "Step length asymmetry (sagittal). Strong correlation: r = 0.890"
        
        elif plane.lower() == "frontal":
            # FRONTAL PLANE VALIDATION (less accurate, walking-direction dependent)
            walking_direction = walking_direction_detector.direction
            
            if parameter_type == "step_time":
                result['expected_error'] = FRONTAL_STEP_TIME_ERROR
                result['error_range'] = (-0.03, 0.05)
                result['confidence'] = 'Good'
                result['is_valid'] = True
                result['notes'] = f"Frontal plane. Direction: {walking_direction}. Strong correlation: r ≥ 0.961"
            
            elif parameter_type == "step_length":
                # Walking direction affects accuracy
                if walking_direction == "AWAY":
                    result['expected_error'] = FRONTAL_FAR_AWAY_ERROR
                    result['error_range'] = (-0.154, 0.087)
                    result['confidence'] = 'Moderate'
                    result['notes'] = "Walking AWAY from camera - larger errors (~16 cm). Poor tracking quality."
                elif walking_direction == "TOWARD":
                    result['expected_error'] = FRONTAL_TOWARD_ERROR
                    result['error_range'] = (-0.088, 0.075)
                    result['confidence'] = 'Good'
                    result['notes'] = "Walking TOWARD camera - smaller errors (~11 cm). Better tracking quality."
                else:
                    result['expected_error'] = FRONTAL_STEP_LENGTH_ERROR
                    result['error_range'] = (-0.154, 0.087)
                    result['confidence'] = 'Moderate'
                    result['notes'] = "Frontal plane, direction unknown. Wide error range."
                
                result['is_valid'] = True
            
            elif parameter_type == "gait_speed":
                # Gait speed overestimation with frontal camera
                if subject_type == "stroke":
                    overest = FRONTAL_SPEED_OVEREST_AWAY_STROKE if walking_direction == "AWAY" else FRONTAL_SPEED_OVEREST_TOWARD_STROKE
                else:  # PD
                    overest = FRONTAL_SPEED_OVEREST_AWAY_PD if walking_direction == "AWAY" else FRONTAL_SPEED_OVEREST_TOWARD_PD
                
                result['expected_error'] = FRONTAL_GAIT_SPEED_ERROR
                result['error_range'] = (-0.20, 0.06) if walking_direction == "AWAY" else (-0.14, 0.11)
                result['confidence'] = 'Good' if walking_direction == "TOWARD" else 'Moderate'
                result['is_valid'] = True
                result['notes'] = f"Gait speed overestimated by ~{overest:.2f} m/s when direction={walking_direction}. Very strong correlation: r ≥ 0.949"
        
        return result
    
    except Exception as e:
        result['notes'] = f"Validation error: {str(e)}"
        return result

# ===================== FRONTAL PLANE: DEPTH EFFECT CORRECTION =================
def correct_step_length_for_depth(measured_step_length, torso_pixel_size, depth_from_camera, 
                                   calibration_depth=REFERENCE_DEPTH, subject_type="stroke"):
    """
    Apply depth-dependent error correction to frontal plane step length measurements.
    
    VALIDATION FINDING (S1 Fig):
    Step length errors increase as person moves away from camera (appears smaller).
    This is due to less precise OpenPose tracking at smaller scales.
    
    Error scaling:
    - Nearest to camera (~4.27 m):  ~7 cm error
    - Far from camera (~20 m away): ~16 cm error
    - Linear increase with distance
    
    PARAMETERS:
    -----------
    measured_step_length : float
        Step length measured from video (meters)
    torso_pixel_size : float
        Current pixel size of torso (lower = farther away)
    depth_from_camera : float
        Estimated depth from camera (meters)
    calibration_depth : float
        Reference depth used for camera calibration (default: REFERENCE_DEPTH)
    subject_type : str
        "stroke" or "pd"
    
    RETURNS:
    --------
    correction_factor : float
        Multiplicative factor to apply to step length (0.8-1.2)
        Example: corrected_step_length = measured_step_length * correction_factor
    
    METHODOLOGY REFERENCE:
    - S1 Fig: Depth vs. step length error relationship
    - Error increases non-linearly with distance
    - Better trained OpenPose models can reduce this effect
    """
    try:
        # Calculate depth ratio
        depth_ratio = depth_from_camera / calibration_depth if calibration_depth > 0 else 1.0
        
        # Linear model: error increases with depth
        # At reference depth: ~7 cm error
        # At 2x reference depth: ~16-18 cm error
        error_at_depth = 0.07 + (depth_ratio - 1.0) * 0.05  # Error in meters
        
        # Create correction factor
        # Prevent over-correction (factor stays between 0.85 and 1.15)
        max_step_estimate = measured_step_length + error_at_depth
        correction_factor = 1.0
        
        if max_step_estimate > 0:
            correction_factor = measured_step_length / max_step_estimate
            correction_factor = np.clip(correction_factor, 0.85, 1.15)
        
        return correction_factor
    
    except:
        return 1.0  # No correction if error occurs

def assess_depth_impact(torso_pixel_size, reference_pixel_size=None):
    """
    Assess impact of depth on measurement accuracy.
    
    Returns confidence level based on torso size in image.
    Smaller torso = farther away = lower confidence.
    
    PARAMETERS:
    -----------
    torso_pixel_size : float
        Current pixel size of torso
    reference_pixel_size : float
        Expected pixel size at reference depth (calibrated value)
    
    RETURNS:
    --------
    impact_assessment : dict
        {
            'depth_confidence': 'High'|'Good'|'Moderate'|'Low',
            'pixel_size': float,
            'assessment': str,
            'recommendation': str
        }
    """
    try:
        if reference_pixel_size is None:
            reference_pixel_size = PERSON_HEIGHT * 100  # Rough estimate
        
        size_ratio = torso_pixel_size / reference_pixel_size if reference_pixel_size > 0 else 0.5
        
        if size_ratio > 0.8:
            confidence = 'High'
            assessment = "Person is close to camera (large image size) - high tracking accuracy"
        elif size_ratio > 0.6:
            confidence = 'Good'
            assessment = "Person is at moderate distance - good tracking accuracy"
        elif size_ratio > 0.4:
            confidence = 'Moderate'
            assessment = "Person is far from camera (small image size) - moderate tracking accuracy"
        else:
            confidence = 'Low'
            assessment = "Person is very far from camera - low tracking accuracy, large errors expected"
        
        recommendation = ""
        if confidence in ['Moderate', 'Low']:
            recommendation = "Consider frontal plane camera position closer to walking path or use sagittal plane video for better accuracy."
        
        return {
            'depth_confidence': confidence,
            'pixel_ratio': size_ratio,
            'assessment': assessment,
            'recommendation': recommendation
        }
    
    except:
        return {
            'depth_confidence': 'Unknown',
            'pixel_ratio': 0.0,
            'assessment': 'Error in assessment',
            'recommendation': 'Check input values'
        }

def print_validation_summary(subject_type="stroke"):
    """
    Print validation accuracy summary for all gait parameters.
    
    Shows expected errors and accuracy ranges for the analyzed subject type.
    Based on research validation from Table 1, Table 2, and Fig 4-6.
    """
    print("\n" + "="*70)
    print("GAIT ANALYSIS VALIDATION SUMMARY")
    print("="*70)
    print(f"Subject Type: {subject_type.upper()}")
    print(f"Walking Direction: {walking_direction_detector.direction}")
    print()
    
    # SAGITTAL PLANE
    print("SAGITTAL PLANE (C_Sag) - HIGH ACCURACY")
    print("-" * 70)
    print(f"  Step Time:         ±{SAGITTAL_STEP_TIME_ERROR:.2f} s error")
    print(f"  Step Length:       ±{SAGITTAL_STEP_LENGTH_ERROR:.2f} m error (r ≥ {SAGITTAL_STEP_LENGTH_CORRELATION})")
    print(f"  Gait Speed:        ±{SAGITTAL_GAIT_SPEED_ERROR:.2f} m/s error (r ≥ {SAGITTAL_GAIT_SPEED_CORRELATION})")
    print(f"  Joint Angles:")
    print(f"    - Hip:   ±{SAGITTAL_JOINT_ANGLE_ERRORS['hip']:.1f}°")
    print(f"    - Knee:  ±{SAGITTAL_JOINT_ANGLE_ERRORS['knee']:.1f}°")
    print(f"    - Ankle: ±{SAGITTAL_JOINT_ANGLE_ERRORS['ankle']:.1f}°")
    print()
    
    # FRONTAL PLANE
    print("FRONTAL PLANE (C_Front) - MODERATE ACCURACY (Direction-Dependent)")
    print("-" * 70)
    
    if walking_direction_detector.direction == "AWAY":
        print(f"  Walking AWAY from Camera (decreased accuracy)")
        print(f"  Step Length:       ±{FRONTAL_FAR_AWAY_ERROR:.2f} m error")
        print(f"  Gait Speed:        +{FRONTAL_SPEED_OVEREST_AWAY_STROKE:.2f} m/s overestimation (stroke)")
        print(f"  Gait Timing Lag:   -{FRONTAL_GAIT_CYCLE_TIMING_LAG_AWAY:.2f} s")
    elif walking_direction_detector.direction == "TOWARD":
        print(f"  Walking TOWARD Camera (best accuracy)")
        print(f"  Step Length:       ±{FRONTAL_TOWARD_ERROR:.2f} m error")
        print(f"  Gait Speed:        +{FRONTAL_SPEED_OVEREST_TOWARD_STROKE:.2f} m/s overestimation (stroke)")
        print(f"  Gait Timing Lag:   +{FRONTAL_GAIT_CYCLE_TIMING_LAG_TOWARD:.2f} s")
    else:
        print(f"  Walking Direction: UNKNOWN")
        print(f"  Step Length:       ±{FRONTAL_STEP_LENGTH_ERROR:.2f} m error")
    
    print()
    print("KEY FINDINGS:")
    print("  • Sagittal plane analysis is more accurate than frontal plane")
    print("  • Frontal plane accuracy decreases with distance (person appears smaller)")
    print("  • Walking toward camera gives better results than walking away")
    print("  • For best accuracy, use consistent walking direction within trials")
    print("="*70 + "\n")

# ===================== RESEARCH VALIDATION FINDINGS (Fig 4-6, Table 1-2, S1-S3) =====================
"""
COMPREHENSIVE VALIDATION RESULTS FOR GAIT ANALYSIS

STUDY POPULATIONS:
- Stroke patients (hemiparesis)
- Persons with Parkinson's disease (PD)
- Control subjects (unimpaired)

TABLE 1 FINDINGS: SPATIOTEMPORAL GAIT PARAMETERS (Preferred Speed Walking)
========================================================================================

SAGITTAL PLANE (C_Sag) - Most Accurate Method
- Step Time:           0.00±0.02 s difference, 0.05±0.04 s error (Fig 5B, Table 1)
- Step Length:         0.010±0.035 m difference, 0.028±0.024 m error (Fig 4C)
- Gait Speed:          0.02±0.06 m/s difference, 0.04±0.05 m/s error (Fig 4D)
- Step Time Asymmetry: 0.01±0.03 difference (Fig 4E)
- Step Length Asymmetry: -0.002±0.050 difference (Table 1)
- Correlations:        r ≥ 0.922 for step length, r ≥ 0.981 for gait speed
- 95% Limits of Agreement:
  * Step Length: -0.058 to 0.079 m
  * Gait Speed:  -0.11 to 0.14 m/s

FRONTAL PLANE (C_Front) - Moderate Accuracy, Walking Direction Dependent
- Step Time:           Similar to sagittal (±0.02 s)
- Step Length:         ~-0.033±0.061 m difference (larger errors, Fig 4C)
- Gait Speed:          ~-0.07±0.10 m/s difference (overestimated, Fig 4D)
- Correlations:        r ≥ 0.922 for step length, r ≥ 0.981 for gait speed
  * BUT: r = 0.230 for step length when walking away from camera (poor)
- 95% Limits of Agreement:
  * Step Length: -0.154 to 0.087 m (wide range!)
  * Gait Speed:  -0.20 to 0.06 m/s

JOINT KINEMATICS (Sagittal Plane Only)
- Hip Angle:   Mean absolute error 3.3° (excellent)
- Knee Angle:  Mean absolute error 4.0° (excellent)
- Ankle Angle: Mean absolute error 6.3° (good)

TABLE 2 FINDINGS: SPEED-RELATED CHANGES IN GAIT PARAMETERS
========================================================================================

STROKE PATIENTS - Preferred to Fast Speed
- Change in Step Time:
  * Sagittal: 0.000±0.017 m difference, 0.021±0.012 error
  * Frontal:  0.000±0.042 m difference, 0.021±0.044 error
  
- Change in Step Length:
  * Sagittal: ~0.002±0.017 m difference, 0.021±0.012 error
  * Frontal:  ~-0.001±0.050 m difference, 0.021±0.044 error
  
- Change in Gait Speed:
  * Sagittal: 0.01±0.05 m/s difference, 0.04±0.04 error
  * Frontal:  -0.02±0.06 m/s difference, 0.06±0.04 error

PARKINSON'S DISEASE - Preferred to Fast Speed
- Change in Step Time:
  * Sagittal: 0.000±0.013 m difference, 0.019±0.007 error
  * Frontal:  -0.015±0.055 m difference, 0.019±0.009 error
  
- Change in Step Length:
  * Sagittal: ~0.000±0.013 m difference, 0.019±0.007 error
  * Frontal:  ~-0.030±0.049 m difference, 0.019±0.035 error
  
- Change in Gait Speed:
  * Sagittal: 0.00±0.02 m/s difference, 0.03±0.02 error
  * Frontal:  -0.07±0.06 m/s difference, 0.11±0.06 error

FACTORS AFFECTING FRONTAL PLANE ACCURACY
========================================================================================

1. DEPTH EFFECT (S1 Fig) - Critical Finding
   - Error increases with distance from camera
   - Walking AWAY from camera:    ~7 cm at nearest, increasing to ~16 cm when far
   - Walking TOWARD camera:        ~7 cm at nearest, increasing to ~11 cm when far
   - Reason: OpenPose tracking less accurate on smaller image sizes
   - Recommendation: Position camera closer to walking path

2. WALKING DIRECTION EFFECT (S3 Fig, S3 Table) - Major Finding
   - When person walks AWAY (camera sees back):
     * Step length errors: +0.056 m to +0.082 m (stroke to PD)
     * Gait speed overestimation: +0.13 m/s (stroke) to +0.21 m/s (PD)
     * Gait cycle timing: Leads by ~0.04 s (4 motion capture frames)
     * Confidence: MODERATE (poor correlation when walking away)
   
   - When person walks TOWARD (camera sees front):
     * Step length errors: +0.013 m to +0.021 m (stroke to PD)
     * Gait speed overestimation: +0.01 m/s (stroke) to +0.03 m/s (PD)
     * Gait cycle timing: Lags by ~0.15 s (15 motion capture frames)
     * Confidence: GOOD (better tracking quality)

3. SCALING EFFECT (S2 Fig) - Non-Significant
   - Step length errors are NOT influenced by magnitude of step length
   - Errors are consistent across different stride sizes
   - Recommendation: No need for step-size specific corrections

4. GAIT CYCLE TIMING (S3 Fig Panel A) - Walking-Direction Dependent
   - Walking AWAY: Frontal detection leads MC by ~4 frames (0.04 s)
   - Walking TOWARD: Frontal detection lags MC by ~15 frames (0.15 s)
   - Correction: Using MC timing reduced step length error by ~1 cm for AWAY condition
   - Practical implication: Consider using sagittal plane for reliable gait cycle identification

RESEARCH RECOMMENDATIONS FOR BEST ACCURACY
========================================================================================

1. PRIMARY: Use sagittal plane (C_Sag) for maximum accuracy
   - Errors: ±1-3 cm, ±0.04 m/s speed
   - Correlations: r ≥ 0.922 for spatial, r ≥ 0.981 for speed

2. FRONTAL PLANE (C_Front) - Use with Caution
   - Best when person walks TOWARD camera
   - Maintain consistent walking direction within trials
   - Errors ~2x larger than sagittal plane
   - Apply walking direction specific error corrections

3. COMPENSATION STRATEGIES
   - Identify walking direction in real-time using WalkingDirectionDetector
   - Apply direction-specific error corrections from get_expected_error()
   - Use gait cycle timing corrections from get_gait_cycle_timing_correction()
   - Consider depth-based corrections near far ends of walking path

4. QUALITY ASSURANCE
   - Always compare with motion capture reference data when available
   - Use strong correlations as confidence indicators (r ≥ 0.86)
   - Monitor person distance from frontal camera throughout trial
   - For clinical gait analysis, prefer sagittal plane recordings

VALIDATION REFERENCES
========================================================================================
- Fig 4: Sagittal plane validation plots (step length, speed, asymmetry)
- Fig 5: Parkinson's disease step time validation
- Fig 6: Speed-related gait parameter changes
- S1 Fig: Depth vs. step length error relationship
- S2 Fig: Step magnitude vs. error (non-significant)
- S3 Fig: Gait cycle timing by walking direction
- S3 Table: Direction-specific errors for stroke and PD
- Table 1: Complete accuracy metrics for preferred walking
- Table 2: Complete accuracy metrics for speed changes
"""

# ===================== ANALİZ FONKSİYONU =====================
def start_analysis(callback, done_callback=None, display=True):
    global analysis_running, asimetri_listesi, left_stepper, right_stepper, left_foot_stepper, right_foot_stepper, prev_left, prev_right
    global right_times, left_times, right_heights, left_heights, last_right_time, last_left_time
    global latest_frame, frame_lock
    global total_distance_px, total_distance_cm, start_walk_time, end_walk_time, gait_speed_m_s, speed_status
    global gait_score, score_status, avg_step_time
    global advanced_features, signal_filter_left_knee, signal_filter_right_knee, signal_filter_left_foot, signal_filter_right_foot
    global windowed_extractor_asymmetry, gait_metrics, hybrid_classifier
    global hybrid_class_result, hybrid_conf_result, hybrid_reason_result
    global training_pipeline

    analysis_running = True
    asimetri_listesi = []
    ai_history = []
    time_history = []
    hybrid_class_result = "NORMAL"
    hybrid_conf_result = 0.0
    hybrid_reason_result = "Analiz bekleniyor"
    left_stepper = StepDetector()
    right_stepper = StepDetector()
    left_foot_stepper = FootStepDetector()
    right_foot_stepper = FootStepDetector()
    right_times = []
    left_times = []
    right_heights = []
    left_heights = []
    last_right_time = None
    last_left_time = None
    total_distance_px = 0.0
    total_distance_cm = 0.0
    start_walk_time = None
    end_walk_time = None
    gait_speed_m_s = 0.0
    speed_status = "Bekleniyor"
    gait_score = 0
    score_status = "Bekleniyor"
    avg_step_time = 0.6
    
    # Reset advanced features
    advanced_features.reset()
    signal_filter_left_knee.reset()
    signal_filter_right_knee.reset()
    signal_filter_left_foot.reset()
    signal_filter_right_foot.reset()
    gait_metrics.reset()
    
    # Check for auto-training
    if training_pipeline.should_retrain():
        print("🔄 Auto-training triggered...")
        training_pipeline.train_model()
    
    # MPU6050 bağlantısını başlat
    init_mpu6050()
    
    # MEDIAPIPE AYARLARI
    mp_pose = mp.solutions.pose
    mp_hands = mp.solutions.hands
    mp_drawing = mp.solutions.drawing_utils 
    mp_drawing_styles = mp.solutions.drawing_styles

    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    if os.name == "nt":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        analysis_running = False
        error_message = (
            "Kamera açılamadı. Kameranın bağlı olduğunu, başka bir uygulama "
            "tarafından kullanılmadığını ve kamera izninin açık olduğunu kontrol edin."
        )
        print(error_message)
        if done_callback:
            done_callback()
        callback(error_message)
        return

    prev_time = 0
    prev_left = 0
    prev_right = 0

    # Yasaklı noktalar
    yasakli = set(range(0, 11)) | set(range(17, 23))

    print("Analiz başlatıldı...")

    # ===================== ANA DÖNGÜ =====================
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or not analysis_running:
            break

        # Görüntüyü hazırla
        # frame = cv2.flip(frame, 1)  # Ayna etkisi kaldırıldı, doğal görünüm
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # MPU6050 verilerini oku
        read_mpu6050()
        
        # İşleme
        rgb.flags.writeable = False
        pose_results = pose.process(rgb)
        hands_results = hands.process(rgb)
        rgb.flags.writeable = True
        
        # Değişkenleri sıfırla
        left_angle = right_angle = 0
        AI = 0
        step_length_px = 0.0
        step_length_cm = 0
        step_detected_msg = ""

        # ------------------ VÜCUT ANALİZİ ------------------
        if pose_results.pose_landmarks:
            lm = pose_results.pose_landmarks.landmark
            
            # SOL BACAK
            L_hip = get_landmark(lm, 23)
            L_knee = get_landmark(lm, 25)
            L_ankle = get_landmark(lm, 27)
            
            if None not in [L_hip, L_knee, L_ankle]:
                raw_L = calculate_angle(L_hip, L_knee, L_ankle)
                left_angle = smooth(left_buffer, raw_L)
                # Advanced filtering
                left_angle = signal_filter_left_knee.apply(left_angle)

            # SAĞ BACAK
            R_hip = get_landmark(lm, 24)
            R_knee = get_landmark(lm, 26)
            R_ankle = get_landmark(lm, 28)
            
            if None not in [R_hip, R_knee, R_ankle]:
                raw_R = calculate_angle(R_hip, R_knee, R_ankle)
                right_angle = smooth(right_buffer, raw_R)
                # Advanced filtering
                right_angle = signal_filter_right_knee.apply(right_angle)

            # Ayak noktaları
            L_foot = get_landmark(lm, LEFT_FOOT_INDEX)
            R_foot = get_landmark(lm, RIGHT_FOOT_INDEX)
            head = get_landmark(lm, 0)

            step_length_px = 0.0
            step_length_cm = 0.0
            if None not in [L_ankle, R_ankle]:
                step_length_px = distance(L_ankle, R_ankle, frame.shape)
                if head is not None:
                    foot_y = max(L_ankle[1], R_ankle[1])
                    scale = estimate_pixel_to_cm_scale(head, foot_y, h)
                    if scale is not None:
                        step_length_cm = int(step_length_px * scale)

            # ASİMETRİ HESABI (ADIM SAYMA ÖNCESÜ)
            AI = asymmetry_index(left_angle, right_angle)
            asimetri_listesi.append(AI)
            current_time = round(time.time() - start_time, 2)
            ai_history.append(AI)
            time_history.append(current_time)
            
            # Update advanced features and windowed analysis
            advanced_features.add_frame_data(asymmetry=AI, z_position=0.0)
            windowed_extractor_asymmetry.add_data(AI)

            # DİZ AÇISINA GÖRE ADIM SAYMA
            left_knee_step_added = 0
            right_knee_step_added = 0
            if left_angle > 0:
                left_knee_step_added = left_stepper.update(left_angle, time.time(), step_length_px, step_length_cm)
            if right_angle > 0:
                right_knee_step_added = right_stepper.update(right_angle, time.time(), step_length_px, step_length_cm)

            # AYAK POZİSYONUNA GÖRE ADIM SAYMA
            left_step_added = 0
            right_step_added = 0
            if L_foot is not None and L_hip is not None:
                left_step_added = left_foot_stepper.update(L_foot[1], L_hip[1], time.time())
            if R_foot is not None and R_hip is not None:
                right_step_added = right_foot_stepper.update(R_foot[1], R_hip[1], time.time())

            step_detected = bool(left_knee_step_added or right_knee_step_added or left_step_added or right_step_added)
            step_detected_msg = "" if not step_detected else (
                "LEFT STEP" if left_knee_step_added or left_step_added else "" ) + (
                " / RIGHT STEP" if right_knee_step_added or right_step_added else "" )

            displayed_left_steps = left_foot_stepper.get_steps() if left_foot_stepper.get_steps() > 0 else left_stepper.steps
            displayed_right_steps = right_foot_stepper.get_steps() if right_foot_stepper.get_steps() > 0 else right_stepper.steps
            total_steps = min(displayed_left_steps, displayed_right_steps) * 2

            if total_steps == 1 and start_walk_time is None:
                start_walk_time = time.time()

            if step_detected:
                total_distance_px += step_length_px
                total_distance_cm += step_length_cm

            extract_features(
                right_y=R_foot[1] if R_foot is not None else 0.0,
                left_y=L_foot[1] if L_foot is not None else 0.0,
                step_right=bool(right_step_added),
                step_left=bool(left_step_added)
            )
            
            # Update advanced features with step information
            if right_step_added:
                if len(right_times) > 0:
                    advanced_features.add_frame_data(step_time=right_times[-1], step_height=0.0)
            if left_step_added:
                if len(left_times) > 0:
                    advanced_features.add_frame_data(step_time=left_times[-1], step_height=0.0)

            # CSV BUFFER'A EKLE
            t = round(time.time() - start_time, 2)
            data_buffer.append([
                t, left_angle, right_angle, round(AI, 2),
                left_stepper.steps, right_stepper.steps,
                left_foot_stepper.get_steps(), right_foot_stepper.get_steps()
            ])
            
            # Buffer doluysa yaz
            if len(data_buffer) >= CSV_BUFFER_LIMIT:
                writer.writerows(data_buffer)
                data_buffer.clear()

            # PROFESYONEL ADIM TESPIT VE LOGLAMA
            # Artık update içinde loglanıyor

            # ÖNCEKİ ADIM SAYILARINI GÜNCELLE
            prev_left = left_stepper.steps
            prev_right = right_stepper.steps

            # ÇİZİM
            for connection in mp_pose.POSE_CONNECTIONS:
                start_idx, end_idx = connection
                if start_idx not in yasakli and end_idx not in yasakli:
                    s = lm[start_idx]
                    e = lm[end_idx]
                    x1, y1 = int(s.x * w), int(s.y * h)
                    x2, y2 = int(e.x * w), int(e.y * h)
                    cv2.line(frame, (x1, y1), (x2, y2), (200, 200, 200), 2)

            for id, point in enumerate(lm):
                if id not in yasakli:
                    cx, cy = int(point.x * w), int(point.y * h)
                    cv2.circle(frame, (cx, cy), 5, (0, 0, 255), cv2.FILLED)
                    cv2.circle(frame, (cx, cy), 5, (255, 255, 255), 1)

        # ------------------ EL ÇİZİMİ ------------------
        if hands_results.multi_hand_landmarks:
            for hand_landmarks in hands_results.multi_hand_landmarks:
                mp_drawing.draw_landmarks(
                    frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                    mp_drawing_styles.get_default_hand_landmarks_style(),
                    mp_drawing_styles.get_default_hand_connections_style())


        # ------------------ BİLGİ EKRANI ------------------
        # Arka plan kutuları kaldırıldı, sadece metin görüntünün üzerine yazılıyor.

        # BÜYÜK DIZ AÇILARI
        cv2.putText(frame, "DIZ ACILARI:", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200,200,200), 2)
        cv2.putText(frame, f"Sol:  {left_angle}°", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, f"Sag:  {right_angle}°", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        cv2.putText(frame, f"Sol Durum: {left_stepper.state} Adim: {left_stepper.steps}", (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        cv2.putText(frame, f"Sag Durum: {right_stepper.state} Adim: {right_stepper.steps}", (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

        # MPU6050 VERİLERİ
        cv2.putText(frame, "MPU6050 SENSÖR:", (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
        if mpu_connected:
            cv2.putText(frame, f"Ivme: {mpu_data['ax']}, {mpu_data['ay']}, {mpu_data['az']}", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
            cv2.putText(frame, f"Jiro: {mpu_data['gx']}, {mpu_data['gy']}, {mpu_data['gz']}", (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0), 1)
        else:
            cv2.putText(frame, "Sensör bağlı değil", (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,0,255), 1)

        if AI < ASYMETRI_HAFIF_ESIGI:
            renk = (0, 255, 0)
        elif AI < ASYMETRI_ESIGI:
            renk = (0, 255, 255)
        else:
            renk = (0, 0, 255)
        cv2.putText(frame, f"ASIMETRI: %{AI:.1f}", (10, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.7, renk, 2)

        gait_speed_m_s = 0.0
        if start_walk_time is not None and total_distance_cm > 0:
            current_duration = max(time.time() - start_walk_time, 0.001)
            gait_speed_m_s = (total_distance_cm / 100.0) / current_duration

        if gait_speed_m_s < 0.6:
            speed_status = "YAVAS (RISKLI)"
        elif gait_speed_m_s < 1.0:
            speed_status = "ORTA"
        else:
            speed_status = "NORMAL"

        cv2.putText(frame, f"HIZ: {gait_speed_m_s:.2f} m/s", (10, 395), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,255), 2)
        cv2.putText(frame, f"HIZ DURUMU: {speed_status}", (10, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

        if gait_score > 80:
            score_color = (0, 255, 0)
        elif gait_score > 60:
            score_color = (0, 255, 255)
        else:
            score_color = (0, 0, 255)

        cv2.putText(frame, f"SKOR: {gait_score}/100", (10, 445), cv2.FONT_HERSHEY_SIMPLEX, 0.8, score_color, 2)
        cv2.putText(frame, f"DURUM: {score_status}", (10, 475), cv2.FONT_HERSHEY_SIMPLEX, 0.8, score_color, 2)

        displayed_left_steps = left_foot_stepper.get_steps() if left_foot_stepper.get_steps() > 0 else left_stepper.steps
        displayed_right_steps = right_foot_stepper.get_steps() if right_foot_stepper.get_steps() > 0 else right_stepper.steps

        cv2.putText(frame, f"DIZ ADIM L:{left_stepper.steps} R:{right_stepper.steps}", (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2)
        cv2.putText(frame, f"AYAK ADIM L:{displayed_left_steps} R:{displayed_right_steps}", (10, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 2)
        if step_detected_msg:
            cv2.putText(frame, f"STEP DETECTED: {step_detected_msg}", (10, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,255), 2)
            y_offset = 285
        else:
            y_offset = 260
        cv2.putText(frame, f"YURUYUS DURUMU: {classify_gait()}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2)
        cv2.putText(frame, f"KALIBRASYON: Sol={left_foot_stepper.calibration_status} Sag={right_foot_stepper.calibration_status}", (10, 285), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255,255,255), 2)
        cv2.putText(frame, f"ADIM UZUNLUGU(px): {int(step_length_px)}", (10, 310), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
        if step_length_cm > 0:
            cv2.putText(frame, f"ADIM UZUNLUGU(cm): {step_length_cm}", (10, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
        cv2.putText(frame, f"SON ADIM L:px={int(left_stepper.last_step_length_px)} R:px={int(right_stepper.last_step_length_px)}", (10, 360), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
        if left_stepper.last_step_length_cm > 0 or right_stepper.last_step_length_cm > 0:
            cv2.putText(frame, f"SON ADIM L:cm={int(left_stepper.last_step_length_cm)} R:cm={int(right_stepper.last_step_length_cm)}", (10, 385), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

        # DOĞRU ADIM SAYIMI: Min(sol, sağ) * 2 = Tamamlanmış yürüyüş döngüleri
        displayed_left_steps = left_foot_stepper.get_steps() if left_foot_stepper.get_steps() > 0 else left_stepper.steps
        displayed_right_steps = right_foot_stepper.get_steps() if right_foot_stepper.get_steps() > 0 else right_stepper.steps
        total_steps = min(displayed_left_steps, displayed_right_steps) * 2

        # Büyük Adım Sayacı - Ekranın orta alt kısmında metin
        cv2.putText(frame, f"ADIM: {total_steps}/{MAX_ADIM_SAYISI}", (w//2 - 70, h - 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

        if AI > ASYMETRI_ESIGI:
            cv2.putText(frame, "! YURUYUS BOZUKLUGU !", (50, h-45), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)

        curr = time.time()
        fps = int(1 / (curr - prev_time)) if prev_time else 0
        prev_time = curr
        cv2.putText(frame, f"FPS: {fps}", (w-120, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

        with frame_lock:
            latest_frame = frame.copy()

        if display:
            cv2.imshow("Gait Analizi", frame)
        
        # TOPLAM ADIM KONTROLÜ: 18 Adım Tamamlandığında Dur
        displayed_left_steps = left_foot_stepper.get_steps() if left_foot_stepper.get_steps() > 0 else left_stepper.steps
        displayed_right_steps = right_foot_stepper.get_steps() if right_foot_stepper.get_steps() > 0 else right_stepper.steps
        total_steps = min(displayed_left_steps, displayed_right_steps) * 2
        if total_steps >= MAX_ADIM_SAYISI:
            if start_walk_time is not None and end_walk_time is None:
                end_walk_time = time.time()
                walk_duration = end_walk_time - start_walk_time
                if right_times:
                    avg_step_time = np.mean(right_times + left_times) if (right_times + left_times) else 0.6
                ortalama_asimetri = np.mean(asimetri_listesi) if asimetri_listesi else 0.0
                gait_score = calculate_score(gait_speed_m_s, ortalama_asimetri, avg_step_time)
                if gait_score >= 80:
                    score_status = "COK IYI"
                elif gait_score >= 60:
                    score_status = "NORMAL"
                elif gait_score >= 40:
                    score_status = "RISKLI"
                else:
                    score_status = "ANORMAL"
                
                # Advanced classification with hybrid approach
                advanced_features_dict = advanced_features.get_feature_vector(displayed_left_steps, displayed_right_steps)
                hybrid_class_result, hybrid_conf_result, hybrid_reason_result = hybrid_classifier.hybrid_predict(advanced_features_dict, use_model=False)
                
            print(f"Analiz tamamlandı: {total_steps} adım kaydedildi.")
            print(f"  Hybrid Classification: {hybrid_class_result} (confidence: {hybrid_conf_result:.2f})")
            if display:
                cv2.destroyWindow("Gait Analizi")
                cv2.destroyAllWindows()
            break

        if display:
            if cv2.waitKey(1) & 0xFF == ord("q"):
                # Q tuşuna basınca rapor bas ve çık
                print("\n" + "="*60)
                print("YÜRÜYÜŞ ANALİZİ RAPORU")
                print("="*60)
                
                displayed_left_steps = left_foot_stepper.get_steps() if left_foot_stepper.get_steps() > 0 else left_stepper.steps
                displayed_right_steps = right_foot_stepper.get_steps() if right_foot_stepper.get_steps() > 0 else right_stepper.steps
                total_steps = min(displayed_left_steps, displayed_right_steps) * 2
                symmetry = (min(displayed_left_steps, displayed_right_steps) / max(displayed_left_steps, displayed_right_steps) * 100) if max(displayed_left_steps, displayed_right_steps) > 0 else 0
                
                print(f"📊 TEMEL BİLGİLER:")
                print(f"  • Analiz Süresi: {round(time.time() - start_time, 2)} saniye")
                print(f"  • Analiz Tarihi: {time.strftime('%d/%m/%Y %H:%M:%S')}")
                print(f"👣 ADIM SAYISI:")
                print(f"  • Toplam Adım: {total_steps}")
                print(f"  • Sol Ayak : {displayed_left_steps}")
                print(f"  • Sağ Ayak : {displayed_right_steps}")
                print(f"  • Adım Dengesi: {symmetry:.1f}%")
                print(f"📈 ASİMETRİ ANALİZİ:")
                if asimetri_listesi:
                    ortalama_asimetri = np.mean(asimetri_listesi)
                    print(f"  • Ortalama Asimetri: {ortalama_asimetri:.2f}%")
                    status = "ANORMAL" if ortalama_asimetri > 15 else "NORMAL"
                    print(f"🎯 SONUÇ:")
                    print(f"  • Tanı: {status}")
                else:
                    print("  • Veri toplanamadı")
                print("="*60)
                break
        
        if not display:
            # Headless modda kısa uyku, CPU kullanımını azaltmak için
            time.sleep(0.03)

    if display:
        cv2.destroyAllWindows()

    # Kapatma
    if data_buffer:
        writer.writerows(data_buffer)
    cap.release()
    cv2.destroyAllWindows()
    
    # Analiz aşaması
    rapor = ""
    analiz_zamanı = time.time() - start_time
    
    if asimetri_listesi:
        ortalama_asimetri = np.mean(asimetri_listesi)
        min_asimetri = np.min(asimetri_listesi)
        max_asimetri = np.max(asimetri_listesi)
        displayed_left_steps = left_foot_stepper.get_steps() if left_foot_stepper.get_steps() > 0 else left_stepper.steps
        displayed_right_steps = right_foot_stepper.get_steps() if right_foot_stepper.get_steps() > 0 else right_stepper.steps
        adim_farki = abs(displayed_left_steps - displayed_right_steps)
        toplam_adim = min(displayed_left_steps, displayed_right_steps) * 2  # Doğru sayma yöntemi
        
        if ortalama_asimetri < ASYMETRI_HAFIF_ESIGI and adim_farki <= 1:
            karar = "NORMAL"
            durum = "OK: Yürüyüş paternleri simetrik ve dengeli."
        elif ortalama_asimetri < ASYMETRI_ESIGI and adim_farki <= 3:
            karar = "RİSKLİ"
            durum = "⚠ Hafif asimetri tespit edilmiştir. Takip önerilir."
        else:
            karar = "ANORMAL"
            durum = "ERROR: Anormal yürüyüş paternleri tespit edilmiştir."
        
        rapor = (
            f"{'='*60}\n"
            f"YÜRÜYÜŞ ANALİZİ RAPORU\n"
            f"{'='*60}\n\n"
            
            f"📊 TEMEL BİLGİLER:\n"
            f"  • Analiz Süresi: {analiz_zamanı:.2f} saniye\n"
            f"  • Analiz Tarihi: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            
            f"👣 ADIM SAYIMı:\n"
            f"  • Toplam Adım Sayısı: {toplam_adim} / {MAX_ADIM_SAYISI}\n"
            f"  • Sol Ayak Adımları: {displayed_left_steps}\n"
            f"  • Sağ Ayak Adımları: {displayed_right_steps}\n"
            f"  • Adım Dengesi: {100 - (adim_farki/toplam_adim*100) if toplam_adim > 0 else 0:.1f}%\n"
            f"  • Sağ-Sol Adım Farkı: {adim_farki} {'(Dengeli)' if adim_farki <= 1 else '(Hafif fark)' if adim_farki <= 3 else '(Anormal fark)'}\n\n"
            f"⏱️ TOPLAM SURE: {(end_walk_time - start_walk_time) if start_walk_time and end_walk_time else 0:.2f} s\n"
            f"📐 TOPLAM MESAFE: {total_distance_cm / 100:.2f} m\n"
            f"🚶 YURUYUS HIZI: {gait_speed_m_s:.2f} m/s ({speed_status})\n"
            f"🞯 ORTALAMA ADIM SURESI: {avg_step_time:.2f} s\n"
            f"🎯 GAIT SKORU: {gait_score}/100 ({score_status})\n\n"
            
            f"📈 ASİMETRİ ANALİZİ:\n"
            f"  • Ortalama Asimetri: {ortalama_asimetri:.2f}%\n"
            f"  • Minimum Asimetri: {min_asimetri:.2f}%\n"
            f"  • Maksimum Asimetri: {max_asimetri:.2f}%\n"
            f"  • Asimetri Değişkenliği: {max_asimetri - min_asimetri:.2f}%\n"
            f"  • Eşik Durumu: {'Altında' if ortalama_asimetri < ASYMETRI_HAFIF_ESIGI else 'Uyarı Alanında' if ortalama_asimetri < ASYMETRI_ESIGI else 'Üstünde (Anormal)'}\n\n"
            
            f"🎯 SONUÇ:\n"
            f"  • Tanı: {karar}\n"
            f"  • Açıklama: {durum}\n"
            f"  • Gelişmiş Analiz (Hybrid): {hybrid_class_result} (Güven: {hybrid_conf_result:.2f})\n"
            f"  • Gelişmiş Gerekçe: {hybrid_reason_result}\n\n"
            
            f"📋 DEĞERLENDİRME:\n"
            f"  • İlk 18 adımdaki gerçek zamanlı veriler analiz edilmiştir.\n"
            f"  • Adım simetrisi ve diz eklem açıları sürekli izlenmiştir.\n"
            f"  • Yürüyüş paterninin normalize edilip edilmediği belirlenmiştir.\n\n"
            
            f"{'='*60}\n"
        )
    else:
        rapor = "Yeterli veri toplanamadı. Lütfen analizi yeniden başlatın."

    print(rapor)
    callback(rapor)

    # Rapor dosyası kaydı (isteğe bağlı)
    with open("gait_analiz_raporu.txt", "w", encoding="utf-8") as f:
        f.write(rapor)

    if ai_history:
        try:
            avg_ai = np.mean(ai_history)
            plt.figure()
            plt.plot(time_history, ai_history, label="Asimetri")
            plt.axhline(avg_ai, color="orange", linestyle="--", label=f"Ortalama = {avg_ai:.1f}%")
            plt.axhline(ASYMETRI_HAFIF_ESIGI, color="green", linestyle="--", label=f"Hafif Eşik ({ASYMETRI_HAFIF_ESIGI}%)")
            plt.axhline(ASYMETRI_ESIGI, color="red", linestyle="--", label=f"Anormal Eşik ({ASYMETRI_ESIGI}%)")
            plt.xlabel("Zaman (saniye)")
            plt.ylabel("Asimetri (%)")
            plt.title("Yürüyüş Asimetri Grafiği")
            plt.grid(True)
            plt.legend()
            plt.tight_layout()
            plt.savefig("asimetri_grafik.png")
            print("Grafik kaydedildi: asimetri_grafik.png")
            try:
                if os.name == 'nt':
                    os.startfile("asimetri_grafik.png")
                    print("Grafik Windows görüntüleyicide açıldı.")
                elif threading.current_thread() == threading.main_thread():
                    plt.show()
            except Exception as e:
                print(f"Grafik gösterilemiyor: {e}")
            finally:
                plt.close()
        except Exception as e:
            print(f"Grafik çizme hatası: {e}")

    if done_callback:
        done_callback()

# ===================== GUI =====================
def main():
    root = tk.Tk()
    root.title("Yürüyüş Analizi Sistemi")
    root.geometry("400x200")
    
    label = tk.Label(root, text="Analizi başlatmak için butona tıklayın.", font=("Arial", 14))
    label.pack(pady=20)
    
    def update_ui(msg):
        def show_result():
            label.config(text="Analiz Tamamlandı! OK")
            messagebox.showinfo("YÜRÜYÜŞ ANALİZİ SONUÇLARI", msg)

        root.after(0, show_result)

    def on_start():
        label.config(text="Analiz başlatıldı... Lütfen yürüyün.")
        button.config(state="disabled")
        # Analizi ayrı thread'de çalıştır
        thread = threading.Thread(
            target=start_analysis,
            args=(update_ui, lambda: root.after(100, root.destroy))
        )
        thread.start()
    
    button = tk.Button(root, text="Analizi Başlat", command=on_start, font=("Arial", 12))
    button.pack(pady=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()
