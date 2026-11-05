import pygame
import time
from typing import List, Tuple, Optional
from frontend.widgets import MBUX_BLUE, MBUX_GLOW, CRITICAL_RED, BORDER_GRAY, CARD_BG, UI_SILVER

class EARChart:
    """
    Real-time scrolling chart for Eye Aspect Ratio (EAR) telemetry.
    Supports gradient fillings, threshold highlights, and mouse hover inspector tooltips.
    """
    def __init__(self, rect: pygame.Rect, max_samples: int = 300) -> None:
        self.rect = rect
        self.max_samples = max_samples
        self.history: List[float] = []
        
        # Fonts
        self.font_axis = pygame.font.SysFont("Segoe UI", 11)
        self.font_tooltip = pygame.font.SysFont("Segoe UI", 12, bold=True)
        
        # Grid settings
        self.grid_rows = 4
        self.grid_cols = 6
        
    def add_sample(self, val: float) -> None:
        """Appends EAR sample to history, keeping max queue size."""
        self.history.append(val)
        if len(self.history) > self.max_samples:
            self.history.pop(0)
            
    def clear(self) -> None:
        self.history.clear()

    def draw(self, surface: pygame.Surface, ear_threshold: float, mouse_pos: Tuple[int, int]) -> None:
        # 1. Draw grid background lines
        h_step = self.rect.height / self.grid_rows
        w_step = self.rect.width / self.grid_cols
        
        # Horizontal grids
        for i in range(1, self.grid_rows):
            y = self.rect.y + i * h_step
            pygame.draw.line(surface, (22, 22, 28), (self.rect.x, y), (self.rect.right, y), 1)
            
        # Vertical grids
        for j in range(1, self.grid_cols):
            x = self.rect.x + j * w_step
            pygame.draw.line(surface, (22, 22, 28), (x, self.rect.y), (x, self.rect.bottom), 1)
            
        # 2. Plot history points
        n_samples = len(self.history)
        if n_samples < 2:
            no_data = self.font_axis.render("CALIBRATING TELEMETRY...", True, (80, 80, 90))
            surface.blit(no_data, (self.rect.centerx - no_data.get_width() // 2, self.rect.centery - 8))
            return
            
        # Value ranges: EAR is typically between 0.1 and 0.45
        min_y_val, max_y_val = 0.0, 0.45
        
        # Map indices to pixels
        points: List[Tuple[float, float]] = []
        x_step = self.rect.width / (self.max_samples - 1)
        
        # Compute coordinates
        for idx, val in enumerate(self.history):
            # Calculate coordinate X
            x_coord = self.rect.x + idx * x_step
            
            # Clamp and normalize value
            norm_val = (val - min_y_val) / (max_y_val - min_y_val)
            norm_val = max(0.0, min(1.0, norm_val))
            
            # Y coordinate (inverted since Y=0 is top)
            y_coord = self.rect.bottom - norm_val * self.rect.height
            points.append((x_coord, y_coord))
            
        # 3. Draw gradient-like filled area under the line
        # Build polygon: bottom-left -> points -> bottom-right -> bottom-left
        poly_points = [(self.rect.x, self.rect.bottom)]
        for pt in points:
            poly_points.append(pt)
        # Add final point at bottom right matching the last sample's X
        last_x = points[-1][0]
        poly_points.append((last_x, self.rect.bottom))
        
        # Create alpha layer surface for filled gradient area
        alpha_surf = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        # Shift points to match local surface coordinates
        shifted_poly = [(pt[0] - self.rect.x, pt[1] - self.rect.y) for pt in poly_points]
        # Draw transparent filled polygon
        pygame.draw.polygon(alpha_surf, (0, 160, 255, 30), shifted_poly)
        surface.blit(alpha_surf, (self.rect.x, self.rect.y))
        
        # 4. Draw EAR threshold line
        norm_th = (ear_threshold - min_y_val) / (max_y_val - min_y_val)
        y_th = self.rect.bottom - norm_th * self.rect.height
        pygame.draw.line(surface, CRITICAL_RED, (self.rect.x, y_th), (self.rect.right, y_th), 1)
        
        # Label for threshold
        th_lbl = self.font_axis.render(f"ALERT THRESHOLD ({ear_threshold:.2f})", True, CRITICAL_RED)
        surface.blit(th_lbl, (self.rect.x + 10, y_th - 16))
        
        # 5. Draw the actual EAR line (cyan)
        for i in range(len(points) - 1):
            pygame.draw.line(surface, MBUX_BLUE, points[i], points[i+1], 2)
            
        # Draw Y-Axis bounds
        min_lbl = self.font_axis.render(f"{min_y_val:.2f}", True, (100, 100, 110))
        max_lbl = self.font_axis.render(f"{max_y_val:.2f}", True, (100, 100, 110))
        surface.blit(max_lbl, (self.rect.x + 5, self.rect.y + 5))
        surface.blit(min_lbl, (self.rect.x + 5, self.rect.bottom - 16))

        # 6. Interactive Inspector Tooltip (Mouse Hover)
        if self.rect.collidepoint(mouse_pos) and points:
            # Find the nearest point to mouse_pos X
            mx, my = mouse_pos
            # Map mx back to sample index
            relative_x = mx - self.rect.x
            target_idx = int(round(relative_x / x_step))
            
            if 0 <= target_idx < len(self.history):
                # Inspect data point
                inspect_x, inspect_y = points[target_idx]
                inspect_val = self.history[target_idx]
                
                # Draw vertical hover guide line
                pygame.draw.line(surface, (150, 150, 150), (inspect_x, self.rect.y), (inspect_x, self.rect.bottom), 1)
                # Draw hover highlight circle
                pygame.draw.circle(surface, (255, 255, 255), (int(inspect_x), int(inspect_y)), 5)
                pygame.draw.circle(surface, MBUX_BLUE, (int(inspect_x), int(inspect_y)), 3)
                
                # Create interactive tooltip
                status_str = "OK" if inspect_val >= ear_threshold else "LOW"
                status_color = MBUX_BLUE if status_str == "OK" else CRITICAL_RED
                
                tt_lines = [
                    f"EAR: {inspect_val:.3f}",
                    f"STATUS: {status_str}",
                    f"T: -{(len(self.history) - target_idx) // 10}s"
                ]
                
                # Measure tooltip dimensions
                tt_w = 110
                tt_h = 60
                
                # Align tooltip left or right of the vertical line to stay inside bounds
                tt_x = inspect_x + 15
                if tt_x + tt_w > self.rect.right:
                    tt_x = inspect_x - tt_w - 15
                    
                tt_y = my - tt_h // 2
                tt_y = max(self.rect.y + 5, min(self.rect.bottom - tt_h - 5, tt_y))
                
                # Draw tooltip box
                tt_rect = pygame.Rect(tt_x, tt_y, tt_w, tt_h)
                pygame.draw.rect(surface, (12, 12, 15), tt_rect, border_radius=5)
                pygame.draw.rect(surface, MBUX_GLOW, tt_rect, 1, border_radius=5)
                
                # Draw text lines
                y_text = tt_y + 8
                for idx, line in enumerate(tt_lines):
                    txt_color = status_color if "STATUS" in line else UI_SILVER
                    txt_surf = self.font_tooltip.render(line, True, txt_color)
                    surface.blit(txt_surf, (tt_x + 10, y_text))
                    y_text += 16
