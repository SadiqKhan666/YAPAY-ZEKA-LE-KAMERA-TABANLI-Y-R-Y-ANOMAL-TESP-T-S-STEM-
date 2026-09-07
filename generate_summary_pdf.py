from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import textwrap

summary_pages = [
    """GaitProject Summary

Project Overview and Goals

This project implements a gait analysis system that combines computer vision, pose estimation, inertial sensing, and web-based doctor review features. The core application is centered on `pose_detect.py`, which uses MediaPipe Pose and OpenCV to extract body landmarks, calculate joint angles, detect steps, and compute gait metrics such as asymmetry, cadence, and walking speed.

The system is designed for clinical evaluation and remote monitoring. It supports both live camera analysis and doctor-mediated review through a Flask web interface. The primary patient workflow begins with a live analysis session, stores results in a local SQLite database, and offers a doctor panel for reviewing and approving gait assessments.

The project's key goals are:
- Provide objective gait analysis metrics using accessible tools.
- Maintain an approval workflow for doctor verification.
- Enable data persistence, review, and optional machine learning training.
- Deliver a lightweight web interface for review and monitoring.
""",
    """pose_detect.py Architecture

The file `pose_detect.py` is the heart of the system. It contains:
- Camera frame capture and processing.
- Pose landmark extraction and angle calculations.
- Step detection using knee angle and foot position thresholds.
- Asymmetry index computation and gait status classification.
- Data buffering, CSV export, and report generation.

Important functional sections include threshold constants, gait metrics, and signal filtering. The file defines constants such as step bend and straighten thresholds, asymmetry limits, and camera calibration parameters. It also contains helper functions like `calculate_angle`, `distance`, and `estimate_pixel_to_cm_scale`.

A hybrid classifier and auto-training pipeline support advanced analytics. These modules can use rule-based thresholds and optional XGBoost model predictions when the required dependencies are installed. The code gracefully degrades if packages like `xgboost` are missing.

The file also includes a GUI mode for direct analysis. This mode uses Tkinter to start analysis and present results. Additionally, a headless-friendly output path was added so Matplotlib figure generation can run without opening a GUI, which is important when the module is imported by the Flask server.
""",
    """Flask Doctor Review Interface

The `flask_server.py` file implements the web backend for doctor interaction. It provides:
- User authentication and session management.
- Patient records and analysis storage in SQLite.
- A review interface at `/review`.
- AJAX-powered approval through `/approve`.

Database tables include patients and analyses, with fields such as `status`, `disease`, `ai_prediction`, `doctor_label`, and diagnostic metrics. The doctor login is seeded with a default account, allowing a clinician to securely enter the review panel.

The doctor review workflow retrieves pending records and displays them in a table. Each row includes patient name, AI prediction, confidence, analysis status, and a doctor label dropdown. When the doctor approves a record, the system stores the label in SQLite and optionally adds a training record to the auto-training pipeline.

The review logic was improved to only consider items with `doctor_label IS NULL` as pending. This ensures that once a record is approved, it no longer appears incorrectly in the pending list.
""",
    """Client-Side AJAX and UI Enhancements

The web interface includes templates `review.html`, `patient.html`, and static assets like `doctor_panel.html` and `doctor_panel.js`. The `review.html` template was updated to submit approval forms via AJAX instead of a full page refresh.

The AJAX process works as follows:
- Each review row contains a form with an analysis ID and label.
- JavaScript intercepts the submit event.
- The form is posted with an `X-Requested-With: XMLHttpRequest` header.
- On success, the approved row is removed from the table instantly.
- If the table becomes empty, a fallback message is displayed.

`flask_server.py` was adjusted to return JSON for AJAX approval requests while preserving normal redirect behavior for standard form submits. This creates a smoother user experience and makes the approval workflow feel responsive.

The doctor panel was also enhanced to display the latest doctor label in each patient card, improving visibility of approval status directly from the dashboard.
""",
    """Testing and Validation

The system has been validated through both internal tests and live request simulations. A custom test script was created to exercise the doctor approval API. Initially, the script used the `requests` package, but `urllib` support was also added for environments without extra dependencies.

Live validation steps included:
- Restarting the Flask server after code changes.
- Loading the review page and confirming that pending records appear correctly.
- Submitting an AJAX approval and verifying that the server returns JSON success.
- Confirming database updates to `doctor_label` and in-memory patient record synchronization.

During validation, an issue was identified in the review template due to Jinja2 syntax on the `None` check. The condition was corrected to use lowercase `none` so the template renders without error.

Another issue surfaced when `pose_detect.py` was imported while running the web server: Matplotlib figures attempted to show GUI windows from a background thread. This was resolved by selecting a non-interactive backend and only calling `plt.show()` when running in the main thread.
""",
    """Summary and Next Steps

The project now supports a complete doctor approval workflow for gait analysis. Key strengths include:
- A robust gait analysis core in `pose_detect.py`.
- A doctor review panel in Flask with authentication.
- AJAX approval to remove pending analysis rows instantly.
- Persistent storage of analysis and approval data in SQLite.
- Compatibility with headless server execution.

Recommended next steps:
- Add a dedicated patient detail view that lists all historical approvals and metrics.
- Add pagination or filtering to the review page for larger datasets.
- Add user roles and audit logging for approvals.
- Improve the training pipeline to use approved labels as ground truth for future model retraining.
- Add a more polished front-end design and status indicators for real-time video analysis.

This PDF summary reflects the current state of the codebase and the most recent improvements made to support AJAX review and server-friendly execution.
"""
]

output_path = 'GaitProject_Summary.pdf'

c = canvas.Canvas(output_path, pagesize=letter)
width, height = letter
margin = 0.75 * inch
for page_text in summary_pages:
    text_obj = c.beginText(margin, height - margin)
    text_obj.setFont('Helvetica', 11)
    for paragraph in page_text.split('\n\n'):
        lines = textwrap.wrap(paragraph, width=100)
        for line in lines:
            text_obj.textLine(line)
        text_obj.textLine('')
    c.drawText(text_obj)
    c.showPage()

c.save()
print(f'Created PDF: {output_path}')
