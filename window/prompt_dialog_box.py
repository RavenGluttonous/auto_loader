import tkinter


def error_window(message: str, window_width: int | str, window_height: int | str):
    window = tkinter.Tk()
    font_size = 18
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window.geometry(
        f"{window_width}x{window_height}+{(screen_width - window_width) // 2}+{(screen_height - window_height) // 2}")
    window.title("AutoLoader 提示")
    window.attributes("-topmost", True)
    tkinter.Label(window, text=message, font=("", font_size), wraplength=window_width - 20).pack(fill="both", pady="3p")
    tkinter.Button(window, text="确认", command=lambda: close_windows(window), width="10", font=("", font_size)).pack(
        side="bottom", pady="3p")
    window.mainloop()


def close_windows(window: tkinter.Tk):
    window.destroy()