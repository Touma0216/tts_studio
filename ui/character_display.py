import os
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFileDialog, QFrame, QApplication, QMessageBox,
                             QScrollArea, QSlider, QDialog)
from PyQt6.QtCore import Qt, QRect, QPoint, QTimer
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPen, QColor

from core.image_manager import ImageManager

class MiniMapWidget(QLabel):
    """右上に表示されるミニマップウィジェット"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 90)
        self.character_display = None
        self.original_pixmap = None
        self.view_rect = QRect()

        self.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200);
                border: 2px solid #666;
                border-radius: 4px;
            }
        """)
        self.setText("ミニマップ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)

    def set_character_display_widget(self, character_display):
        self.character_display = character_display

    def update_minimap(self, original_pixmap, view_rect):
        if not original_pixmap or original_pixmap.isNull():
            self.clear()
            self.setText("ミニマップ")
            return

        self.original_pixmap = original_pixmap
        self.view_rect = view_rect
        mini_pixmap = original_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        if not view_rect.isNull():
            painter = QPainter(mini_pixmap)
            painter.setPen(QPen(QColor(255, 0, 0, 200), 2))
            scale_x = mini_pixmap.width() / original_pixmap.width()
            scale_y = mini_pixmap.height() / original_pixmap.height()
            mini_view_rect = QRect(
                round(view_rect.x() * scale_x), round(view_rect.y() * scale_y),
                round(view_rect.width() * scale_x), round(view_rect.height() * scale_y)
            )
            painter.drawRect(mini_view_rect)
            painter.end()

        self.setPixmap(mini_pixmap)

    def mousePressEvent(self, event):
        if not self.character_display or not self.original_pixmap:
            return

        click_pos = event.position().toPoint()
        scale_x = self.original_pixmap.width() / self.width()
        scale_y = self.original_pixmap.height() / self.height()
        target_x = round(click_pos.x() * scale_x)
        target_y = round(click_pos.y() * scale_y)
        self.character_display.move_view_to_position(target_x, target_y)

class DraggableImageLabel(QLabel):
    """ドラッグで移動可能な画像表示ラベル"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_area = None
        self.character_display = None
        self.last_pan_pos = None
        self.is_dragging = False
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def set_scroll_area(self, scroll_area):
        self.scroll_area = scroll_area

    def set_character_display_widget(self, character_display):
        self.character_display = character_display

    def wheelEvent(self, event):
        if not self.pixmap() or not self.character_display:
            super().wheelEvent(event)
            return

        delta = event.angleDelta().y()
        zoom_step = 5
        current_zoom = self.character_display.zoom_slider.value()

        if delta > 0:
            new_zoom = min(150, current_zoom + zoom_step)
        else:
            new_zoom = max(20, current_zoom - zoom_step)

        self.character_display.zoom_slider.setValue(new_zoom)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap():
            self.last_pan_pos = event.position().toPoint()
            self.is_dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.last_pan_pos and self.scroll_area:
            delta = event.position().toPoint() - self.last_pan_pos
            h_scroll = self.scroll_area.horizontalScrollBar()
            v_scroll = self.scroll_area.verticalScrollBar()
            h_scroll.setValue(h_scroll.value() - delta.x())
            v_scroll.setValue(v_scroll.value() - delta.y())
            self.last_pan_pos = event.position().toPoint()

            if self.character_display:
                self.character_display.update_minimap_view()
                self.character_display.update_custom_scrollbars()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            self.last_pan_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self.character_display:
                self.character_display.save_ui_settings()
        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        if self.pixmap():
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_dragging:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().leaveEvent(event)

class CharacterDisplayWidget(QWidget):
    """キャラクター表示エリア専門ウィジェット（画像履歴統合版）"""
    def __init__(self, parent=None):
        super().__init__(parent)

        self.image_manager = ImageManager()
        self.current_image_path = None
        self.current_image_id = None
        self.original_pixmap = None
        self.current_zoom_percent = 50

        self.init_ui()

        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.update_image_display)

        QTimer.singleShot(100, self.load_last_image)

    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #ffffff; border: 1px solid #dee2e6; border-radius: 4px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ... (UI setup code remains the same) ...
        # (The rest of init_ui is unchanged, so it's omitted for brevity)
        header_layout = QHBoxLayout()
        header_label = QLabel("キャラクター表示")
        header_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_label.setStyleSheet("color: #333; border: none; padding: 5px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        self.toggle_minimap_btn = QPushButton("🗺️ ミニマップ")
        self.toggle_minimap_btn.setToolTip("ミニマップの表示/非表示")
        self.toggle_minimap_btn.setEnabled(False)
        self.toggle_minimap_btn.setCheckable(True)
        self.toggle_minimap_btn.setStyleSheet("QPushButton { background-color: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; font-size: 11px; padding: 4px 8px; } QPushButton:hover:enabled { background-color: #e9ecef; } QPushButton:checked { background-color: #e0e6ef; border-color: #007bff; } QPushButton:disabled { color: #ccc; }")
        header_layout.addWidget(self.toggle_minimap_btn)
        
        zoom_layout = QVBoxLayout()
        self.zoom_label = QLabel("50%")
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoom_label.setStyleSheet("color: #666; font-size: 11px; font-weight: bold; border: none;")
        slider_layout = QHBoxLayout()
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(20, 150)
        self.zoom_slider.setValue(50)
        self.zoom_slider.setEnabled(False)
        slider_style = "QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 4px; border-radius: 2px; } QSlider::sub-page:horizontal { background: #66e; } QSlider::handle:horizontal { background: #eee; border: 1px solid #777; width: 14px; margin: -6px 0; border-radius: 7px; }"
        self.zoom_slider.setStyleSheet(slider_style)
        slider_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addLayout(slider_layout)
        
        image_container = QWidget()
        image_container.setStyleSheet("border: 1px solid #ccc; border-radius: 4px; background-color: #f8f9fa;")
        image_main_layout = QHBoxLayout(image_container)
        image_main_layout.setContentsMargins(5, 5, 5, 5)
        left_side_layout = QVBoxLayout()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("border: none;")
        self.character_image_label = DraggableImageLabel()
        self.character_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character_image_label.setMinimumSize(200, 200)
        self.character_image_label.setStyleSheet("QLabel { background-color: #f8f9fa; border: 2px dashed #adb5bd; border-radius: 6px; color: #6c757d; font-size: 14px; padding: 20px; }")
        self.character_image_label.setText("画像が読み込まれていません\n\nファイルメニューから\n「立ち絵画像を読み込み」\nを選択してください")
        self.character_image_label.setWordWrap(True)
        self.character_image_label.set_scroll_area(self.scroll_area)
        self.character_image_label.set_character_display_widget(self)
        self.scroll_area.setWidget(self.character_image_label)
        self.minimap = MiniMapWidget(self.scroll_area)
        self.minimap.set_character_display_widget(self)
        self.minimap.hide()
        h_slider_layout = QHBoxLayout()
        h_label = QLabel("左右:")
        h_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.h_position_slider = QSlider(Qt.Orientation.Horizontal)
        self.h_position_slider.setRange(0, 100)
        self.h_position_slider.setEnabled(False)
        self.h_position_slider.setStyleSheet(slider_style)
        h_slider_layout.addWidget(h_label)
        h_slider_layout.addWidget(self.h_position_slider)
        left_side_layout.addWidget(self.scroll_area, 1)
        left_side_layout.addLayout(h_slider_layout)
        v_slider_layout = QVBoxLayout()
        v_label = QLabel("上下")
        v_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        self.v_position_slider = QSlider(Qt.Orientation.Vertical)
        self.v_position_slider.setRange(0, 100)
        self.v_position_slider.setEnabled(False)
        v_slider_style = "QSlider::groove:vertical { border: 1px solid #bbb; background: white; width: 4px; border-radius: 2px; } QSlider::sub-page:vertical { background: #66e; } QSlider::handle:vertical { background: #eee; border: 1px solid #777; height: 14px; margin: 0 -6px; border-radius: 7px; }"
        self.v_position_slider.setStyleSheet(v_slider_style)
        v_slider_layout.addWidget(v_label)
        v_slider_layout.addWidget(self.v_position_slider, 1)
        image_main_layout.addLayout(left_side_layout, 1)
        image_main_layout.addLayout(v_slider_layout)
        
        self.image_info_label = QLabel("")
        self.image_info_label.setStyleSheet("color: #666; font-size: 10px; border: none;")
        button_layout = QHBoxLayout()
        self.image_clear_btn = QPushButton("🗑️")
        self.image_clear_btn.setFixedSize(30, 30)
        self.image_clear_btn.setToolTip("画像をクリア")
        self.image_clear_btn.setEnabled(False)
        self.image_clear_btn.setStyleSheet("QPushButton { background-color: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; } QPushButton:hover:enabled { background-color: #f5c6cb; } QPushButton:disabled { color: #999; }")
        button_layout.addStretch()
        button_layout.addWidget(self.image_clear_btn)
        
        layout.addLayout(header_layout)
        layout.addLayout(zoom_layout)
        layout.addWidget(image_container, 1)
        layout.addWidget(self.image_info_label)
        layout.addLayout(button_layout)

        self.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.h_position_slider.valueChanged.connect(self.on_position_slider_changed)
        self.v_position_slider.valueChanged.connect(self.on_position_slider_changed)
        self.toggle_minimap_btn.toggled.connect(self.toggle_minimap)
        self.image_clear_btn.clicked.connect(self.clear_character_image)


    def load_last_image(self):
        self.image_manager.cleanup_missing_images()
        last_image = self.image_manager.get_last_image()
        if last_image and Path(last_image['image_path']).exists():
            self.load_image_from_data(last_image)

    def load_image_from_data(self, image_data):
        image_path = image_data['image_path']
        if not Path(image_path).exists():
            QMessageBox.warning(self, "エラー", f"画像ファイルが見つかりません:\n{image_path}")
            return
        
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            return

        self.original_pixmap = pixmap
        self.current_image_path = image_path
        self.current_image_id = image_data['id']
        self.image_manager.add_image(image_path, image_data['name'])
        
        ui_settings = self.image_manager.get_ui_settings(self.current_image_id)
        
        self.restore_ui_settings(ui_settings)
        
        self.character_image_label.setStyleSheet("QLabel { background-color: white; border: none; }")
        file_info = Path(image_path)
        img_size = pixmap.size()
        self.image_info_label.setText(f"📁 {image_data['name']}\n📐 {img_size.width()}×{img_size.height()}px 💾 {file_info.stat().st_size // 1024} KB")
        self.enable_controls()
        self.update_minimap_position()

    def load_character_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "立ち絵画像を選択", "", "画像ファイル (*.png *.jpg *.jpeg)")
        if not file_path:
            return
        
        image_name = Path(file_path).stem
        image_id = self.image_manager.add_image(file_path, image_name)
        new_image_data = self.image_manager.get_image_by_id(image_id)
        if new_image_data:
            self.load_image_from_data(new_image_data)
    
    def enable_controls(self):
        for widget in [self.image_clear_btn, self.zoom_slider, self.h_position_slider, self.v_position_slider, self.toggle_minimap_btn]:
            widget.setEnabled(True)

    def clear_character_image(self):
        self.character_image_label.clear()
        self.character_image_label.setText("画像が読み込まれていません...")
        self.character_image_label.setStyleSheet("QLabel { background-color: #f8f9fa; border: 2px dashed #adb5bd; }")
        self.original_pixmap = None
        self.current_image_path = None
        self.current_image_id = None
        self.image_info_label.setText("")
        for widget in [self.image_clear_btn, self.zoom_slider, self.h_position_slider, self.v_position_slider, self.toggle_minimap_btn]:
            widget.setEnabled(False)
        self.zoom_slider.setValue(50)
        self.h_position_slider.setValue(50)
        self.v_position_slider.setValue(50)
        self.toggle_minimap_btn.setChecked(False)
        self.zoom_label.setText("50%")
        self.minimap.hide()

    def restore_ui_settings(self, ui_settings):
        zoom = ui_settings.get('zoom_percent', 50)
        h_pos = ui_settings.get('h_position', 50)
        v_pos = ui_settings.get('v_position', 50)
        minimap_visible = ui_settings.get('minimap_visible', False)
        
        self.zoom_slider.blockSignals(True)
        self.current_zoom_percent = zoom
        self.zoom_slider.setValue(zoom)
        self.zoom_label.setText(f"{zoom}%")
        self.zoom_slider.blockSignals(False)

        self.update_image_display()
        
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        if h_scroll.maximum() > 0:
            h_value = round(h_scroll.maximum() * h_pos / 100)
            h_scroll.setValue(h_value)
        if v_scroll.maximum() > 0:
            v_value = round(v_scroll.maximum() * (100 - v_pos) / 100)
            v_scroll.setValue(v_value)
            
        self.update_custom_scrollbars()

        self.toggle_minimap_btn.setChecked(minimap_visible)
        self.toggle_minimap(minimap_visible)

    def save_ui_settings(self):
        if not self.current_image_id:
            return
        
        ui_settings = {
            'zoom_percent': self.current_zoom_percent,
            'h_position': self.h_position_slider.value(),
            'v_position': self.v_position_slider.value(),
            'minimap_visible': self.toggle_minimap_btn.isChecked()
        }
        self.image_manager.update_ui_settings(self.current_image_id, ui_settings)

    def show_image_history_dialog(self):
        from .image_history import ImageHistoryWidget
        
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("画像履歴から選択")
            dlg.setModal(True)
            dlg.resize(600, 500)
            dlg.setStyleSheet("QDialog { background:#f8f9fa; }")

            layout = QVBoxLayout(dlg)
            history_widget = ImageHistoryWidget(self.image_manager, dlg)

            def on_image_selected(image_data):
                if not Path(image_data['image_path']).exists():
                    QMessageBox.warning(dlg, "エラー", "画像ファイルが見つかりません。")
                    return
                dlg.accept()
                self.load_image_from_data(image_data)

            history_widget.image_selected.connect(on_image_selected)
            layout.addWidget(history_widget)
            dlg.exec()
            
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"画像履歴ダイアログでエラーが発生しました:\n{str(e)}")

    def on_zoom_slider_changed(self, value):
        if not self.original_pixmap:
            return
        
        # ★★★ 変更点 1: 画面更新を一時停止 ★★★
        self.setUpdatesEnabled(False)
        try:
            scroll_area = self.scroll_area
            h_scroll = scroll_area.horizontalScrollBar()
            v_scroll = scroll_area.verticalScrollBar()
            
            old_label_size = self.character_image_label.size()
            viewport_size = scroll_area.viewport().size()
            
            if old_label_size.width() > 0 and old_label_size.height() > 0:
                center_x_ratio = (h_scroll.value() + viewport_size.width() / 2) / old_label_size.width()
                center_y_ratio = (v_scroll.value() + viewport_size.height() / 2) / old_label_size.height()
            else:
                center_x_ratio = 0.5
                center_y_ratio = 0.5

            self.current_zoom_percent = value
            self.update_image_display()
            self.update_zoom_label()

            new_label_size = self.character_image_label.size()
            
            new_h_scroll_value = round((new_label_size.width() * center_x_ratio) - (viewport_size.width() / 2))
            new_v_scroll_value = round((new_label_size.height() * center_y_ratio) - (viewport_size.height() / 2))
            
            h_scroll.setValue(new_h_scroll_value)
            v_scroll.setValue(new_v_scroll_value)
            
            self.update_custom_scrollbars()
            self.save_ui_settings()
        finally:
            # ★★★ 変更点 2: 画面更新を再開 ★★★
            self.setUpdatesEnabled(True)

    def update_image_display(self):
        if not self.original_pixmap: return
        self.current_zoom_percent = self.zoom_slider.value()
        original_size = self.original_pixmap.size()
        new_width = round(original_size.width() * self.current_zoom_percent / 100)
        new_height = round(original_size.height() * self.current_zoom_percent / 100)
        scaled_pixmap = self.original_pixmap.scaled(new_width, new_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.character_image_label.setPixmap(scaled_pixmap)
        self.character_image_label.resize(scaled_pixmap.size())
        
        # ★★★ 変更点 3: ちらつきの原因だったため削除 ★★★
        # QApplication.processEvents()
        
        self.update_minimap_view()

    def update_zoom_label(self):
        self.zoom_label.setText(f"{self.current_zoom_percent}%")
    
    def on_position_slider_changed(self):
        if not self.original_pixmap: return
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        h_max = h_scroll.maximum()
        v_max = v_scroll.maximum()

        if h_max > 0:
            h_scroll.setValue(round(h_max * self.h_position_slider.value() / 100))
        if v_max > 0:
            v_scroll.setValue(round(v_max * (100 - self.v_position_slider.value()) / 100))
        
        self.update_minimap_view()
        if not self.h_position_slider.signalsBlocked():
            self.save_ui_settings()

    def update_custom_scrollbars(self):
        if not self.original_pixmap: return
        # ★★★ 変更点 4: ちらつきの原因だったため削除 ★★★
        # QApplication.processEvents()
        h_scroll = self.scroll_area.horizontalScrollBar()
        v_scroll = self.scroll_area.verticalScrollBar()
        h_max = h_scroll.maximum()
        v_max = v_scroll.maximum()

        self.h_position_slider.blockSignals(True)
        self.v_position_slider.blockSignals(True)
        
        self.h_position_slider.setValue(round(100 * h_scroll.value() / h_max) if h_max > 0 else 50)
        self.v_position_slider.setValue(100 - round(100 * v_scroll.value() / v_max) if v_max > 0 else 50)
        
        self.h_position_slider.blockSignals(False)
        self.v_position_slider.blockSignals(False)

    def toggle_minimap(self, checked):
        if not self.original_pixmap: return
        if checked:
            self.minimap.show()
            self.update_minimap_view()
        else:
            self.minimap.hide()
        
        if not self.toggle_minimap_btn.signalsBlocked():
            self.save_ui_settings()

    def update_minimap_view(self):
        if not self.original_pixmap or not self.minimap.isVisible(): return
        h_scroll, v_scroll = self.scroll_area.horizontalScrollBar(), self.scroll_area.verticalScrollBar()
        view_w, view_h = self.scroll_area.viewport().width(), self.scroll_area.viewport().height()
        img_w, img_h = self.character_image_label.width(), self.character_image_label.height()
        if img_w <= 0: return

        scale_x = self.original_pixmap.width() / img_w
        scale_y = self.original_pixmap.height() / img_h
        view_rect = QRect(
            round(h_scroll.value() * scale_x), round(v_scroll.value() * scale_y),
            round(view_w * scale_x), round(view_h * scale_y)
        )
        self.minimap.update_minimap(self.original_pixmap, view_rect)
    
    def move_view_to_position(self, target_x, target_y):
        if not self.original_pixmap: return
        img_w = self.character_image_label.width()
        img_h = self.character_image_label.height()
        scale_x = img_w / self.original_pixmap.width()
        scale_y = img_h / self.original_pixmap.height()
        scroll_x = round(target_x * scale_x - self.scroll_area.viewport().width() / 2)
        scroll_y = round(target_y * scale_y - self.scroll_area.viewport().height() / 2)
        
        self.scroll_area.horizontalScrollBar().setValue(scroll_x)
        self.scroll_area.verticalScrollBar().setValue(scroll_y)
        self.update_minimap_view()
        self.update_custom_scrollbars()
        self.save_ui_settings()

    def update_minimap_position(self):
        if self.scroll_area:
            x_pos = self.scroll_area.viewport().width() - self.minimap.width() - 5
            self.minimap.move(x_pos, 5)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_minimap_position()
        if self.original_pixmap:
            self.resize_timer.start(150)