import tkinter as tk
from tkinter import ttk, messagebox
import os

class ClassEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Class Editor")

        # --- Center the window ---
        window_width = 400
        window_height = 450
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        self.master.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        self.file_path = "classes.txt"
        self.classes = []

        # --- UI Elements ---
        self.frame = ttk.Frame(self.master, padding="10")
        self.frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Listbox to display classes
        self.listbox_frame = ttk.LabelFrame(self.frame, text="Classes")
        self.listbox_frame.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        self.listbox = tk.Listbox(self.listbox_frame, height=10, width=40)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = ttk.Scrollbar(self.listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        # Entry fields for class details
        self.entry_frame = ttk.LabelFrame(self.frame, text="Details")
        self.entry_frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=(tk.W, tk.E))
        ttk.Label(self.entry_frame, text="Class Number:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.class_num_var = tk.StringVar()
        self.class_num_entry = ttk.Entry(self.entry_frame, textvariable=self.class_num_var)
        self.class_num_entry.grid(row=0, column=1, padx=5, pady=2, sticky=tk.EW)
        ttk.Label(self.entry_frame, text="Class Name:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.class_name_var = tk.StringVar()
        self.class_name_entry = ttk.Entry(self.entry_frame, textvariable=self.class_name_var)
        self.class_name_entry.grid(row=1, column=1, padx=5, pady=2, sticky=tk.EW)

        # Buttons for actions
        self.button_frame = ttk.Frame(self.frame)
        self.button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        self.add_button = ttk.Button(self.button_frame, text="Add", command=self.add_class)
        self.add_button.grid(row=0, column=0, padx=5)
        self.update_button = ttk.Button(self.button_frame, text="Update", command=self.update_class)
        self.update_button.grid(row=0, column=1, padx=5)
        self.delete_button = ttk.Button(self.button_frame, text="Delete", command=self.delete_class)
        self.delete_button.grid(row=0, column=2, padx=5)
        self.save_button = ttk.Button(self.button_frame, text="Save to File", command=self.save_classes)
        self.save_button.grid(row=0, column=3, padx=5)

        # --- Load initial data ---
        self.load_classes()

    def load_classes(self):
        self.classes = []
        self.listbox.delete(0, tk.END)
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            self.classes.append({'num': parts[0].strip(), 'name': parts[1].strip()})
        self.refresh_listbox()

    def refresh_listbox(self):
        self.listbox.delete(0, tk.END)
        # Sort classes by number before displaying
        self.classes.sort(key=lambda x: int(x['num']) if x['num'].isdigit() else float('inf'))
        for item in self.classes:
            self.listbox.insert(tk.END, f"{item['num']}, {item['name']}")

    def on_select(self, event):
        selection_indices = self.listbox.curselection()
        if not selection_indices:
            return
        selected_index = selection_indices[0]
        selected_class = self.classes[selected_index]
        self.class_num_var.set(selected_class['num'])
        self.class_name_var.set(selected_class['name'])

    def add_class(self):
        num = self.class_num_var.get().strip()
        name = self.class_name_var.get().strip()

        if not num or not name:
            messagebox.showerror("Error", "Class Number and Name cannot be empty.")
            return
        if not num.isdigit():
            messagebox.showerror("Error", "Class Number must be an integer.")
            return
        if any(c['num'] == num for c in self.classes):
            messagebox.showerror("Error", f"Class Number {num} already exists.")
            return

        self.classes.append({'num': num, 'name': name})
        self.refresh_listbox()
        self.clear_entries()
        messagebox.showinfo("Success", "Class added. Press 'Save to File' to apply changes.")

    def update_class(self):
        selection_indices = self.listbox.curselection()
        if not selection_indices:
            messagebox.showerror("Error", "Please select a class to update.")
            return
        selected_index = selection_indices[0]

        num = self.class_num_var.get().strip()
        name = self.class_name_var.get().strip()

        if not num or not name:
            messagebox.showerror("Error", "Class Number and Name cannot be empty.")
            return
        if not num.isdigit():
            messagebox.showerror("Error", "Class Number must be an integer.")
            return

        # Check if the new number conflicts with another existing class
        original_num = self.classes[selected_index]['num']
        if num != original_num and any(c['num'] == num for c in self.classes):
            messagebox.showerror("Error", f"Class Number {num} already exists.")
            return

        self.classes[selected_index] = {'num': num, 'name': name}
        self.refresh_listbox()
        self.clear_entries()
        messagebox.showinfo("Success", "Class updated. Press 'Save to File' to apply changes.")


    def delete_class(self):
        selection_indices = self.listbox.curselection()
        if not selection_indices:
            messagebox.showerror("Error", "Please select a class to delete.")
            return
        selected_index = selection_indices[0]

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this class?"):
            del self.classes[selected_index]
            self.refresh_listbox()
            self.clear_entries()
            messagebox.showinfo("Success", "Class deleted. Press 'Save to File' to apply changes.")

    def save_classes(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write("# 클래스 설정 파일\n")
                f.write("# 형식: 클래스번호,클래스이름\n")
                for item in self.classes:
                    f.write(f"{item['num']},{item['name']}\n")
            messagebox.showinfo("Success", f"Classes successfully saved to {self.file_path}")
        except IOError as e:
            messagebox.showerror("Save Error", f"Failed to save file: {e}")

    def clear_entries(self):
        self.class_num_var.set("")
        self.class_name_var.set("")
        self.listbox.selection_clear(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = ClassEditor(root)
    root.mainloop()
