"""Theme selection and customization tab."""

from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QSlider, QLineEdit, QMessageBox, QScrollArea,
    QComboBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from music_player.config import ConfigManager
from music_player.themes.theme_manager import Theme, ThemeManager
from music_player.themes.app_theme_manager import AppThemeManager
from music_player.themes.collapsible_section import CollapsibleSection
from music_player.player.settings_dialog import ColorPickerButton


class ThemeCard(QWidget):
    """A clickable card representing a theme preset."""
    
    clicked = pyqtSignal(str)  # theme name
    
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._theme = theme
        self._is_selected = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Theme name
        name_label = QLabel(self._theme.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(name_label)
        
        # Color preview
        preview = QWidget()
        preview.setFixedHeight(60)
        preview.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self._theme.played_color},
                    stop:1 {self._theme.unplayed_color});
                border-radius: 6px;
            }}
        """)
        layout.addWidget(preview)
        
        # Opacity info
        opacity_text = f"Played: {int(self._theme.played_opacity * 100)}% | Unplayed: {int(self._theme.unplayed_opacity * 100)}%"
        opacity_label = QLabel(opacity_text)
        opacity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        opacity_label.setStyleSheet("font-size: 9pt; color: #888;")
        layout.addWidget(opacity_label)
        
        self.setFixedSize(180, 120)
        self._update_style()
    
    def _update_style(self):
        if self._is_selected:
            self.setStyleSheet("""
                ThemeCard {
                    background-color: #45475a;
                    border: 2px solid #89b4fa;
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                ThemeCard {
                    background-color: #313244;
                    border: 1px solid #45475a;
                    border-radius: 8px;
                }
                ThemeCard:hover {
                    background-color: #383a4a;
                    border-color: #585b70;
                }
            """)
    
    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._update_style()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._theme.name)
        super().mousePressEvent(event)


class ThemeTab(QWidget):
    """Tab for theme selection and customization."""
    
    theme_changed = pyqtSignal(Theme)
    
    def __init__(self, config: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config = config
        self._theme_manager = ThemeManager()
        self._app_theme_manager = AppThemeManager()
        self._theme_cards: dict[str, ThemeCard] = {}
        self._current_theme_name: Optional[str] = None
        
        self._build_ui()
        self._load_current_theme()
    
    def _build_ui(self):
        # Outer scroll area so the whole tab scrolls if needed
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Section 1: App Theme ──────────────────────────────────────────
        self._app_section = CollapsibleSection("App Theme")
        self._app_section.set_expanded(True)

        app_inner = QWidget()
        app_inner_layout = QVBoxLayout(app_inner)
        app_inner_layout.setContentsMargins(0, 0, 0, 0)
        app_inner_layout.setSpacing(10)

        # App theme combo + preview
        app_row = QHBoxLayout()
        app_row.addWidget(QLabel("Theme:"))
        self._app_theme_combo = QComboBox()
        for t in self._app_theme_manager.get_all_themes():
            self._app_theme_combo.addItem(t.name, t.name)
        saved_app = self._config.get("app_theme", "Catppuccin Dark")
        idx = self._app_theme_combo.findData(saved_app)
        if idx >= 0:
            self._app_theme_combo.setCurrentIndex(idx)
        app_row.addWidget(self._app_theme_combo)

        self._btn_apply_app_theme = QPushButton("Apply App Theme")
        self._btn_apply_app_theme.setFixedWidth(140)
        self._btn_apply_app_theme.clicked.connect(self._apply_app_theme)
        app_row.addWidget(self._btn_apply_app_theme)
        app_row.addStretch()
        app_inner_layout.addLayout(app_row)

        # Accent color preview strip
        self._app_accent_preview = QWidget()
        self._app_accent_preview.setFixedHeight(8)
        self._app_accent_preview.setStyleSheet("border-radius: 4px;")
        self._update_app_accent_preview()
        app_inner_layout.addWidget(self._app_accent_preview)

        self._app_section.add_widget(app_inner)
        main_layout.addWidget(self._app_section)

        # ── Section 2: Overlay Theme ──────────────────────────────────────
        self._overlay_section = CollapsibleSection("Overlay Theme")
        self._overlay_section.set_expanded(True)

        overlay_inner = QWidget()
        overlay_layout = QVBoxLayout(overlay_inner)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(10)

        # Preset theme cards
        cards_label = QLabel("Preset Overlay Themes")
        cards_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        overlay_layout.addWidget(cards_label)

        cards_scroll = QScrollArea()
        cards_scroll.setWidgetResizable(True)
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cards_scroll.setMaximumHeight(280)
        cards_scroll.setMinimumHeight(180)

        cards_widget = QWidget()
        cards_grid = QGridLayout(cards_widget)
        cards_grid.setSpacing(10)

        themes = self._theme_manager.get_all_themes()
        row, col = 0, 0
        for theme in themes:
            card = ThemeCard(theme)
            card.clicked.connect(self._on_theme_selected)
            self._theme_cards[theme.name] = card
            cards_grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        cards_scroll.setWidget(cards_widget)
        overlay_layout.addWidget(cards_scroll)
