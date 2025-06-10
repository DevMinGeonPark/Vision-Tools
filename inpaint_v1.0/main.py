import tkinter as tk
from controller import InpaintController
from settings_window import SettingsWindow

if __name__ == "__main__":
    """애플리케이션 시작점"""
    root = tk.Tk()
    settings_window = SettingsWindow(root)
    settings = settings_window.run()
    
    if settings:
        app = InpaintController(settings["image_dir"], settings["save_dir"])
        if app.is_initialized:
            app.run()

