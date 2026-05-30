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

        # Custom overlay theme controls
        custom_label = QLabel("Custom Overlay Colors")
        custom_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        overlay_layout.addWidget(custom_label)

        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Theme Name:"))
        self._custom_name_edit = QLineEdit()
        self._custom_name_edit.setPlaceholderText("My Custom Theme")
        name_layout.addWidget(self._custom_name_edit)
        overlay_layout.addLayout(name_layout)

        played_layout = QHBoxLayout()
        played_layout.addWidget(QLabel("Played Color:"))
        self._played_color_btn = ColorPickerButton()
        played_layout.addWidget(self._played_color_btn)
        played_layout.addWidget(QLabel("Opacity:"))
        self._played_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._played_opacity_slider.setRange(0, 100)
        self._played_opacity_slider.setValue(100)
        self._played_opacity_slider.setFixedWidth(150)
        played_layout.addWidget(self._played_opacity_slider)
        self._played_opacity_label = QLabel("100%")
        self._played_opacity_label.setFixedWidth(40)
        played_layout.addWidget(self._played_opacity_label)
        played_layout.addStretch()
        overlay_layout.addLayout(played_layout)

        unplayed_layout = QHBoxLayout()
        unplayed_layout.addWidget(QLabel("Unplayed Color:"))
        self._unplayed_color_btn = ColorPickerButton()
        unplayed_layout.addWidget(self._unplayed_color_btn)
        unplayed_layout.addWidget(QLabel("Opacity:"))
        self._unplayed_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._unplayed_opacity_slider.setRange(0, 100)
        self._unplayed_opacity_slider.setValue(100)
        self._unplayed_opacity_slider.setFixedWidth(150)
        unplayed_layout.addWidget(self._unplayed_opacity_slider)
        self._unplayed_opacity_label = QLabel("100%")
        self._unplayed_opacity_label.setFixedWidth(40)
        unplayed_layout.addWidget(self._unplayed_opacity_label)
        unplayed_layout.addStretch()
        overlay_layout.addLayout(unplayed_layout)

        # Text size
        text_row = QHBoxLayout()
        text_row.addWidget(QLabel("Lyric Text Size:"))
        self._text_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._text_size_slider.setRange(12, 72)
        self._text_size_slider.setValue(self._config.get("font_size_base", 28))
        self._text_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._text_size_slider.setTickInterval(4)
        self._text_size_slider.setFixedWidth(200)
        text_row.addWidget(self._text_size_slider)
        self._text_size_label = QLabel(f"{self._config.get('font_size_base', 28)} pt")
        self._text_size_label.setFixedWidth(50)
        text_row.addWidget(self._text_size_label)
        text_row.addStretch()
        overlay_layout.addLayout(text_row)

        # Action buttons
        button_layout = QHBoxLayout()
        self._save_custom_btn = QPushButton("Save Custom Theme")
        self._save_custom_btn.clicked.connect(self._save_custom_theme)
        button_layout.addWidget(self._save_custom_btn)

        self._delete_custom_btn = QPushButton("Delete Custom Theme")
        self._delete_custom_btn.clicked.connect(self._delete_custom_theme)
        button_layout.addWidget(self._delete_custom_btn)

        self._apply_btn = QPushButton("Apply Overlay Theme")
        self._apply_btn.clicked.connect(self._apply_current_theme)
        button_layout.addWidget(self._apply_btn)
        button_layout.addStretch()
        overlay_layout.addLayout(button_layout)

        self._overlay_section.add_widget(overlay_inner)
        main_layout.addWidget(self._overlay_section)

        main_layout.addStretch()

        # Connect signals
        self._played_opacity_slider.valueChanged.connect(
            lambda v: self._played_opacity_label.setText(f"{v}%")
        )
        self._unplayed_opacity_slider.valueChanged.connect(
            lambda v: self._unplayed_opacity_label.setText(f"{v}%")
        )
        self._text_size_slider.valueChanged.connect(self._on_text_size_changed)
        self._app_theme_combo.currentIndexChanged.connect(self._update_app_accent_preview)
    
    def _update_app_accent_preview(self):
        """Update the accent color preview strip based on the selected app theme."""
        name = self._app_theme_combo.currentData()
        theme = self._app_theme_manager.get_theme_by_name(name)
        if theme:
            self._app_accent_preview.setStyleSheet(
                f"background-color: {theme.accent_color}; border-radius: 4px;"
            )

    def _apply_app_theme(self):
        """Apply the selected app theme immediately."""
        name = self._app_theme_combo.currentData()
        theme = self._app_theme_manager.get_theme_by_name(name)
        if theme:
            self._app_theme_manager.apply_theme(theme)
            self._config.set("app_theme", name)
            self._config.save()

    def _load_current_theme(self):
        """Load and select the current theme from config."""
        theme_name = self._config.get("current_theme", "Classic Green")
        theme = self._theme_manager.get_theme_by_name(theme_name)
        
        if theme:
            self._select_theme(theme)
        else:
            # Load from config colors
            self._played_color_btn.color_hex = self._config.get("played_color", "#00FF00")
            self._unplayed_color_btn.color_hex = self._config.get("unplayed_color", "#FFFFFF")
            self._played_opacity_slider.setValue(int(self._config.get("played_opacity", 1.0) * 100))
            self._unplayed_opacity_slider.setValue(int(self._config.get("unplayed_opacity", 1.0) * 100))
    
    def _on_theme_selected(self, theme_name: str):
        """Handle theme card click."""
        theme = self._theme_manager.get_theme_by_name(theme_name)
        if theme:
            self._select_theme(theme)
    
    def _select_theme(self, theme: Theme):
        """Select a theme and update UI."""
        # Update card selection
        for name, card in self._theme_cards.items():
            card.set_selected(name == theme.name)
        
        self._current_theme_name = theme.name
        
        # Update custom theme controls
        self._custom_name_edit.setText(theme.name)
        self._played_color_btn.color_hex = theme.played_color
        self._unplayed_color_btn.color_hex = theme.unplayed_color
        self._played_opacity_slider.setValue(int(theme.played_opacity * 100))
        self._unplayed_opacity_slider.setValue(int(theme.unplayed_opacity * 100))
        
        # Enable/disable delete button
        self._delete_custom_btn.setEnabled(not theme.is_builtin)
    
    def _save_custom_theme(self):
        """Save current settings as a custom theme."""
        name = self._custom_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a theme name.")
            return
        
        # Check if it's a built-in theme name
        for builtin in self._theme_manager.get_builtin_themes():
            if builtin.name == name:
                QMessageBox.warning(
                    self, "Invalid Name",
                    "Cannot overwrite built-in theme. Please choose a different name."
                )
                return
