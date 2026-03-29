import sys
from env_loader import load_env_file
from database.db_manager import initialize_db
from PyQt6.QtWidgets import QApplication
from Admin_Dashboard.login import AdminLogin
from Admin_Dashboard.dashboard import AdminDashboard


class AdminController:
    def __init__(self):
        # We start by only creating the login window
        self.login_window = AdminLogin()
        self.dashboard_window = None # We wait for a successful login to create this

        # Connect signals
        # Note: login_success now receives a 'role' string from login.py
        self.login_window.login_success.connect(self.switch_to_dashboard)

    def start(self):
        """Launches the application at the Login screen."""
        self.login_window.show()

    def switch_to_dashboard(self, role, username):
        """Creates the dashboard with the correct role and shows it."""
        # Hide login
        self.login_window.hide()
        
        # Create the dashboard and pass the role ('Admin' or 'Staff')
        self.dashboard_window = AdminDashboard(user_role=role, current_username=username)
        
        # Connect the logout signal for this specific dashboard instance
        self.dashboard_window.logout_requested.connect(self.switch_to_login)
        
        self.dashboard_window.show()
        self.dashboard_window.change_page(0)

    def switch_to_login(self):
        """Handles logout and security cleanup."""
        if self.dashboard_window:
            self.dashboard_window.hide()
            # We "delete" the dashboard instance on logout to ensure 
            # the next user gets a fresh permission check
            self.dashboard_window = None 
        
        # Cleanup login fields
        self.login_window.username.clear()
        self.login_window.password.clear()
        self.login_window.status_label.clear()
        
        self.login_window.show()


if __name__ == "__main__":
    load_env_file(__file__)
    app = QApplication(sys.argv)
    
    # Setup the SQLite Database
    initialize_db() 
    
    controller = AdminController()
    controller.start()
    
    sys.exit(app.exec())
