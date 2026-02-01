import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import paramiko
from scp import SCPClient
import threading
import os
import sys

class SCPTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple SCP Transfer Tool")
        self.root.geometry("500x650")
        self.root.resizable(False, False)

        # Style configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # --- Variables ---
        self.host_var = tk.StringVar()
        self.user_var = tk.StringVar()
        self.pass_var = tk.StringVar()
        self.port_var = tk.StringVar(value="22")
        
        self.transfer_mode = tk.StringVar(value="upload") # upload or download
        self.content_type = tk.StringVar(value="file")    # file or folder
        
        self.local_path_var = tk.StringVar()
        self.remote_path_var = tk.StringVar(value="~/") # Default to home dir
        
        self.status_var = tk.StringVar(value="Ready")
        self.progress_val = tk.DoubleVar(value=0)

        self._create_widgets()

    def _create_widgets(self):
        # --- Connection Details Frame ---
        conn_frame = ttk.LabelFrame(self.root, text="Remote Connection Details", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)

        # Host
        ttk.Label(conn_frame, text="Host IP:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(conn_frame, textvariable=self.host_var).grid(row=0, column=1, sticky="ew", pady=2)
        
        # Port
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=2, sticky="e", pady=2, padx=(5,2))
        ttk.Entry(conn_frame, textvariable=self.port_var, width=5).grid(row=0, column=3, sticky="w", pady=2)

        # User
        ttk.Label(conn_frame, text="Username:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(conn_frame, textvariable=self.user_var).grid(row=1, column=1, columnspan=3, sticky="ew", pady=2)

        # Password
        ttk.Label(conn_frame, text="Password:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(conn_frame, textvariable=self.pass_var, show="*").grid(row=2, column=1, columnspan=3, sticky="ew", pady=2)
        
        conn_frame.columnconfigure(1, weight=1)

        # --- Settings Frame ---
        settings_frame = ttk.LabelFrame(self.root, text="Transfer Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)

        # Direction
        ttk.Label(settings_frame, text="Direction:").grid(row=0, column=0, sticky="w")
        radio_frame_dir = ttk.Frame(settings_frame)
        radio_frame_dir.grid(row=0, column=1, sticky="w", pady=2)
        ttk.Radiobutton(radio_frame_dir, text="Upload (Send to Remote)", variable=self.transfer_mode, value="upload", command=self._update_labels).pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame_dir, text="Download (Get from Remote)", variable=self.transfer_mode, value="download", command=self._update_labels).pack(side="left", padx=5)

        # Content Type
        ttk.Label(settings_frame, text="Content:").grid(row=1, column=0, sticky="w")
        radio_frame_type = ttk.Frame(settings_frame)
        radio_frame_type.grid(row=1, column=1, sticky="w", pady=2)
        ttk.Radiobutton(radio_frame_type, text="Single File", variable=self.content_type, value="file", command=self._update_labels).pack(side="left", padx=5)
        ttk.Radiobutton(radio_frame_type, text="Folder", variable=self.content_type, value="folder", command=self._update_labels).pack(side="left", padx=5)

        # --- Path Selection Frame ---
        path_frame = ttk.LabelFrame(self.root, text="Paths", padding=10)
        path_frame.pack(fill="x", padx=10, pady=5)

        # Local Path
        self.lbl_local = ttk.Label(path_frame, text="Local Path:")
        self.lbl_local.grid(row=0, column=0, sticky="w", pady=2)
        
        local_entry_frame = ttk.Frame(path_frame)
        local_entry_frame.grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Entry(local_entry_frame, textvariable=self.local_path_var).pack(side="left", fill="x", expand=True)
        self.btn_browse = ttk.Button(local_entry_frame, text="Browse", command=self._browse_local)
        self.btn_browse.pack(side="right", padx=(5, 0))

        # Remote Path
        self.lbl_remote = ttk.Label(path_frame, text="Remote Dest:")
        self.lbl_remote.grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(path_frame, textvariable=self.remote_path_var).grid(row=1, column=1, sticky="ew", pady=2)
        
        path_frame.columnconfigure(1, weight=1)

        # --- Action ---
        self.btn_action = ttk.Button(self.root, text="Start Transfer", command=self._start_thread)
        self.btn_action.pack(fill="x", padx=20, pady=15)

        # --- Status & Log ---
        log_frame = ttk.LabelFrame(self.root, text="Status", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ttk.Label(log_frame, textvariable=self.status_var, foreground="blue").pack(anchor="w")
        
        self.progress = ttk.Progressbar(log_frame, orient="horizontal", mode="determinate", variable=self.progress_val)
        self.progress.pack(fill="x", pady=5)

        self.log_text = tk.Text(log_frame, height=8, width=50, state="disabled", font=("Consolas", 9))
        self.log_text.pack(fill="both", expand=True)

    def _update_labels(self):
        """Updates labels and placeholders based on mode selection."""
        mode = self.transfer_mode.get()
        # Visual cues to help user understand what goes where
        if mode == "upload":
            self.lbl_local.config(text="File/Folder to Send:")
            self.lbl_remote.config(text="Save at Remote Path:")
            self.btn_browse.config(state="normal")
            self.btn_action.config(text=f"Upload {self.content_type.get().capitalize()}")
        else:
            self.lbl_local.config(text="Save to Local Folder:")
            self.lbl_remote.config(text="Remote File/Folder Path:")
            self.btn_browse.config(text="Browse Folder") # Always saving to a folder when downloading
            self.btn_action.config(text=f"Download {self.content_type.get().capitalize()}")

    def _browse_local(self):
        """Opens file/folder dialog based on current settings."""
        mode = self.transfer_mode.get()
        ctype = self.content_type.get()
        
        path = ""
        if mode == "upload":
            # If uploading, we pick what we want to send
            if ctype == "file":
                path = filedialog.askopenfilename()
            else:
                path = filedialog.askdirectory()
        else:
            # If downloading, we pick where to save it (directory)
            path = filedialog.askdirectory()

        if path:
            self.local_path_var.set(path)

    def _log(self, message):
        """Thread-safe logging to text area."""
        def _write():
            self.log_text.config(state="normal")
            self.log_text.insert("end", message + "\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.root.after(0, _write)

    def _update_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def _progress_callback(self, filename, size, sent):
        """Callback from SCPClient to update progress bar."""
        try:
            filename = filename.decode()
        except:
            pass # filename might already be string
            
        percent = (sent / size) * 100
        self.root.after(0, lambda: self.progress_val.set(percent))
        self.root.after(0, lambda: self.status_var.set(f"Transferring: {filename} ({int(percent)}%)"))

    def _start_thread(self):
        """Starts the transfer in a separate thread to keep GUI responsive."""
        if not self.host_var.get() or not self.user_var.get() or not self.pass_var.get():
            messagebox.showerror("Error", "Please fill in Host, Username, and Password.")
            return
            
        if not self.local_path_var.get() or not self.remote_path_var.get():
            messagebox.showerror("Error", "Please specify both local and remote paths.")
            return

        self.btn_action.config(state="disabled")
        t = threading.Thread(target=self._perform_transfer)
        t.daemon = True
        t.start()

    def _perform_transfer(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            self._log(f"Connecting to {self.host_var.get()}...")
            ssh.connect(
                self.host_var.get(), 
                port=int(self.port_var.get()), 
                username=self.user_var.get(), 
                password=self.pass_var.get(),
                timeout=10
            )
            self._log("SSH Connection successful.")

            mode = self.transfer_mode.get()
            ctype = self.content_type.get()
            local_path = self.local_path_var.get()
            remote_path = self.remote_path_var.get()

            # Initialize SCP
            with SCPClient(ssh.get_transport(), progress=self._progress_callback) as scp:
                if mode == "upload":
                    self._log(f"Uploading {local_path} -> {remote_path}")
                    recursive = (ctype == "folder")
                    scp.put(local_path, remote_path, recursive=recursive)
                
                else: # download
                    self._log(f"Downloading {remote_path} -> {local_path}")
                    recursive = (ctype == "folder")
                    scp.get(remote_path, local_path, recursive=recursive)

            self._log("Transfer Complete!")
            self._update_status("Transfer Complete")
            self.root.after(0, lambda: messagebox.showinfo("Success", "File transfer completed successfully."))

        except paramiko.AuthenticationException:
            self._log("Error: Authentication failed.")
            self.root.after(0, lambda: messagebox.showerror("Auth Error", "Authentication failed. Check username/password."))
        except Exception as e:
            self._log(f"Error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            ssh.close()
            self.root.after(0, lambda: self.btn_action.config(state="normal"))
            self.root.after(0, lambda: self.progress_val.set(0))

if __name__ == "__main__":
    root = tk.Tk()
    app = SCPTransferApp(root)
    root.mainloop()
