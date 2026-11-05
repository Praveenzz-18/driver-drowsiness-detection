import os
import sys
import traceback

# Ensure the root project directory is in the Python path so we can resolve imports
# e.g., 'backend.api' and 'frontend.dashboard' from anywhere
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api import DMSAPI
from frontend.dashboard import DMSDashboard

def main() -> None:
    """
    Bootstrap launcher for the Driver Monitoring System (DMS) Application.
    Initializes double-threaded API pipelines and boots the UI cockpit.
    """
    print("======================================================")
    print("    MBUX DRIVER MONITORING SYSTEM - DIGITAL COCKPIT    ")
    print("======================================================")
    print("Initializing Core Telemetry Engine...")
    
    # Initialize Core Threaded API
    api = DMSAPI(camera_index=0)
    
    try:
        # Start capture and face processing threads
        api.start()
        
        # Launch UI Dashboard
        print("Launching Digital Cockpit Dashboard...")
        dashboard = DMSDashboard(api=api)
        dashboard.run()
        
    except Exception as e:
        print(f"\nFATAL ERROR during runtime: {e}")
        traceback.print_exc()
        
    finally:
        # Graceful Thread and Resource cleanup
        print("\nShutting down cockpit engine...")
        api.stop()
        print("Goodbye.")

if __name__ == "__main__":
    main()
