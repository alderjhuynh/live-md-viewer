import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, font as tkfont
from datetime import datetime

LIGHT_THEME = {
    "bg": "#f4eefb",
    "editor_bg": "#faf7fd",
    "editor_fg": "#3d2b52",
    "accent": "#d1b9eb",
    "accent_dark": "#a583d1",
    "accent_darker": "#7c53a8",
    "select_bg": "#e4d4f7",
    "cursor": "#7c53a8",
    "toolbar_bg": "#e9def6",
    "status_bg": "#e4d4f7",
    "status_fg": "#5b4479",
    "border": "#c9aee6",
    "code_bg": "#ece2f7",
    "code_fg": "#5b3d80",
    "quote_fg": "#8a72a8",
    "link_fg": "#6b3fa0",
    "list_fg": "#a583d1",
    "muted": "#9c86b8",
}

DARK_THEME = {
    "bg": "#1e1a26",
    "editor_bg": "#211c2b",
    "editor_fg": "#e6def5",
    "accent": "#5b4479",
    "accent_dark": "#8a72a8",
    "accent_darker": "#c9aee6",
    "select_bg": "#3d2f52",
    "cursor": "#c9aee6",
    "toolbar_bg": "#2a2235",
    "status_bg": "#2a2235",
    "status_fg": "#c9aee6",
    "border": "#4a3a63",
    "code_bg": "#2f2640",
    "code_fg": "#d8c8ef",
    "quote_fg": "#a58fc9",
    "link_fg": "#b28fe0",
    "list_fg": "#c9aee6",
    "muted": "#8b7aa3",
}

THEMES = {"Light": LIGHT_THEME, "Dark": DARK_THEME}

MD_EXTENSIONS = (".md", ".markdown", ".mdown", ".mkd", ".txt")


