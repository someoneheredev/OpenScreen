import os
import json
import ctypes
from ctypes import wintypes
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, font
from PIL import Image, ImageTk
import threading
import keyboard
import struct
import subprocess
import platform

# Directories
GALLERY_DIR = "gallery"
CONFIG_FILE = "config.json"
os.makedirs(GALLERY_DIR, exist_ok=True)

# Default config
default_config = {"keybind": "F12", "format": "png"}

# Load or create config
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)
else:
    config = default_config
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

def take_screenshot(file_format=None):
    if file_format is None:
        file_format = config.get("format", "png")
    try:
        screen_width = user32.GetSystemMetrics(0)
        screen_height = user32.GetSystemMetrics(1)
        hdc_screen = user32.GetDC(0)
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, screen_width, screen_height)
        gdi32.SelectObject(hdc_mem, hbmp)
        SRCCOPY = 0x00CC0020
        gdi32.BitBlt(hdc_mem, 0, 0, screen_width, screen_height, hdc_screen, 0, 0, SRCCOPY)
        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", wintypes.LONG),
                ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG),
                ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)
            ]
        bmp_info = BITMAPINFOHEADER()
        bmp_info.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmp_info.biWidth = screen_width
        bmp_info.biHeight = screen_height
        bmp_info.biPlanes = 1
        bmp_info.biBitCount = 24
        bmp_info.biCompression = 0
        bmp_info.biSizeImage = 0
        row_padding = (4 - (screen_width * 3) % 4) % 4
        bmp_data_size = (screen_width * 3 + row_padding) * screen_height
        pixel_data = (ctypes.c_ubyte * bmp_data_size)()
        gdi32.GetDIBits(hdc_mem, hbmp, 0, screen_height, pixel_data, ctypes.byref(bmp_info), 0)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_screen)
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{now}.{file_format}"
        filepath = os.path.join(GALLERY_DIR, filename)
        from PIL import Image
        img = Image.frombytes("RGB", (screen_width, screen_height), bytes(pixel_data))
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.save(filepath, file_format.upper())
        update_gallery()
    except Exception as e:
        messagebox.showerror("Error", str(e))

def bind_hotkey():
    keyboard.add_hotkey(config["keybind"], lambda: take_screenshot())
    keyboard.wait()

def open_image(filepath):
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(filepath)
        elif system == "Darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
    except:
        pass

# --- Modern Dark Mode UI with Sidebar ---
root = tk.Tk()
root.title("Screenshot Tool")
root.geometry("900x600")
root.configure(bg="#1a1a1a")
root.resizable(True, True)

# Color scheme
BG_DARK = "#1a1a1a"
SIDEBAR_BG = "#1a1a1a"
NAV_BTN_BG = "#2d2d2d"
NAV_BTN_HOVER = "#3d3d3d"
CONTENT_BG = "#242424"
ACCENT_COLOR = "#ff6f81"

title_font = font.Font(root, family="Segoe UI", size=14, weight="bold")
button_font = font.Font(root, family="Segoe UI", size=11)
nav_font = font.Font(root, family="Segoe UI", size=11, weight="bold")

# Main container
main_container = tk.Frame(root, bg=BG_DARK)
main_container.pack(fill="both", expand=True)

# --- LEFT SIDEBAR ---
sidebar = tk.Frame(main_container, bg=SIDEBAR_BG, width=150)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

sidebar_title = tk.Label(sidebar, text="Menu", font=title_font, bg=SIDEBAR_BG, fg="white")
sidebar_title.pack(pady=20)

# Current page tracker
current_page = tk.StringVar(value="home")

def nav_button_hover(btn, hover=True):
    btn.config(bg=NAV_BTN_HOVER if hover else NAV_BTN_BG)

nav_buttons = {}

def create_nav_button(text, page_name):
    def on_enter(e): e.widget.config(bg=NAV_BTN_HOVER)
    def on_leave(e): e.widget.config(bg=NAV_BTN_BG if current_page.get() != page_name else ACCENT_COLOR)
    def on_click():
        for btn_name, btn in nav_buttons.items():
            btn.config(bg=NAV_BTN_BG)
        nav_buttons[page_name].config(bg=ACCENT_COLOR)
        current_page.set(page_name)
        show_page(page_name)
    
    btn = tk.Button(
        sidebar, text=text, font=nav_font, bg=NAV_BTN_BG, fg="white",
        width=15, height=2, bd=0, relief="flat", cursor="hand2", command=on_click
    )
    btn.pack(padx=10, pady=8)
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    nav_buttons[page_name] = btn
    return btn

create_nav_button("Home", "home")
create_nav_button("Gallery", "gallery")
create_nav_button("Settings", "settings")

# Set Home as active
nav_buttons["home"].config(bg=ACCENT_COLOR)

# --- CONTENT AREA ---
content_frame = tk.Frame(main_container, bg=CONTENT_BG)
content_frame.pack(side="right", fill="both", expand=True)

pages = {}

