import re
import sys
import os
import smtplib
from email.mime.text import MIMEText
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from env_loader import load_env_file
from database.db_manager import (
    create_user_account,
    generate_reset_code,
    reset_password_with_code,
    verify_admin,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

load_env_file(__file__)


CARD_STYLE = "background-color: white; border-radius: 18px; border: 1px solid #D9D9D9;"
INPUT_STYLE = """
    QLineEdit {
        padding: 12px;
        border: 1px solid #CFCFCF;
        border-radius: 6px;
        color: black;
        background-color: white;
    }
"""
PRIMARY_BUTTON_STYLE = """
    QPushButton {
        background-color: #1F5A37;
        color: white;
        padding: 12px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #18492D; }
"""
LINK_BUTTON_STYLE = """
    QPushButton {
        background: transparent;
        border: none;
        color: #1F5A37;
        font-weight: bold;
        text-align: left;
    }
"""


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_SENDER_EMAIL = os.getenv("SMTP_SENDER_EMAIL", "")
SMTP_SENDER_PASSWORD = os.getenv("SMTP_SENDER_PASSWORD", "")
RESET_CODE_COOLDOWN_SECONDS = 60


def send_reset_email(receiver_email, code):
    if not SMTP_SENDER_EMAIL or not SMTP_SENDER_PASSWORD:
        return False, "Email sender is not configured yet."

    message = MIMEText(
        f"Your CDM Inventory System password reset code is: {code}\n\n"
        "Enter this 6-digit code in the Reset Password form."
    )
    message["Subject"] = "CDM Inventory System Reset Code"
    message["From"] = SMTP_SENDER_EMAIL
    message["To"] = receiver_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_SENDER_EMAIL, SMTP_SENDER_PASSWORD)
            server.send_message(message)
        return True, "Reset code sent successfully."
    except Exception as exc:
        return False, f"Unable to send email: {exc}"


class CreateAccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Account")
        self.setFixedSize(430, 470)
        self.setStyleSheet("background-color: white; color: black;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title = QLabel("Create New Account")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("border: none; color: black; margin-bottom: 8px;")
        layout.addWidget(title)

        self.email = self._build_input(layout, "Email", "Enter email")
        self.password = self._build_input(layout, "Password", "Enter password", password=True)
        self.confirm_password = self._build_input(
            layout, "Confirm Password", "Re-enter password", password=True
        )

        create_btn = QPushButton("CREATE ACCOUNT")
        create_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        create_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        create_btn.clicked.connect(self.handle_create_account)

        layout.addStretch(0)
        layout.addWidget(create_btn)

    def _build_input(self, layout, label_text, placeholder, password=False):
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        label.setStyleSheet("border: none; color: #202020;")
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setStyleSheet(INPUT_STYLE)
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label)
        layout.addWidget(field)
        return field

    def handle_create_account(self):
        email = self.email.text().strip()
        password = self.password.text().strip()
        confirm_password = self.confirm_password.text().strip()

        if not all([email, password, confirm_password]):
            QMessageBox.warning(self, "Missing Information", "Please fill in all fields.")
            return

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return

        password_ok, password_message = self.validate_password(password)
        if not password_ok:
            QMessageBox.warning(self, "Weak Password", password_message)
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return

        username = email
        success, message = create_user_account(username, email, password, role="Admin")
        if not success:
            QMessageBox.warning(self, "Create Account Failed", message)
            return

        QMessageBox.information(self, "Account Created", message)
        self.accept()

    def validate_password(self, password):
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must include at least one uppercase letter."
        if not re.search(r"[a-z]", password):
            return False, "Password must include at least one lowercase letter."
        if not re.search(r"\d", password):
            return False, "Password must include at least one number."
        return True, ""


class ForgotPasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Forgot Password")
        self.setFixedSize(430, 520)
        self.setStyleSheet("background-color: white; color: black;")
        self.generated_code = None
        self.cooldown_seconds_left = 0
        self.cooldown_timer = QTimer(self)
        self.cooldown_timer.timeout.connect(self.update_cooldown)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        title = QLabel("Reset Password")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("border: none; color: black;")

        subtitle = QLabel("Enter your account email to receive a reset code.")
        subtitle.setStyleSheet("border: none; color: #555555;")
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.email = self._build_input(layout, "Email", "Enter email")

        self.send_btn = QPushButton("SEND RESET CODE")
        self.send_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.send_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.send_btn.clicked.connect(self.handle_send_code)
        layout.addWidget(self.send_btn)

        self.reset_code = self._build_input(layout, "Reset Code", "Enter the 6-digit code")
        self.reset_code.setMaxLength(6)
        self.reset_code.textChanged.connect(self.keep_reset_code_numeric)

        self.new_password = self._build_input(layout, "New Password", "Enter new password", password=True)
        self.confirm_password = self._build_input(
            layout, "Confirm New Password", "Re-enter new password", password=True
        )

        update_btn = QPushButton("UPDATE PASSWORD")
        update_btn.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        update_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #B87918;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9A6613; }
            """
        )
        update_btn.clicked.connect(self.handle_update_password)
        layout.addWidget(update_btn)

    def _build_input(self, layout, label_text, placeholder, password=False):
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        label.setStyleSheet("border: none; color: #202020;")
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setStyleSheet(INPUT_STYLE)
        if password:
            field.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(label)
        layout.addWidget(field)
        return field

    def handle_send_code(self):
        email = self.email.text().strip()
        if not email:
            QMessageBox.warning(self, "Missing Email", "Please enter your email address.")
            return

        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
            return

        success, message, code = generate_reset_code(email)
        if not success:
            QMessageBox.warning(self, "Reset Failed", message)
            return

        self.generated_code = code
        email_sent, email_message = send_reset_email(email, code)
        if not email_sent:
            QMessageBox.warning(self, "Email Sending Failed", email_message)
            return

        QMessageBox.information(self, "Reset Code Sent", f"A reset code was sent to {email}.")
        self.reset_code.setFocus()
        self.start_cooldown()

    def handle_update_password(self):
        email = self.email.text().strip()
        code = self.reset_code.text().strip()
        new_password = self.new_password.text().strip()
        confirm_password = self.confirm_password.text().strip()

        if not all([email, code, new_password, confirm_password]):
            QMessageBox.warning(self, "Missing Information", "Please complete all password reset fields.")
            return

        if len(code) != 6 or not code.isdigit():
            QMessageBox.warning(self, "Invalid Code", "Reset code must be exactly 6 digits.")
            return

        password_ok, password_message = self.validate_password(new_password)
        if not password_ok:
            QMessageBox.warning(self, "Weak Password", password_message)
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "Password Mismatch", "Passwords do not match.")
            return

        success, message = reset_password_with_code(email, code, new_password)
        if not success:
            QMessageBox.warning(self, "Update Failed", message)
            return

        QMessageBox.information(self, "Password Updated", message)
        self.accept()

    def keep_reset_code_numeric(self, value):
        digits_only = "".join(ch for ch in value if ch.isdigit())[:6]
        if digits_only != value:
            self.reset_code.blockSignals(True)
            self.reset_code.setText(digits_only)
            self.reset_code.blockSignals(False)

    def validate_password(self, password):
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[A-Z]", password):
            return False, "Password must include at least one uppercase letter."
        if not re.search(r"[a-z]", password):
            return False, "Password must include at least one lowercase letter."
        if not re.search(r"\d", password):
            return False, "Password must include at least one number."
        return True, ""

    def start_cooldown(self):
        self.cooldown_seconds_left = RESET_CODE_COOLDOWN_SECONDS
        self.send_btn.setEnabled(False)
        self.update_cooldown()
        self.cooldown_timer.start(1000)

    def update_cooldown(self):
        if self.cooldown_seconds_left <= 0:
            self.cooldown_timer.stop()
            self.send_btn.setEnabled(True)
            self.send_btn.setText("RESEND RESET CODE")
            return

        self.send_btn.setText(f"RESEND IN {self.cooldown_seconds_left}s")
        self.cooldown_seconds_left -= 1

class AdminLogin(QWidget):
    # UPDATED: This signal now carries a string (the user's role: 'Admin' or 'Staff')
    login_success = pyqtSignal(str, str) 

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CDM PSO - Admin Login")
        self.setGeometry(100, 100, 1000, 600) 
        self.setStyleSheet("background-color: #F5F5F5;") 

        # Main Layout
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Container Frame (The Login Card)
        self.card = QFrame()
        self.card.setFixedSize(380, 520)
        self.card.setStyleSheet(CARD_STYLE)
        
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(30, 36, 30, 34)
        self.card_layout.setSpacing(16)

        # Title
        self.title = QLabel("ADMIN LOGIN")
        self.title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        self.title.setStyleSheet("color: #1B4D2E; border: none;") 
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.subtitle = QLabel("Sign in with your email.")
        self.subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle.setStyleSheet("color: #6B6B6B; border: none;")

        # Username Input
        self.username = QLineEdit()
        self.username.setPlaceholderText("Email")
        self.username.setStyleSheet(INPUT_STYLE)

        # Password Input
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setStyleSheet(INPUT_STYLE)

        # Login Button
        self.login_btn = QPushButton("LOGIN")
        self.login_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.login_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.login_btn.clicked.connect(self.check_login)

        links_row = QHBoxLayout()
        self.forgot_password_btn = QPushButton("Forgot Password?")
        self.forgot_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.forgot_password_btn.setStyleSheet(
            LINK_BUTTON_STYLE.replace("#1F5A37", "#B87918")
        )
        self.forgot_password_btn.clicked.connect(self.open_forgot_password)
        links_row.addStretch()
        links_row.addWidget(self.forgot_password_btn)
        links_row.addStretch()

        # Status Message
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red; border: none;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_layout.addWidget(self.title)
        self.card_layout.addWidget(self.subtitle)
        self.card_layout.addSpacing(12)
        self.card_layout.addWidget(self.username)
        self.card_layout.addWidget(self.password)
        self.card_layout.addWidget(self.login_btn)
        self.card_layout.addLayout(links_row)
        self.card_layout.addWidget(self.status_label)
        self.card_layout.addStretch()

        self.layout.addWidget(self.card)
        self.setLayout(self.layout)

    def check_login(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        
        # UPDATED: verify_admin now returns a tuple (success, role)
        # Ensure your database/db_manager.py has been updated to return both!
        success, role, account_username = verify_admin(username, password)
        
        if success:
            self.status_label.setStyleSheet("color: green; border: none;")
            self.status_label.setText("Login Successful!")
            # UPDATED: Emit the role so the Dashboard knows how to restrict access
            self.login_success.emit(role, account_username) 
        else:
            self.status_label.setStyleSheet("color: red; border: none;")
            self.status_label.setText("Invalid Credentials")

    def open_forgot_password(self):
        dialog = ForgotPasswordDialog(self)
        dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminLogin()
    window.show()
    sys.exit(app.exec())




