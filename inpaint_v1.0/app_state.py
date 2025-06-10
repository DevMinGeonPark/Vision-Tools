import numpy as np
import os

class AppState:
    """애플리케이션의 모든 상태를 관리하는 클래스"""
    def __init__(self, image_dir, save_dir):
        self.image_dir = image_dir
        self.save_dir = save_dir
        
        self.image_files = self._get_image_files()
        if not self.image_files:
            raise ValueError("선택한 폴더에 이미지 파일이 없습니다.")
            
        self.current_index = 0
        
        # 이미지 및 마스크
        self.original_image = None
        self.display_image = None
        self.target_mask = None
        self.source_mask = None
        
        # 그리기 상태
        self.drawing = False
        self.mode = "target"  # 'target' 또는 'source'
        self.has_source_selection = False
        self.is_painted = False
        
        # 브러시 설정
        self.brush_size = 20
        self.min_brush_size = 1
        self.max_brush_size = 50
        
        # UI 설정
        self.target_size = (800, 600)
        self.status_height = 60
        
        # 경고 메시지
        self.warning_message = ""
        self.warning_timer = 0

        # 도움말 표시
        self.show_help = False

    def _get_image_files(self):
        files = [f for f in os.listdir(self.image_dir) 
                 if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        files.sort()
        return files

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            return True
        return False

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            return True
        return False

    def get_current_image_path(self):
        return os.path.join(self.image_dir, self.image_files[self.current_index])

    def reset_for_new_image(self, image):
        self.original_image = image.copy()
        self.display_image = image.copy()
        self.target_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        self.source_mask = np.zeros(image.shape[:2], dtype=np.uint8)
        self.drawing = False
        self.mode = "target"
        self.has_source_selection = False
        self.is_painted = False

    def show_warning(self, message, duration=100):
        self.warning_message = message
        self.warning_timer = duration

    def decrease_warning_timer(self):
        if self.warning_timer > 0:
            self.warning_timer -= 1
