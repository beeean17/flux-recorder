from __future__ import annotations

from pathlib import Path

from PIL import Image
from PIL.ImageQt import ImageQt
from PyQt6.QtCore import QPoint, QPointF, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QResizeEvent
from PyQt6.QtWidgets import QButtonGroup, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


ImageCropRect = tuple[int, int, int, int]
AspectRatio = tuple[int, int] | None

ASPECT_RATIO_OPTIONS: tuple[tuple[str, AspectRatio], ...] = (
    ("Free", None),
    ("1:1", (1, 1)),
    ("4:5", (4, 5)),
    ("16:9", (16, 9)),
    ("5:4", (5, 4)),
    ("9:16", (9, 16)),
)

HANDLE_TOP_LEFT = "top_left"
HANDLE_TOP_RIGHT = "top_right"
HANDLE_BOTTOM_LEFT = "bottom_left"
HANDLE_BOTTOM_RIGHT = "bottom_right"

HANDLE_CURSORS = {
    HANDLE_TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    HANDLE_BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    HANDLE_TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    HANDLE_BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
}


CROP_DIALOG_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Crop Image",
        "instructions": "Drag to create a crop, drag inside it to move, or pull a corner handle to resize.",
        "image_size": "Original image: {width} x {height}px",
        "preview_size": "Preview window: {width} x {height}px",
        "aspect_ratio": "Aspect Ratio",
        "current_ratio": "Current ratio: {ratio}",
        "selection_none": "No crop selected. The original image will be used.",
        "selection_active": "Crop box: {width} x {height}px at ({x}, {y})",
        "reset": "Reset",
        "cancel": "Cancel",
        "apply": "Apply",
    },
}


def _crop_text(language: str, key: str, **kwargs) -> str:
    normalized = language if language in CROP_DIALOG_TRANSLATIONS else "en"
    template = CROP_DIALOG_TRANSLATIONS[normalized].get(key, CROP_DIALOG_TRANSLATIONS["en"][key])
    return template.format(**kwargs)


