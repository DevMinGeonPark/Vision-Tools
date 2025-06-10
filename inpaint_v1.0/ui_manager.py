import cv2
import numpy as np
import os

class UIManager:
    """UI 관련 로직을 처리하는 클래스"""
    WINDOW_NAME = 'Inpaint'

    def __init__(self, app_state, brush_callback, mouse_callback):
        self.state = app_state
        self.brush_callback = brush_callback
        self.mouse_callback = mouse_callback
        
    def setup_ui(self):
        cv2.namedWindow(self.WINDOW_NAME)
        cv2.createTrackbar('Brush Size', self.WINDOW_NAME, self.state.brush_size, self.state.max_brush_size, self.brush_callback)
        cv2.setMouseCallback(self.WINDOW_NAME, self.mouse_callback)

    def update_display(self):
        display = self.state.display_image.copy()
        
        # A 영역 (제거할 부분, 빨간색)
        display[self.state.target_mask == 255] = [0, 0, 255]
        
        # B 영역 (소스, 파란색)
        display[self.state.source_mask == 255] = [255, 0, 0]
        
        self._draw_warning(display)
        self._draw_help_overlay(display)
        status_bar = self._create_status_bar()
        
        # 상태 표시줄과 이미지 합치기
        h, w, _ = display.shape
        status_h, status_w, _ = status_bar.shape
        
        if status_w != w:
            status_bar = cv2.resize(status_bar, (w, status_h))

        combined_display = np.vstack((display, status_bar))
        cv2.imshow(self.WINDOW_NAME, combined_display)

    def _draw_warning(self, display):
        if self.state.warning_timer > 0:
            cv2.rectangle(display, (50, 50), (display.shape[1]-50, 100), (0, 0, 0), -1)
            cv2.rectangle(display, (50, 50), (display.shape[1]-50, 100), (0, 0, 255), 2)
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(self.state.warning_message, font, 0.7, 2)[0]
            text_x = (display.shape[1] - text_size[0]) // 2
            cv2.putText(display, self.state.warning_message, (text_x, 80), font, 0.7, (0, 0, 255), 2)
            
            self.state.decrease_warning_timer()

    def _create_status_bar(self):
        status_bar = np.full((self.state.status_height, self.state.target_size[0], 3), 50, dtype=np.uint8)
        
        painted_count = len([f for f in os.listdir(self.state.save_dir) if os.path.exists(self.state.save_dir)])
        
        status_text = f"Image: {os.path.basename(self.state.get_current_image_path())} ({self.state.current_index + 1}/{len(self.state.image_files)})"
        count_text = f"Saved: {painted_count}"
        mode_text = f"Mode: {'Select A (Target)' if self.state.mode == 'target' else 'Select B (Source)'}"
        size_text = f"Size: {self.state.original_image.shape[1]}x{self.state.original_image.shape[0]}" if self.state.original_image is not None else "Size: N/A"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        color = (255, 255, 255)
        
        cv2.putText(status_bar, status_text, (10, 20), font, font_scale, color, thickness)
        cv2.putText(status_bar, count_text, (status_bar.shape[1] - 150, 20), font, font_scale, color, thickness)
        cv2.putText(status_bar, mode_text, (10, 45), font, font_scale, color, thickness)
        cv2.putText(status_bar, size_text, (status_bar.shape[1] - 150, 45), font, font_scale, color, thickness)
        return status_bar

    def update_brush_size_trackbar(self):
        cv2.setTrackbarPos('Brush Size', self.WINDOW_NAME, self.state.brush_size)

    def _draw_help_overlay(self, display):
        if not self.state.show_help:
            return

        h, w, _ = display.shape
        overlay = display.copy()
        # 반투명 배경 그리기
        cv2.rectangle(overlay, (50, 50), (w - 50, h - 50), (0, 0, 0), -1)
        alpha = 0.7
        cv2.addWeighted(overlay, alpha, display, 1 - alpha, 0, display)

        help_text = [
            "--- Controls ---",
            "'H': Toggle Help",
            "'Q': Select Area A (Target)",
            "'W': Select Area B (Source)",
            "'E': Apply Inpainting",
            "'R': Reset Current Image",
            "'A' / 'D': Previous / Next Image",
            "'S': Save and Next",
            "'F': Save Only",
            "'Ctrl+Wheel': Adjust Brush Size",
            "'ESC': Exit",
        ]

        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 1
        color = (255, 255, 255)
        
        y_pos = 80
        for line in help_text:
            cv2.putText(display, line, (70, y_pos), font, font_scale, color, thickness, cv2.LINE_AA)
            y_pos += 30

    def destroy_windows(self):
        cv2.destroyAllWindows()
