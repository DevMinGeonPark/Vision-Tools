import cv2
import numpy as np
import os

class ImageManager:
    """이미지 로딩, 리사이징, 저장을 담당하는 클래스"""
    def __init__(self, target_size=(800, 600)):
        self.target_size = target_size

    def load_image(self, path):
        try:
            # 한글 경로 처리를 위해 imdecode 사용
            image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                print(f"이미지를 읽을 수 없습니다: {path}")
                return self._create_blank_image()
            return self.resize_image(image)
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {e}")
            return self._create_blank_image()

    def resize_image(self, image):
        h, w = image.shape[:2]
        target_w, target_h = self.target_size
        
        # 가로, 세로 비율을 유지하며 리사이즈
        aspect = w / h
        if w > h:
            new_w = min(w, target_w)
            new_h = int(new_w / aspect)
        else:
            new_h = min(h, target_h)
            new_w = int(new_h * aspect)
            
        return cv2.resize(image, (new_w, new_h))

    def save_image(self, image, path):
        try:
            # 한글 경로 처리를 위해 imencode 사용
            is_success, im_buf_arr = cv2.imencode(os.path.splitext(path)[1], image)
            if is_success:
                im_buf_arr.tofile(path)
                print(f"이미지 저장 성공: {path}")
            else:
                print(f"이미지 인코딩 실패: {path}")
        except Exception as e:
            print(f"이미지 저장 중 오류 발생: {e}")

    def _create_blank_image(self):
        return np.zeros((self.target_size[1], self.target_size[0], 3), dtype=np.uint8)
