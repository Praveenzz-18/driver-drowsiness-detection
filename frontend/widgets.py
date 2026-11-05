import pygame
import math
import time
from typing import Tuple, List, Dict, Any, Callable, Optional

# Theme Colors (Premium Automotive Style)
BG_BLACK = (10, 10, 12)
CARD_BG = (18, 18, 22)
BORDER_GRAY = (40, 40, 46)
MBUX_BLUE = (0, 160, 255)
MBUX_GLOW = (0, 80, 150)
UI_SILVER = (200, 200, 210)
CRITICAL_RED = (255, 30, 30)
WARNING_YELLOW = (255, 180, 0)
SAFE_GREEN = (0, 255, 120)

class Card:
    """A premium dashboard panel container with rounded corners and neon outer glows."""
    def __init__(self, rect: pygame.Rect, title: str, glow_color: Tuple[int, int, int] = MBUX_GLOW) -> None:
        self.rect = rect
        self.title = title
        self.glow_color = glow_color
        self.font_title = pygame.font.SysFont("Segoe UI", 18, bold=True)
        
    def draw(self, surface: pygame.Surface) -> None:
        # 1. Draw subtle outer neon glow
        glow_radius = 4
        for i in range(1, glow_radius + 1):
            alpha = int(80 * (1.0 - (i / glow_radius)))
            g_color = (self.glow_color[0], self.glow_color[1], self.glow_color[2], alpha)
            g_surface = pygame.Surface((self.rect.width + i*2, self.rect.height + i*2), pygame.SRCALPHA)
            pygame.draw.rect(g_surface, g_color, (0, 0, self.rect.width + i*2, self.rect.height + i*2), 2, border_radius=12)
            surface.blit(g_surface, (self.rect.x - i, self.rect.y - i))
            
        # 2. Draw card body
        pygame.draw.rect(surface, CARD_BG, self.rect, border_radius=10)
        
        # 3. Draw card border
        pygame.draw.rect(surface, BORDER_GRAY, self.rect, 1, border_radius=10)
        
        # 4. Draw Header Title text if set
        if self.title:
            txt_surf = self.font_title.render(self.title.upper(), True, MBUX_BLUE)
            surface.blit(txt_surf, (self.rect.x + 18, self.rect.y + 15))
            # Draw a subtle separator line under title
            pygame.draw.line(surface, BORDER_GRAY, 
                             (self.rect.x + 15, self.rect.y + 45), 
                             (self.rect.right - 15, self.rect.y + 45), 1)


