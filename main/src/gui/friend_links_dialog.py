"""Friend links dialog"""
import customtkinter as ctk
import webbrowser
from tkinter import messagebox, Listbox
from core.models import FriendLink


class FriendLinksDialog(ctk.CTkToplevel):
    """Dialog for displaying and managing friend links"""

    def __init__(self, parent, current_links: list[FriendLink], callback):
        super().__init__(parent)
        self.callback = callback
        self.links = current_links.copy()

        self.title("友情链接")
        self.geometry("500x400")
        self.resizable(False, False)
        self.grab_set()

        self.create_widgets()
        self.update_list()

    def create_widgets(self):
        """Create dialog widgets"""
        ctk.CTkLabel(
            self,
            text="友情链接",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=(10, 5))

        # Links listbox - use standard Listbox
        listbox_frame = ctk.CTkFrame(self, fg_color="transparent")
        listbox_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self.listbox = Listbox(
            listbox_frame,
            bg="#333333",
            fg="white",
            selectbackground="#1f538d",
            selectforeground="white"
        )
        self.listbox.pack(fill="both", expand=True)
        self.listbox.bind("<Double-Button-1>", self.open_selected)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        open_btn = ctk.CTkButton(
            btn_frame,
            text="打开链接",
            command=self.open_selected,
            width=90
        )
        open_btn.pack(side="left", padx=5)

        add_btn = ctk.CTkButton(
            btn_frame,
            text="添加",
            command=self.add_link,
            width=90
        )
        add_btn.pack(side="left", padx=5)

        delete_btn = ctk.CTkButton(
            btn_frame,
            text="删除",
            command=self.delete_selected,
            width=90,
            fg_color="#cc3333",
            hover_color="#aa2222"
        )
        delete_btn.pack(side="left", padx=5)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            command=self.save,
            width=90
        )
        save_btn.pack(side="right", padx=5)

    def update_list(self):
        """Update the listbox"""
        self.listbox.delete(0, ctk.END)
        for link in self.links:
            self.listbox.insert(ctk.END, f"{link.text} - {link.url}")

    def get_selected(self):
        """Get selected link"""
        selection = self.listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        return self.links[index]

    def open_selected(self, event=None):
        """Open the selected link in browser"""
        link = self.get_selected()
        if link:
            webbrowser.open(link.url)

    def add_link(self):
        """Open dialog to add new link"""
        dialog = AddLinkDialog(self.winfo_toplevel(), self.on_add_done)

    def on_add_done(self, text, url):
        """Callback after adding link"""
        try:
            new_link = FriendLink(text, url)
            self.links.append(new_link)
            self.update_list()
        except ValueError as e:
            messagebox.showerror("错误", str(e))

    def delete_selected(self):
        """Delete selected link"""
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        del self.links[index]
        self.update_list()

    def save(self):
        """Save changes and close"""
        self.callback(self.links)
        self.destroy()


class AddLinkDialog(ctk.CTkToplevel):
    """Dialog to add a new friend link"""

    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback

        self.title("添加友情链接")
        self.geometry("400x200")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text="文字说明",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(20, 5))
        self.text_entry = ctk.CTkEntry(self, width=300)
        self.text_entry.pack(pady=5)

        ctk.CTkLabel(
            self,
            text="链接地址",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(10, 5))
        self.url_entry = ctk.CTkEntry(self, width=300)
        self.url_entry.pack(pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="确定",
            command=self.confirm,
            width=80
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            command=self.destroy,
            width=80,
            fg_color="#888888",
            hover_color="#666666"
        ).pack(side="left", padx=5)

    def confirm(self):
        """Confirm and add link"""
        text = self.text_entry.get().strip()
        url = self.url_entry.get().strip()
        self.callback(text, url)
        self.destroy()
