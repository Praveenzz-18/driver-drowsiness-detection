import pygame
import time
from typing import List, Dict, Any, Optional

class AlertsManager:
    """
    Handles driver status changes, alarms via Pygame mixer, and 
    stores alert event logs (timestamp, description, severity).
    """
    def __init__(self, alarm_sound_path: str = "alarm.wav") -> None:
        import os
        if not os.path.isabs(alarm_sound_path):
            possible_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", alarm_sound_path))
            if os.path.exists(possible_path):
                self.alarm_sound_path = possible_path
            else:
                self.alarm_sound_path = os.path.abspath(alarm_sound_path)
        else:
            self.alarm_sound_path = alarm_sound_path
            
        self.alarm_sound: Optional[pygame.mixer.Sound] = None
        self.alarm_playing: bool = False
        
        # Load audio resources
        self._init_sound()
        
        # Alerts log: list of dicts {"timestamp": str, "event": str, "severity": str}
        self.history: List[Dict[str, str]] = []
        self.max_history: int = 50
        
        # State tracking for status transitions
        self.current_status: str = "SAFE"  # SAFE, WARNING, DROWSY
        
    def _init_sound(self) -> None:
        """Initializes Pygame mixer and loads the alarm wave asset."""
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"Warning: Could not initialize pygame mixer: {e}")
                return
                
        try:
            self.alarm_sound = pygame.mixer.Sound(self.alarm_sound_path)
        except Exception as e:
            print(f"Warning: Could not load alarm sound file {self.alarm_sound_path}: {e}")
            self.alarm_sound = None

    def trigger_alarm(self) -> None:
        """Plays the alarm sound on a loop if loaded and not already playing."""
        if self.alarm_sound and not self.alarm_playing:
            try:
                self.alarm_sound.play(-1)  # Play infinitely
                self.alarm_playing = True
            except Exception as e:
                print(f"Error playing alarm sound: {e}")

    def stop_alarm(self) -> None:
        """Stops the alarm sound if playing."""
        if pygame.mixer.get_init() and self.alarm_sound and self.alarm_playing:
            try:
                self.alarm_sound.stop()
                self.alarm_playing = False
            except Exception as e:
                print(f"Error stopping alarm sound: {e}")

    def log_alert(self, event_type: str, severity: str) -> None:
        """Logs an event to history with the current timestamp."""
        # Check for duplicate events in the last 2 seconds to avoid log spamming
        timestamp_str = time.strftime("%I:%M:%S %p")
        
        # If the same event occurred in the last few logs with the same severity, ignore duplicates
        if self.history:
            last_alert = self.history[0]
            if last_alert["event"] == event_type and last_alert["severity"] == severity:
                # Basic duplicate prevention
                # We still want to log critical state changes, but avoid continuous logging of 'yawn detected' in the same minute
                # Let's check time
                if last_alert["timestamp"] == timestamp_str:
                    return

        alert_item = {
            "timestamp": timestamp_str,
            "event": event_type,
            "severity": severity  # SAFE (Green), WARNING (Yellow), DROWSY (Red)
        }
        
        # Insert at the beginning of the list (newest first)
        self.history.insert(0, alert_item)
        
        # Cap log history size
        if len(self.history) > self.max_history:
            self.history.pop()

    def update_status(self, fatigue_score: float) -> str:
        """
        Calculates driver status from fatigue score:
        - SAFE: < 30
        - WARNING: 30 - 70
        - DROWSY: > 70
        Triggers alarm states and logs status changes.
        """
        previous_status = self.current_status
        
        if fatigue_score >= 70.0:
            self.current_status = "DROWSY"
            self.trigger_alarm()
        elif fatigue_score >= 30.0:
            self.current_status = "WARNING"
            self.stop_alarm()
        else:
            self.current_status = "SAFE"
            self.stop_alarm()
            
        # Log status transitions
        if self.current_status != previous_status:
            severity = "SAFE" if self.current_status == "SAFE" else ("WARNING" if self.current_status == "WARNING" else "DROWSY")
            self.log_alert(f"Status changed to {self.current_status}", severity)
            
        return self.current_status

    def get_history(self) -> List[Dict[str, str]]:
        """Returns the logged event history list."""
        return self.history

    def clear_history(self) -> None:
        """Clears the logged alert history list."""
        self.history.clear()
        self.log_alert("System initialized", "SAFE")
