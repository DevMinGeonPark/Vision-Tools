import cv2
import numpy as np
import os
from tkinter import filedialog
import tkinter as tk

class InpaintApp:
    def __init__(self):
        # tkinter 초기화 (숨김)
        self.root = tk.Tk()
        self.root.withdraw()
        
        # 이미지 폴더 선택
        self.image_dir = filedialog.askdirectory(title="이미지 폴더를 선택하세요")
        if not self.image_dir:
            print("폴더를 선택하지 않았습니다.")
            return
            
        # 저장 폴더 선택
        self.save_dir = filedialog.askdirectory(title="저장할 폴더를 선택하세요")
        if not self.save_dir:
            print("저장 폴더를 선택하지 않았습니다.")
            return
            
        # 이미지 파일 리스트 가져오기
        self.image_files = [f for f in os.listdir(self.image_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        self.image_files.sort()
        
        if not self.image_files:
            print("선택한 폴더에 이미지 파일이 없습니다.")
            return
            
        self.current_index = 0
        self.brush_size = 20
        self.min_brush_size = 1
        self.max_brush_size = 50
        self.has_source_selection = False
        self.is_painted = False
        self.target_size = (800, 600)
        
        # 상태 표시를 위한 이미지 생성
        self.status_height = 60
        self.status_bar = np.zeros((self.status_height, self.target_size[0], 3), dtype=np.uint8)
        
        # 경고 메시지 관련 변수 추가
        self.warning_message = ""
        self.warning_timer = 0
        
        # temp_image 초기화
        self.temp_image = None
        
        # 윈도우 생성 및 마우스 콜백 설정
        cv2.namedWindow('Inpaint')
        cv2.createTrackbar('Brush Size', 'Inpaint', self.brush_size, 50, self.on_brush_size)
        cv2.setMouseCallback('Inpaint', self.mouse_callback)
        
        self.load_current_image()
        
    def resize_image(self, image):
        h, w = image.shape[:2]
        target_w, target_h = self.target_size
        
        # 가로, 세로 비율 유지하면서 크기 조정
        aspect = w / h
        if w > h:
            new_w = min(w, target_w)
            new_h = int(new_w / aspect)
        else:
            new_h = min(h, target_h)
            new_w = int(new_h * aspect)
            
        return cv2.resize(image, (new_w, new_h))
        
    def update_status_bar(self):
        # 상태 표시줄 초기화
        self.status_bar.fill(50)  # 회색 배경
        
        # 현재 저장된 파일 개수 계산
        painted_count = len([f for f in os.listdir(self.save_dir)]) if os.path.exists(self.save_dir) else 0
        
        # 상태 정보 텍스트
        status_text = f"Image: {self.image_files[self.current_index]} ({self.current_index + 1}/{len(self.image_files)})"
        count_text = f"Saved: {painted_count}"
        mode_text = f"Mode: {'Select A' if self.mode == 'target' else 'Select B'}"
        size_text = f"Size: {self.image.shape[1]}x{self.image.shape[0]}"
        save_dir_text = f"Save: {os.path.basename(self.save_dir)}"
        
        # 텍스트 표시
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        color = (255, 255, 255)  # 흰색
        
        # 첫 번째 줄
        cv2.putText(self.status_bar, status_text, (10, 20), font, font_scale, color, thickness)
        cv2.putText(self.status_bar, count_text, (self.target_size[0] - 150, 20), font, font_scale, color, thickness)
        
        # 두 번째 줄
        cv2.putText(self.status_bar, mode_text, (10, 45), font, font_scale, color, thickness)
        cv2.putText(self.status_bar, size_text, (self.target_size[0] - 150, 45), font, font_scale, color, thickness)
        
        # 세 번째 줄
        cv2.putText(self.status_bar, save_dir_text, (10, 60), font, font_scale, color, thickness)
        
    def load_current_image(self):
        image_path = os.path.join(self.image_dir, self.image_files[self.current_index])
        print(f"이미지 로드 시도: {image_path}")
        
        # 한글 경로 처리를 위한 수정
        try:
            # numpy를 사용하여 이미지 로드
            self.image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {e}")
            self.image = None
            
        if self.image is None:
            print(f"이미지를 읽을 수 없습니다: {image_path}")
            # 이미지 로드 실패 시 빈 이미지 생성
            self.image = np.zeros((self.target_size[1], self.target_size[0], 3), dtype=np.uint8)
        else:
            print(f"이미지 로드 성공: {self.image.shape}")
            
        # 이미지 크기 조정
        self.image = self.resize_image(self.image)
        print(f"이미지 크기 조정 후: {self.image.shape}")
        
        self.original = self.image.copy()
        self.temp_image = self.image.copy()
        self.target_mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        self.source_mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        self.drawing = False
        self.mode = "target"
        self.has_source_selection = False
        self.is_painted = False
        
        return True
        
    def show_warning(self, message):
        self.warning_message = message
        self.warning_timer = 100  # 약 3초간 표시 (30fps 기준)
        
    def on_brush_size(self, value):
        self.brush_size = max(1, value)
        
    def mouse_callback(self, event, x, y, flags, param):
        # Ctrl 키가 눌린 상태인지 확인
        ctrl_pressed = flags & cv2.EVENT_FLAG_CTRLKEY
        
        if event == cv2.EVENT_MOUSEWHEEL:
            if ctrl_pressed:
                # 휠 방향에 따라 브러시 크기 조절
                if flags > 0:  # 위로 스크롤
                    self.brush_size = min(self.max_brush_size, self.brush_size + 1)
                else:  # 아래로 스크롤
                    self.brush_size = max(self.min_brush_size, self.brush_size - 1)
                # 트랙바 업데이트
                cv2.setTrackbarPos('Brush Size', 'Inpaint', self.brush_size)
                print(f"브러시 크기: {self.brush_size}")
            return
            
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            if self.mode == "target":
                cv2.circle(self.target_mask, (x, y), self.brush_size, 255, -1)
            else:
                cv2.circle(self.source_mask, (x, y), self.brush_size, 255, -1)
                self.has_source_selection = True  # B 영역이 선택되었음을 표시
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                if self.mode == "target":
                    cv2.circle(self.target_mask, (x, y), self.brush_size, 255, -1)
                else:
                    cv2.circle(self.source_mask, (x, y), self.brush_size, 255, -1)
                    self.has_source_selection = True  # B 영역이 선택되었음을 표시
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            
    def update_display(self):
        display = self.temp_image.copy()
        
        # A 영역 (빨간색)
        display[self.target_mask == 255] = [0, 0, 255]
        
        # B 영역 (파란색)
        display[self.source_mask == 255] = [255, 0, 0]
        
        # 경고 메시지 표시
        if self.warning_timer > 0:
            # 경고 메시지 배경
            cv2.rectangle(display, (50, 50), (display.shape[1]-50, 100), (0, 0, 0), -1)
            cv2.rectangle(display, (50, 50), (display.shape[1]-50, 100), (0, 0, 255), 2)
            
            # 경고 메시지 텍스트
            font = cv2.FONT_HERSHEY_SIMPLEX
            text_size = cv2.getTextSize(self.warning_message, font, 0.7, 2)[0]
            text_x = (display.shape[1] - text_size[0]) // 2
            cv2.putText(display, self.warning_message, (text_x, 80), font, 0.7, (0, 0, 255), 2)
            
            self.warning_timer -= 1
        
        # 상태 표시줄 업데이트
        self.update_status_bar()
        
        # status_bar의 너비를 display와 동일하게 조정
        if self.status_bar.shape[1] != display.shape[1]:
            self.status_bar = cv2.resize(self.status_bar, (display.shape[1], self.status_bar.shape[0]))
        
        # 이미지와 상태 표시줄 합치기
        combined = np.vstack([display, self.status_bar])
        
        cv2.imshow('Inpaint', combined)
            
    def apply_replacement(self):
        if np.sum(self.target_mask) == 0 or np.sum(self.source_mask) == 0:
            self.show_warning("Please select both A and B areas!")
            return
            
        # B 영역의 경계 상자 찾기
        source_y, source_x = np.where(self.source_mask == 255)
        source_min_y, source_max_y = np.min(source_y), np.max(source_y)
        source_min_x, source_max_x = np.min(source_x), np.max(source_x)
        source_height = source_max_y - source_min_y + 1
        source_width = source_max_x - source_min_x + 1
        
        # A 영역의 경계 상자 찾기
        target_y, target_x = np.where(self.target_mask == 255)
        target_min_y, target_max_y = np.min(target_y), np.max(target_y)
        target_min_x, target_max_x = np.min(target_x), np.max(target_x)
        target_height = target_max_y - target_min_y + 1
        target_width = target_max_x - target_min_x + 1
        
        # B 영역 이미지 추출
        source_region = self.image[source_min_y:source_max_y+1, source_min_x:source_max_x+1].copy()
        
        # A 영역 크기에 맞게 B 영역 리사이즈
        resized_source = cv2.resize(source_region, (target_width, target_height))
        
        # A 영역에 B 영역 합성
        for y in range(target_height):
            for x in range(target_width):
                if self.target_mask[target_min_y + y, target_min_x + x] == 255:
                    self.temp_image[target_min_y + y, target_min_x + x] = resized_source[y, x]
        
        # 마스크 초기화
        self.target_mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        self.source_mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
        self.image = self.temp_image.copy()
        self.is_painted = True  # painting 완료 표시
            
    def save_result(self, move_to_next=True):
        if not self.has_source_selection:
            self.show_warning("Please complete the selection of area B!")
            return
            
        if not self.is_painted:
            self.show_warning("Please apply the painting first!")
            return
            
        # 저장 폴더 생성
        os.makedirs(self.save_dir, exist_ok=True)
        
        # 기존 파일 목록 확인하여 다음 번호 결정
        existing_files = [f for f in os.listdir(self.save_dir) if f.endswith('.jpg')]
        if existing_files:
            max_num = max([int(f.split('.')[0]) for f in existing_files])
            next_num = max_num + 1
        else:
            next_num = 1
            
        # 새 파일명 생성 (예: 001.jpg)
        output_path = os.path.join(self.save_dir, f"{next_num:03d}.jpg")
        
        try:
            # 한글 경로 처리를 위한 수정
            success = cv2.imwrite(output_path, self.temp_image)
            if not success:
                # imwrite 실패 시 imencode 사용
                _, buffer = cv2.imencode('.jpg', self.temp_image)
                with open(output_path, 'wb') as f:
                    f.write(buffer)
            
            print(f"\n✅ 저장 완료: {output_path}")
            
            # 윈도우 제목 업데이트
            self.update_status_bar()
            
            # move_to_next가 True일 때만 다음 이미지로 이동
            if move_to_next:
                self.next_image()
            
        except Exception as e:
            print(f"저장 중 오류 발생: {e}")
            self.show_warning(f"저장 중 오류가 발생했습니다: {e}")
        
    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.load_current_image()
            
    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()
            
    def run(self):
        if not hasattr(self, 'image_files') or not self.image_files:
            return
            
        print("\nControls:")
        print("1. 'q': Select area A (red, area to be replaced)")
        print("2. 'w': Select area B (blue, area to copy from)")
        print("3. 'e': Apply selected areas")
        print("4. 'r': Reset current image")
        print("5. 's': Save result and move to next image")
        print("6. 'a'/'d': Previous/Next image")
        print("7. 'f': Save result only (저장만)")
        print("8. Ctrl + 마우스 휠: 브러시 크기 조절")
        
        while True:
            self.update_display()
            key = cv2.waitKey(1) & 0xFF
            
            # 창이 닫혔는지 확인
            if cv2.getWindowProperty('Inpaint', cv2.WND_PROP_VISIBLE) < 1:
                break
                
            if key == ord('q'):  # A 영역 선택 모드
                self.mode = "target"
                print("A 영역을 선택하세요 (빨간색, 대체될 영역)")
            elif key == ord('w'):  # B 영역 선택 모드
                self.mode = "source"
                print("B 영역을 선택하세요 (파란색, 복사할 영역)")
            elif key == ord('e'):  # 영역 대체
                self.apply_replacement()
            elif key == ord('r'):  # 리셋
                self.load_current_image()
            elif key == ord('s'):  # 저장 후 다음 이미지로
                self.save_result(move_to_next=True)
            elif key == ord('a'):  # 이전 이미지
                self.prev_image()
            elif key == ord('d'):  # 다음 이미지
                self.next_image()
            elif key == ord('f'):  # F 키로 저장만
                self.save_result(move_to_next=False)
            elif key == 27:  # ESC: 종료
                break
                
        cv2.destroyAllWindows()

if __name__ == "__main__":
    app = InpaintApp()
    app.run()