# --- HOME PAGE ---
def create_home_page():
    page = tk.Frame(content_frame, bg=CONTENT_BG)
    
    header = tk.Label(page, text="Screenshot Tool", font=title_font, bg=CONTENT_BG, fg="white")
    header.pack(pady=30)
    
    subtitle = tk.Label(page, text="Take screenshots with style!", bg=CONTENT_BG, fg="#999999")
    subtitle.pack(pady=5)
    
    def on_enter(e): e.widget['bg'] = "#ff4b5c"
    def on_leave(e): e.widget['bg'] = ACCENT_COLOR
    
    take_btn = tk.Button(
        page, text="Take Screenshot", bg=ACCENT_COLOR, fg="white",
        font=button_font, width=25, height=3, bd=0, relief="flat",
        cursor="hand2", command=lambda: take_screenshot()
    )
    take_btn.bind("<Enter>", on_enter)
    take_btn.bind("<Leave>", on_leave)
    take_btn.pack(pady=30)
    
    info = tk.Label(
        page, text="Press F12 or click above to capture your screen",
        bg=CONTENT_BG, fg="#666666", font=("Segoe UI", 10)
    )
    info.pack()
    
    return page

pages["home"] = create_home_page()

# --- GALLERY PAGE ---
def create_gallery_page():
    page = tk.Frame(content_frame, bg=CONTENT_BG)
    
    header = tk.Label(page, text="Gallery", font=title_font, bg=CONTENT_BG, fg="white")
    header.pack(pady=20)
    
    global gallery_frame
    gallery_frame = tk.Frame(page, bg=CONTENT_BG)
    gallery_frame.pack(pady=20, fill="both", expand=True, padx=20)
    
    return page

pages["gallery"] = create_gallery_page()

# --- SETTINGS PAGE ---
def create_settings_page():
    page = tk.Frame(content_frame, bg=CONTENT_BG)
    
    header = tk.Label(page, text="Settings", font=title_font, bg=CONTENT_BG, fg="white")
    header.pack(pady=20)
    
    settings_frame = tk.Frame(page, bg=CONTENT_BG)
    settings_frame.pack(pady=20, padx=40)
    
    # Format setting
    format_label = tk.Label(settings_frame, text="File Format:", bg=CONTENT_BG, fg="white", font=("Segoe UI", 11))
    format_label.grid(row=0, column=0, padx=10, pady=15, sticky="w")
    
    format_var = tk.StringVar(value=config.get("format", "png"))
    format_menu = tk.OptionMenu(settings_frame, format_var, "png", "jpg", "bmp")
    format_menu.config(bg=NAV_BTN_BG, fg="white", font=("Segoe UI", 10))
    format_menu.grid(row=0, column=1, padx=10, pady=15, sticky="w")
    
    # Hotkey setting
    hotkey_label = tk.Label(settings_frame, text="Hotkey:", bg=CONTENT_BG, fg="white", font=("Segoe UI", 11))
    hotkey_label.grid(row=1, column=0, padx=10, pady=15, sticky="w")
    
    hotkey_entry = tk.Entry(settings_frame, font=("Segoe UI", 10), width=20, bg=NAV_BTN_BG, fg="white", insertbackground="white")
    hotkey_entry.insert(0, config.get("keybind", "F12"))
    hotkey_entry.grid(row=1, column=1, padx=10, pady=15, sticky="w")
    
    def save_settings():
        config["keybind"] = hotkey_entry.get()
        config["format"] = format_var.get()
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        messagebox.showinfo("Success", "Settings saved!")
    
    save_btn = tk.Button(
        settings_frame, text="Save Settings", bg=ACCENT_COLOR, fg="white",
        font=button_font, width=20, height=2, bd=0, relief="flat", cursor="hand2", command=save_settings
    )
    save_btn.grid(row=2, columnspan=2, pady=30)
    
    return page

pages["settings"] = create_settings_page()

def show_page(page_name):
    for page in pages.values():
        page.pack_forget()
    pages[page_name].pack(fill="both", expand=True)

def update_gallery():
    for widget in gallery_frame.winfo_children():
        widget.destroy()
    
    files = sorted(os.listdir(GALLERY_DIR), reverse=True)
    
    if not files:
        no_img = tk.Label(gallery_frame, text="No screenshots yet", bg=CONTENT_BG, fg="#666666", font=("Segoe UI", 12))
        no_img.pack(pady=50)
        return
    
    recent = files[:8]
    for fname in recent:
        path = os.path.join(GALLERY_DIR, fname)
        try:
            img = Image.open(path)
            img.thumbnail((150, 150))
            photo = ImageTk.PhotoImage(img)
            
            card = tk.Label(gallery_frame, image=photo, bg=NAV_BTN_BG, bd=0, relief="flat", cursor="hand2")
            card.image = photo
            card.pack(side="left", padx=10, pady=10)
            card.bind("<Button-1>", lambda e, p=path: open_image(p))
        except:
            continue

show_page("home")
update_gallery()
threading.Thread(target=bind_hotkey, daemon=True).start()
root.mainloop()