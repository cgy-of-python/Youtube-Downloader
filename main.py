import os.path
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as tf
import pytube
from urllib.error import URLError
import tkinter.messagebox as tm
import requests
import io
from PIL import ImageTk, Image
import threading
import subprocess
from pytube.exceptions import *


class ScrollableFrame(tk.Frame):
    def __init__(self, container: tk.Misc | None, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.width = kwargs['width']
        self.height = kwargs['height']
        canvas = tk.Canvas(self, width=self.width, height=self.height)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, width=self.width, height=self.height)
        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):  # 鼠标滚轮
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # 绑定鼠标滚


class TubeVideo:
    def __init__(self, url, progressbar: ttk.Progressbar, label: tk.Label, root: tk.Tk, frame: tk.Frame):
        self.progressbar = progressbar
        self.label = label
        self.root = root
        self.frame = frame
        self.yt = pytube.YouTube(url,
                                 on_progress_callback=lambda stream, chunk, bytes_remaining: self.on_progress(
                                     bytes_remaining),
                                 on_complete_callback=lambda stream, file_path: self.on_complete(file_path),
                                 use_oauth=True, allow_oauth_cache=True)
        self.success = True

        try:
            self.title = self.yt.title
        except (URLError, Exception) as e:
            print(type(e), e)
            self.success = False
        self.percentage = 0.0
        if self.success:
            self.total_size = self.yt.streams.get_highest_resolution().filesize
            self.length = self.yt.length
        else:
            pass

    def get_title(self):
        return self.title

    def get_succeed(self):
        return self.success

    def get_size(self, res):
        self.total_size = self.yt.streams.get_by_resolution(res).filesize

    def download_video(self, path, is_highest, res=None):
        self.label.config(foreground='gold')
        if is_highest:
            stream = self.yt.streams.get_highest_resolution()
        else:
            stream = self.yt.streams.get_by_resolution(res)
        os.path.join(path, f"{self.title}.mp4")
        stream.download(output_path=path)

    def calc_percentage(self, bytes_remaining):
        bytes_downloaded = self.total_size - bytes_remaining
        self.percentage = bytes_downloaded / self.total_size * 100

    def get_thumbnail_url(self):
        url = '/'.join(self.yt.thumbnail_url.split('/')[:-1]) + "/hqdefault.jpg"
        return url

    def on_progress(self, bytes_remaining):
        self.calc_percentage(bytes_remaining)
        self.progressbar['value'] = int(self.percentage)
        self.label['text'] = (f"{(self.total_size - bytes_remaining) / 1024 / 1024:.2f}MB/"
                              f"{self.total_size / 1024 / 1024:.2f}MB {self.percentage:.2f}%")
        self.root.update()

    def on_complete(self, file_path):
        try:
            os.startfile(file_path)
        except AttributeError:
            try:
                subprocess.run(['open', file_path])
            except (OSError, Exception):
                tm.showerror("")
        self.label.config(foreground="green")
        self.label['text'] = "下载完成!单击关闭。"
        self.frame['cursor'] = 'hand2'
        self.frame.bind("<Button-1>", lambda e: (self.frame.destroy(), self.root.update()))
        self.root.update()


