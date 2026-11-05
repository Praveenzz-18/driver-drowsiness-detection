# Driver Drowsiness Detection

A desktop driver-monitoring prototype that uses a webcam, MediaPipe Face Landmarker, OpenCV, and Pygame to estimate fatigue indicators and display them in a live dashboard.

> **Safety notice:** This project is for educational and demonstration purposes only. It is not a certified driver-safety system and must not be used as a substitute for safe driving practices.

## Features

- Live webcam face-landmark processing
- Eye and mouth measurements, blink and yawn tracking, and head-pose estimates
- Fatigue and alertness indicators with visual and audio warnings
- Dashboard with live video, event history, and an eye-aspect-ratio chart
- Local calibration and metric reset controls

## Requirements

- Python 3.9 or later
- A webcam
- Windows, macOS, or Linux with a graphical desktop

## Setup (Windows PowerShell)

Run these commands from the repository root:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python .\download_model.py
```

The model file is downloaded locally and is intentionally not tracked in Git.

## Run

With the virtual environment active and the terminal at the repository root:

```powershell
python .\backend\main.py
```

The app opens camera device `0` by default. Allow camera access and face the camera during startup calibration.

## Controls

- **C**: Restart calibration
- **R**: Reset metrics
- **Up / Down**: Scroll event history
- **Q**: Quit
- Hover over the live EAR chart to inspect recent values.

## Project layout

```text
backend/       Camera pipeline, face detection, fatigue tracking, and alerts
frontend/      Pygame dashboard, widgets, and chart
download_model.py
               Downloads the MediaPipe Face Landmarker model
test_*.py      Test and diagnostic scripts
alarm.wav      Audio alert
```

## Tests

Run the core test suite from the repository root:

```powershell
python -m unittest test_dms
```
