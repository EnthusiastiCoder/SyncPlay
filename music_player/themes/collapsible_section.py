"""Collapsible section widget for grouping UI controls."""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve


class CollapsibleSection(QWidget):
    """A titled section that can be expanded or collapsed."""

    toggled = pyqtSignal(bool)  # True = expanded

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._expanded = True

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header row
        header = QWidget()
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header.setStyleSheet(
            "QWidget { background-color: #313244; border-radius: 6px; padding: 2px; }"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)

        self._arrow = QLabel("▼")
        self._arrow.setFixedWidth(16)
        self._arrow.setStyleSheet("color: #89b4fa; font-size: 10pt; background: transparent;")

        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(
            "font-weight: bold; font-size: 11pt; color: #cdd6f4; background: transparent;"
        )

        header_layout.addWidget(self._arrow)
        header_layout.addWidget(self._title_label)
        header_layout.addStretch()
        outer.addWidget(header)

        # Content widget
        self._content = QWidget()
        content_outer = QVBoxLayout(self._content)
        content_outer.setContentsMargins(0, 8, 0, 8)
        content_outer.setSpacing(0)

        self._inner_layout = QVBoxLayout()
        self._inner_layout.setSpacing(8)
        content_outer.addLayout(self._inner_layout)

        outer.addWidget(self._content)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #45475a;")
        outer.addWidget(sep)

        # Make header clickable
        header.mousePressEvent = lambda e: self._toggle()

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._arrow.setText("▼" if self._expanded else "▶")
        self.toggled.emit(self._expanded)

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._content.setVisible(expanded)
        self._arrow.setText("▼" if expanded else "▶")

    def add_widget(self, widget: QWidget):
        self._inner_layout.addWidget(widget)

    def add_layout(self, layout):
        self._inner_layout.addLayout(layout)

    def inner_layout(self):
        return self._inner_layout
