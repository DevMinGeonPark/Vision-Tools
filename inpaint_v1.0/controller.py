import cv2
import numpy as np
import os
import cv2
import numpy as np
import os

from app_state import AppState
from image_manager import ImageManager
from ui_manager import UIManager

class InpaintController:
    """애플리케이션의 핵심 로직 및 사용자 입력 처리"""
    def __init__(self, image_dir, save_dir):
        self.is_initialized = False

        try:
            self.state = AppState(image_dir, save_dir)
        except ValueError as e:
            print(e)
            return

        self.image_manager = ImageManager(self.state.target_size)
        self.ui_manager = UIManager(self.state, self.on_brush_size_change, self.mouse_callback)
        
        self.is_running = True
        self.is_initialized = True

    def run(self):
        if not self.is_initialized:
            return
            
        self.ui_manager.setup_ui()
        self._load_current_image()

        while self.is_running:
            self.ui_manager.update_display()
            key = cv2.waitKey(1) & 0xFF
            self.handle_key_press(key)

        self.ui_manager.destroy_windows()

    def _load_current_image(self):
        path = self.state.get_current_image_path()
        image = self.image_manager.load_image(path)
        self.state.reset_for_new_image(image)
    
    def on_brush_size_change(self, value):
        self.state.brush_size = max(1, value)

    def mouse_callback(self, event, x, y, flags, param):
        ctrl_pressed = flags & cv2.EVENT_FLAG_CTRLKEY
        
        if event == cv2.EVENT_MOUSEWHEEL and ctrl_pressed:
            if flags > 0:
                self.state.brush_size = min(self.state.max_brush_size, self.state.brush_size + 1)
            else:
                self.state.brush_size = max(self.state.min_brush_size, self.state.brush_size - 1)
            self.ui_manager.update_brush_size_trackbar()
            return
            
        if event == cv2.EVENT_LBUTTONDOWN:
            self.state.drawing = True
            self._draw_on_mask(x, y)
        elif event == cv2.EVENT_MOUSEMOVE and self.state.drawing:
            self._draw_on_mask(x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.state.drawing = False

    def _draw_on_mask(self, x, y):
        mask = self.state.target_mask if self.state.mode == "target" else self.state.source_mask
        cv2.circle(mask, (x, y), self.state.brush_size, 255, -1)
        if self.state.mode == "source":
            self.state.has_source_selection = True

    def handle_key_press(self, key):
        key_actions = {
            27: self.quit,
            ord('d'): self.next_image,
            ord('a'): self.prev_image,
            ord('q'): self.set_mode_target,
            ord('w'): self.set_mode_source,
            ord('r'): self.reset_image,
            ord('e'): self.perform_inpaint,
            ord('s'): self.save_and_next,
            ord('f'): self.save_result, # 저장만
            ord('h'): self.toggle_help,
        }
        action = key_actions.get(key)
        if action:
            action()

    def toggle_help(self):
        self.state.show_help = not self.state.show_help

    def quit(self):
        self.is_running = False

    def next_image(self):
        if self.state.next_image():
            self._load_current_image()
        else:
            self.state.show_warning("마지막 이미지입니다.")

    def prev_image(self):
        if self.state.prev_image():
            self._load_current_image()
        else:
            self.state.show_warning("첫 번째 이미지입니다.")

    def set_mode_target(self):
        self.state.mode = "target"

    def set_mode_source(self):
        self.state.mode = "source"

    def reset_image(self):
        self._load_current_image()

    def perform_inpaint(self):
        if np.sum(self.state.target_mask) == 0:
            self.state.show_warning("A 영역(제거할 부분)을 선택하세요.")
            return

        if self.state.has_source_selection:
            self.state.show_warning("B 영역 사용은 미지원. 기본 인페인팅 실행.")
        
        result = cv2.inpaint(self.state.original_image, self.state.target_mask, 3, cv2.INPAINT_NS)
        self.state.display_image = result
        self.state.is_painted = True

    def _save_current_image(self):
        """Internal helper to save the image. Returns True on success."""
        if not self.state.is_painted:
            self.state.show_warning("인페인팅을 먼저 실행하세요 (E).")
            return False
        
        original_filename = self.state.image_files[self.state.current_index]
        save_path = os.path.join(self.state.save_dir, original_filename)
        
        os.makedirs(self.state.save_dir, exist_ok=True)
        
        self.image_manager.save_image(self.state.display_image, save_path)
        self.state.show_warning(f"저장 완료: {original_filename}")
        return True

    def save_and_next(self):
        """Saves the result and moves to the next image."""
        if self._save_current_image():
            self.next_image()

    def save_result(self): # 'f' key
        """Saves the result without moving to the next image."""
        self._save_current_image()