class ImageCropCanvas(QFrame):
    selection_changed = pyqtSignal(object)
    preview_size_changed = pyqtSignal(object)

    def __init__(
        self,
        pixmap: QPixmap,
        crop_rect: ImageCropRect | None = None,
        aspect_ratio: AspectRatio = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._pixmap = pixmap
        self._selection = self._normalize_crop_rect(crop_rect)
        self._aspect_ratio = aspect_ratio
        self._drag_mode: str | None = None
        self._drag_origin: tuple[int, int] | None = None
        self._drag_reference_selection: ImageCropRect | None = None
        self._drag_handle: str | None = None
        self._move_offset: tuple[int, int] | None = None

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumSize(520, 340)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def sizeHint(self) -> QSize:
        if self._pixmap.isNull():
            return QSize(760, 520)
        return QSize(
            min(max(self._pixmap.width(), 640), 1024),
            min(max(self._pixmap.height(), 420), 760),
        )

    def selection(self) -> ImageCropRect | None:
        return self._selection

    def aspect_ratio(self) -> AspectRatio:
        return self._aspect_ratio

    def display_size(self) -> tuple[int, int]:
        image_rect = self._display_rect()
        return (max(0, image_rect.width()), max(0, image_rect.height()))

    def clear_selection(self) -> None:
        self._drag_mode = None
        self._drag_origin = None
        self._drag_reference_selection = None
        self._drag_handle = None
        self._move_offset = None
        self._set_selection(None)

    def set_aspect_ratio(self, aspect_ratio: AspectRatio) -> None:
        if self._aspect_ratio == aspect_ratio:
            return

        self._aspect_ratio = aspect_ratio
        if self._selection is not None and aspect_ratio is not None:
            self._set_selection(self._fit_selection_to_ratio(self._selection, aspect_ratio))
            return
        self.update()

    def resizeEvent(self, event: QResizeEvent) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.preview_size_changed.emit(self.display_size())

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_mode is None:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor("#08100b"))

        image_rect = self._display_rect()
        if image_rect.isNull():
            return

        painter.drawPixmap(image_rect, self._pixmap)
        painter.setPen(QPen(QColor("#244234"), 1))
        painter.drawRect(image_rect.adjusted(0, 0, -1, -1))

        selection_rect = self._selection_display_rect(image_rect)
        if selection_rect is None:
            return

        self._paint_overlay(painter, image_rect, selection_rect)
        painter.setPen(QPen(QColor("#10b981"), 2))
        painter.drawRect(selection_rect.adjusted(0, 0, -1, -1))
        self._paint_handles(painter, selection_rect)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        image_rect = self._display_rect()
        if image_rect.isNull() or not image_rect.contains(event.position().toPoint()):
            event.ignore()
            return

        image_point = self._point_to_image(event.position(), clamp_to_image=True)
        handle = self._handle_at_display_point(event.position().toPoint())
        if self._selection is not None and handle is not None:
            self._drag_mode = "resize"
            self._drag_handle = handle
            self._drag_origin = self._opposite_corner(self._selection, handle)
            self._drag_reference_selection = self._selection
            self.setCursor(HANDLE_CURSORS[handle])
            event.accept()
            return

        if self._selection is not None:
            selection_rect = self._selection_display_rect(image_rect)
            if selection_rect is not None and selection_rect.contains(event.position().toPoint()):
                self._drag_mode = "move"
                self._drag_reference_selection = self._selection
                self._move_offset = (
                    image_point[0] - self._selection[0],
                    image_point[1] - self._selection[1],
                )
                self.setCursor(Qt.CursorShape.SizeAllCursor)
                event.accept()
                return

        self._drag_mode = "create"
        self._drag_origin = image_point
        self._drag_reference_selection = None
        self._move_offset = None
        self._update_selection_from_anchor(image_point, image_point)
        self.setCursor(Qt.CursorShape.CrossCursor)
        event.accept()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._drag_mode is None:
            self._sync_cursor(event.position().toPoint())
            super().mouseMoveEvent(event)
            return

        current_point = self._point_to_image(event.position(), clamp_to_image=True)
        if self._drag_mode == "create" and self._drag_origin is not None:
            self._update_selection_from_anchor(self._drag_origin, current_point)
        elif self._drag_mode == "resize" and self._drag_origin is not None:
            self._update_selection_from_anchor(self._drag_origin, current_point)
        elif self._drag_mode == "move" and self._drag_reference_selection is not None and self._move_offset is not None:
            self._move_selection(current_point)

        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() != Qt.MouseButton.LeftButton:
            super().mouseReleaseEvent(event)
            return

        if self._drag_mode is not None:
            self._drag_mode = None
            self._drag_origin = None
            self._drag_reference_selection = None
            self._drag_handle = None
            self._move_offset = None
            self._sync_cursor(event.position().toPoint())
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def _set_selection(self, selection: ImageCropRect | None) -> None:
        self._selection = selection
        self.selection_changed.emit(selection)
        self.update()

    def _display_rect(self) -> QRect:
        if self._pixmap.isNull():
            return QRect()

        bounds = self.rect().adjusted(12, 12, -12, -12)
        if bounds.isEmpty():
            return QRect()

        scaled_size = self._pixmap.size().scaled(bounds.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x_pos = bounds.x() + (bounds.width() - scaled_size.width()) // 2
        y_pos = bounds.y() + (bounds.height() - scaled_size.height()) // 2
        return QRect(x_pos, y_pos, scaled_size.width(), scaled_size.height())

    def _paint_overlay(self, painter: QPainter, image_rect: QRect, selection_rect: QRect) -> None:
        overlay = QColor(4, 10, 7, 175)
        image_right = image_rect.x() + image_rect.width()
        image_bottom = image_rect.y() + image_rect.height()
        selection_right = selection_rect.x() + selection_rect.width()
        selection_bottom = selection_rect.y() + selection_rect.height()

        painter.fillRect(
            QRect(image_rect.x(), image_rect.y(), image_rect.width(), max(0, selection_rect.y() - image_rect.y())),
            overlay,
        )
        painter.fillRect(
            QRect(
                image_rect.x(),
                selection_rect.y(),
                max(0, selection_rect.x() - image_rect.x()),
                selection_rect.height(),
            ),
            overlay,
        )
        painter.fillRect(
            QRect(
                selection_right,
                selection_rect.y(),
                max(0, image_right - selection_right),
                selection_rect.height(),
            ),
            overlay,
        )
        painter.fillRect(
            QRect(image_rect.x(), selection_bottom, image_rect.width(), max(0, image_bottom - selection_bottom)),
            overlay,
        )

    def _paint_handles(self, painter: QPainter, selection_rect: QRect) -> None:
        painter.setPen(QPen(QColor("#10b981"), 1.5))
        painter.setBrush(QColor("#08100b"))
        for handle_rect in self._handle_rects(selection_rect).values():
            painter.drawRect(handle_rect.adjusted(0, 0, -1, -1))
            painter.fillRect(handle_rect.adjusted(2, 2, -2, -2), QColor("#ecfdf5"))

    def _selection_display_rect(self, image_rect: QRect) -> QRect | None:
        if self._selection is None or image_rect.isNull():
            return None

        left, top, width, height = self._selection
        scale_x = image_rect.width() / max(1, self._pixmap.width())
        scale_y = image_rect.height() / max(1, self._pixmap.height())
        return QRect(
            image_rect.x() + int(round(left * scale_x)),
            image_rect.y() + int(round(top * scale_y)),
            max(1, int(round(width * scale_x))),
            max(1, int(round(height * scale_y))),
        )

    def _handle_rects(self, selection_rect: QRect) -> dict[str, QRect]:
        half_size = 5
        points = {
            HANDLE_TOP_LEFT: selection_rect.topLeft(),
            HANDLE_TOP_RIGHT: selection_rect.topRight(),
            HANDLE_BOTTOM_LEFT: selection_rect.bottomLeft(),
            HANDLE_BOTTOM_RIGHT: selection_rect.bottomRight(),
        }
        return {
            name: QRect(point.x() - half_size, point.y() - half_size, half_size * 2 + 1, half_size * 2 + 1)
            for name, point in points.items()
        }

    def _handle_at_display_point(self, point: QPoint) -> str | None:
        image_rect = self._display_rect()
        selection_rect = self._selection_display_rect(image_rect)
        if selection_rect is None:
            return None

        for name, handle_rect in self._handle_rects(selection_rect).items():
            if handle_rect.contains(point):
                return name
        return None

    def _sync_cursor(self, point: QPoint) -> None:
        image_rect = self._display_rect()
        if image_rect.isNull() or not image_rect.contains(point):
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        handle = self._handle_at_display_point(point)
        if handle is not None:
            self.setCursor(HANDLE_CURSORS[handle])
            return

        selection_rect = self._selection_display_rect(image_rect)
        if selection_rect is not None and selection_rect.contains(point):
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            return

        self.setCursor(Qt.CursorShape.CrossCursor)

    def _point_to_image(self, point: QPointF, clamp_to_image: bool = False) -> tuple[int, int]:
        image_rect = self._display_rect()
        if image_rect.isNull():
            return (0, 0)

        x_pos = point.x()
        y_pos = point.y()
        max_x = image_rect.x() + image_rect.width()
        max_y = image_rect.y() + image_rect.height()
        if clamp_to_image:
            x_pos = max(image_rect.x(), min(x_pos, max_x))
            y_pos = max(image_rect.y(), min(y_pos, max_y))

        relative_x = (x_pos - image_rect.x()) / max(1.0, float(image_rect.width()))
        relative_y = (y_pos - image_rect.y()) / max(1.0, float(image_rect.height()))
        image_x = int(round(max(0.0, min(relative_x, 1.0)) * self._pixmap.width()))
        image_y = int(round(max(0.0, min(relative_y, 1.0)) * self._pixmap.height()))
        return (image_x, image_y)

    def _update_selection_from_anchor(self, anchor_point: tuple[int, int], current_point: tuple[int, int]) -> None:
        selection = self._selection_from_anchor(anchor_point, current_point)
        self._set_selection(selection)

    def _selection_from_anchor(
        self,
        anchor_point: tuple[int, int],
        current_point: tuple[int, int],
    ) -> ImageCropRect | None:
        anchor_x, anchor_y = anchor_point
        current_x, current_y = current_point

        delta_x = current_x - anchor_x
        delta_y = current_y - anchor_y
        if delta_x == 0 and delta_y == 0:
            return None

        default_direction_x, default_direction_y = self._default_drag_directions()
        direction_x = 1 if delta_x > 0 else -1 if delta_x < 0 else default_direction_x
        direction_y = 1 if delta_y > 0 else -1 if delta_y < 0 else default_direction_y
        max_width = self._pixmap.width() - anchor_x if direction_x > 0 else anchor_x
        max_height = self._pixmap.height() - anchor_y if direction_y > 0 else anchor_y
        if max_width <= 0 or max_height <= 0:
            return None

        width, height = self._target_size(abs(delta_x), abs(delta_y), max_width, max_height)
        if width <= 0 or height <= 0:
            return None

        left = anchor_x if direction_x > 0 else anchor_x - width
        top = anchor_y if direction_y > 0 else anchor_y - height
        return self._normalize_crop_rect((left, top, width, height))

    def _default_drag_directions(self) -> tuple[int, int]:
        if self._drag_mode == "resize":
            if self._drag_handle == HANDLE_TOP_LEFT:
                return (-1, -1)
            if self._drag_handle == HANDLE_TOP_RIGHT:
                return (1, -1)
            if self._drag_handle == HANDLE_BOTTOM_LEFT:
                return (-1, 1)
            if self._drag_handle == HANDLE_BOTTOM_RIGHT:
                return (1, 1)
        return (1, 1)

    def _target_size(
        self,
        drag_width: int,
        drag_height: int,
        max_width: int,
        max_height: int,
    ) -> tuple[int, int]:
        if self._aspect_ratio is None:
            return (min(drag_width, max_width), min(drag_height, max_height))

        ratio_width, ratio_height = self._aspect_ratio
        if drag_width == 0 and drag_height == 0:
            return (0, 0)

        x_dominant = drag_width * ratio_height >= drag_height * ratio_width
        if x_dominant:
            width = min(drag_width if drag_width > 0 else 1, max_width)
            height = max(1, int(round(width * ratio_height / ratio_width)))
            if height > max_height:
                height = max_height
                width = max(1, int(round(height * ratio_width / ratio_height)))
        else:
            height = min(drag_height if drag_height > 0 else 1, max_height)
            width = max(1, int(round(height * ratio_width / ratio_height)))
            if width > max_width:
                width = max_width
                height = max(1, int(round(width * ratio_height / ratio_width)))

        return (min(width, max_width), min(height, max_height))

    def _move_selection(self, current_point: tuple[int, int]) -> None:
        if self._drag_reference_selection is None or self._move_offset is None:
            return

        _, _, width, height = self._drag_reference_selection
        offset_x, offset_y = self._move_offset
        max_left = max(0, self._pixmap.width() - width)
        max_top = max(0, self._pixmap.height() - height)
        left = max(0, min(current_point[0] - offset_x, max_left))
        top = max(0, min(current_point[1] - offset_y, max_top))
        self._set_selection((left, top, width, height))

    def _opposite_corner(self, selection: ImageCropRect, handle: str) -> tuple[int, int]:
        left, top, width, height = selection
        right = left + width
        bottom = top + height
        if handle == HANDLE_TOP_LEFT:
            return (right, bottom)
        if handle == HANDLE_TOP_RIGHT:
            return (left, bottom)
        if handle == HANDLE_BOTTOM_LEFT:
            return (right, top)
        return (left, top)

    def _fit_selection_to_ratio(self, selection: ImageCropRect, aspect_ratio: tuple[int, int]) -> ImageCropRect:
        left, top, width, height = selection
        ratio_width, ratio_height = aspect_ratio

        if width * ratio_height >= height * ratio_width:
            new_height = height
            new_width = max(1, int(round(new_height * ratio_width / ratio_height)))
            if new_width > width:
                new_width = width
                new_height = max(1, int(round(new_width * ratio_height / ratio_width)))
        else:
            new_width = width
            new_height = max(1, int(round(new_width * ratio_height / ratio_width)))
            if new_height > height:
                new_height = height
                new_width = max(1, int(round(new_height * ratio_width / ratio_height)))

        center_x = left + width / 2
        center_y = top + height / 2
        return self._place_rect_around_center(center_x, center_y, new_width, new_height)

    def _place_rect_around_center(
        self,
        center_x: float,
        center_y: float,
        width: int,
        height: int,
    ) -> ImageCropRect:
        width = min(max(1, width), self._pixmap.width())
        height = min(max(1, height), self._pixmap.height())
        max_left = max(0, self._pixmap.width() - width)
        max_top = max(0, self._pixmap.height() - height)
        left = max(0, min(int(round(center_x - width / 2)), max_left))
        top = max(0, min(int(round(center_y - height / 2)), max_top))
        return (left, top, width, height)

    def _normalize_crop_rect(self, crop_rect: ImageCropRect | None) -> ImageCropRect | None:
        if crop_rect is None:
            return None

        left, top, width, height = crop_rect
        if width <= 0 or height <= 0:
            return None
        if left < 0 or top < 0:
            return None
        if left + width > self._pixmap.width() or top + height > self._pixmap.height():
            return None
        return (left, top, width, height)


class ImageCropDialog(QDialog):
    def __init__(
        self,
        source_path: Path,
        crop_rect: ImageCropRect | None = None,
        language: str = "en",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._source_path = source_path
        self._language = language
        self._pixmap = _load_preview_pixmap(source_path)
        self._is_ready = not self._pixmap.isNull()
        initial_ratio = _matching_aspect_ratio(crop_rect)

        self.setWindowTitle(_crop_text(self._language, "title"))
        self.setModal(True)

        instructions_label = QLabel(_crop_text(self._language, "instructions"))
        instructions_label.setWordWrap(True)
        instructions_label.setStyleSheet("color: #d1fae5; font-size: 12px;")

        self._image_size_label = QLabel()
        self._image_size_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        self._preview_size_label = QLabel()
        self._preview_size_label.setStyleSheet("color: #94a3b8; font-size: 12px;")

        ratio_title = QLabel(_crop_text(self._language, "aspect_ratio"))
        ratio_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase;")

        self._ratio_value_label = QLabel()
        self._ratio_value_label.setStyleSheet("color: #ecfdf5; font-size: 12px; font-weight: 700;")

        self._selection_label = QLabel()
        self._selection_label.setWordWrap(True)
        self._selection_label.setStyleSheet("color: #ecfdf5; font-size: 12px; font-weight: 700;")

        self._ratio_buttons = QButtonGroup(self)
        self._ratio_buttons.setExclusive(True)
        ratio_row = QHBoxLayout()
        ratio_row.setContentsMargins(0, 0, 0, 0)
        ratio_row.setSpacing(8)
        for label, ratio in ASPECT_RATIO_OPTIONS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setStyleSheet(_ratio_button_style())
            if ratio == initial_ratio:
                button.setChecked(True)
            button.clicked.connect(lambda checked, value=ratio: self._set_aspect_ratio(value))
            self._ratio_buttons.addButton(button)
            ratio_row.addWidget(button)
        ratio_row.addStretch(1)

        self._canvas = ImageCropCanvas(self._pixmap, crop_rect=crop_rect, aspect_ratio=initial_ratio)
        self._canvas.setStyleSheet(
            """
            QFrame {
                background: #09100c;
                border: 1px solid #244234;
                border-radius: 14px;
            }
            """
        )
        self._canvas.selection_changed.connect(self._on_selection_changed)
        self._canvas.preview_size_changed.connect(self._on_preview_size_changed)

        reset_button = QPushButton(_crop_text(self._language, "reset"))
        reset_button.clicked.connect(self._canvas.clear_selection)
        reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_button.setStyleSheet(_dialog_button_style(primary=False))

        cancel_button = QPushButton(_crop_text(self._language, "cancel"))
        cancel_button.clicked.connect(self.reject)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_button.setStyleSheet(_dialog_button_style(primary=False))

        apply_button = QPushButton(_crop_text(self._language, "apply"))
        apply_button.clicked.connect(self.accept)
        apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_button.setStyleSheet(_dialog_button_style(primary=True))

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(10)
        button_row.addWidget(reset_button)
        button_row.addStretch(1)
        button_row.addWidget(cancel_button)
        button_row.addWidget(apply_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(instructions_label)
        layout.addWidget(self._image_size_label)
        layout.addWidget(self._preview_size_label)
        layout.addWidget(ratio_title)
        layout.addLayout(ratio_row)
        layout.addWidget(self._ratio_value_label)
        layout.addWidget(self._selection_label)
        layout.addWidget(self._canvas, 1)
        layout.addLayout(button_row)
        self.setLayout(layout)
        self.setStyleSheet("QDialog { background: #08100b; }")

        self._refresh_labels(self._canvas.selection())
        self._on_preview_size_changed(self._canvas.display_size())
        self.resize(
            min(max(self._canvas.sizeHint().width() + 72, 860), 1320),
            min(max(self._canvas.sizeHint().height() + 240, 720), 980),
        )

    def is_ready(self) -> bool:
        return self._is_ready

    def selected_crop_rect(self) -> ImageCropRect | None:
        return self._canvas.selection()

    def _set_aspect_ratio(self, aspect_ratio: AspectRatio) -> None:
        self._canvas.set_aspect_ratio(aspect_ratio)
        self._update_ratio_label(aspect_ratio)

    def _on_selection_changed(self, selection: ImageCropRect | None) -> None:
        self._refresh_labels(selection)

    def _on_preview_size_changed(self, preview_size: tuple[int, int]) -> None:
        self._preview_size_label.setText(
            _crop_text(self._language, "preview_size", width=preview_size[0], height=preview_size[1])
        )

    def _refresh_labels(self, selection: ImageCropRect | None) -> None:
        self._image_size_label.setText(
            _crop_text(self._language, "image_size", width=self._pixmap.width(), height=self._pixmap.height())
        )
        self._update_ratio_label(self._canvas.aspect_ratio())
        if selection is None:
            self._selection_label.setText(_crop_text(self._language, "selection_none"))
            return

        left, top, width, height = selection
        self._selection_label.setText(
            _crop_text(self._language, "selection_active", width=width, height=height, x=left, y=top)
        )

    def _update_ratio_label(self, aspect_ratio: AspectRatio) -> None:
        self._ratio_value_label.setText(
            _crop_text(self._language, "current_ratio", ratio=_ratio_label(aspect_ratio))
        )


def _load_preview_pixmap(source_path: Path) -> QPixmap:
    try:
        with Image.open(source_path) as image:
            preview = image.convert("RGBA").copy()
    except OSError:
        return QPixmap()

    return QPixmap.fromImage(ImageQt(preview))


def _matching_aspect_ratio(crop_rect: ImageCropRect | None) -> AspectRatio:
    if crop_rect is None:
        return None

    _, _, width, height = crop_rect
    if width <= 0 or height <= 0:
        return None

    for _, aspect_ratio in ASPECT_RATIO_OPTIONS:
        if aspect_ratio is None:
            continue
        ratio_width, ratio_height = aspect_ratio
        if width * ratio_height == height * ratio_width:
            return aspect_ratio
    return None


def _ratio_label(aspect_ratio: AspectRatio) -> str:
    if aspect_ratio is None:
        return "Free"
    return f"{aspect_ratio[0]}:{aspect_ratio[1]}"


def _dialog_button_style(primary: bool) -> str:
    if primary:
        return (
            "QPushButton {"
            "background: #10b981;"
            "color: #ecfdf5;"
            "border: none;"
            "border-radius: 10px;"
            "padding: 10px 18px;"
            "font-size: 12px;"
            "font-weight: 700;"
            "}"
            "QPushButton:hover { background: #34d399; }"
        )

    return (
        "QPushButton {"
        "background: #132019;"
        "color: #ecfdf5;"
        "border: 1px solid #244234;"
        "border-radius: 10px;"
        "padding: 10px 18px;"
        "font-size: 12px;"
        "font-weight: 700;"
        "}"
        "QPushButton:hover { border-color: #10b981; }"
    )


def _ratio_button_style() -> str:
    return (
        "QPushButton {"
        "background: #132019;"
        "color: #d1fae5;"
        "border: 1px solid #244234;"
        "border-radius: 10px;"
        "padding: 8px 14px;"
        "font-size: 12px;"
        "font-weight: 700;"
        "}"
        "QPushButton:hover { border-color: #10b981; color: #ecfdf5; }"
        "QPushButton:checked {"
        "background: rgba(16, 185, 129, 0.18);"
        "border-color: #10b981;"
        "color: #ecfdf5;"
        "}"
    )