class EachVideoFrame:
    def __init__(self, _root, url, path, rel=None):
        self.rel = rel
        self.path = path
        self.url = url
        self.root = _root
        self.frame = tk.Frame(_root)  # 690*120
        self.info_frame = tk.Frame(self.frame)
        self.progress_frame = tk.Frame(self.frame)
        self.image = tk.Label(self.frame)
        self.title = tk.Label(self.info_frame, font=("黑体", 20), wraplength=200)
        self.info = tk.Label(self.info_frame, font=("黑体", 10), fg='grey')
        self.text = tk.Label(self.progress_frame, justify='left')
        self.progressbar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=300, mode="determinate")
        self.yt: TubeVideo | None = None
        self.loading = tk.Label(self.frame, text="正在加载视频信息...", font=("黑体", 30))
        self.loading.pack()
        self.root.update()
        self.succeed = True
        threading.Thread(target=self.network_part).start()

    def network_part(self):
        try:
            self.yt = TubeVideo(self.url, self.progressbar, self.text, self.root, self.frame)
        except RegexMatchError:
            tm.showerror("错误！", "下载失败，请输入正确的URL地址！")
            self.frame.destroy()
            return
        except AgeRestrictedError:
            tm.showerror("错误！", "该视频无法下载，因为它是年龄限制的。")
            self.frame.destroy()
            return
        except (ConnectionError, Exception):
            tm.showerror("错误！", "下载失败，请检查网络连接或视频链接是否正确。")
            self.frame.destroy()
            return
        if not self.yt.get_succeed():
            tm.showerror("错误！", "无法下载该视频，请检查网络连接或视频链接是否正确。")
            self.succeed = False
            return
        response = requests.get(self.yt.get_thumbnail_url(), stream=True)
        image_bytes = io.BytesIO(response.content)
        img_obj = Image.open(image_bytes)
        w, h = img_obj.size
        img_obj = img_obj.resize((int(w * 0.3), int(h * 0.3)))
        img = ImageTk.PhotoImage(img_obj)
        self.image['image'] = img
        self.image.image = img
        title = self.yt.get_title()
        if len(title) >= 40:
            title = title[:37] + '...'
        self.title['text'] = title
        self.info[
            "text"] = f'{self.yt.total_size / 1024 / 1024:.2f}MB  {self.yt.length // 60}:{str(self.yt.length % 60)[:1]}S'
        self.text['text'] = f"00.00MB/{self.yt.total_size / 1024 / 1024:.2f}MB 00.00%"
        self.loading.destroy()
        del self.loading
        self.image.grid(row=0, column=0, padx=5, pady=5)
        self.title.pack(padx=5, pady=5)
        self.info.pack(padx=5, pady=5)
        self.info_frame.grid(row=0, column=1, padx=5, pady=5)
        self.text.pack(side=tk.TOP, padx=5, pady=5)
        self.progressbar.pack(side=tk.TOP, fill=tk.X, expand=True, padx=5, pady=5)
        self.progress_frame.grid(row=0, column=2, sticky="w", padx=5, pady=5)
        if self.rel is not None:
            self.yt.download_video(path=self.path, is_highest=False, res=self.rel)
        else:
            self.yt.download_video(path=self.path, is_highest=True)

    def pack(self, *args, **kwargs):
        self.frame.pack(*args, **kwargs)

    def grid(self, *args, **kwargs):
        self.frame.grid(*args, **kwargs)

    def place(self, *args, **kwargs):
        self.frame.place(*args, **kwargs)


class NewVideo:
    def __init__(self, root):
        self.var = tk.StringVar()
        self.var.set("Best")
        self.filenameVar = tk.StringVar()
        self._root = root
        self.root = tk.Toplevel(self._root)
        self.root.title("YouTube 视频下载器--新建下载任务")
        self.label = tk.Label(self.root, text="输入视频链接:")
        self.label.grid(row=0, column=0, padx=5, pady=5)
        self.entry = ttk.Entry(self.root)
        self.entry.grid(row=0, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W + tk.E)
        self.label2 = tk.Label(self.root, text="下载清晰度:")
        self.label2.grid(row=1, column=0, padx=5, pady=5)
        self.radios = ttk.Radiobutton(self.root, text="最高画质", value='Best', variable=self.var)
        self.radios2 = ttk.Radiobutton(self.root, text="标清", value='480p', variable=self.var)
        self.radios3 = ttk.Radiobutton(self.root, text="流畅", value='360p', variable=self.var)
        self.radios.grid(row=1, column=1, padx=5, pady=5)
        self.radios2.grid(row=1, column=2, padx=5, pady=5)
        self.radios3.grid(row=1, column=3, padx=5, pady=5)
        self.label3 = tk.Label(self.root, text="保存到：")
        self.label3.grid(row=2, column=0, padx=5, pady=5)
        self.entry2 = ttk.Entry(self.root, textvariable=self.filenameVar)
        self.entry2.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W + tk.E)
        self.btn = ttk.Button(self.root, text="浏览", command=self.blowse)
        self.btn.grid(row=2, column=3, padx=5, pady=5)
        self.btn2 = ttk.Button(self.root, text="下载", command=self.download)
        self.btn2.grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W + tk.E)

    def blowse(self):
        filename = tf.askdirectory()
        self.filenameVar.set(filename)

    def download(self):
        url = self.entry.get()
        path = self.filenameVar.get()
        if path == '':
            tm.showerror("错误，请输入有效的地址")
            return
        quality = self.var.get()
        frame = EachVideoFrame(self._root, url, path, None if quality == "Best" else quality)
        frame.pack()
        self.root.destroy()


class Application:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube 视频下载器")
        self.add_frame = tk.Frame(self.root)
        self.btn1 = ttk.Button(self.add_frame, text="下载一个新视频", command=self.add_video)
        self.btn1.pack(padx=5, pady=5)
        self.add_frame.pack(side=tk.TOP, fill=tk.X)
        self.frame = ScrollableFrame(self.root, width=690, height=180)
        self.frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH)
        self.root.resizable(False, False)
        try:
            self.root.iconphoto(True, tk.PhotoImage(file="icon.png"))
        except (tk.TclError, FileNotFoundError, Exception):
            pass

    def add_video(self):
        NewVideo(self.frame.scrollable_frame)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = Application()
    app.run()
