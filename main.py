# Updated main.py
import ttkbootstrap as ttk
from tkinter import messagebox
from core import *

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM Text Editor")
        self.root.geometry("700x650")
        self.user = None
        self.build_login_ui()

    def build_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        ttk.Label(self.root, text="LLM Text Editor", font=("Helvetica", 20)).pack(pady=20)

        self.username_entry = ttk.Entry(self.root, width=30)
        self.username_entry.pack(pady=5)
        self.username_entry.insert(0, "Enter your username")

        self.login_password_entry = ttk.Entry(self.root, width=30, show="*")
        self.login_password_entry.pack(pady=5)
        self.login_password_entry.insert(0, "password")

        ttk.Button(self.root, text="Login", bootstyle="success", command=self.login).pack(pady=5)
        ttk.Button(self.root, text="Register as New User", bootstyle="info", command=self.build_register_ui).pack(pady=5)

    def build_register_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        ttk.Label(self.root, text="Register New User", font=("Helvetica", 16)).pack(pady=20)

        self.new_username = ttk.Entry(self.root, width=30)
        self.new_username.pack(pady=5)
        self.new_username.insert(0, "Choose a username")

        self.password_entry = ttk.Entry(self.root, width=30, show="*")
        self.password_entry.pack(pady=5)
        self.password_entry.insert(0, "password123")

        self.user_type_var = ttk.StringVar()
        self.user_type_combo = ttk.Combobox(self.root, textvariable=self.user_type_var, values=["Free", "Paid", "Super User"])
        self.user_type_combo.pack(pady=5)
        self.user_type_combo.current(0)

        ttk.Button(self.root, text="Register", bootstyle="primary", command=self.register_user).pack(pady=5)
        ttk.Button(self.root, text="Back to Login", command=self.build_login_ui).pack()

    def register_user(self):
        username = self.new_username.get().strip()
        password = self.password_entry.get().strip()
        user_type = self.user_type_var.get().strip()
        if username and password:
            success, msg = add_user(username, user_type, password)
            if success:
                messagebox.showinfo("Success", msg)
                self.build_login_ui()
            else:
                messagebox.showerror("Error", msg)
        else:
            messagebox.showerror("Error", "Username and password required.")

    def login(self):
        username = self.username_entry.get().strip()
        password = self.login_password_entry.get().strip()

        user_doc = get_user(username, password)
        if user_doc == "invalid_password":
            messagebox.showerror("Login Failed", "Incorrect password.")
            return
        elif user_doc == "login_cooldown":
            messagebox.showwarning("Too Soon", "Free users must wait 3 minutes between logins.")
            return
        elif not user_doc:
            messagebox.showerror("Login Failed", "User not found.")
            return

        if user_doc["user_type"] == "Free":
            self.user = FreeUser(user_doc)
        elif user_doc["user_type"] == "Paid":
            self.user = PaidUser(user_doc)
        elif user_doc["user_type"] == "Super":
            self.user = SuperUser(user_doc)

        self.build_editor_ui()

    def build_editor_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        ttk.Label(self.root, text=f"Welcome {self.user.username} ({self.user.type})", font=("Arial", 16)).pack(pady=10)
        self.token_label = ttk.Label(self.root, text=f"Tokens: {self.user.tokens}", bootstyle="info")
        self.token_label.pack(pady=5)

        if self.user.type == "Super":
            ttk.Button(self.root, text="Manage Users", bootstyle="primary", command=self.manage_users).pack(pady=5)
            ttk.Button(self.root, text="Review Complaints", bootstyle="primary", command=self.review_complaints).pack(pady=5)
            return

        self.text_input = ttk.Text(self.root, height=8)
        self.text_input.pack(pady=10)

        ttk.Button(self.root, text="Submit", bootstyle="success", command=self.submit_text).pack(pady=5)
        ttk.Button(self.root, text="LLM Correct", bootstyle="warning", command=self.correct_text).pack(pady=5)
        ttk.Button(self.root, text="Save to File", bootstyle="secondary", command=self.save_text).pack(pady=5)
        ttk.Button(self.root, text="Purchase Tokens", bootstyle="info", command=self.purchase_tokens).pack(pady=5)
        ttk.Button(self.root, text="Logout", bootstyle="danger", command=self.build_login_ui).pack(pady=10)

        self.output_box = ttk.Text(self.root, height=8)
        self.output_box.pack()

    def submit_text(self):
        text = self.text_input.get("1.0", "end").strip()
        result = submit_text(self.user, text)
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", result)
        self.update_tokens()

    def correct_text(self):
        original = self.output_box.get("1.0", "end").strip()
        corrected = llm_correction(original)
        final = apply_correction(self.user, original, corrected)
        self.output_box.delete("1.0", "end")
        self.output_box.insert("end", final)
        self.update_tokens()

    def save_text(self):
        content = self.output_box.get("1.0", "end").strip()
        msg = save_text_file(self.user, content)
        messagebox.showinfo("Save", msg)
        self.update_tokens()

    def purchase_tokens(self):
        amount = 50
        if purchase_tokens(self.user.username, amount):
            self.user.tokens += amount
            messagebox.showinfo("Purchased", f"Added {amount} tokens.")
        else:
            messagebox.showerror("Error", "Token purchase failed.")
        self.update_tokens()

    def update_tokens(self):
        self.token_label.config(text=f"Tokens: {self.user.tokens}")

    def manage_users(self):
        import tkinter.simpledialog as sd
        target = sd.askstring("Suspend/Fine/Terminate", "Enter Paid Username:")
        if not target:
            return
        action = sd.askstring("Action", "Type: suspend, fine, terminate")
        if action == "suspend":
            suspend_user(target)
            messagebox.showinfo("Action", f"{target} suspended.")
        elif action == "fine":
            amount = sd.askinteger("Fine", "Enter token amount to deduct:")
            fine_user(target, amount)
            messagebox.showinfo("Action", f"{amount} tokens deducted from {target}.")
        elif action == "terminate":
            terminate_user(target)
            messagebox.showinfo("Action", f"{target} terminated.")

    def review_complaints(self):
        from tkinter.simpledialog import askstring
        result = handle_pending_complaints()
        if not result:
            messagebox.showinfo("Complaints", "No complaints found.")
            return
        for c in result:
            decision = askstring("Complaint Review", f"Complaint from {c['from']} against {c['to']}\nReason: {c['reason']}\nType approve/deny")
            if decision == "approve":
                fine_user(c['to'], 5)
            elif decision == "deny":
                fine_user(c['from'], 5)
            update_complaint_status(c['_id'], decision)

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = App(root)
    root.mainloop()
