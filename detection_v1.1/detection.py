import cv2
import numpy as np
import os
from tkinter import filedialog, ttk, messagebox
import tkinter as tk
from PIL import Image, ImageTk
import threading
import sys

class DetectionApp:
    def __init__(self, window):
        self.window = window
        self.window.title("객체 검출 라벨링 도구")
        
        # 기본 설정
        self.target_size = (800, 600)  # 디스플레이 크기를 800x600으로 조정
        self.scale = 1.0  # 기본 스케일
        self.min_scale = 0.1  # 최소 스케일
        self.max_scale = 5.0  # 최대 스케일
        self.save_dir = None  # 저장 경로 초기화
        self.image_dir = None  # 이미지 폴더 초기화
        
        # 라벨링 모드 설정
        self.label_mode = tk.StringVar(value="bbox")  # 기본값을 bbox로 설정
        
        # 모드별 이미지 인덱스 관리
        self.mode_indices = {
            "bbox": 0,
            "polygon": 0
        }
        
        # 실행 파일 경로 기준으로 classes.txt 찾기
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우
            application_path = os.path.dirname(sys.executable)
        else:
            # 일반 Python 스크립트로 실행된 경우
            application_path = os.path.dirname(os.path.abspath(__file__))
            
        # 클래스 설정 로드
        self.classes = self.load_classes(application_path)
        if not self.classes:
            messagebox.showerror("오류", "클래스 설정 파일을 찾을 수 없습니다.")
            self.window.quit()
            return
            
        # 클래스별 색상 설정
        self.class_colors = {
            0: (0, 255, 0),    # 초록색
            1: (255, 0, 0),    # 파란색
            2: (0, 0, 255),    # 빨간색
            3: (255, 255, 0),  # 청록색
            4: (255, 0, 255),  # 보라색
            5: (0, 255, 255),  # 노란색
            6: (128, 0, 0),    # 진한 파란색
            7: (0, 128, 0),    # 진한 초록색
            8: (0, 0, 128),    # 진한 빨간색
            9: (128, 128, 0)   # 진한 청록색
        }
        
        # 이미지 폴더 선택
        self.image_dir = filedialog.askdirectory(title="라벨링할 이미지 폴더를 선택하세요")
        if not self.image_dir:
            messagebox.showwarning("경고", "이미지 폴더를 선택하지 않았습니다.")
            self.window.quit()
            return
            
        # 이미지 파일 리스트 가져오기
        self.image_files = [f for f in os.listdir(self.image_dir) 
                          if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        self.image_files.sort()
        
        if not self.image_files:
            messagebox.showwarning("경고", "선택한 폴더에 이미지 파일이 없습니다.")
            self.window.quit()
            return
            
        # 라벨 저장 경로 선택
        self.save_dir = filedialog.askdirectory(title="라벨 저장 경로를 선택하세요")
        if not self.save_dir:
            messagebox.showwarning("경고", "라벨 저장 경로를 선택하지 않았습니다.")
            self.window.quit()
            return
            
        # 상태 변수 초기화
        self.current_index = 0
        self.drawing = False
        self.brush_size = 20
        self.mask = None
        self.current_class = 0
        self.delete_mode = False
        self.edit_mode = False  # 편집 모드 추가
        self.selected_box = None
        self.drag_start = None
        self.resize_handle = None  # 크기 조절 핸들 위치
        self.boxes = []
        self.temp_image = None
        self.original = None
        self.photo = None
        
        # 폴리곤 관련 변수
        self.polygons = []  # [(points, class_id), ...]
        self.current_polygon = []  # 현재 그리고 있는 폴리곤의 점들
        self.selected_polygon = None  # 선택된 폴리곤 인덱스
        self.selected_point = None  # 선택된 점 인덱스
        self.polygon_edit_mode = False  # 폴리곤 편집 모드
        
        # 화면 이동 관련 변수
        self.panning = False  # 화면 이동 중인지 여부
        self.pan_start_x = 0  # 화면 이동 시작 X 좌표
        self.pan_start_y = 0  # 화면 이동 시작 Y 좌표
        self.image_offset_x = 0  # 이미지 X 오프셋
        self.image_offset_y = 0  # 이미지 Y 오프셋
        
        # GUI 초기화
        self.initialize_gui()
        
        # 첫 이미지 로드
        self.load_current_image()
        
    def initialize_gui(self):
        """GUI를 초기화합니다."""
        # 메인 프레임
        self.frame = ttk.Frame(self.window)
        self.frame.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        
        # 상단 컨트롤 프레임 (최소 높이 설정)
        self.control_frame = ttk.Frame(self.frame)
        self.control_frame.pack(fill=tk.X, pady=(0, 5))
        self.control_frame.grid_propagate(False)  # 크기 고정
        self.control_frame.grid_rowconfigure(0, minsize=80)  # 최소 높이 설정
        
        # 라벨링 모드 선택 프레임
        self.mode_frame = ttk.LabelFrame(self.control_frame, text="라벨링 모드 (W: 모드 전환)")
        self.mode_frame.pack(fill=tk.X, pady=2)
        
        # 라벨링 모드 라디오 버튼
        ttk.Radiobutton(self.mode_frame, text="바운딩 박스", variable=self.label_mode, 
                       value="bbox", command=self.on_label_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.mode_frame, text="폴리곤", variable=self.label_mode,
                       value="polygon", command=self.on_label_mode_change).pack(side=tk.LEFT, padx=5)
        
        # 경로 표시 프레임
        self.path_frame = ttk.LabelFrame(self.control_frame, text="경로 설정")
        self.path_frame.pack(fill=tk.X, pady=2)
        
        # 이미지 폴더 경로
        path_frame1 = ttk.Frame(self.path_frame)
        path_frame1.pack(fill=tk.X, pady=1)
        ttk.Label(path_frame1, text="이미지:").pack(side=tk.LEFT, padx=(5,0))
        self.img_path_label = ttk.Label(path_frame1, text=self.image_dir, width=40)  # 너비 조정
        self.img_path_label.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.img_path_btn = ttk.Button(path_frame1, text="변경", width=6, command=self.change_directory)  # 너비 조정
        self.img_path_btn.pack(side=tk.LEFT, padx=2)
        
        # 저장 경로
        path_frame2 = ttk.Frame(self.path_frame)
        path_frame2.pack(fill=tk.X, pady=1)
        ttk.Label(path_frame2, text="저장:").pack(side=tk.LEFT, padx=(5,0))
        self.save_path_label = ttk.Label(path_frame2, text=self.save_dir, width=40)  # 너비 조정
        self.save_path_label.pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        self.save_path_btn = ttk.Button(path_frame2, text="변경", width=6, command=self.change_save_directory)  # 너비 조정
        self.save_path_btn.pack(side=tk.LEFT, padx=2)
        
        # 구분선
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=5)
        
        # 이미지 표시 프레임 (수정된 부분)
        self.image_frame = ttk.Frame(self.frame)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 캔버스 생성 (수정된 부분)
        self.canvas = tk.Canvas(self.image_frame, width=self.target_size[0], height=self.target_size[1],
                              bg='gray90', highlightthickness=1, highlightbackground='gray70')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)  # 패딩 추가
        
        # 마우스 이벤트 바인딩
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_move)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)  # Windows
        self.canvas.bind('<Control-MouseWheel>', self.on_mouse_wheel)  # Windows
        self.canvas.bind('<Control-Button-4>', self.on_mouse_wheel)  # Linux
        self.canvas.bind('<Control-Button-5>', self.on_mouse_wheel)  # Linux
        
        # 스페이스바 관련 이벤트 바인딩
        self.window.bind('<space>', self.on_space_press)
        self.window.bind('<KeyRelease-space>', self.on_space_release)
        
        # 구분선
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=5)
        
        # 하단 컨트롤 프레임 (최소 높이 설정)
        self.bottom_frame = ttk.Frame(self.frame)
        self.bottom_frame.pack(fill=tk.X, pady=5)
        self.bottom_frame.grid_propagate(False)  # 크기 고정
        self.bottom_frame.grid_rowconfigure(0, minsize=60)  # 최소 높이 설정
        
        # 클래스 선택 프레임
        self.class_frame = ttk.LabelFrame(self.bottom_frame, text="클래스 선택 (1~9)")
        self.class_frame.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 클래스 버튼 생성 - 존재하는 클래스만 표시
        for class_id, class_name in sorted(self.classes.items()):
            btn = ttk.Button(self.class_frame, text=f"{class_id+1}\n{class_name}",  # 버튼 텍스트에 키 번호 표시
                           command=lambda x=class_id: self.select_class(x))
            btn.pack(side=tk.LEFT, padx=2)
        
        # 도구 프레임
        self.tool_frame = ttk.LabelFrame(self.bottom_frame, text="도구")
        self.tool_frame.pack(side=tk.LEFT, padx=5)
        
        # 브러시 크기 조절
        ttk.Label(self.tool_frame, text="브러시:").pack(side=tk.LEFT, padx=2)
        self.brush_scale = ttk.Scale(self.tool_frame, from_=1, to=50, orient=tk.HORIZONTAL,
                                   command=self.on_brush_size, length=100)  # 길이 조정
        self.brush_scale.set(self.brush_size)
        self.brush_scale.pack(side=tk.LEFT, padx=2)
        
        # 편집 모드 토글
        self.edit_btn = ttk.Button(self.tool_frame, text="편집 (E)", width=8, command=self.toggle_edit_mode)  # 너비 조정
        self.edit_btn.pack(side=tk.LEFT, padx=2)
        
        # 삭제 모드 토글
        self.delete_btn = ttk.Button(self.tool_frame, text="삭제 (R)", width=8, command=self.toggle_delete_mode)  # 너비 조정
        self.delete_btn.pack(side=tk.LEFT, padx=2)
        
        # 이미지 탐색 프레임
        self.nav_frame = ttk.LabelFrame(self.bottom_frame, text="이미지 탐색")
        self.nav_frame.pack(side=tk.LEFT, padx=5)
        
        # 이전/다음 버튼
        ttk.Button(self.nav_frame, text="이전 (A)", width=8, command=self.prev_image).pack(side=tk.LEFT, padx=2)  # 너비 조정
        ttk.Button(self.nav_frame, text="다음 (D)", width=8, command=self.next_image).pack(side=tk.LEFT, padx=2)  # 너비 조정
        ttk.Button(self.nav_frame, text="저장 (S)", width=8, command=self.save_result).pack(side=tk.LEFT, padx=2)  # 너비 조정
        
        # 상태 표시 레이블
        self.status_label = ttk.Label(self.frame, text="")
        self.status_label.pack(pady=5)
        
        # 키보드 단축키 바인딩
        self.window.bind('<Key>', self.on_key_press)
        
        # 윈도우가 포커스를 가질 때 키보드 이벤트 활성화
        self.window.focus_force()
        self.canvas.focus_set()
        
    def on_key_press(self, event):
        """키보드 이벤트 처리"""
        if hasattr(event, 'processed') and event.processed:
            return
            
        key = event.char.lower() if event.char else event.keysym.lower()
        
        if key == 'w':  # W 키로 모드 전환
            current_mode = self.label_mode.get()
            new_mode = "polygon" if current_mode == "bbox" else "bbox"
            self.label_mode.set(new_mode)
            self.on_label_mode_change()
            self.window.focus_force()  # 윈도우 포커스 강제 설정
            event.processed = True
        elif key in ['e', 'e']:
            self.toggle_edit_mode()
            event.processed = True
        elif key in ['r', 'r']:
            self.toggle_delete_mode()
            event.processed = True
        elif key in ['s', 's']:
            self.save_result()
            event.processed = True
        elif key in ['a', 'a']:
            self.prev_image()  # 이전 이미지로 이동
            event.processed = True
        elif key in ['q', 'q']:
            # 스케일 리셋 및 화면 중앙 정렬
            self.scale = 1.0
            self.image_offset_x = 0
            self.image_offset_y = 0
            self.update_display()
            self.update_status("스케일 리셋됨 (Q)")
            event.processed = True
        elif key in ['d', 'd']:
            self.next_image()
            event.processed = True
        elif key.isdigit():  # 숫자키를 클래스 선택으로 사용 (1->0, 2->1, ...)
            pressed_key = int(key)
            if pressed_key > 0:  # 0번 키는 무시
                class_id = pressed_key - 1  # 1번 키는 0번 클래스, 2번 키는 1번 클래스, ...
                if class_id in self.classes:
                    self.select_class(class_id)
                    event.processed = True
            
    def select_class(self, class_id):
        """클래스 선택"""
        if class_id in self.classes:
            self.current_class = class_id
            self.update_status(f"선택된 클래스: {class_id} ({self.classes[class_id]})")
            
    def toggle_edit_mode(self):
        """편집 모드 토글"""
        if self.edit_mode:  # 이미 편집 모드인 경우
            self.edit_mode = False
            self.selected_box = None
            self.selected_polygon = None
            self.selected_point = None
            self.resize_handle = None
            self.drag_start = None
            self.edit_btn.state(['!pressed'])
            self.update_status("편집 모드: OFF")
        else:  # 편집 모드로 전환
            self.edit_mode = True
            self.delete_mode = False  # 삭제 모드 비활성화
            self.delete_btn.state(['!pressed'])
            self.edit_btn.state(['pressed'])
            self.update_status("편집 모드: ON (박스 선택 후 드래그로 이동, 모서리/변 핸들로 크기 조절)")
        self.update_display()  # 화면 갱신
        
    def toggle_delete_mode(self):
        """삭제 모드 토글"""
        if self.delete_mode:  # 이미 삭제 모드인 경우
            self.delete_mode = False
            self.selected_box = None
            self.selected_polygon = None
            self.selected_point = None
            self.resize_handle = None
            self.drag_start = None
            self.delete_btn.state(['!pressed'])
            self.update_status("삭제 모드: OFF")
        else:  # 삭제 모드로 전환
            self.delete_mode = True
            self.edit_mode = False  # 편집 모드 비활성화
            self.edit_btn.state(['!pressed'])
            self.delete_btn.state(['pressed'])
            self.update_status("삭제 모드: ON")
        self.update_display()  # 화면 갱신
        
    def on_brush_size(self, value):
        """브러시 크기 변경"""
        self.brush_size = int(float(value))
        
    def get_canvas_to_image_coords(self, x, y):
        """캔버스 좌표를 이미지 좌표로 변환"""
        # 캔버스 좌표에서 이미지 오프셋을 빼고 스케일로 나눔
        img_x = (x - self.image_x) / self.scale
        img_y = (y - self.image_y) / self.scale
        return img_x, img_y
        
    def get_image_to_canvas_coords(self, x, y):
        """이미지 좌표를 캔버스 좌표로 변환"""
        # 이미지 좌표에 스케일을 곱하고 오프셋을 더함
        canvas_x = x * self.scale + self.image_x
        canvas_y = y * self.scale + self.image_y
        return canvas_x, canvas_y
        
    def is_point_in_box(self, x, y, box):
        """점이 박스 내부에 있는지 확인 (이미지 좌표 기준)"""
        x1, y1, x2, y2 = box[:4]
        return x1 <= x <= x2 and y1 <= y <= y2
        
    def on_mouse_down(self, event):
        """마우스 버튼 누름 이벤트"""
        if self.panning:  # 화면 이동 중이면 다른 동작 무시
            return
            
        self.drawing = True
        # 캔버스 좌표를 이미지 좌표로 변환
        x, y = self.get_canvas_to_image_coords(event.x, event.y)
        
        if self.label_mode.get() == "polygon":
            if self.edit_mode:
                # 폴리곤 편집 모드
                for i, (points, class_id) in enumerate(self.polygons):
                    for j, (px, py) in enumerate(points):
                        if abs(x - px) <= 5 and abs(y - py) <= 5:
                            self.selected_polygon = i
                            self.selected_point = j
                            self.drag_start = (x, y)
                            return
                            
                # 폴리곤 선택
                for i, (points, class_id) in enumerate(self.polygons):
                    if self.is_point_in_polygon(x, y, points):
                        self.selected_polygon = i
                        self.drag_start = (x, y)
                        return
                        
            elif self.delete_mode:
                # 폴리곤 삭제 모드
                for i, (points, class_id) in enumerate(self.polygons):
                    if self.is_point_in_polygon(x, y, points):
                        self.polygons.pop(i)
                        self.update_display()
                        self.update_status(f"폴리곤 {i} 삭제됨")
                        return
                        
            else:
                # 브러시 모드에서 마스크 초기화
                self.mask = np.zeros((self.target_size[1], self.target_size[0]), dtype=np.uint8)
                cv2.circle(self.mask, (event.x, event.y), self.brush_size, 255, -1)
                
        else:  # bbox mode
            if self.edit_mode:
                # 이미지 좌표 기준으로 박스 선택
                found_box = False
                for i, box in enumerate(self.boxes):
                    if self.is_point_in_box(x, y, box):
                        self.selected_box = i
                        # 크기 조절 핸들 위치 계산 (이미지 좌표 기준)
                        self.resize_handle = self.get_resize_handle(x, y, box)
                        self.drag_start = (x, y)
                        found_box = True
                        self.update_status(f"박스 {i} 선택됨 (클래스 {box[4]})")
                        break
                if not found_box:
                    self.selected_box = None
                    self.resize_handle = None
                    self.drag_start = None
                    self.update_status("편집 모드: 박스를 선택하세요")
            elif self.delete_mode:
                # 이미지 좌표 기준으로 박스 선택
                for i, (x1, y1, x2, y2, class_id) in enumerate(self.boxes):
                    if self.is_point_in_box(x, y, (x1, y1, x2, y2)):
                        self.boxes.pop(i)
                        self.update_display()
                        self.update_status(f"박스 {i} 삭제됨")
                        break
            else:
                # 브러시 모드에서 마스크 초기화 (캔버스 좌표 기준)
                self.mask = np.zeros((self.target_size[1], self.target_size[0]), dtype=np.uint8)
                cv2.circle(self.mask, (event.x, event.y), self.brush_size, 255, -1)
                
    def on_mouse_move(self, event):
        """마우스 이동 이벤트"""
        if self.panning:  # 화면 이동 모드
            dx = event.x - self.pan_start_x
            dy = event.y - self.pan_start_y
            self.image_offset_x += dx
            self.image_offset_y += dy
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.update_display()
            return
            
        if not self.drawing or self.panning:  # 그리기 중이 아니거나 화면 이동 중이면 무시
            return
            
        # 캔버스 좌표를 이미지 좌표로 변환
        x, y = self.get_canvas_to_image_coords(event.x, event.y)
        
        if self.label_mode.get() == "polygon":
            if self.edit_mode and self.selected_polygon is not None:
                if self.selected_point is not None:
                    # 점 이동
                    points, class_id = self.polygons[self.selected_polygon]
                    points[self.selected_point] = (x, y)
                    self.polygons[self.selected_polygon] = (points, class_id)
                else:
                    # 폴리곤 전체 이동
                    points, class_id = self.polygons[self.selected_polygon]
                    dx = x - self.drag_start[0]
                    dy = y - self.drag_start[1]
                    new_points = [(px + dx, py + dy) for px, py in points]
                    self.polygons[self.selected_polygon] = (new_points, class_id)
                    self.drag_start = (x, y)
                self.update_display()
            elif not self.delete_mode and self.mask is not None:
                # 브러시 모드에서 마스크 그리기
                cv2.circle(self.mask, (event.x, event.y), self.brush_size, 255, -1)
                self.update_display()
                
        else:  # bbox mode
            if self.edit_mode and self.selected_box is not None and self.drag_start is not None:
                # 박스 편집 (이미지 좌표 기준)
                dx = x - self.drag_start[0]
                dy = y - self.drag_start[1]
                x1, y1, x2, y2, class_id = self.boxes[self.selected_box]
                
                if self.resize_handle:
                    # 크기 조절 (이미지 좌표 기준)
                    min_size = 10 / self.scale  # 최소 크기
                    if 'n' in self.resize_handle:
                        y1 = min(y1 + dy, y2 - min_size)
                    if 's' in self.resize_handle:
                        y2 = max(y2 + dy, y1 + min_size)
                    if 'w' in self.resize_handle:
                        x1 = min(x1 + dx, x2 - min_size)
                    if 'e' in self.resize_handle:
                        x2 = max(x2 + dx, x1 + min_size)
                else:
                    # 이동 (이미지 좌표 기준)
                    x1, x2 = x1 + dx, x2 + dx
                    y1, y2 = y1 + dy, y2 + dy
                    
                # 경계 체크 (이미지 좌표 기준)
                h, w = self.original.shape[:2]
                x1 = max(0, min(x1, w - min_size))
                y1 = max(0, min(y1, h - min_size))
                x2 = max(x1 + min_size, min(x2, w))
                y2 = max(y1 + min_size, min(y2, h))
                
                self.boxes[self.selected_box] = (x1, y1, x2, y2, class_id)
                self.drag_start = (x, y)
                self.update_display()
                
                # 상태 업데이트
                if self.resize_handle:
                    self.update_status(f"박스 크기 조절 중... ({int(x2-x1)}x{int(y2-y1)})")
                else:
                    self.update_status(f"박스 이동 중... ({int(x1)},{int(y1)})")
            elif not self.delete_mode and self.mask is not None:
                # 브러시 모드에서 마스크 그리기 (캔버스 좌표 기준)
                cv2.circle(self.mask, (event.x, event.y), self.brush_size, 255, -1)
                self.update_display()
                
    def on_mouse_up(self, event):
        """마우스 버튼 뗌 이벤트"""
        if self.panning:  # 화면 이동 중이면 다른 동작 무시
            return
            
        if self.drawing and not self.delete_mode and not self.edit_mode and self.mask is not None:
            if self.label_mode.get() == "polygon":
                # 마스크에서 윤곽선 찾기
                contours, _ = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    # 가장 큰 윤곽선 선택
                    max_contour = max(contours, key=cv2.contourArea)
                    # 윤곽선 단순화
                    epsilon = 0.005 * cv2.arcLength(max_contour, True)
                    approx = cv2.approxPolyDP(max_contour, epsilon, True)
                    
                    # 윤곽선을 폴리곤으로 변환
                    points = []
                    for point in approx:
                        x, y = point[0]
                        points.append((float(x), float(y)))
                    
                    if len(points) >= 3:  # 최소 3개의 점이 필요
                        # 잠시 대기하여 사용자가 변환 과정을 볼 수 있게 함
                        self.update_display()
                        self.window.after(100)  # 100ms 대기
                        self.polygons.append((points, self.current_class))
                        self.update_status(f"폴리곤 추가됨 (클래스 {self.current_class})")
                        print(f"폴리곤 추가됨: {len(points)}개의 점, 클래스 {self.current_class}")  # 디버깅용
                    else:
                        self.update_status("폴리곤을 생성하기에는 점이 부족합니다.")
                self.mask = None
                self.update_display()
            else:  # bbox mode
                # 마스크를 박스로 변환
                y_indices, x_indices = np.where(self.mask == 255)
                if len(y_indices) > 0 and len(x_indices) > 0:
                    min_y, max_y = np.min(y_indices), np.max(y_indices)
                    min_x, max_x = np.min(x_indices), np.max(x_indices)
                    self.boxes.append((min_x, min_y, max_x, max_y, self.current_class))
                    self.mask = None
                    self.update_display()
                    self.update_status(f"새 박스 추가됨 (클래스 {self.current_class})")
                    
        self.drawing = False
        self.selected_box = None
        self.selected_polygon = None
        self.selected_point = None
        self.resize_handle = None
        self.drag_start = None
        
    def is_point_in_polygon(self, x, y, points):
        """점이 폴리곤 내부에 있는지 확인"""
        n = len(points)
        inside = False
        p1x, p1y = points[0]
        for i in range(n + 1):
            p2x, p2y = points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside
        
    def on_mouse_wheel(self, event):
        """마우스 휠 이벤트 처리 (확대/축소)"""
        # Ctrl 키가 눌려있는지 확인
        if not (event.state & 0x4):  # 0x4는 Ctrl 키의 상태 비트
            return
            
        # 휠 방향 확인 (Windows와 Linux 모두 지원)
        if event.num == 5 or event.delta < 0:  # 축소
            factor = 0.9
        elif event.num == 4 or event.delta > 0:  # 확대
            factor = 1.1
        else:
            return
            
        # 현재 마우스 위치를 기준으로 확대/축소
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # 스케일 업데이트
        new_scale = self.scale * factor
        if self.min_scale <= new_scale <= self.max_scale:
            self.scale = new_scale
            self.update_display()
            self.update_status(f"확대/축소: {self.scale:.1f}x")
            
    def update_display(self):
        """화면 업데이트"""
        if self.temp_image is None:
            return
            
        # 캔버스 초기화
        self.canvas.delete("all")
        
        # 배경색 설정
        self.canvas.configure(bg='gray90')
        
        display = self.temp_image.copy()
        
        # 현재 이미지 크기 계산
        h, w = display.shape[:2]
        scaled_w = int(w * self.scale)
        scaled_h = int(h * self.scale)
        
        # 이미지 크기 조정
        if self.scale != 1.0:
            display = cv2.resize(display, (scaled_w, scaled_h), interpolation=cv2.INTER_LINEAR)
        
        if self.label_mode.get() == "polygon":
            # 마스크 표시 (브러시 영역)
            if self.mask is not None:
                # 브러시 영역을 반투명하게 표시
                scaled_mask = cv2.resize(self.mask, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
                mask_overlay = display.copy()
                mask_overlay[scaled_mask == 255] = [0, 255, 0]  # 초록색으로 표시
                cv2.addWeighted(mask_overlay, 0.3, display, 0.7, 0, display)
                
                # 브러시 영역의 윤곽선 표시
                contours, _ = cv2.findContours(scaled_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    # 가장 큰 윤곽선 선택
                    max_contour = max(contours, key=cv2.contourArea)
                    # 윤곽선 단순화
                    epsilon = 0.005 * cv2.arcLength(max_contour, True)
                    approx = cv2.approxPolyDP(max_contour, epsilon, True)
                    # 윤곽선 그리기
                    cv2.drawContours(display, [approx], -1, (0, 255, 0), 2)
                    # 윤곽선의 꼭지점 표시
                    for point in approx:
                        x, y = point[0]
                        cv2.circle(display, (x, y), 4, (0, 255, 0), -1)
            
            # 폴리곤 표시 (크기 조정된 좌표 사용)
            for i, (points, class_id) in enumerate(self.polygons):
                try:
                    if not points or len(points) < 3:
                        continue
                        
                    color = self.class_colors.get(class_id, (0, 255, 0))
                    if self.delete_mode:
                        color = (0, 0, 255)
                    elif self.edit_mode and i == self.selected_polygon:
                        color = (255, 255, 0)
                    
                    # 점들을 스케일에 맞게 조정
                    scaled_points = []
                    for x, y in points:
                        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                            scaled_points.append([int(x * self.scale), int(y * self.scale)])
                    
                    if len(scaled_points) >= 3:
                        points_array = np.array(scaled_points, np.int32)
                        points_array = points_array.reshape((-1, 1, 2))
                        cv2.polylines(display, [points_array], True, color, 2)
                        
                        if points_array.size > 0:
                            x, y = points_array[0][0]
                            cv2.putText(display, str(class_id), (x, y-5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        
                        if self.edit_mode and i == self.selected_polygon:
                            for j, (px, py) in enumerate(scaled_points):
                                point_color = (255, 0, 0) if j == self.selected_point else (255, 255, 0)
                                cv2.circle(display, (px, py), 4, point_color, -1)
                except Exception as e:
                    print(f"폴리곤 표시 중 오류 발생: {e}, 폴리곤 {i}")
                    continue
                
        else:  # bbox mode
            # 기존 바운딩 박스 표시 코드
            if self.mask is not None:
                # 브러시 영역을 반투명하게 표시
                scaled_mask = cv2.resize(self.mask, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
                mask_overlay = display.copy()
                mask_overlay[scaled_mask == 255] = [0, 255, 0]
                cv2.addWeighted(mask_overlay, 0.3, display, 0.7, 0, display)
                
            for i, (x1, y1, x2, y2, class_id) in enumerate(self.boxes):
                # 박스 좌표를 스케일에 맞게 조정
                scaled_x1 = int(x1 * self.scale)
                scaled_y1 = int(y1 * self.scale)
                scaled_x2 = int(x2 * self.scale)
                scaled_y2 = int(y2 * self.scale)
                
                color = self.class_colors.get(class_id, (0, 255, 0))
                if self.delete_mode:
                    color = (0, 0, 255)
                elif self.edit_mode:
                    if i == self.selected_box:
                        color = (255, 255, 0)  # 선택된 박스는 노란색
                    else:
                        color = (0, 255, 255)  # 편집 모드의 다른 박스는 청록색
                    
                # 박스 그리기
                cv2.rectangle(display, (scaled_x1, scaled_y1), (scaled_x2, scaled_y2), color, 2)
                
                # 클래스 ID 표시
                cv2.putText(display, str(class_id), (scaled_x1, scaled_y1-5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                           
                # 편집 모드일 때 모든 박스에 핸들 표시
                if self.edit_mode:
                    handle_size = max(4, int(4 * self.scale))  # 핸들 크기를 스케일에 맞게 조정
                    handle_color = (255, 0, 0) if i == self.selected_box else (0, 255, 255)  # 선택된 박스는 파란색, 나머지는 청록색
                    
                    # 모서리 핸들
                    cv2.circle(display, (scaled_x1, scaled_y1), handle_size, handle_color, -1)
                    cv2.circle(display, (scaled_x2, scaled_y1), handle_size, handle_color, -1)
                    cv2.circle(display, (scaled_x1, scaled_y2), handle_size, handle_color, -1)
                    cv2.circle(display, (scaled_x2, scaled_y2), handle_size, handle_color, -1)
                    
                    # 변 핸들
                    mid_x1 = (scaled_x1 + scaled_x2) // 2
                    mid_y1 = (scaled_y1 + scaled_y2) // 2
                    cv2.circle(display, (mid_x1, scaled_y1), handle_size, handle_color, -1)  # 상단 중앙
                    cv2.circle(display, (mid_x1, scaled_y2), handle_size, handle_color, -1)  # 하단 중앙
                    cv2.circle(display, (scaled_x1, mid_y1), handle_size, handle_color, -1)  # 좌측 중앙
                    cv2.circle(display, (scaled_x2, mid_y1), handle_size, handle_color, -1)  # 우측 중앙
                    
                    # 선택 영역 표시 (반투명)
                    if i == self.selected_box:
                        overlay = display.copy()
                        cv2.rectangle(overlay, (scaled_x1, scaled_y1), (scaled_x2, scaled_y2), (255, 255, 0), -1)
                        cv2.addWeighted(overlay, 0.1, display, 0.9, 0, display)  # 반투명 효과
        
        # PIL 이미지로 변환 및 표시
        display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        self.photo = ImageTk.PhotoImage(image=Image.fromarray(display_rgb))
        
        # 이미지를 캔버스 중앙에 배치 (오프셋 적용)
        self.canvas_width = self.target_size[0]
        self.canvas_height = self.target_size[1]
        self.image_x = (self.canvas_width - scaled_w) // 2 + self.image_offset_x
        self.image_y = (self.canvas_height - scaled_h) // 2 + self.image_offset_y
        self.canvas.create_image(self.image_x, self.image_y, image=self.photo, anchor=tk.NW)
        
        # 상태 업데이트
        self.update_status_bar()
        
    def update_status_bar(self):
        """상태 표시줄 업데이트"""
        mode = self.label_mode.get()
        mode_text = "폴리곤" if mode == "polygon" else "바운딩 박스"
        count = len(self.polygons) if mode == "polygon" else len(self.boxes)
        
        status_text = (f"이미지: {self.image_files[self.current_index]} "
                      f"({self.current_index + 1}/{len(self.image_files)}) | "
                      f"모드: {mode_text} (W: 모드 전환) - {'편집' if self.edit_mode else '삭제' if self.delete_mode else '그리기'} | "
                      f"클래스: {self.current_class+1} ({self.classes.get(self.current_class, 'Unknown')}) | "
                      f"객체: {count}개 | Q: 스케일 리셋")
        self.status_label.config(text=status_text)
        
    def update_status(self, message):
        """상태 메시지 업데이트"""
        self.status_label.config(text=message)
        
    def change_directory(self):
        """이미지 폴더 변경"""
        new_dir = filedialog.askdirectory(title="라벨링할 이미지 폴더를 선택하세요")
        if new_dir:
            self.image_dir = new_dir
            # 경로가 너무 길 경우 중간을 ...으로 표시
            display_path = self.shorten_path(new_dir)
            self.img_path_label.config(text=display_path)
            self.image_files = [f for f in os.listdir(self.image_dir) 
                              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
            self.image_files.sort()
            
            if not self.image_files:
                messagebox.showwarning("경고", "선택한 폴더에 이미지 파일이 없습니다.")
                return
                
            self.current_index = 0
            self.load_current_image()
            
    def change_save_directory(self):
        """라벨 저장 경로 변경"""
        new_dir = filedialog.askdirectory(title="라벨 저장 경로를 선택하세요")
        if new_dir:
            self.save_dir = new_dir
            # 경로가 너무 길 경우 중간을 ...으로 표시
            display_path = self.shorten_path(new_dir)
            self.save_path_label.config(text=display_path)
            self.update_status(f"라벨 저장 경로가 변경되었습니다: {display_path}")
            
    def shorten_path(self, path, max_length=50):
        """경로를 짧게 표시"""
        if len(path) <= max_length:
            return path
            
        # 경로를 구성 요소로 분리
        parts = path.split(os.sep)
        if len(parts) <= 2:
            return path
            
        # 시작과 끝 부분 유지
        start = parts[0]
        end = parts[-1]
        
        # 중간 부분을 ...으로 대체
        middle = "..."
        
        # 남은 길이 계산
        remaining_length = max_length - len(start) - len(end) - len(middle) - 2
        
        # 시작 부분 길이 조정
        start_length = min(len(start), remaining_length // 2)
        start = start[:start_length]
        
        # 끝 부분 길이 조정
        end_length = min(len(end), remaining_length - start_length)
        end = end[-end_length:]
        
        return f"{start}{os.sep}{middle}{os.sep}{end}"
        
    def load_current_image(self):
        """현재 이미지 로드"""
        if not self.image_files:
            return
            
        image_path = os.path.join(self.image_dir, self.image_files[self.current_index])
        try:
            self.original = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if self.original is None:
                raise Exception("이미지를 읽을 수 없습니다.")
                
            # 이미지 크기 조정 - 여백 최소화
            h, w = self.original.shape[:2]
            canvas_aspect = self.target_size[0] / self.target_size[1]
            image_aspect = w / h
            
            # 이미지가 캔버스보다 크면 크기 조정
            if w > self.target_size[0] or h > self.target_size[1]:
                if image_aspect > canvas_aspect:
                    # 이미지가 더 넓은 경우
                    new_w = self.target_size[0]
                    new_h = int(new_w / image_aspect)
                else:
                    # 이미지가 더 높은 경우
                    new_h = self.target_size[1]
                    new_w = int(new_h * image_aspect)
                    
                self.original = cv2.resize(self.original, (new_w, new_h))
            else:
                # 이미지가 캔버스보다 작은 경우 원본 크기 유지
                pass
                
            # 이미지를 캔버스 중앙에 배치
            self.canvas_width = self.target_size[0]
            self.canvas_height = self.target_size[1]
            self.image_x = (self.canvas_width - self.original.shape[1]) // 2
            self.image_y = (self.canvas_height - self.original.shape[0]) // 2
            
            self.temp_image = self.original.copy()
            self.boxes = []
            self.polygons = []  # 폴리곤 모드일 때도 초기화
            self.mask = None
            
            # 기존 라벨 로드
            self.load_existing_labels()
            
            # 이미지 로드 시 오프셋 초기화
            self.image_offset_x = 0
            self.image_offset_y = 0
            
            self.update_display()
            self.update_status(f"이미지 로드됨: {self.image_files[self.current_index]}")
            
        except Exception as e:
            messagebox.showerror("오류", f"이미지 로드 중 오류 발생: {str(e)}")
            
    def load_existing_labels(self):
        """기존 라벨 파일 로드"""
        if not self.save_dir:
            return
            
        mode = self.label_mode.get()
        mode_folder = "bounding" if mode == "bbox" else "poly"
        label_dir = os.path.join(self.save_dir, mode_folder, "label")
        label_path = os.path.join(label_dir, os.path.splitext(self.image_files[self.current_index])[0] + '.txt')
        
        if os.path.exists(label_path):
            try:
                with open(label_path, 'r') as f:
                    h, w = self.original.shape[:2]
                    for line in f:
                        values = line.strip().split()
                        if not values:  # 빈 줄 건너뛰기
                            continue
                            
                        class_id = int(values[0])
                        
                        if mode == "polygon":
                            # 폴리곤 데이터 로드
                            try:
                                points = []
                                for i in range(1, len(values), 2):
                                    if i + 1 >= len(values):  # 좌표가 짝이 맞지 않는 경우
                                        break
                                    x = float(values[i]) * w
                                    y = float(values[i+1]) * h
                                    points.append((x, y))
                                if len(points) >= 3:  # 최소 3개의 점이 있는 경우만 추가
                                    self.polygons.append((points, class_id))
                            except (ValueError, IndexError) as e:
                                print(f"폴리곤 데이터 로드 중 오류 발생: {e}")
                                continue
                        else:
                            # 바운딩 박스 데이터 로드
                            try:
                                if len(values) >= 5:  # 최소한 필요한 값이 있는지 확인
                                    x_center, y_center, width, height = map(float, values[1:5])
                                    x1 = int((x_center - width/2) * w)
                                    y1 = int((y_center - height/2) * h)
                                    x2 = int((x_center + width/2) * w)
                                    y2 = int((y_center + height/2) * h)
                                    self.boxes.append((x1, y1, x2, y2, class_id))
                            except (ValueError, IndexError) as e:
                                print(f"바운딩 박스 데이터 로드 중 오류 발생: {e}")
                                continue
                            
                count = len(self.polygons) if mode == "polygon" else len(self.boxes)
                self.update_status(f"기존 라벨 로드 완료: {count}개의 객체 ({mode_folder} 모드)")
                
            except Exception as e:
                messagebox.showwarning("경고", f"라벨 로드 중 오류 발생: {str(e)}")
                self.update_status(f"라벨 로드 실패: {str(e)}")
        else:
            self.update_status(f"기존 라벨 없음 ({mode_folder} 모드)")
        
    def save_result(self):
        """현재 작업 저장"""
        if self.label_mode.get() == "polygon":
            if not self.polygons:
                messagebox.showwarning("경고", "저장할 폴리곤이 없습니다.")
                return
        else:
            if not self.boxes:
                messagebox.showwarning("경고", "저장할 박스가 없습니다.")
                return
                
        if not self.save_dir:
            messagebox.showwarning("경고", "저장 경로가 선택되지 않았습니다.")
            self.change_save_directory()
            if not self.save_dir:
                return
                
        try:
            # 모드별 저장 경로 설정
            mode = self.label_mode.get()
            mode_folder = "bounding" if mode == "bbox" else "poly"
            
            # 저장 디렉토리 생성
            img_dir = os.path.join(self.save_dir, mode_folder, "img")
            label_dir = os.path.join(self.save_dir, mode_folder, "label")
            os.makedirs(img_dir, exist_ok=True)
            os.makedirs(label_dir, exist_ok=True)
            
            # 이미지 저장
            img_path = os.path.join(img_dir, self.image_files[self.current_index])
            cv2.imwrite(img_path, self.original)
            
            # 라벨 저장
            label_path = os.path.join(label_dir, os.path.splitext(self.image_files[self.current_index])[0] + '.txt')
            
            h, w = self.original.shape[:2]
            with open(label_path, 'w') as f:
                if mode == "polygon":
                    for points, class_id in self.polygons:
                        try:
                            # 폴리곤 포인트들을 정규화된 좌표로 변환
                            normalized_points = []
                            for x, y in points:
                                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                                    normalized_points.append((x/w, y/h))
                            
                            if normalized_points:  # 유효한 점이 있는 경우만 저장
                                points_str = " ".join([f"{x:.6f} {y:.6f}" for x, y in normalized_points])
                                f.write(f"{class_id} {points_str}\n")
                        except Exception as e:
                            print(f"폴리곤 저장 중 오류 발생: {e}")
                            continue
                else:
                    for x1, y1, x2, y2, class_id in self.boxes:
                        try:
                            x_center = (x1 + x2) / (2 * w)
                            y_center = (y1 + y2) / (2 * h)
                            width = (x2 - x1) / w
                            height = (y2 - y1) / h
                            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
                        except Exception as e:
                            print(f"바운딩 박스 저장 중 오류 발생: {e}")
                            continue
                        
            self.update_status(f"저장 완료: {self.image_files[self.current_index]} ({mode_folder} 모드)")
            
        except Exception as e:
            messagebox.showerror("오류", f"저장 중 오류 발생: {str(e)}")
            
    def next_image(self):
        """다음 이미지로 이동"""
        # 현재 이미지에 박스나 폴리곤이 있으면 저장
        if self.boxes or self.polygons:
            self.save_result()
            
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.mode_indices[self.label_mode.get()] = self.current_index  # 현재 모드의 인덱스 업데이트
            self.load_current_image()
            
    def prev_image(self):
        """이전 이미지로 이동"""
        if self.current_index > 0:
            self.current_index -= 1
            self.mode_indices[self.label_mode.get()] = self.current_index  # 현재 모드의 인덱스 업데이트
            self.load_current_image()
            
    def load_classes(self, application_path):
        """클래스 설정 파일 로드"""
        try:
            classes = {}
            classes_path = os.path.join(application_path, 'classes.txt')
            with open(classes_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        class_id, class_name = line.split(',')
                        classes[int(class_id)] = class_name
            return classes
        except Exception as e:
            print(f"클래스 설정 파일 로드 중 오류 발생: {e}")
            print(f"시도한 경로: {classes_path}")
            return None

    def on_space_press(self, event):
        """스페이스바 누름 이벤트"""
        if not self.panning:  # 화면 이동 모드가 아닐 때만 시작
            self.panning = True
            self.pan_start_x = event.x
            self.pan_start_y = event.y
            self.canvas.config(cursor="fleur")  # 커서 모양 변경
            # 현재 진행 중인 작업 초기화
            self.drawing = False
            self.selected_box = None
            self.selected_polygon = None
            self.selected_point = None
            self.resize_handle = None
            self.drag_start = None
            self.mask = None
            self.update_display()  # 화면 갱신
            event.processed = True
            
    def on_space_release(self, event):
        """스페이스바 뗌 이벤트"""
        if self.panning:
            self.panning = False
            self.canvas.config(cursor="")  # 커서 모양 원래대로
            event.processed = True

    def get_resize_handle(self, x, y, box):
        """박스의 크기 조절 핸들 위치 반환 (이미지 좌표 기준)"""
        x1, y1, x2, y2 = box[:4]
        handle_size = 12 / self.scale  # 핸들 크기를 더 크게 조정
        
        # 모서리 핸들
        if abs(x - x1) <= handle_size and abs(y - y1) <= handle_size:
            return 'nw'  # 북서쪽
        if abs(x - x2) <= handle_size and abs(y - y1) <= handle_size:
            return 'ne'  # 북동쪽
        if abs(x - x1) <= handle_size and abs(y - y2) <= handle_size:
            return 'sw'  # 남서쪽
        if abs(x - x2) <= handle_size and abs(y - y2) <= handle_size:
            return 'se'  # 남동쪽
            
        # 변 핸들
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        if abs(x - mid_x) <= handle_size and abs(y - y1) <= handle_size:
            return 'n'  # 북쪽
        if abs(x - mid_x) <= handle_size and abs(y - y2) <= handle_size:
            return 's'  # 남쪽
        if abs(x - x1) <= handle_size and abs(y - mid_y) <= handle_size:
            return 'w'  # 서쪽
        if abs(x - x2) <= handle_size and abs(y - mid_y) <= handle_size:
            return 'e'  # 동쪽
            
        return None

    def on_label_mode_change(self):
        """라벨링 모드 변경 시 호출되는 함수"""
        mode = self.label_mode.get()
        # 현재 모드의 인덱스 저장
        self.mode_indices[mode] = self.current_index
        
        # 새 모드의 인덱스로 변경
        self.current_index = self.mode_indices[mode]
        
        # 현재 이미지 정보 저장
        current_image = self.image_files[self.current_index] if self.image_files else None
        
        # 데이터 초기화
        if mode == "bbox":
            self.boxes = []
            self.polygons = []
            self.current_polygon = []
            self.selected_polygon = None
            self.selected_point = None
        else:  # polygon mode
            self.boxes = []
            self.current_polygon = []
            self.selected_polygon = None
            self.selected_point = None
            
        # 현재 이미지가 있다면 새 모드의 라벨 로드
        if current_image and self.save_dir:
            mode_folder = "bounding" if mode == "bbox" else "poly"
            label_dir = os.path.join(self.save_dir, mode_folder, "label")
            label_path = os.path.join(label_dir, os.path.splitext(current_image)[0] + '.txt')
            
            if os.path.exists(label_path):
                try:
                    h, w = self.original.shape[:2]
                    with open(label_path, 'r') as f:
                        for line in f:
                            values = line.strip().split()
                            if not values:  # 빈 줄 건너뛰기
                                continue
                                
                            class_id = int(values[0])
                            
                            if mode == "polygon":
                                # 폴리곤 데이터 로드
                                try:
                                    points = []
                                    for i in range(1, len(values), 2):
                                        if i + 1 >= len(values):  # 좌표가 짝이 맞지 않는 경우
                                            break
                                        x = float(values[i]) * w
                                        y = float(values[i+1]) * h
                                        points.append((x, y))
                                    if len(points) >= 3:  # 최소 3개의 점이 있는 경우만 추가
                                        self.polygons.append((points, class_id))
                                except (ValueError, IndexError) as e:
                                    print(f"폴리곤 데이터 로드 중 오류 발생: {e}")
                                    continue
                            else:
                                # 바운딩 박스 데이터 로드
                                try:
                                    if len(values) >= 5:  # 최소한 필요한 값이 있는지 확인
                                        x_center, y_center, width, height = map(float, values[1:5])
                                        x1 = int((x_center - width/2) * w)
                                        y1 = int((y_center - height/2) * h)
                                        x2 = int((x_center + width/2) * w)
                                        y2 = int((y_center + height/2) * h)
                                        self.boxes.append((x1, y1, x2, y2, class_id))
                                except (ValueError, IndexError) as e:
                                    print(f"바운딩 박스 데이터 로드 중 오류 발생: {e}")
                                    continue
                                    
                    count = len(self.polygons) if mode == "polygon" else len(self.boxes)
                    self.update_status(f"모드 변경: {mode_folder} 모드의 기존 라벨 로드 완료 ({count}개의 객체)")
                except Exception as e:
                    print(f"라벨 로드 중 오류 발생: {e}")
                    self.update_status(f"모드 변경: {mode_folder} 모드로 전환됨 (라벨 로드 실패)")
            else:
                self.update_status(f"모드 변경: {mode_folder} 모드로 전환됨 (기존 라벨 없음)")
        else:
            self.update_status(f"라벨링 모드: {'바운딩 박스' if mode == 'bbox' else '폴리곤'}")
            
        # 모드 변경 시 오프셋 초기화
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        self.update_display()

if __name__ == "__main__":
    root = tk.Tk()
    app = DetectionApp(root)
    root.mainloop() 