class MarkdownEditor:
    def __init__(self, root, initial_path=None):
        self.root = root
        self.filepath = None
        self.memory_snapshots = []
        self._highlight_job = None
        self._dirty = False
        self.theme_name = "Light"
        self.theme = THEMES[self.theme_name]

        self._build_fonts()
        self._build_ui()
        self._bind_shortcuts()

        if initial_path and os.path.isfile(initial_path):
            self._load_file(initial_path)
        else:
            self._update_title()

        self._highlight()

    def _build_fonts(self):
        base_family = "Menlo" if sys.platform == "darwin" else "Consolas"
        try:
            tkfont.Font(family=base_family, size=13)
        except tk.TclError:
            base_family = "Courier New"

        self.font_scale = 1.0
        self._base_sizes = {"normal": 13, "code": 12, "h1": 16, "h2": 14, "h3": 13}

        self.font_normal = tkfont.Font(family=base_family, size=13)
        self.font_bold = tkfont.Font(family=base_family, size=13, weight="bold")
        self.font_italic = tkfont.Font(family=base_family, size=13, slant="italic")
        self.font_bold_italic = tkfont.Font(family=base_family, size=13, weight="bold", slant="italic")
        self.font_code = tkfont.Font(family=base_family, size=12)
        self.font_h1 = tkfont.Font(family=base_family, size=16, weight="bold")
        self.font_h2 = tkfont.Font(family=base_family, size=14, weight="bold")
        self.font_h3 = tkfont.Font(family=base_family, size=13, weight="bold")

    def _build_ui(self):
        self.root.title("Untitled")
        self.root.configure(bg=self.theme["bg"])
        self.root.geometry("920x680")
        self.root.minsize(480, 360)

        self._build_menu()

        self.toolbar = tk.Frame(self.root, bg=self.theme["toolbar_bg"], height=36)
        self.toolbar.pack(side="top", fill="x")
        self.path_label = tk.Label(
            self.toolbar, text="Untitled.md", bg=self.theme["toolbar_bg"],
            fg=self.theme["accent_darker"], font=("Helvetica", 11, "bold"), anchor="w"
        )
        self.path_label.pack(side="left", padx=12, pady=6)

        self.editor_frame = tk.Frame(self.root, bg=self.theme["accent"], padx=2, pady=2)
        self.editor_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(8, 4))

        self.text = tk.Text(
            self.editor_frame,
            wrap="word",
            undo=True,
            font=self.font_normal,
            bg=self.theme["editor_bg"],
            fg=self.theme["editor_fg"],
            insertbackground=self.theme["cursor"],
            selectbackground=self.theme["select_bg"],
            selectforeground=self.theme["editor_fg"],
            relief="flat",
            padx=18,
            pady=16,
            spacing1=2,
            spacing3=4,
            borderwidth=0,
            highlightthickness=0,
        )
        self.scrollbar = tk.Scrollbar(self.editor_frame, command=self.text.yview,
                                       troughcolor=self.theme["bg"], bg=self.theme["accent"])
        self.text.configure(yscrollcommand=self.scrollbar.set)
        self.text.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self._configure_tags()

        self.status = tk.Label(
            self.root, text="Ready", bg=self.theme["status_bg"], fg=self.theme["status_fg"],
            anchor="w", font=("Helvetica", 10), padx=12, pady=4
        )
        self.status.pack(side="bottom", fill="x")

        self.text.bind("<<Modified>>", self._on_modified)

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        accel_save = "Cmd+S" if sys.platform == "darwin" else "Ctrl+S"
        accel_saveas = "Cmd+Shift+S" if sys.platform == "darwin" else "Ctrl+Shift+S"
        file_menu.add_command(label="New", command=self._new_file, accelerator="Cmd+N")
        file_menu.add_command(label="Open...", command=self._open_file, accelerator="Cmd+O")
        file_menu.add_separator()
        file_menu.add_command(label="Save", command=self.save, accelerator=accel_save)
        file_menu.add_command(label="Save As...", command=self.save_as, accelerator=accel_saveas)
        file_menu.add_separator()
        file_menu.add_command(label="Snapshot History...", command=self._show_snapshots)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self._quit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Undo", command=lambda: self.text.edit_undo(), accelerator="Cmd+Z")
        edit_menu.add_command(label="Redo", command=lambda: self.text.edit_redo(), accelerator="Cmd+Shift+Z")
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        self.theme_var = tk.StringVar(value=self.theme_name)
        for name in THEMES:
            view_menu.add_radiobutton(
                label=name, value=name, variable=self.theme_var,
                command=lambda n=name: self._set_theme(n),
            )
        view_menu.add_separator()
        accel_bigger = "Cmd+=" if sys.platform == "darwin" else "Ctrl+="
        accel_smaller = "Cmd+-" if sys.platform == "darwin" else "Ctrl+-"
        accel_reset = "Cmd+0" if sys.platform == "darwin" else "Ctrl+0"
        view_menu.add_command(label="Increase Font Size", command=lambda: self._change_font_size(0.1),
                               accelerator=accel_bigger)
        view_menu.add_command(label="Decrease Font Size", command=lambda: self._change_font_size(-0.1),
                               accelerator=accel_smaller)
        view_menu.add_command(label="Reset Font Size", command=self._reset_font_size,
                               accelerator=accel_reset)
        menubar.add_cascade(label="View", menu=view_menu)

        self.root.config(menu=menubar)

    def _configure_tags(self):
        t = self.text
        th = self.theme
        t.tag_configure("h1", font=self.font_h1, foreground=th["accent_darker"], spacing1=10, spacing3=6)
        t.tag_configure("h2", font=self.font_h2, foreground=th["accent_darker"], spacing1=8, spacing3=4)
        t.tag_configure("h3", font=self.font_h3, foreground=th["accent_dark"], spacing1=6, spacing3=2)
        t.tag_configure("bold", font=self.font_bold)
        t.tag_configure("italic", font=self.font_italic)
        t.tag_configure("bold_italic", font=self.font_bold_italic)
        t.tag_configure("code_inline", font=self.font_code, background=th["code_bg"],
                         foreground=th["code_fg"])
        t.tag_configure("code_block", font=self.font_code, background=th["code_bg"],
                         foreground=th["code_fg"])
        t.tag_configure("quote", foreground=th["quote_fg"], font=self.font_italic,
                         lmargin1=20, lmargin2=20)
        t.tag_configure("list_marker", foreground=th["list_fg"], font=self.font_bold)
        t.tag_configure("link", foreground=th["link_fg"], underline=True)
        t.tag_configure("markup", foreground=th["muted"])  # the literal #, *, ` chars
        t.tag_configure("hr", foreground=th["accent"], font=self.font_bold)

    def _set_theme(self, name):
        if name not in THEMES or name == self.theme_name:
            return
        self.theme_name = name
        self.theme = THEMES[name]
        self._apply_theme()

    def _apply_theme(self):
        th = self.theme
        self.root.configure(bg=th["bg"])
        self.toolbar.configure(bg=th["toolbar_bg"])
        self.path_label.configure(bg=th["toolbar_bg"], fg=th["accent_darker"])
        self.editor_frame.configure(bg=th["accent"])
        self.text.configure(
            bg=th["editor_bg"],
            fg=th["editor_fg"],
            insertbackground=th["cursor"],
            selectbackground=th["select_bg"],
            selectforeground=th["editor_fg"],
        )
        self.scrollbar.configure(troughcolor=th["bg"], bg=th["accent"])
        self.status.configure(bg=th["status_bg"], fg=th["status_fg"])
        self._configure_tags()
        self.status.config(text=f"Switched to {self.theme_name} theme")

    def _scaled(self, base):
        return max(1, round(base * self.font_scale))

    def _apply_font_scale(self):
        self.font_normal.configure(size=self._scaled(self._base_sizes["normal"]))
        self.font_bold.configure(size=self._scaled(self._base_sizes["normal"]))
        self.font_italic.configure(size=self._scaled(self._base_sizes["normal"]))
        self.font_bold_italic.configure(size=self._scaled(self._base_sizes["normal"]))
        self.font_code.configure(size=self._scaled(self._base_sizes["code"]))
        self.font_h1.configure(size=self._scaled(self._base_sizes["h1"]))
        self.font_h2.configure(size=self._scaled(self._base_sizes["h2"]))
        self.font_h3.configure(size=self._scaled(self._base_sizes["h3"]))
    
    def _change_font_size(self, delta):
        new_scale = min(max(round(self.font_scale + delta, 2), 0.6), 2.5)
        if new_scale == self.font_scale:
            return
        self.font_scale = new_scale
        self._apply_font_scale()
        self.status.config(text=f"Font size {round(self.font_scale * 100)}%")

    def _reset_font_size(self):
        if self.font_scale == 1.0:
            return
        self.font_scale = 1.0
        self._apply_font_scale()
        self.status.config(text="Font size 100%")

    def _bind_shortcuts(self):
        for seq in ("<Command-s>", "<Control-s>"):
            self.root.bind_all(seq, self._on_save_shortcut)
        for seq in ("<Command-S>", "<Control-S>", "<Command-Shift-s>", "<Control-Shift-S>"):
            self.root.bind_all(seq, self._on_save_as_shortcut)
        for seq in ("<Command-n>", "<Control-n>"):
            self.root.bind_all(seq, lambda e: self._new_file())
        for seq in ("<Command-o>", "<Control-o>"):
            self.root.bind_all(seq, lambda e: self._open_file())
        for seq in ("<Command-equal>", "<Control-equal>", "<Command-plus>", "<Control-plus>"):
            self.root.bind_all(seq, lambda e: self._change_font_size(0.1))
        for seq in ("<Command-minus>", "<Control-minus>"):
            self.root.bind_all(seq, lambda e: self._change_font_size(-0.1))
        for seq in ("<Command-0>", "<Control-0>"):
            self.root.bind_all(seq, lambda e: self._reset_font_size())
        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _on_save_shortcut(self, event=None):
        self.save()
        return "break"

    def _on_save_as_shortcut(self, event=None):
        self.save_as()
        return "break"

    def _snapshot(self):
        content = self.text.get("1.0", "end-1c")
        self.memory_snapshots.append((datetime.now(), content))
        if len(self.memory_snapshots) > 50:
            self.memory_snapshots.pop(0)
        return content

    def save(self):
        content = self._snapshot()
        if self.filepath:
            self._write_to_disk(self.filepath, content)
            self.status.config(text=f"Saved · {self._short_path(self.filepath)} · "
                                     f"{len(self.memory_snapshots)} snapshot(s) in memory")
        else:
            self.save_as(_content=content)

    def save_as(self, _content=None):
        content = _content if _content is not None else self._snapshot()
        initial = os.path.basename(self.filepath) if self.filepath else "Untitled.md"
        path = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".md",
            initialfile=initial,
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            self.status.config(text="Save cancelled")
            return
        self.filepath = path
        self._write_to_disk(path, content)
        self._update_title()
        self.status.config(text=f"Saved as {self._short_path(path)} · "
                                 f"{len(self.memory_snapshots)} snapshot(s) in memory")

    def _write_to_disk(self, path, content):
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self._dirty = False
            self._update_title()
        except OSError as e:
            messagebox.showerror("Save failed", f"Could not save file:\n{e}")

    def _show_snapshots(self):
        if not self.memory_snapshots:
            messagebox.showinfo("Snapshot History", "No in-memory snapshots yet. Press Cmd+S to create one.")
            return
        win = tk.Toplevel(self.root)
        win.title("Snapshot History")
        win.configure(bg=self.theme["bg"])
        win.geometry("360x300")
        listbox = tk.Listbox(win, bg=self.theme["editor_bg"], fg=self.theme["editor_fg"],
                              selectbackground=self.theme["select_bg"], relief="flat")
        listbox.pack(fill="both", expand=True, padx=10, pady=10)
        for ts, content in reversed(self.memory_snapshots):
            preview = content.strip().splitlines()[0][:40] if content.strip() else "(empty)"
            listbox.insert("end", f"{ts.strftime('%H:%M:%S')} — {preview}")

        def restore(event=None):
            sel = listbox.curselection()
            if not sel:
                return
            idx = len(self.memory_snapshots) - 1 - sel[0]
            _, content = self.memory_snapshots[idx]
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self._highlight()
            win.destroy()

        listbox.bind("<Double-Button-1>", restore)
        tk.Label(win, text="Double-click to restore a snapshot into the editor",
                 bg=self.theme["bg"], fg=self.theme["muted"], font=("Helvetica", 9)).pack(pady=(0, 8))

    def _new_file(self):
        if self._dirty and not self._confirm_discard():
            return
        self.filepath = None
        self.text.delete("1.0", "end")
        self._dirty = False
        self._update_title()
        self._highlight()

    def _open_file(self):
        if self._dirty and not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="Open",
            filetypes=[("Markdown / Text", "*.md *.markdown *.mdown *.mkd *.txt"), ("All files", "*.*")],
        )
        if path:
            self._load_file(path)

    def _load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            messagebox.showerror("Open failed", "That file isn't valid UTF-8 text.")
            return
        except OSError as e:
            messagebox.showerror("Open failed", f"Could not open file:\n{e}")
            return
        self.filepath = path
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._dirty = False
        self._update_title()
        self._highlight()
        self.status.config(text=f"Opened {self._short_path(path)}")

    def _confirm_discard(self):
        return messagebox.askyesno("Discard changes?", "You have unsaved changes. Continue anyway?")

    def _quit(self):
        if self._dirty and not self._confirm_discard():
            return
        self.root.destroy()

    def _on_modified(self, event=None):
        self.text.edit_modified(False)
        self._dirty = True
        self._update_title()
        if self._highlight_job:
            self.root.after_cancel(self._highlight_job)
        self._highlight_job = self.root.after(120, self._highlight)

    def _highlight(self):
        t = self.text
        all_tags = ("h1", "h2", "h3", "bold", "italic", "bold_italic", "code_inline",
                    "code_block", "quote", "list_marker", "link", "markup", "hr")
        for tag in all_tags:
            t.tag_remove(tag, "1.0", "end")

        content = t.get("1.0", "end-1c")
        lines = content.split("\n")

        in_code_block = False
        for lineno, line in enumerate(lines, start=1):
            line_start = f"{lineno}.0"
            line_end = f"{lineno}.end"

            fence_match = re.match(r"^\s*```", line)
            if fence_match:
                t.tag_add("code_block", line_start, line_end)
                in_code_block = not in_code_block
                continue
            if in_code_block:
                t.tag_add("code_block", line_start, line_end)
                continue

            h = re.match(r"^(#{1,3})\s+(.*)$", line)
            if h:
                level = len(h.group(1))
                tag = {1: "h1", 2: "h2", 3: "h3"}[level]
                t.tag_add(tag, line_start, line_end)
                t.tag_add("markup", line_start, f"{lineno}.{level + 1}")
                continue

            if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", line):
                t.tag_add("hr", line_start, line_end)
                continue

            bq = re.match(r"^(\s*>+\s?)(.*)$", line)
            if bq:
                t.tag_add("quote", line_start, line_end)
                t.tag_add("markup", line_start, f"{lineno}.{len(bq.group(1))}")

            lm = re.match(r"^(\s*)([-*+]|\d+\.)(\s+)", line)
            if lm:
                start_col = len(lm.group(1))
                end_col = start_col + len(lm.group(2))
                t.tag_add("list_marker", f"{lineno}.{start_col}", f"{lineno}.{end_col}")

            for m in re.finditer(r"`([^`\n]+)`", line):
                t.tag_add("code_inline", f"{lineno}.{m.start()}", f"{lineno}.{m.end()}")

            for m in re.finditer(r"(\*\*\*|___)(.+?)\1", line):
                t.tag_add("bold_italic", f"{lineno}.{m.start()}", f"{lineno}.{m.end()}")

            for m in re.finditer(r"(\*\*|__)(.+?)\1", line):
                t.tag_add("bold", f"{lineno}.{m.start()}", f"{lineno}.{m.end()}")

            for m in re.finditer(r"(?<!\*)\*(?!\*)([^*\n]+?)\*(?!\*)", line):
                t.tag_add("italic", f"{lineno}.{m.start()}", f"{lineno}.{m.end()}")

            for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
                t.tag_add("link", f"{lineno}.{m.start()}", f"{lineno}.{m.end()}")

        self._update_word_count()

    def _update_word_count(self):
        content = self.text.get("1.0", "end-1c")
        words = len(content.split())
        chars = len(content)
        lines = content.count("\n") + 1 if content else 0
        marker = "●" if self._dirty else "○"
        self.status.config(
            text=f"{marker}  {words} words · {chars} chars · {lines} lines"
            f"   |   {len(self.memory_snapshots)} snapshot(s) in memory"
        )

    def _short_path(self, path):
        home = os.path.expanduser("~")
        return path.replace(home, "~") if path.startswith(home) else path

    def _update_title(self):
        name = os.path.basename(self.filepath) if self.filepath else "Untitled.md"
        dirty_flag = " •" if self._dirty else ""
        self.root.title(f"{name}{dirty_flag}")
        self.path_label.config(text=f"{self._short_path(self.filepath) if self.filepath else name}{dirty_flag}")


def main():
    root = tk.Tk()
    initial_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = MarkdownEditor(root, initial_path=initial_path)
    root.mainloop()


if __name__ == "__main__":
    main()