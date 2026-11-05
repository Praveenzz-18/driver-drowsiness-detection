import pygame
import sys
import time
import math
import cv2
from typing import Tuple, Dict, Any, Optional
from backend.api import DMSAPI
from frontend.widgets import (
    Card, CircularGauge, Button, TextGrid, AlertHistoryPanel,
    BG_BLACK, MBUX_BLUE, MBUX_GLOW, UI_SILVER, CRITICAL_RED, WARNING_YELLOW, SAFE_GREEN, CARD_BG, BORDER_GRAY
)
from frontend.charts import EARChart

class DMSDashboard:
    """
    Main user interface dashboard for the Driver Monitoring System.
    Manages layout, polling telemetry from the API, interactive buttons,
    pulsing animation overlays, and the main Pygame graphics loop.
    """
    def __init__(self, api: DMSAPI, width: int = 1400, height: int = 850) -> None:
        self.api = api
        self.width = width
        self.height = height
        
        # Initialize Pygame Screen
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("MBUX Driver Monitoring System")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_header = pygame.font.SysFont("Segoe UI", 28, bold=True)
        self.font_subheader = pygame.font.SysFont("Segoe UI", 12, bold=True)
        self.font_status = pygame.font.SysFont("Segoe UI", 22, bold=True)
        self.font_status_lbl = pygame.font.SysFont("Segoe UI", 11, bold=True)
        self.font_cal = pygame.font.SysFont("Segoe UI", 16, bold=True)
        self.font_crash = pygame.font.SysFont("Segoe UI", 24, bold=True)
        
        # Left Panel Cards (Simulator, Camera, EAR Chart)
        self.sim_card = Card(pygame.Rect(20, 95, 670, 320), "ADAS Highway Simulator Feed")
        self.sim_surface = pygame.Surface((640, 260))  # Drawing canvas for 3D road
        
        self.camera_card = Card(pygame.Rect(20, 430, 670, 220), "Driver Camera HUD")
        self.chart_card = Card(pygame.Rect(20, 665, 670, 170), "Live EAR Analysis")
        
        # Right Panel Cards (Digital Cluster, Telemetry Grid, Alert Log History)
        self.scores_card = Card(pygame.Rect(710, 95, 670, 240), "MBUX Digital Instrument Cluster")
        self.metrics_card = Card(pygame.Rect(710, 350, 670, 240), "Live Telemetry Grid")
        self.history_card = Card(pygame.Rect(710, 605, 670, 230), "System Alert History")
        
        # Circular Dials (Side-by-side in Digital Cluster card)
        # We place Alertness, Fatigue, Speed, Tachometer (RPM) side-by-side
        self.gauge_alertness = CircularGauge(center=(925, 225), radius=45, title="Alertness", color_scheme="alertness")
        self.gauge_fatigue = CircularGauge(center=(1035, 225), radius=45, title="Fatigue", color_scheme="fatigue")
        self.gauge_speed = CircularGauge(center=(1145, 225), radius=45, title="Speed", color_scheme="speed", max_val=220.0, unit="km/h")
        self.gauge_rpm = CircularGauge(center=(1255, 225), radius=45, title="Tachometer", color_scheme="rpm", max_val=80.0, unit="x100 RPM")
        
        # Chart (Inside Live EAR Card)
        self.ear_chart = EARChart(pygame.Rect(40, 715, 630, 105))
        
        # Alert History Scroll List
        self.history_panel = AlertHistoryPanel(pygame.Rect(730, 655, 540, 165))
        
        # Interactive Buttons
        self.btn_recalibrate = Button(
            rect=pygame.Rect(1020, 545, 160, 32),
            text="Calibrate baseline",
            callback=self.api.trigger_calibration
        )
        self.btn_reset = Button(
            rect=pygame.Rect(1200, 545, 140, 32),
            text="Reset metrics",
            callback=self.api.reset_simulator
        )
        self.btn_scroll_up = Button(
            rect=pygame.Rect(1290, 665, 45, 30),
            text="Up",
            callback=lambda: self.history_panel.scroll(-1),
            base_color=(35, 35, 45)
        )
        self.btn_scroll_down = Button(
            rect=pygame.Rect(1290, 705, 45, 30),
            text="Down",
            callback=lambda: self.history_panel.scroll(1),
            base_color=(35, 35, 45)
        )
        
        self.buttons = [self.btn_recalibrate, self.btn_reset, self.btn_scroll_up, self.btn_scroll_down]
        self.running = True
        
    def run(self) -> None:
        """Main Pygame dashboard execution loop (60 FPS for fluid layout)."""
        while self.running:
            # 1. Keyboard Inputs & Event Polling
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        self.running = False
                    elif event.key == pygame.K_c:
                        self.api.trigger_calibration()
                    elif event.key == pygame.K_r:
                        self.api.reset_simulator()
                        
                # Handle Button events
                for btn in self.buttons:
                    btn.handle_event(event)
                    
            # 2. Steer, Accelerate, Brake Inputs propagation to Simulator
            keys = pygame.key.get_pressed()
            accelerate = keys[pygame.K_UP] or keys[pygame.K_w]
            brake = keys[pygame.K_DOWN] or keys[pygame.K_s]
            steer_dir = -1 if (keys[pygame.K_LEFT] or keys[pygame.K_a]) else (1 if (keys[pygame.K_RIGHT] or keys[pygame.K_d]) else 0)
            
            # Restart simulator on 'R' key if crashed
            _, data = self.api.get_latest_data()
            if data and data.get("crashed", False) and keys[pygame.K_r]:
                self.api.reset_simulator()
            
            if data and not data.get("crashed", False):
                self.api.update_simulator_controls(accelerate, brake, steer_dir)
                
            # Update button mouse hover statuses
            for btn in self.buttons:
                btn.check_hover(mouse_pos)
                
            # 3. Retrieve latest telemetry data from API
            frame, data = self.api.get_latest_data()
            
            # Feed real-time EAR graph samples
            if data and data.get("face_detected", False):
                self.ear_chart.add_sample(data["ear"])
            elif data:
                self.ear_chart.add_sample(0.0)
                
            # 4. Clear Canvas
            self.screen.fill(BG_BLACK)
            
            # 5. Render Layout Cards
            self.sim_card.draw(self.screen)
            self.camera_card.draw(self.screen)
            self.chart_card.draw(self.screen)
            self.scores_card.draw(self.screen)
            self.metrics_card.draw(self.screen)
            self.history_card.draw(self.screen)
            
            # 6. Draw Header HUD
            self._draw_header(data)
            
            # 7. Render Road Simulator View Card
            self._draw_road_simulator(data, accelerate, brake)
            
            # 8. Render Camera Feed Container
            self._draw_camera_feed(frame, data)
            
            # 9. Render Charts
            ear_th = data.get("ear", 0.22)  # Fallback
            if data and data.get("calibrated", False):
                ear_th = self.api.baseline_ear * 0.82
            self.ear_chart.draw(self.screen, ear_th, mouse_pos)
            
            # 10. Render Circular Dials & Status Info
            self._draw_status_panel(data)
            
            # 11. Render Metrics Grid & Control Buttons
            self._draw_metrics_panel(data)
            
            # 12. Render Alert History List
            history_logs = data.get("history", [])
            self.history_panel.draw(self.screen, history_logs)
            
            # Draw scroll buttons
            self.btn_scroll_up.draw(self.screen)
            self.btn_scroll_down.draw(self.screen)
            
            # 13. Screen Flip & Cap tick rate at 60 FPS
            pygame.display.flip()
            self.clock.tick(60)
            
        pygame.quit()
        sys.exit()

    def _draw_header(self, data: Dict[str, Any]) -> None:
        """Renders premium top header dashboard title."""
        title_surf = self.font_header.render("DRIVER MONITORING SYSTEM", True, UI_SILVER)
        self.screen.blit(title_surf, (20, 15))
        
        sub_surf = self.font_subheader.render("MBUX INTELLIGENT EYE COCKPIT", True, MBUX_BLUE)
        self.screen.blit(sub_surf, (22, 50))
        
        # Render system diagnostic details (FPS, active thread state)
        fps = data.get("fps", 0.0) if data else 0.0
        sys_status_str = f"CORE ACTIVE | PROC FPS: {fps:.1f} | UI FPS: {int(self.clock.get_fps())}"
        sys_status_surf = pygame.font.SysFont("Segoe UI", 12).render(sys_status_str, True, (120, 120, 130))
        self.screen.blit(sys_status_surf, (self.width - sys_status_surf.get_width() - 20, 32))
        
        # Header bottom separator line
        pygame.draw.line(self.screen, (30, 30, 36), (20, 80), (self.width - 20, 80), 2)

    # ── Simulator: perspective projection helper ──────────────────────────────

    def _project(self, world_x: float, world_z: float,
                 player_x: float, curve_accum: float,
                 cam_h: float, cam_depth: float,
                 sw: int, sh: int, horizon_y: int) -> tuple:
        """
        Classic pseudo-3D road projection (Outrun/DR.Driving style).
        Returns (screen_x, screen_y, scale)  or None if behind camera.
        cam_depth   = camera lens depth  (~0.84 of screen height)
        curve_accum = accumulated curve shift from horizon to this strip
        """
        if world_z <= 0:
            return None
        scale  = cam_depth / world_z
        # lateral: road center follows player_x; curve shifts the projected centre
        proj_x = sw // 2 + (world_x - player_x + curve_accum) * scale * sw * 0.5
        proj_y = horizon_y + (cam_h - 0)  * scale   # simplified; strips drive this
        return int(proj_x), int(proj_y), scale

    # ── Main road renderer ────────────────────────────────────────────────────

    def _draw_road_simulator(self, data: Dict[str, Any], accelerate: bool, brake: bool) -> None:
        """Classic trapezoid perspective road renderer."""
        if not data:
            return

        SW, SH = 640, 260
        HORIZON_Y = 50          # horizon line y-pixel
        ROAD_Y    = SH          # bottom of road

        player_x = data.get("player_x", 0.0)   # normalised -1.5 … +1.5
        speed    = data.get("speed",    0.0)
        camera_z = data.get("camera_z", 0.0)
        steering = data.get("steering_angle", 0.0)
        status   = data.get("driver_status",  "SAFE")

        # Convert normalised player_x → pixel parallax shift
        parallax_x = -player_x * (200.0 / 1.5)

        # ── 1. Clear & sky ────────────────────────────────────────────────────
        self.sim_surface.fill((10, 10, 14))

        # Sky gradient
        for sy in range(HORIZON_Y + 1):
            t = sy / max(1, HORIZON_Y)
            pygame.draw.line(self.sim_surface,
                             (int(8 + 18 * t), int(8 + 20 * t), int(14 + 28 * t)),
                             (0, sy), (SW, sy))

        # Thin horizon glow
        pygame.draw.line(self.sim_surface, (20, 60, 100), (0, HORIZON_Y), (SW, HORIZON_Y), 1)

        # ── 2. Grass ground below horizon ────────────────────────────────────
        pygame.draw.rect(self.sim_surface, (18, 52, 18),
                         (0, HORIZON_Y + 1, SW, SH - HORIZON_Y))

        # Alternating grass stripes (scroll with speed)
        stripe_offset = int(camera_z * 0.4) % 40
        for stripe_y in range(HORIZON_Y, SH, 40):
            sy = stripe_y + stripe_offset
            if sy < HORIZON_Y or sy > SH:
                continue
            pygame.draw.rect(self.sim_surface, (14, 42, 14), (0, sy, SW, 20))

        # ── 3. Trapezoid road polygon ─────────────────────────────────────────
        road_curve = data.get("road_curve", 0.0)
        curve_shift = road_curve * 55.0

        top_cx   = SW // 2 + parallax_x * 0.15 + curve_shift
        bot_cx   = SW // 2 + parallax_x

        top_half = 55
        bot_half = 280

        tl = (top_cx - top_half, HORIZON_Y)
        tr = (top_cx + top_half, HORIZON_Y)
        br = (bot_cx + bot_half, ROAD_Y)
        bl = (bot_cx - bot_half, ROAD_Y)

        pygame.draw.polygon(self.sim_surface, (28, 28, 32), [tl, tr, br, bl])
        pygame.draw.line(self.sim_surface, (55, 55, 62), tl, bl, 2)
        pygame.draw.line(self.sim_surface, (55, 55, 62), tr, br, 2)

        # ── 4. Red/white kerb rumble strips ──────────────────────────────────
        kerb_idx = int(camera_z / 35) % 2
        kerb_col = (220, 30, 30) if kerb_idx == 0 else (230, 230, 230)
        kerb_w   = 18
        lk_tl = (tl[0] - kerb_w, HORIZON_Y)
        lk_bl = (bl[0] - kerb_w, ROAD_Y)
        pygame.draw.polygon(self.sim_surface, kerb_col, [lk_tl, tl, bl, lk_bl])
        rk_tr = (tr[0] + kerb_w, HORIZON_Y)
        rk_br = (br[0] + kerb_w, ROAD_Y)
        pygame.draw.polygon(self.sim_surface, kerb_col, [tr, rk_tr, rk_br, br])

        # ── 5. Lane dashes ────────────────────────────────────────────────────
        line_speed = speed / 10.0
        dash_offset = (camera_z * line_speed * 0.8) % 90

        def interp_x(y, lane_frac):
            t = max(0.0, min(1.0, (y - HORIZON_Y) / max(1, ROAD_Y - HORIZON_Y)))
            center = top_cx + (bot_cx - top_cx) * t
            half   = top_half + (bot_half - top_half) * t
            return int(center + lane_frac * half * 0.666)

        for lane in [-1, 1]:
            for seg in range(-1, 6):
                y_top = seg * 90 + dash_offset
                y_bot = y_top + 45
                y_top = max(HORIZON_Y, y_top)
                y_bot = min(ROAD_Y,    y_bot)
                if y_top >= y_bot:
                    continue
                x_top = interp_x(y_top, lane)
                x_bot = interp_x(y_bot, lane)
                t_avg = ((y_top + y_bot) * 0.5 - HORIZON_Y) / max(1, ROAD_Y - HORIZON_Y)
                lw = max(1, int(1 + t_avg * 5))
                pygame.draw.line(self.sim_surface, (180, 180, 190),
                                 (x_top, int(y_top)), (x_bot, int(y_bot)), lw)

        # ── 6. Roadside objects ───────────────────────────────────────────────
        FOV   = 320.0
        CAM_Z = 5.0
        CENTER = SW // 2

        roadside = data.get("roadside", [])
        for obj in sorted(roadside, key=lambda o: o["z"], reverse=True):
            oz = obj["z"]
            if oz <= 2:
                continue
            ratio  = 1.0 - oz / 1000.0
            sy_gnd = HORIZON_Y + int((ROAD_Y - HORIZON_Y) * ratio)
            scale  = FOV / (oz + CAM_Z)
            side_px = obj["side"] * (bot_half + 40)
            t_o = max(0.0, min(1.0, ratio))
            c_cx = top_cx + (bot_cx - top_cx) * t_o
            c_hw = top_half + (bot_half - top_half) * t_o
            sx = int(c_cx + obj["side"] * (c_hw + kerb_w + 20))

            if obj["obj_type"] == 'pole':
                pw = max(1, int(scale * 0.06))
                ph = max(4, int(scale * 0.9))
                pygame.draw.rect(self.sim_surface, (70, 75, 85),
                                 (sx - pw, sy_gnd - ph, pw * 2, ph))
                pygame.draw.circle(self.sim_surface, (255, 235, 160),
                                   (sx, sy_gnd - ph), max(2, pw + 1))
            elif obj["obj_type"] == 'tree':
                tw = max(4, int(scale * 0.28))
                th = max(8, int(scale * 1.2))
                pygame.draw.rect(self.sim_surface, (80, 50, 20),
                                 (sx - tw // 5, sy_gnd - th // 2, tw // 3, th // 2))
                for layer in range(2):
                    oy  = layer * (th // 6)
                    pts = [(sx, sy_gnd - th + oy),
                           (sx - tw + oy, sy_gnd - th // 2 + oy),
                           (sx + tw - oy, sy_gnd - th // 2 + oy)]
                    pygame.draw.polygon(self.sim_surface,
                                        (15 + layer * 8, 90 + layer * 15, 20), pts)

        # ── 7. Traffic cars ───────────────────────────────────────────────────
        LANE_NX = {0: -1.0, 1: 0.0, 2: 1.0}
        for car in sorted(data.get("traffic", []), key=lambda c: c["z"], reverse=True):
            cz = car["z"]
            if cz <= 2:
                continue
            ratio  = 1.0 - cz / 1000.0
            sy_car = HORIZON_Y + int((ROAD_Y - HORIZON_Y) * ratio)
            scale  = FOV / (cz + CAM_Z)
            t_c    = max(0.0, min(1.0, ratio))
            c_cx   = top_cx + (bot_cx - top_cx) * t_c
            c_hw   = top_half + (bot_half - top_half) * t_c
            lane_frac = LANE_NX.get(car["lane"], 0.0)
            cx = int(c_cx + lane_frac * c_hw * 0.5)

            cw = max(10, int(scale * 1.8))
            ch = max(6,  int(scale * 1.2))
            color = car.get("color", (180, 50, 50))
            pygame.draw.rect(self.sim_surface, color,
                             (cx - cw, sy_car - ch, cw * 2, ch), border_radius=2)
            rc = tuple(min(255, v + 40) for v in color)
            pygame.draw.rect(self.sim_surface, rc,
                             (cx - cw // 2, sy_car - ch - ch // 2, cw, ch // 2), border_radius=1)
            lw = max(2, cw // 5)
            pygame.draw.rect(self.sim_surface, (255, 50, 50),
                             (cx - cw + 2, sy_car - ch + 2, lw, max(2, ch // 3)))
            pygame.draw.rect(self.sim_surface, (255, 50, 50),
                             (cx + cw - lw - 2, sy_car - ch + 2, lw, max(2, ch // 3)))

        # ── 8. Player car at bottom center ───────────────────────────────────
        pcx, pcy = SW // 2, SH - 2
        pbw, pbh = 88, 42
        pygame.draw.rect(self.sim_surface, (30, 80, 200),
                         (pcx - pbw // 2, pcy - pbh, pbw, pbh), border_radius=6)
        pygame.draw.rect(self.sim_surface, (20, 55, 160),
                         (pcx - pbw // 3, pcy - pbh - 22, pbw * 2 // 3, 24), border_radius=4)
        ws = [(pcx - pbw // 3 + 4, pcy - pbh),
              (pcx + pbw // 3 - 4, pcy - pbh),
              (pcx + pbw // 3 - 9, pcy - pbh - 18),
              (pcx - pbw // 3 + 9, pcy - pbh - 18)]
        pygame.draw.polygon(self.sim_surface, (80, 140, 210), ws)
        pygame.draw.polygon(self.sim_surface, (50, 90, 170), ws, 1)
        for hx in [pcx - pbw // 2 + 7, pcx + pbw // 2 - 7]:
            pygame.draw.ellipse(self.sim_surface, (255, 240, 140), (hx - 7, pcy - 9, 14, 7))
        for wx in [pcx - pbw // 2 - 5, pcx + pbw // 2 - 9]:
            pygame.draw.rect(self.sim_surface, (15, 15, 15),
                             (wx, pcy - pbh + 6, 14, 32), border_radius=3)
            pygame.draw.rect(self.sim_surface, (50, 50, 56),
                             (wx + 2, pcy - pbh + 10, 10, 24), border_radius=2)

        # ── 9. Cockpit steering wheel ─────────────────────────────────────────
        self._draw_steering_wheel(self.sim_surface, steering)

        # ── 10. Speed badge ───────────────────────────────────────────────────
        spd_surf = pygame.font.SysFont("Consolas", 14, bold=True).render(
                       f"{int(speed):3d} km/h", True, MBUX_BLUE)
        pygame.draw.rect(self.sim_surface, (10, 10, 14), (SW - 90, 4, 86, 22), border_radius=4)
        self.sim_surface.blit(spd_surf, (SW - 88, 6))

        # ── 11. Pedals ────────────────────────────────────────────────────────
        self._draw_pedals(self.sim_surface, accelerate, brake)

        # ── 12. ADAS warning overlay ──────────────────────────────────────────
        if status == "DROWSY":
            ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
            pa = int(35 + 35 * math.sin(time.time() * 9.0))
            ov.fill((220, 0, 0, pa))
            self.sim_surface.blit(ov, (0, 0))
            wtx = pygame.font.SysFont("Segoe UI", 15, bold=True).render(
                      "! WAKE UP! ADAS AUTO-BRAKING ACTIVE", True, (255, 220, 220))
            pygame.draw.rect(self.sim_surface, (60, 0, 0),
                             (SW // 2 - 185, 6, 370, 26), border_radius=5)
            pygame.draw.rect(self.sim_surface, CRITICAL_RED,
                             (SW // 2 - 185, 6, 370, 26), 1, border_radius=5)
            self.sim_surface.blit(wtx, (SW // 2 - wtx.get_width() // 2, 10))

        # ── 13. Crash screen ──────────────────────────────────────────────────
        if data.get("crashed", False):
            ov2 = pygame.Surface((SW, SH), pygame.SRCALPHA)
            ov2.fill((10, 10, 12, 215))
            self.sim_surface.blit(ov2, (0, 0))
            ct  = self.font_crash.render("COLLISION DETECTED", True, CRITICAL_RED)
            cd  = pygame.font.SysFont("Segoe UI", 13, bold=True).render(
                      data.get("crash_msg", "").upper(), True, UI_SILVER)
            ci  = pygame.font.SysFont("Segoe UI", 12).render(
                      "PRESS 'R' OR RESET TO RESTART", True, MBUX_BLUE)
            self.sim_surface.blit(ct, (SW//2 - ct.get_width()//2, 70))
            self.sim_surface.blit(cd, (SW//2 - cd.get_width()//2, 115))
            self.sim_surface.blit(ci, (SW//2 - ci.get_width()//2, 155))

        # ── Blit to main screen ───────────────────────────────────────────────
        sim_rect = pygame.Rect(35, 140, SW, SH)
        self.screen.blit(self.sim_surface, sim_rect)
        pygame.draw.rect(self.screen, BORDER_GRAY, sim_rect, 2, border_radius=6)

    def _draw_steering_wheel(self, surface: pygame.Surface, steering_angle: float) -> None:
        """Renders cockpit 3-spoke steering wheel with leather rim."""
        sw_center = (105, 205)  # bottom-left cockpit area
        # Outer rim (leather look)
        pygame.draw.circle(surface, (35, 25, 15), sw_center, 38)
        pygame.draw.circle(surface, (60, 45, 30), sw_center, 38, 5)
        # Rotating spokes
        ang = math.radians(steering_angle)
        for i in range(3):
            sp = ang + i * (2.0 * math.pi / 3.0)
            ep = (sw_center[0] + 34 * math.sin(sp),
                  sw_center[1] - 34 * math.cos(sp))
            pygame.draw.line(surface, (90, 70, 50), sw_center, ep, 5)
            pygame.draw.line(surface, UI_SILVER, sw_center, ep, 2)
        # Centre boss
        pygame.draw.circle(surface, (20, 20, 24), sw_center, 10)
        pygame.draw.circle(surface, MBUX_BLUE, sw_center, 10, 1)
        # Steering angle label
        lf  = pygame.font.SysFont("Consolas", 9)
        lbl = lf.render(f"{int(steering_angle):+d}°", True, (120, 120, 130))
        surface.blit(lbl, (sw_center[0] - lbl.get_width()//2, sw_center[1] + 42))

    def _draw_pedals(self, surface: pygame.Surface, accelerate: bool, brake: bool) -> None:
        """Cockpit gas / brake pedal indicators at bottom right."""
        pw, ph = 22, 38
        gx, gy = 612, 198
        bx, by = 574, 198
        # Gas
        gc = (0, 210, 90) if accelerate else (40, 50, 40)
        pygame.draw.rect(surface, gc,
                         (gx, gy + (4 if accelerate else 0), pw, ph), border_radius=4)
        pygame.draw.rect(surface, (60, 70, 60),
                         (gx, gy + (4 if accelerate else 0), pw, ph), 1, border_radius=4)
        # Brake
        bc = (220, 30, 30) if brake else (50, 40, 40)
        pygame.draw.rect(surface, bc,
                         (bx, by + (4 if brake else 0), pw + 4, ph), border_radius=4)
        pygame.draw.rect(surface, (70, 60, 60),
                         (bx, by + (4 if brake else 0), pw + 4, ph), 1, border_radius=4)
        # Labels
        pf = pygame.font.SysFont("Consolas", 8, bold=True)
        surface.blit(pf.render("BRK", True, UI_SILVER), (bx + 3, by - 14))
        surface.blit(pf.render("GAS", True, UI_SILVER), (gx + 3, gy - 14))

    def _draw_camera_feed(self, frame: Optional[cv2.Mat], data: Dict[str, Any]) -> None:
        """Positions rearview style driver camera HUD inside card."""
        # Rearview shape bounds Y: 430, Height: 220. Center width 240, blit at X=235, Y=470
        feed_rect = pygame.Rect(235, 470, 240, 170)
        
        if frame is not None:
            small_frame = cv2.resize(frame, (240, 170))
            frame_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            frame_surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            self.screen.blit(frame_surf, feed_rect)
        else:
            pygame.draw.rect(self.screen, (12, 12, 14), feed_rect, border_radius=6)
            no_cam_txt = pygame.font.SysFont("Segoe UI", 12).render("NO SIGNAL", True, (80, 80, 90))
            self.screen.blit(no_cam_txt, (feed_rect.centerx - no_cam_txt.get_width() // 2, feed_rect.centery - 6))
            
        pygame.draw.rect(self.screen, BORDER_GRAY, feed_rect, 2, border_radius=6)
        
        # Calibration Overlay
        if data and not data.get("calibrated", False):
            overlay = pygame.Surface((feed_rect.width, feed_rect.height), pygame.SRCALPHA)
            overlay.fill((10, 10, 15, 215))
            self.screen.blit(overlay, feed_rect)
            
            pct = data.get("calibration_progress", 0)
            cal_title = self.font_cal.render("CALIBRATING", True, MBUX_BLUE)
            progress_lbl = pygame.font.SysFont("Consolas", 11).render(f"Progress: {pct}%", True, UI_SILVER)
            
            self.screen.blit(cal_title, (feed_rect.centerx - cal_title.get_width() // 2, feed_rect.centery - 20))
            self.screen.blit(progress_lbl, (feed_rect.centerx - progress_lbl.get_width() // 2, feed_rect.centery + 10))

    def _draw_status_panel(self, data: Optional[Dict[str, Any]]) -> None:
        """Renders focus state banner and updates speedometer/tachometer circular progress dials."""
        status = data.get("driver_status", "SAFE") if data else "SAFE"
        alt_score = data.get("alertness_score", 100.0) if data else 100.0
        fat_score = data.get("fatigue_score", 0.0) if data else 0.0
        speed = data.get("speed", 0.0) if data else 0.0
        rpm = data.get("rpm", 1000.0) if data else 1000.0
        
        # 1. Update circular progress dials
        self.gauge_alertness.update(alt_score)
        self.gauge_fatigue.update(fat_score)
        self.gauge_speed.update(speed)
        # Display tachometer in RPM x100 (e.g. 1000rpm is 10)
        self.gauge_rpm.update(rpm / 100.0)
        
        # 2. Draw progress dials
        self.gauge_alertness.draw(self.screen)
        self.gauge_fatigue.draw(self.screen)
        self.gauge_speed.draw(self.screen)
        self.gauge_rpm.draw(self.screen)
        
        # 3. Draw Driver Status box on the left of gauges (X: 730, Y: 135)
        status_rect = pygame.Rect(730, 135, 140, 160)
        pygame.draw.rect(self.screen, (24, 24, 28), status_rect, border_radius=8)
        pygame.draw.rect(self.screen, BORDER_GRAY, status_rect, 1, border_radius=8)
        
        lbl = self.font_status_lbl.render("DRIVER STATUS", True, (120, 120, 130))
        self.screen.blit(lbl, (status_rect.centerx - lbl.get_width() // 2, status_rect.y + 15))
        
        if status == "DROWSY":
            status_col = CRITICAL_RED
            desc_text = "FATIGUED"
            text_alpha = 150 + int(105 * math.sin(time.time() * 9.0))
            status_col_alpha = (status_col[0], status_col[1], status_col[2], text_alpha)
        elif status == "WARNING":
            status_col = WARNING_YELLOW
            desc_text = "DISTRACTED"
            status_col_alpha = status_col
        else:
            status_col = SAFE_GREEN
            desc_text = "OPTIMAL"
            status_col_alpha = status_col
            
        status_surf = self.font_status.render(status, True, status_col_alpha if status == "DROWSY" else status_col)
        self.screen.blit(status_surf, (status_rect.centerx - status_surf.get_width() // 2, status_rect.y + 55))
        
        desc_surf = pygame.font.SysFont("Segoe UI", 12, bold=True).render(desc_text, True, UI_SILVER)
        self.screen.blit(desc_surf, (status_rect.centerx - desc_surf.get_width() // 2, status_rect.y + 100))

    def _draw_metrics_panel(self, data: Optional[Dict[str, Any]]) -> None:
        """Constructs live parameter values grid and draws recalibration/reset buttons."""
        if not data:
            return
            
        is_face = data.get("face_detected", False)
        
        # Map values to grid strings
        face_str = "DETECTED" if is_face else "DISCONNECTED"
        face_col = SAFE_GREEN if is_face else CRITICAL_RED
        
        eye_state_str = data.get("eye_state", "OPEN")
        eye_col = SAFE_GREEN if eye_state_str == "OPEN" else CRITICAL_RED
        if not is_face:
            eye_state_str = "N/A"
            eye_col = (100, 100, 110)
            
        yawn_status = "YAWNING" if data.get("is_yawning", False) else "NORMAL"
        yawn_col = CRITICAL_RED if data.get("is_yawning", False) else SAFE_GREEN
        if not is_face:
            yawn_status = "N/A"
            yawn_col = (100, 100, 110)
            
        distract_status = "DISTRACTED" if data.get("is_distracted", False) else "FOCUSED"
        distract_col = WARNING_YELLOW if data.get("is_distracted", False) else SAFE_GREEN
        if not is_face:
            distract_status = "N/A"
            distract_col = (100, 100, 110)
            
        ear_val = data.get("ear", 0.0)
        mar_val = data.get("mar", 0.0)
        
        # Construct parameters list for grid
        metrics_list = [
            ("Camera Feed", face_str, face_col),
            ("Gaze Alignment", distract_status, distract_col),
            ("Eye Status", eye_state_str, eye_col),
            ("Mouth Aperture", yawn_status, yawn_col),
            ("Blink Count", str(data.get("blink_count", 0)), UI_SILVER),
            ("Yawn Count", str(data.get("yawn_count", 0)), UI_SILVER),
            ("Current EAR", f"{ear_val:.3f}", MBUX_BLUE if ear_val > 0 else (100, 100, 110)),
            ("Current MAR", f"{mar_val:.3f}", MBUX_BLUE if mar_val > 0 else (100, 100, 110))
        ]
        
        # Setup TextGrid area Y shifted to match panel (Rect: 710, 350, 670, 240)
        grid_rect = pygame.Rect(725, 395, 640, 120)
        t_grid = TextGrid(grid_rect, cols=2)
        t_grid.draw(self.screen, metrics_list)
        
        # Draw control buttons
        self.btn_recalibrate.draw(self.screen)
        self.btn_reset.draw(self.screen)