class CircularGauge:
    """
    Circular gauge for displaying telemetry values (speed, RPM, scores).
    Features smooth LERP value transitions and dynamic status color updates.
    """
    def __init__(
        self, 
        center: Tuple[int, int], 
        radius: int, 
        title: str, 
        color_scheme: str = "blue",  # blue, fatigue, alertness, speed, rpm
        max_val: float = 100.0,
        unit: str = "%"
    ) -> None:
        self.center = center
        self.radius = radius
        self.title = title
        self.color_scheme = color_scheme
        self.max_val = max_val
        self.unit = unit
        
        self.value: float = 0.0
        self.target_value: float = 0.0
        
        self.font_val = pygame.font.SysFont("Segoe UI", 30, bold=True)  # Slightly smaller for custom units
        self.font_lbl = pygame.font.SysFont("Segoe UI", 12, bold=True)

    def update(self, target: float) -> None:
        self.target_value = target
        # Smooth interpolation: 10% movement per frame
        self.value += (self.target_value - self.value) * 0.1

    def draw(self, surface: pygame.Surface) -> None:
        # Background tracks
        pygame.draw.circle(surface, (28, 28, 33), self.center, self.radius, 10)
        pygame.draw.circle(surface, (15, 15, 18), self.center, self.radius - 8)
        
        # Select active color based on current interpolated value and scheme
        if self.color_scheme == "alertness":
            if self.value > 70:
                color = SAFE_GREEN
            elif self.value > 30:
                color = WARNING_YELLOW
            else:
                color = CRITICAL_RED
        elif self.color_scheme == "fatigue":
            if self.value < 30:
                color = SAFE_GREEN
            elif self.value < 70:
                color = WARNING_YELLOW
            else:
                color = CRITICAL_RED
        elif self.color_scheme == "speed":
            # High speed gets orange/red warning
            if self.value > 140:
                color = CRITICAL_RED
            elif self.value > 90:
                color = WARNING_YELLOW
            else:
                color = MBUX_BLUE
        elif self.color_scheme == "rpm":
            color = (255, 120, 0)  # Orange tachometer
        else:
            color = MBUX_BLUE

        # Value limits and arc boundaries
        val_pct = max(0.0, min(self.max_val, self.value))
        sweep_angle = (val_pct / self.max_val) * (1.5 * math.pi)  # 270 degree sweep
        start_angle = 0.75 * math.pi
        end_angle = start_angle + sweep_angle
        
        # Draw active value arc
        rect = (self.center[0] - self.radius, self.center[1] - self.radius, self.radius * 2, self.radius * 2)
        pygame.draw.arc(surface, color, rect, -end_angle, -start_angle, 10)
        
        # Draw glow on the active arc
        glow_surf = pygame.Surface((self.radius * 2 + 10, self.radius * 2 + 10), pygame.SRCALPHA)
        g_rect = (5, 5, self.radius * 2, self.radius * 2)
        g_color = (color[0], color[1], color[2], 60)
        pygame.draw.arc(glow_surf, g_color, g_rect, -end_angle, -start_angle, 14)
        surface.blit(glow_surf, (self.center[0] - self.radius - 5, self.center[1] - self.radius - 5))
        
        # Inner Value Text
        display_val = int(round(self.value))
        val_text = self.font_val.render(f"{display_val}", True, UI_SILVER)
        
        # Draw unit string underneath value inside dial
        unit_text = pygame.font.SysFont("Segoe UI", 10, bold=True).render(self.unit, True, (140, 140, 150))
        
        surface.blit(val_text, (self.center[0] - val_text.get_width() // 2, self.center[1] - 25))
        surface.blit(unit_text, (self.center[0] - unit_text.get_width() // 2, self.center[1] + 8))
        
        # Bottom label
        lbl_text = self.font_lbl.render(self.title.upper(), True, (120, 120, 130))
        surface.blit(lbl_text, (self.center[0] - lbl_text.get_width() // 2, self.center[1] + 24))


class Button:
    """A glassmorphic, interactive button that changes style on mouse hovers and clicks."""
    def __init__(
        self, 
        rect: pygame.Rect, 
        text: str, 
        callback: Callable[[], None],
        base_color: Tuple[int, int, int] = (25, 25, 30),
        hover_color: Tuple[int, int, int] = (40, 40, 50)
    ) -> None:
        self.rect = rect
        self.text = text
        self.callback = callback
        self.base_color = base_color
        self.hover_color = hover_color
        self.is_hovered: bool = False
        self.font = pygame.font.SysFont("Segoe UI", 14, bold=True)
        
    def check_hover(self, mouse_pos: Tuple[int, int]) -> bool:
        self.is_hovered = self.rect.collidepoint(mouse_pos)
        return self.is_hovered
        
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                self.callback()
                
    def draw(self, surface: pygame.Surface) -> None:
        # Hover animations
        bg_col = self.hover_color if self.is_hovered else self.base_color
        border_col = MBUX_BLUE if self.is_hovered else BORDER_GRAY
        glow_alpha = 90 if self.is_hovered else 0
        
        # Outer glow on hover
        if glow_alpha > 0:
            g_surf = pygame.Surface((self.rect.width + 8, self.rect.height + 8), pygame.SRCALPHA)
            pygame.draw.rect(g_surf, (0, 160, 255, glow_alpha), (0, 0, self.rect.width + 8, self.rect.height + 8), 2, border_radius=8)
            surface.blit(g_surf, (self.rect.x - 4, self.rect.y - 4))
            
        pygame.draw.rect(surface, bg_col, self.rect, border_radius=6)
        pygame.draw.rect(surface, border_col, self.rect, 1, border_radius=6)
        
        txt_surf = self.font.render(self.text.upper(), True, UI_SILVER)
        surface.blit(txt_surf, (self.rect.centerx - txt_surf.get_width() // 2, self.rect.centery - txt_surf.get_height() // 2))


class TextGrid:
    """A formatted, space-efficient grid displaying current metrics."""
    def __init__(self, rect: pygame.Rect, cols: int = 2) -> None:
        self.rect = rect
        self.cols = cols
        self.font_lbl = pygame.font.SysFont("Segoe UI", 14)
        self.font_val = pygame.font.SysFont("Segoe UI", 16, bold=True)
        
    def draw(self, surface: pygame.Surface, items: List[Tuple[str, str, Tuple[int, int, int]]]) -> None:
        """
        Draws list of (label, value, value_color) in columns.
        """
        # Distribute items
        w_col = self.rect.width / self.cols
        h_row = 32
        
        for idx, item in enumerate(items):
            c = idx % self.cols
            r = idx // self.cols
            
            x = self.rect.x + c * w_col + 15
            y = self.rect.y + r * h_row + 10
            
            label, val, val_col = item
            
            # Label
            lbl_surf = self.font_lbl.render(f"{label}:", True, (140, 140, 150))
            surface.blit(lbl_surf, (x, y))
            
            # Value (Shifted right of label)
            val_surf = self.font_val.render(val, True, val_col)
            surface.blit(val_surf, (x + lbl_surf.get_width() + 8, y - 2))


class AlertHistoryPanel:
    """Vertical list panel that displays warning logs with severity coloring."""
    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = rect
        self.font_msg = pygame.font.SysFont("Segoe UI", 14)
        self.font_time = pygame.font.SysFont("Consolas", 13)
        self.page_offset = 0
        self.items_per_page = 7
        
    def scroll(self, direction: int) -> None:
        """Scrolls history up or down."""
        self.page_offset = max(0, self.page_offset + direction)
        
    def draw(self, surface: pygame.Surface, history: List[Dict[str, str]]) -> None:
        if not history:
            no_alert_txt = self.font_msg.render("No alerts logged", True, (100, 100, 110))
            surface.blit(no_alert_txt, (self.rect.x + 20, self.rect.y + 15))
            return
            
        # Limit page offset
        self.page_offset = min(self.page_offset, max(0, len(history) - self.items_per_page))
        
        row_h = 32
        y_start = self.rect.y + 10
        
        # Display slice of history
        visible_alerts = history[self.page_offset : self.page_offset + self.items_per_page]
        
        for idx, alert in enumerate(visible_alerts):
            y = y_start + idx * row_h
            
            # Draw row separator line
            if idx > 0:
                pygame.draw.line(surface, (28, 28, 34), (self.rect.x + 10, y - 5), (self.rect.right - 10, y - 5), 1)
            
            severity = alert.get("severity", "SAFE")
            if severity == "DROWSY":
                bullet_color = CRITICAL_RED
            elif severity == "WARNING":
                bullet_color = WARNING_YELLOW
            else:
                bullet_color = SAFE_GREEN
                
            # Draw Severity Bullet Dot
            pygame.draw.circle(surface, bullet_color, (self.rect.x + 22, y + 8), 5)
            
            # Time stamp (Cyan)
            time_surf = self.font_time.render(alert["timestamp"], True, MBUX_BLUE)
            surface.blit(time_surf, (self.rect.x + 40, y))
            
            # Event description
            desc_surf = self.font_msg.render(alert["event"], True, UI_SILVER)
            surface.blit(desc_surf, (self.rect.x + 145, y - 1))
            
        # Draw scroll indicators if records exceed page size
        if len(history) > self.items_per_page:
            indicator_txt = pygame.font.SysFont("Segoe UI", 11).render(
                f"Page {self.page_offset // self.items_per_page + 1} | Use Scroll Buttons", True, (80, 80, 90)
            )
            surface.blit(indicator_txt, (self.rect.right - indicator_txt.get_width() - 20, self.rect.bottom - 18))
