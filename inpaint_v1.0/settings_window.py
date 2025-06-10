import tkinter as tk
from tkinter import filedialog, messagebox

class SettingsWindow:
    """애플리케이션 시작 전 설정을 위한 Tkinter 창"""
    def __init__(self, root):
        self.root = root
        self.root.title("설정")
        self.root.geometry("500x150")

        self.image_dir = tk.StringVar()
        self.save_dir = tk.StringVar()
        
        self.result = None

        # 프레임 생성
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        # 이미지 폴더 설정
        tk.Label(frame, text="이미지 폴더:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.image_entry = tk.Entry(frame, textvariable=self.image_dir, width=50)
        self.image_entry.grid(row=0, column=1, padx=5)
        tk.Button(frame, text="찾아보기...", command=self._browse_image_dir).grid(row=0, column=2)

        # 저장 폴더 설정
        tk.Label(frame, text="저장 폴더:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.save_entry = tk.Entry(frame, textvariable=self.save_dir, width=50)
        self.save_entry.grid(row=1, column=1, padx=5)
        tk.Button(frame, text="찾아보기...", command=self._browse_save_dir).grid(row=1, column=2)

        # 버튼 프레임
        button_frame = tk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=10)

        tk.Button(button_frame, text="시작", command=self._start).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="취소", command=self._cancel).pack(side=tk.LEFT, padx=5)

    def _browse_image_dir(self):
        path = filedialog.askdirectory(title="이미지 폴더를 선택하세요")
        if path:
            self.image_dir.set(path)

    def _browse_save_dir(self):
        path = filedialog.askdirectory(title="저장할 폴더를 선택하세요")
        if path:
            self.save_dir.set(path)

    def _start(self):
        image_dir = self.image_dir.get()
        save_dir = self.save_dir.get()

        if not image_dir or not save_dir:
            messagebox.showwarning("경고", "이미지 폴더와 저장 폴더를 모두 선택해야 합니다.")
            return
        
        self.result = {"image_dir": image_dir, "save_dir": save_dir}
        self.root.destroy()

    def _cancel(self):
        self.result = None
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.result
