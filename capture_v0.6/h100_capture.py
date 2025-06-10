import cv2
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import time
from datetime import datetime
import numpy as np
import threading
import os
import glob
import shutil

class CameraApp:
    def __init__(self, window):
        self.window = window
        self.window.title("Camera Stream")
        self.width = 1536
        self.height = 1536
        
        # 스케일 초기화
        self.scale = 1.0  # 기본 스케일
        
        # 이미지 저장 관련 초기화
        self.base_directory = None  # 기본 저장 경로
        self.normal_directory = None  # 정상 데이터 저장 경로
        self.abnormal_directory = None  # 비정상 데이터 저장 경로
        self.merge_directory = None  # 병합 데이터 저장 경로
        self.image_format = "bmp"  # 기본 이미지 형식
        self.is_normal = True  # 정상/비정상 상태 (기본값: 정상)
        self.normal_start_number = 1  # 정상 데이터 시작 번호
        self.abnormal_start_number = 10001  # 비정상 데이터 시작 번호
        
        # 사용 가능한 카메라 목록 확인
        self.available_cameras = self.get_available_cameras()
        if not self.available_cameras:
            print("사용 가능한 카메라가 없습니다!")
            self.window.quit()
            return
            
        # 카메라 선택 다이얼로그
        self.selected_camera = self.show_camera_selection_dialog()
        if self.selected_camera is None:
            self.window.quit()
            return

        # 로딩 화면 표시
        self.show_loading_screen()
        
        # 별도 스레드에서 카메라 초기화
        self.init_thread = threading.Thread(target=self.initialize_camera)
        self.init_thread.start()
        
    def show_loading_screen(self):
        """로딩 화면을 표시합니다."""
        self.loading_window = tk.Toplevel(self.window)
        self.loading_window.title("카메라 초기화")
        self.loading_window.geometry("300x100")
        self.loading_window.transient(self.window)
        self.loading_window.grab_set()
        
        ttk.Label(self.loading_window, text="카메라를 초기화하는 중입니다...").pack(pady=20)
        self.progress = ttk.Progressbar(self.loading_window, mode='indeterminate')
        self.progress.pack(pady=10, padx=20, fill=tk.X)
        self.progress.start()

    def initialize_camera(self):
        """카메라를 초기화합니다."""
        try:
            # 카메라 설정
            self.camera = cv2.VideoCapture(self.selected_camera)
            time.sleep(1)  # 초기화 대기 시간 단축
            
            # 해상도 설정
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # 실제 카메라 해상도 확인
            ret, test_frame = self.camera.read()
            if ret:
                self.actual_height, self.actual_width = test_frame.shape[:2]
                print(f"실제 카메라 해상도: {self.actual_width}x{self.actual_height}")
            
            if not self.camera.isOpened():
                raise Exception("카메라를 열 수 없습니다!")
            
            # 저장 경로 선택 강제
            self.window.after(0, self.force_save_directory_selection)
            
            # GUI 초기화
            self.window.after(0, self.initialize_gui)
            
        except Exception as e:
            print(f"카메라 초기화 중 오류 발생: {str(e)}")
            self.window.after(0, self.show_error, str(e))
        finally:
            # 로딩 화면 닫기
            self.window.after(0, self.loading_window.destroy)

    def setup_directories(self, base_dir):
        """저장 디렉토리 구조를 설정합니다."""
        self.base_directory = base_dir
        self.normal_directory = os.path.join(base_dir, "normal")
        self.abnormal_directory = os.path.join(base_dir, "abnormal")
        self.merge_directory = os.path.join(base_dir, "merge")
        
        # 필요한 디렉토리 생성
        for directory in [self.normal_directory, self.abnormal_directory, self.merge_directory]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def force_save_directory_selection(self):
        """저장 경로 선택을 강제합니다."""
        messagebox.showinfo("저장 경로 선택", "이미지 저장 경로를 선택해주세요.")
        self.change_save_directory()
        if not self.base_directory:  # 사용자가 취소한 경우
            messagebox.showwarning("경고", "저장 경로를 선택하지 않으면 프로그램이 종료됩니다.")
            self.window.quit()

    def initialize_gui(self):
        """GUI를 초기화합니다."""
        # 이미지 처리 파라미터
        self.is_grayscale = True  # 흑백 모드 기본값
            
        # GUI 구성
        self.frame = ttk.Frame(self.window)
        self.frame.pack(padx=0, pady=0, fill=tk.BOTH, expand=True)
        
        # 저장 경로 프레임
        self.path_frame = ttk.Frame(self.frame)
        self.path_frame.pack(pady=0, fill=tk.X)
        
        # 저장 경로 표시 레이블
        self.path_label = ttk.Label(self.path_frame, text=f"저장 경로: {self.base_directory}")
        self.path_label.pack(side=tk.LEFT, padx=2)
        
        # 저장 경로 변경 버튼
        self.path_btn = ttk.Button(self.path_frame, text="저장 경로 변경", command=self.change_save_directory)
        self.path_btn.pack(side=tk.RIGHT, padx=2)
        
        # 구분선 추가
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=0)
        
        # 시작 번호 설정 프레임
        self.start_number_frame = ttk.Frame(self.frame)
        self.start_number_frame.pack(pady=5)
        
        # 정상 데이터 시작 번호
        ttk.Label(self.start_number_frame, text="정상 시작 번호:").pack(side=tk.LEFT, padx=2)
        self.normal_start_var = tk.StringVar(value=str(self.normal_start_number))
        self.normal_start_entry = ttk.Entry(self.start_number_frame, textvariable=self.normal_start_var, width=8)
        self.normal_start_entry.pack(side=tk.LEFT, padx=2)
        
        # 비정상 데이터 시작 번호
        ttk.Label(self.start_number_frame, text="비정상 시작 번호:").pack(side=tk.LEFT, padx=2)
        self.abnormal_start_var = tk.StringVar(value=str(self.abnormal_start_number))
        self.abnormal_start_entry = ttk.Entry(self.start_number_frame, textvariable=self.abnormal_start_var, width=8)
        self.abnormal_start_entry.pack(side=tk.LEFT, padx=2)
        
        # 시작 번호 적용 버튼
        ttk.Button(self.start_number_frame, text="적용", command=self.apply_start_numbers).pack(side=tk.LEFT, padx=5)
        
        # 구분선 추가
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=0)
        
        # 상태 선택 프레임
        self.state_frame = ttk.Frame(self.frame)
        self.state_frame.pack(pady=0)
        ttk.Label(self.state_frame, text="상태:").pack(side=tk.LEFT, padx=2)
        self.state_var = tk.StringVar(value="normal")
        self.normal_radio = ttk.Radiobutton(self.state_frame, text="정상 (Tab)", value="normal", 
                                          variable=self.state_var, command=self.change_state)
        self.normal_radio.pack(side=tk.LEFT, padx=2)
        self.abnormal_radio = ttk.Radiobutton(self.state_frame, text="비정상 (Tab)", value="abnormal", 
                                            variable=self.state_var, command=self.change_state)
        self.abnormal_radio.pack(side=tk.LEFT, padx=2)
        
        # 상태 표시 레이블
        self.state_label = ttk.Label(self.state_frame, text="[정상]", foreground="blue")
        self.state_label.pack(side=tk.LEFT, padx=5)
        
        # 이미지 형식 선택
        self.format_frame = ttk.Frame(self.frame)
        self.format_frame.pack(pady=0)
        ttk.Label(self.format_frame, text="이미지 형식:").pack(side=tk.LEFT, padx=2)
        self.format_var = tk.StringVar(value="bmp")
        for fmt in ["bmp", "jpg", "png"]:
            ttk.Radiobutton(self.format_frame, text=fmt.upper(), value=fmt, 
                           variable=self.format_var, command=self.change_image_format).pack(side=tk.LEFT, padx=2)
        
        # 구분선 추가
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=0)
        
        # 카메라 화면 프레임
        self.camera_frame = ttk.Frame(self.frame)
        self.camera_frame.pack(pady=0, fill=tk.BOTH, expand=True)  # 프레임을 남은 공간에 꽉 채움
        
        # 카메라 화면 (4:3 비율 유지)
        self.display_width = 800
        self.display_height = 800
        self.canvas = tk.Canvas(self.camera_frame, width=self.display_width, height=self.display_height, 
                              highlightthickness=0)  # 캔버스 테두리 제거
        self.canvas.pack(fill=tk.BOTH, expand=True)  # 캔버스를 프레임에 꽉 채움
        
        # 구분선 추가
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=0)
        
        # 컨트롤 프레임
        self.control_frame = ttk.Frame(self.frame)
        self.control_frame.pack(pady=0)
        
        # 스케일 조절 프레임
        self.scale_frame = ttk.Frame(self.control_frame)
        self.scale_frame.pack(pady=0)
        
        # 스케일 레이블
        self.scale_label = ttk.Label(self.scale_frame, text=f"현재 스케일: {self.scale:.1f}x")
        self.scale_label.pack(side=tk.LEFT, padx=2)
        
        # 해상도 레이블
        self.resolution_label = ttk.Label(self.scale_frame, text="")
        self.resolution_label.pack(side=tk.LEFT, padx=2)
        self.update_resolution_label()
        
        # 스케일 조절 버튼들
        ttk.Button(self.scale_frame, text="-", width=2, command=lambda: self.change_scale(-0.1)).pack(side=tk.LEFT, padx=1)
        ttk.Button(self.scale_frame, text="+", width=2, command=lambda: self.change_scale(0.1)).pack(side=tk.LEFT, padx=1)
        ttk.Button(self.scale_frame, text="초기화", width=6, command=self.reset_scale).pack(side=tk.LEFT, padx=2)
        
        # 구분선 추가
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=0)
        
        # 버튼 프레임
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.pack(pady=0)
        
        # 캡처 버튼
        self.capture_btn = ttk.Button(self.button_frame, text="캡처 (Space)", width=12, command=self.capture_image)
        self.capture_btn.pack(side=tk.LEFT, padx=2)
        
        # 흑백/컬러 모드 토글 버튼
        self.mode_btn = ttk.Button(self.button_frame, text="컬러 모드", width=10, command=self.toggle_mode)
        self.mode_btn.pack(side=tk.LEFT, padx=2)
        
        # 종료 버튼
        self.quit_btn = ttk.Button(self.button_frame, text="종료", width=8, command=self.quit_app)
        self.quit_btn.pack(side=tk.LEFT, padx=2)
        
        # 구분선 추가
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=0)
        
        # 상태 레이블
        self.status_label = ttk.Label(self.frame, text="")
        self.status_label.pack(pady=0)
        
        # 스페이스바 바인딩
        self.window.bind('<space>', lambda e: self.capture_image())
        # Tab 키 바인딩
        self.window.bind('<Tab>', self.toggle_state)
        
        # 더미 프레임 읽기
        for _ in range(3):
            self.camera.read()
        
        # 화면 업데이트 시작
        self.update_frame()
    
    def toggle_mode(self):
        self.is_grayscale = not self.is_grayscale
        self.mode_btn.config(text="컬러 모드" if self.is_grayscale else "흑백 모드")
        self.status_label.config(text=f"{'흑백' if self.is_grayscale else '컬러'} 모드로 전환됨")
    
    def change_scale(self, delta):
        """스케일을 변경합니다."""
        new_scale = self.scale + delta
        if 0.1 <= new_scale <= 2.0:  # 스케일 범위 제한
            self.scale = new_scale
            self.scale_label.config(text=f"현재 스케일: {self.scale:.1f}x")
            self.update_resolution_label()
            self.status_label.config(text=f"스케일이 {self.scale:.1f}x로 변경되었습니다.")

    def reset_scale(self):
        """스케일을 초기값으로 리셋합니다."""
        self.scale = 1.0
        self.scale_label.config(text=f"현재 스케일: {self.scale:.1f}x")
        self.update_resolution_label()
        self.status_label.config(text="스케일이 초기값으로 리셋되었습니다.")

    def change_image_format(self):
        """이미지 저장 형식을 변경합니다."""
        self.image_format = self.format_var.get()
        self.status_label.config(text=f"이미지 저장 형식이 {self.image_format.upper()}로 변경되었습니다.")

    def update_resolution_label(self):
        """현재 스케일에 따른 해상도를 업데이트합니다."""
        scaled_width = int(self.actual_width * self.scale)
        scaled_height = int(self.actual_height * self.scale)
        self.resolution_label.config(text=f"해상도: {scaled_width}x{scaled_height}")

    def update_frame(self):
        ret, frame = self.camera.read()
        if ret:
            if self.is_grayscale:
                # 흑백으로 변환
                frame_processed = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                # 흑백 이미지를 3채널로 변환
                frame_display = cv2.cvtColor(frame_processed, cv2.COLOR_GRAY2RGB)
            else:
                # 컬러 이미지 처리 - BGR을 RGB로 변환
                frame_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 현재 캔버스 크기 가져오기
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            # 스케일 적용하여 프레임 크기 조정
            scaled_width = int(canvas_width * self.scale)
            scaled_height = int(canvas_height * self.scale)
            frame_resized = cv2.resize(frame_display, (scaled_width, scaled_height), interpolation=cv2.INTER_NEAREST)
            
            # PIL 이미지로 변환
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(frame_resized))
            
            # 캔버스에 이미지 중앙 정렬하여 표시
            x_center = (canvas_width - scaled_width) // 2
            y_center = (canvas_height - scaled_height) // 2
            self.canvas.create_image(x_center, y_center, image=self.photo, anchor=tk.NW)
        
        # 다음 프레임 업데이트 예약 (33ms = 약 30fps)
        self.window.after(33, self.update_frame)

    def change_save_directory(self):
        """저장 폴더를 변경합니다."""
        new_directory = filedialog.askdirectory(initialdir=self.base_directory if self.base_directory else None)
        if new_directory:  # 사용자가 폴더를 선택한 경우
            self.setup_directories(new_directory)
            self.path_label.config(text=f"저장 경로: {self.base_directory}")
            self.status_label.config(text=f"저장 경로가 변경되었습니다: {self.base_directory}")

    def toggle_state(self, event=None):
        """Tab 키로 정상/비정상 상태를 전환합니다."""
        self.is_normal = not self.is_normal
        self.state_var.set("normal" if self.is_normal else "abnormal")
        self.change_state()
        return "break"  # Tab 키의 기본 동작 방지

    def change_state(self):
        """정상/비정상 상태를 변경합니다."""
        self.is_normal = self.state_var.get() == "normal"
        state_text = "정상" if self.is_normal else "비정상"
        color = "blue" if self.is_normal else "red"
        self.state_label.config(text=f"[{state_text}]", foreground=color)
        
        # 현재 상태의 마지막 번호 확인
        next_number = self.get_next_image_number()
        self.status_label.config(
            text=f"상태가 {state_text}으로 변경되었습니다.\n"
                 f"다음 저장 번호: {next_number:05d}"
        )

    def apply_start_numbers(self):
        """시작 번호를 적용합니다."""
        try:
            # 입력값 검증
            normal_start = int(self.normal_start_var.get())
            abnormal_start = int(self.abnormal_start_var.get())
            
            if normal_start < 0 or abnormal_start < 0:
                raise ValueError("시작 번호는 0 이상이어야 합니다.")
            
            if normal_start == abnormal_start:
                raise ValueError("정상과 비정상의 시작 번호는 서로 달라야 합니다.")
            
            # 시작 번호 업데이트
            self.normal_start_number = normal_start
            self.abnormal_start_number = abnormal_start
            
            # 상태 업데이트
            self.status_label.config(
                text=f"시작 번호가 변경되었습니다.\n"
                     f"정상: {self.normal_start_number:05d}\n"
                     f"비정상: {self.abnormal_start_number:05d}"
            )
            
        except ValueError as e:
            messagebox.showerror("오류", str(e))
            # 잘못된 입력값 복원
            self.normal_start_var.set(str(self.normal_start_number))
            self.abnormal_start_var.set(str(self.abnormal_start_number))

    def get_next_image_number(self):
        """다음 이미지 번호를 가져옵니다."""
        if self.is_normal:
            # 정상 상태: normal 폴더에서 검색
            pattern = os.path.join(self.normal_directory, f"[0-9][0-9][0-9][0-9][0-9].{self.image_format}")
            existing_files = glob.glob(pattern)
            
            if not existing_files:
                return self.normal_start_number
            
            numbers = []
            for file in existing_files:
                try:
                    num = int(os.path.splitext(os.path.basename(file))[0])
                    if num >= self.normal_start_number:  # 시작 번호 이상의 파일만 고려
                        numbers.append(num)
                except ValueError:
                    continue
            
            return max(numbers, default=self.normal_start_number - 1) + 1
        else:
            # 비정상 상태: abnormal 폴더에서 검색
            pattern = os.path.join(self.abnormal_directory, f"[0-9][0-9][0-9][0-9][0-9].{self.image_format}")
            existing_files = glob.glob(pattern)
            
            if not existing_files:
                return self.abnormal_start_number
            
            numbers = []
            for file in existing_files:
                try:
                    num = int(os.path.splitext(os.path.basename(file))[0])
                    if num >= self.abnormal_start_number:  # 시작 번호 이상의 파일만 고려
                        numbers.append(num)
                except ValueError:
                    continue
            
            return max(numbers, default=self.abnormal_start_number - 1) + 1

    def save_to_merge_directory(self, source_path, is_normal):
        """이미지를 merge 디렉토리에 저장합니다."""
        # 정상 데이터의 마지막 번호 확인
        pattern = os.path.join(self.merge_directory, f"[0-9][0-9][0-9][0-9][0-9].{self.image_format}")
        existing_files = glob.glob(pattern)
        
        if not existing_files:
            next_number = 1
        else:
            numbers = []
            for file in existing_files:
                try:
                    num = int(os.path.splitext(os.path.basename(file))[0])
                    numbers.append(num)
                except ValueError:
                    continue
            next_number = max(numbers, default=0) + 1
        
        # merge 디렉토리에 파일 복사
        dest_filename = f"{next_number:05d}.{self.image_format}"
        dest_path = os.path.join(self.merge_directory, dest_filename)
        shutil.copy2(source_path, dest_path)

    def capture_image(self):
        ret, frame = self.camera.read()
        if ret:
            if self.is_grayscale:
                # 흑백으로 변환
                frame_processed = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            else:
                # 컬러 이미지는 원본 그대로 저장 (BGR 형식)
                frame_processed = frame
            
            # 다음 이미지 번호 가져오기
            image_number = self.get_next_image_number()
            filename = f"{image_number:05d}.{self.image_format}"
            
            # 현재 상태에 맞는 디렉토리에 저장
            current_dir = self.normal_directory if self.is_normal else self.abnormal_directory
            save_path = os.path.join(current_dir, filename)
            cv2.imwrite(save_path, frame_processed)
            
            # merge 디렉토리에 복사
            self.save_to_merge_directory(save_path, self.is_normal)
            
            # 상태 업데이트
            scaled_width = int(self.actual_width * self.scale)
            scaled_height = int(self.actual_height * self.scale)
            state_text = "정상" if self.is_normal else "비정상"
            self.status_label.config(
                text=f"이미지 저장됨: {filename}\n"
                     f"상태: {state_text}\n"
                     f"해상도: {scaled_width}x{scaled_height}\n"
                     f"스케일: {self.scale:.1f}x\n"
                     f"저장 위치: {current_dir}\n"
                     f"병합 위치: {self.merge_directory}"
            )
    
    def quit_app(self):
        if self.camera.isOpened():
            self.camera.release()
        self.window.quit()

    def get_available_cameras(self):
        """사용 가능한 카메라 목록을 반환합니다."""
        available_cameras = []
        for i in range(10):  # 0부터 9까지의 카메라 인덱스 확인
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
        return available_cameras

    def show_camera_selection_dialog(self):
        """카메라 선택 다이얼로그를 표시합니다."""
        dialog = tk.Toplevel(self.window)
        dialog.title("카메라 선택")
        dialog.geometry("300x200")
        dialog.transient(self.window)
        dialog.grab_set()

        selected_camera = [None]  # 리스트로 감싸서 참조 전달

        def on_select():
            selected_camera[0] = camera_listbox.get(camera_listbox.curselection())
            dialog.destroy()

        # 카메라 목록 표시
        ttk.Label(dialog, text="사용 가능한 카메라 목록:").pack(pady=10)
        
        camera_listbox = tk.Listbox(dialog, height=5)
        camera_listbox.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        for camera in self.available_cameras:
            camera_listbox.insert(tk.END, f"카메라 {camera}")
        
        # 선택 버튼
        ttk.Button(dialog, text="선택", command=on_select).pack(pady=10)

        # 다이얼로그가 닫힐 때까지 대기
        self.window.wait_window(dialog)
        
        if selected_camera[0] is not None:
            return int(selected_camera[0].split()[-1])
        return None

# 메인 윈도우 생성 및 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop() 