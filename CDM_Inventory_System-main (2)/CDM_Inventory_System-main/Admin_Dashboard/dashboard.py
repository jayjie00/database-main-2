import sys
import os
# This adds the parent directory to your path so it can find the 'database' folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import re

from PyQt6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
                             QFrame, QStackedWidget, QLineEdit, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QComboBox, QFileDialog, QDialog) 
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, pyqtSignal

# Import database functions
from database.db_manager import (get_all_items, add_inventory_item, delete_inventory_item, 
                                 update_inventory_item, get_all_requests, update_request_status,
                                 add_user, update_admin_credentials, deduct_stock)

# Ensure you have added return_item to your db_manager.py
try:
    from database.db_manager import return_item
except ImportError:
    pass

class EditItemDialog(QDialog):
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Item")
        self.setFixedWidth(300)
        self.setStyleSheet("background-color: white; color: black;")
        layout = QVBoxLayout(self)

        self.name_in = QLineEdit(str(item_data[1]))
        self.brand_in = QLineEdit(str(item_data[2]))
        self.qty_in = QLineEdit(str(item_data[3]))
        self.cat_in = QComboBox()
        self.cat_in.addItems(["Equipment", "Sound", "Supplies", "Printing"])
        self.cat_in.setCurrentText(str(item_data[5]))

        for w in [self.name_in, self.brand_in, self.qty_in, self.cat_in]:
            w.setStyleSheet("border: 1px solid #CCC; padding: 5px; color: black; background: white;")
            layout.addWidget(w)

        save_btn = QPushButton("SAVE CHANGES")
        save_btn.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold; padding: 10px;")
        save_btn.clicked.connect(self.accept)
        layout.addWidget(save_btn)

    def get_values(self):
        return self.name_in.text(), self.brand_in.text(), self.qty_in.text(), self.cat_in.currentText()

class ClickableCard(QFrame):
    clicked = pyqtSignal()
    def __init__(self, title, color):
        super().__init__()
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background-color: #E0E4D9; border-radius: 15px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label_header = QLabel(title)
        label_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_header.setFixedHeight(50)
        label_header.setStyleSheet(f"background-color: {color}; color: white; border-top-left-radius: 15px; border-top-right-radius: 15px;")
        label_header.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        content_label = QLabel("Click to View Details")
        content_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_label.setStyleSheet("color: #555; padding: 20px;")
        layout.addWidget(label_header)
        layout.addWidget(content_label)

    def mousePressEvent(self, event):
        self.clicked.emit()

class AdminDashboard(QWidget):
    logout_requested = pyqtSignal()

    def __init__(self, user_role="Admin", current_username=""): 
        super().__init__()
        self.user_role = user_role 
        self.current_username = current_username
        self.is_refreshing = False
        self.selected_image_path = ""
        self.setWindowTitle("CDM PSO Admin Dashboard")
        self.setGeometry(100, 100, 1100, 650)
        self.setStyleSheet("background-color: white;")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setup_top_bar()
        self.pages = QStackedWidget()
        
        self.menu_page = self.create_menu_page()
        self.inventory_page = self.create_inventory_page()
        self.queue_page = self.create_queue_page()
        self.history_page = self.create_history_page() 
        self.returns_page = self.create_returns_page() 
        self.user_mgmt_page = self.create_user_mgmt_page()
        
        self.pages.addWidget(self.menu_page)      
        self.pages.addWidget(self.inventory_page) 
        self.pages.addWidget(self.queue_page)     
        self.pages.addWidget(self.history_page)   
        self.pages.addWidget(self.returns_page)   
        self.pages.addWidget(self.user_mgmt_page) 

        self.main_layout.addWidget(self.top_bar)
        self.main_layout.addWidget(self.pages)

    def setup_top_bar(self):
        self.top_bar = QFrame()
        self.top_bar.setFixedHeight(80)
        self.top_bar.setStyleSheet("background-color: #1B4D2E;")
        lay = QHBoxLayout(self.top_bar)
        self.back_btn = QPushButton("BACK")
        self.back_btn.setVisible(False)
        self.back_btn.setStyleSheet("color: white; border: 1px solid white; padding: 8px; font-weight: bold;")
        self.back_btn.clicked.connect(lambda: self.change_page(0))
        
        self.header = QLabel("ADMIN DASHBOARD")
        self.header.setStyleSheet("color: white; font-weight: bold; font-size: 20px;")
        
        self.logout_btn = QPushButton("LOGOUT")
        self.logout_btn.setStyleSheet("background-color: #A32A2A; color: white; padding: 8px 15px; font-weight: bold;")
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        
        lay.addWidget(self.back_btn); lay.addSpacing(20); lay.addWidget(self.header); lay.addStretch(); lay.addWidget(self.logout_btn)

    def create_menu_page(self):
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(50, 40, 50, 40)
        lay.setSpacing(20)

        self.card_queue = ClickableCard("REQUEST QUEUES", "#2D5A27")
        self.card_inventory = ClickableCard("STOCKS & INVENTORY", "#2D5A27")
        self.card_history = ClickableCard("TRANSACTION HISTORY", "#2D5A27")
        self.card_returns = ClickableCard("EQUIPMENT RETURNS", "#2D5A27") 
        self.card_users = ClickableCard("STAFF MANAGEMENT", "#1B4D2E")

        if self.user_role == "Staff":
            self.card_inventory.setVisible(False)
            self.card_users.setVisible(False)

        self.card_inventory.clicked.connect(lambda: self.change_page(1))
        self.card_queue.clicked.connect(lambda: self.change_page(2))
        self.card_history.clicked.connect(lambda: self.change_page(3))
        self.card_returns.clicked.connect(lambda: self.change_page(4))
        self.card_users.clicked.connect(lambda: self.change_page(5))

        for card in [self.card_queue, self.card_inventory, self.card_history, self.card_returns, self.card_users]:
            card.setFixedSize(200, 250)
            lay.addWidget(card)
        return page

    def create_inventory_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(30, 20, 30, 30)
        self.name_in = QLineEdit(placeholderText="Item Name"); self.brand_in = QLineEdit(placeholderText="Brand") 
        self.qty_in = QLineEdit(placeholderText="Qty"); self.qty_in.setFixedWidth(50)
        self.cat_in = QComboBox(); self.cat_in.addItems(["Equipment", "Sound", "Supplies", "Printing"])
        self.img_btn = QPushButton("IMAGE"); self.img_btn.clicked.connect(self.browse_image)
        add_btn = QPushButton("ADD ITEM"); add_btn.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold;"); add_btn.clicked.connect(self.handle_add)
        input_row = QHBoxLayout()
        for w in [self.name_in, self.brand_in, self.qty_in, self.cat_in, self.img_btn, add_btn]:
            w.setStyleSheet("color: black; background-color: white; border: 1px solid #CCC; padding: 5px;"); input_row.addWidget(w)
        self.inv_table = QTableWidget(0, 7); self.inv_table.setHorizontalHeaderLabels(["ID", "Name", "Brand", "Qty", "Status", "Category", "Action"])
        self.inv_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.inv_table.setStyleSheet("QTableWidget { color: black; background-color: white; } QHeaderView::section { color: black; }")
        lay.addLayout(input_row); lay.addWidget(self.inv_table); return page

    def browse_image(self):
        file_filter = "Image Files (*.png *.jpg *.jpeg *.bmp)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Item Image", "", file_filter)
        if path:
            self.selected_image_path = path; self.img_btn.setText("SET")
            self.img_btn.setStyleSheet("background-color: #4B8B3B; color: white; font-weight: bold;")

    def handle_add(self):
        name, brand, qty = self.name_in.text().strip(), self.brand_in.text().strip(), self.qty_in.text().strip()
        if name and qty.isdigit():
            add_inventory_item(name, brand, int(qty), self.cat_in.currentText(), self.selected_image_path)
            self.name_in.clear(); self.brand_in.clear(); self.qty_in.clear(); self.selected_image_path = ""; self.img_btn.setText("📷 IMAGE")
            self.refresh_table()
        else: QMessageBox.warning(self, "Error", "Invalid inputs.")

    def refresh_table(self):
        self.is_refreshing = True; self.inv_table.setRowCount(0); items = get_all_items()
        for idx, data in enumerate(items):
            self.inv_table.insertRow(idx)
            for c in range(6):
                it = QTableWidgetItem(str(data[c])); it.setForeground(Qt.GlobalColor.black); self.inv_table.setItem(idx, c, it)
            
            btns_widget = QWidget(); btns_layout = QHBoxLayout(btns_widget); btns_layout.setContentsMargins(2, 2, 2, 2)
            edit_btn = QPushButton("EDIT"); edit_btn.setStyleSheet("background-color: #2D5A27; color: white; font-weight: bold;")
            edit_btn.clicked.connect(lambda ch, d=data: self.handle_edit(d))
            del_btn = QPushButton("DELETE"); del_btn.setStyleSheet("background-color: #A32A2A; color: white; font-weight: bold;")
            del_btn.clicked.connect(lambda ch, id=data[0]: (delete_inventory_item(id), self.refresh_table()))
            btns_layout.addWidget(edit_btn); btns_layout.addWidget(del_btn)
            self.inv_table.setCellWidget(idx, 6, btns_widget)
        self.is_refreshing = False

    def handle_edit(self, item_data):
        dialog = EditItemDialog(item_data, self)
        if dialog.exec():
            name, brand, qty, cat = dialog.get_values()
            if name and qty.isdigit():
                update_inventory_item(item_data[0], name, brand, int(qty), cat, item_data[6])
                self.refresh_table()
            else: QMessageBox.warning(self, "Error", "Invalid inputs.")

    def create_queue_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(30, 20, 30, 30)
        title = QLabel("PENDING REQUESTS"); title.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        self.que_table = QTableWidget(0, 5); self.que_table.setHorizontalHeaderLabels(["ID", "Student", "Items", "Purpose", "Action"])
        self.que_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.que_table.setStyleSheet("QTableWidget { color: black; background-color: white; } QHeaderView::section { color: black; }")
        ref = QPushButton("REFRESH QUEUE"); ref.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold; padding: 10px;"); ref.clicked.connect(self.refresh_queue)
        lay.addWidget(title); lay.addWidget(ref); lay.addWidget(self.que_table); return page

    def refresh_queue(self):
        self.que_table.setRowCount(0); reqs = get_all_requests()
        for data in reqs:
            if data[4] != 'PENDING': continue
            row = self.que_table.rowCount(); self.que_table.insertRow(row)
            def make_black_item(text):
                it = QTableWidgetItem(str(text)); it.setForeground(Qt.GlobalColor.black); return it
            self.que_table.setItem(row, 0, make_black_item(data[0])); self.que_table.setItem(row, 1, make_black_item(data[1]))
            items_dict = json.loads(data[2]); txt = ", ".join([f"{n} (x{q})" for n, q in items_dict.items()])
            self.que_table.setItem(row, 2, make_black_item(txt)); self.que_table.setItem(row, 3, make_black_item(data[3]))
            btns = QWidget(); b_lay = QHBoxLayout(btns); b_lay.setContentsMargins(2,2,2,2)
            app = QPushButton("APPROVE"); rej = QPushButton("REJECT")
            app.setStyleSheet("background-color: green; color: white; font-weight: bold;"); rej.setStyleSheet("background-color: red; color: white; font-weight: bold;")
            app.clicked.connect(lambda ch, id=data[0]: self.handle_update_request(id, "APPROVED"))
            rej.clicked.connect(lambda ch, id=data[0]: self.handle_update_request(id, "REJECTED"))
            b_lay.addWidget(app); b_lay.addWidget(rej); self.que_table.setCellWidget(row, 4, btns)

    def handle_update_request(self, rid, status):
        update_request_status(rid, status, self.current_username)
        if status == "APPROVED":
            reqs = get_all_requests()
            this_req = next((r for r in reqs if r[0] == rid), None)
            if this_req:
                items_dict = json.loads(this_req[2])
                for item_name, qty in items_dict.items():
                    deduct_stock(item_name, qty)
            msg = QMessageBox(self); msg.setText(f"Request #{rid} Approved."); msg.setStyleSheet("QLabel{ color: black; }"); msg.exec()
        self.refresh_queue(); self.refresh_history(); self.refresh_returns()

    def create_history_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(30, 20, 30, 30)
        title = QLabel("TRANSACTION HISTORY"); title.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        self.hist_table = QTableWidget(0, 8); self.hist_table.setHorizontalHeaderLabels(["ID", "Student", "Items", "Purpose", "Status", "Date", "Approved By", "Returned By"])
        self.hist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hist_table.setStyleSheet("QTableWidget { color: black; background-color: white; } QHeaderView::section { color: black; }")
        ref = QPushButton("REFRESH HISTORY"); ref.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold; padding: 10px;"); ref.clicked.connect(self.refresh_history)
        lay.addWidget(title); lay.addWidget(ref); lay.addWidget(self.hist_table); return page

    def refresh_history(self):
        self.hist_table.setRowCount(0); reqs = get_all_requests()
        for data in reqs:
            if data[4] == 'PENDING': continue
            row = self.hist_table.rowCount(); self.hist_table.insertRow(row)
            def make_item(text, color=Qt.GlobalColor.black):
                it = QTableWidgetItem(str(text)); it.setForeground(color); return it
            self.hist_table.setItem(row, 0, make_item(data[0])); self.hist_table.setItem(row, 1, make_item(data[1]))
            items_dict = json.loads(data[2]); txt = ", ".join([f"{n} (x{q})" for n, q in items_dict.items()])
            self.hist_table.setItem(row, 2, make_item(txt)); self.hist_table.setItem(row, 3, make_item(data[3]))
            st_color = Qt.GlobalColor.darkGreen if data[4] == "APPROVED" else Qt.GlobalColor.red
            if data[4] == "RETURNED": st_color = Qt.GlobalColor.blue
            self.hist_table.setItem(row, 4, make_item(data[4], st_color)); self.hist_table.setItem(row, 5, make_item(data[5]))
            self.hist_table.setItem(row, 6, make_item(data[6] or ""))
            self.hist_table.setItem(row, 7, make_item(data[7] or ""))

    def create_returns_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(30, 20, 30, 30)
        title = QLabel("PENDING RETURNS (Equipment & Sound)"); title.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        self.ret_table = QTableWidget(0, 5); self.ret_table.setHorizontalHeaderLabels(["ID", "Student", "Items", "Status", "Action"])
        self.ret_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ret_table.setStyleSheet("QTableWidget { color: black; background-color: white; } QHeaderView::section { color: black; }")
        ref = QPushButton("REFRESH RETURNS"); ref.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold; padding: 10px;"); ref.clicked.connect(self.refresh_returns)
        lay.addWidget(title); lay.addWidget(ref); lay.addWidget(self.ret_table); return page

    def refresh_returns(self):
        self.ret_table.setRowCount(0); reqs = get_all_requests(); inventory_items = get_all_items()
        item_categories = {item[1]: item[5] for item in inventory_items}
        for data in reqs:
            if data[4] != "APPROVED": continue
            items_dict = json.loads(data[2]); needs_return = False
            for item_name in items_dict.keys():
                category = item_categories.get(item_name, "")
                if category in ["Equipment", "Sound"]: needs_return = True; break
            if not needs_return: continue
            row = self.ret_table.rowCount(); self.ret_table.insertRow(row)
            def make_item(text):
                it = QTableWidgetItem(str(text)); it.setForeground(Qt.GlobalColor.black); return it
            self.ret_table.setItem(row, 0, make_item(data[0])); self.ret_table.setItem(row, 1, make_item(data[1]))
            txt = ", ".join([f"{n} (x{q})" for n, q in items_dict.items()])
            self.ret_table.setItem(row, 2, make_item(txt)); self.ret_table.setItem(row, 3, make_item("BORROWED"))
            btn = QPushButton("MARK AS RETURNED"); btn.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold;")
            btn.clicked.connect(lambda ch, r_id=data[0], items=items_dict: self.handle_return(r_id, items))
            self.ret_table.setCellWidget(row, 4, btn)

    def handle_return(self, rid, items_dict):
        from database.db_manager import return_item, get_all_items
        inventory_items = get_all_items(); item_categories = {item[1]: item[5] for item in inventory_items}
        update_request_status(rid, "RETURNED", self.current_username)
        for name, qty in items_dict.items():
            category = item_categories.get(name, "")
            if category in ["Equipment", "Sound"]: return_item(name, qty)
        QMessageBox.information(self, "Success", f"Request #{rid} items returned."); self.refresh_returns(); self.refresh_table(); self.refresh_history()

    def create_user_mgmt_page(self):
        page = QWidget()
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(30, 20, 30, 30)

        # --- TOP SECTION: Account Management ---
        input_row = QHBoxLayout()
        
        # Admin Update Box
        admin_frame = QFrame()
        admin_frame.setStyleSheet("background-color: #F4F6F1; border-radius: 10px; border: 1px solid #1B4D2E; color: black;")
        admin_lay = QVBoxLayout(admin_frame)
        self.admin_user_in = QLineEdit(placeholderText="Username")
        self.admin_email_in = QLineEdit(placeholderText="Email")
        self.admin_pass_in = QLineEdit(placeholderText="New Admin Pass")
        self.admin_pass_in.setEchoMode(QLineEdit.EchoMode.Password)
        update_admin_btn = QPushButton("UPDATE ADMIN")
        update_admin_btn.setStyleSheet("background-color: #1B4D2E; color: white; font-weight: bold;")
        update_admin_btn.clicked.connect(self.handle_update_admin)
        for w in [self.admin_user_in, self.admin_email_in, self.admin_pass_in]:
            w.setStyleSheet("color: black; background: white; padding: 5px;")
        admin_lay.addWidget(QLabel("RENEW ADMIN CREDENTIALS")); admin_lay.addWidget(self.admin_user_in); admin_lay.addWidget(self.admin_email_in); admin_lay.addWidget(self.admin_pass_in); admin_lay.addWidget(update_admin_btn)

        # Staff Creation Box
        staff_frame = QFrame()
        staff_frame.setStyleSheet("background-color: #E0E4D9; border-radius: 10px; border: 1px solid #1B4D2E; color: black;")
        staff_lay = QVBoxLayout(staff_frame)
        self.new_staff_user = QLineEdit(placeholderText="Username")
        self.new_staff_email = QLineEdit(placeholderText="Email")
        self.new_staff_pass = QLineEdit(placeholderText="Password")
        self.new_staff_pass.setEchoMode(QLineEdit.EchoMode.Password)
        for w in [self.new_staff_user, self.new_staff_email, self.new_staff_pass]:
            w.setStyleSheet("color: black; background: white; padding: 5px;")
        add_btn = QPushButton("ADD STAFF")
        add_btn.setStyleSheet("background-color: #2D5A27; color: white; font-weight: bold;")
        add_btn.clicked.connect(self.handle_add_staff)
        staff_lay.addWidget(QLabel("CREATE NEW STAFF")); staff_lay.addWidget(self.new_staff_user); staff_lay.addWidget(self.new_staff_email); staff_lay.addWidget(self.new_staff_pass); staff_lay.addWidget(add_btn)
        
        input_row.addWidget(admin_frame)
        input_row.addWidget(staff_frame)
        main_layout.addLayout(input_row)

        # --- BOTTOM SECTION: User List Table ---
        table_title = QLabel("MANAGED ACCOUNTS")
        table_title.setStyleSheet("font-size: 18px; font-weight: bold; color: black; margin-top: 20px;")
        main_layout.addWidget(table_title)

        self.user_table = QTableWidget(0, 5)
        self.user_table.setHorizontalHeaderLabels(["ID", "Username", "Email", "Role", "Actions"])
        self.user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.user_table.setStyleSheet("QTableWidget { color: black; background-color: white; }")
        
        main_layout.addWidget(self.user_table)
        self.refresh_user_table()
        return page

    def refresh_user_table(self):
        from database.db_manager import get_all_users
        self.user_table.setRowCount(0)
        try:
            users = get_all_users()
            for idx, user in enumerate(users):
                self.user_table.insertRow(idx)
                for c in range(4):
                    it = QTableWidgetItem(str(user[c]))
                    it.setForeground(Qt.GlobalColor.black)
                    self.user_table.setItem(idx, c, it)
                
                btn_widget = QWidget(); btn_lay = QHBoxLayout(btn_widget); btn_lay.setContentsMargins(2,2,2,2)
                del_btn = QPushButton("DELETE")
                del_btn.setStyleSheet("background-color: #A32A2A; color: white; font-weight: bold;")
                if user[0] == 1: # Protect primary admin
                    del_btn.setEnabled(False); del_btn.setStyleSheet("background-color: #CCC; color: white;")
                del_btn.clicked.connect(lambda ch, uid=user[0]: self.handle_delete_user(uid))
                btn_lay.addWidget(del_btn); self.user_table.setCellWidget(idx, 4, btn_widget)
        except ImportError:
            pass

    def handle_delete_user(self, uid):
        from database.db_manager import delete_user
        confirm = QMessageBox.question(self, "Confirm", "Delete this account?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            delete_user(uid)
            self.refresh_user_table()

    def handle_update_admin(self):
        u = self.admin_user_in.text().strip()
        e = self.admin_email_in.text().strip()
        p = self.admin_pass_in.text().strip()
        if u and e and p:
            if not self.validate_email(e):
                QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
                return
            password_ok, password_message = self.validate_password(p)
            if not password_ok:
                QMessageBox.warning(self, "Weak Password", password_message)
                return
            if update_admin_credentials(u, e, p): 
                QMessageBox.information(self, "Success", "Admin updated!"); self.admin_user_in.clear(); self.admin_email_in.clear(); self.admin_pass_in.clear()
                self.refresh_user_table()
        else: QMessageBox.warning(self, "Error", "Fill in all fields.")

    def handle_add_staff(self):
        u = self.new_staff_user.text().strip()
        e = self.new_staff_email.text().strip()
        p = self.new_staff_pass.text().strip()
        if u and e and p:
            if not self.validate_email(e):
                QMessageBox.warning(self, "Invalid Email", "Please enter a valid email address.")
                return
            password_ok, password_message = self.validate_password(p)
            if not password_ok:
                QMessageBox.warning(self, "Weak Password", password_message)
                return
            if add_user(u, e, p, "Staff"): 
                QMessageBox.information(self, "Success", f"Staff '{u}' created!"); self.new_staff_user.clear(); self.new_staff_email.clear(); self.new_staff_pass.clear()
                self.refresh_user_table()
        else: QMessageBox.warning(self, "Error", "Fill in all fields.")

    def validate_email(self, email):
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email))

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

    def change_page(self, index):
        if self.user_role == "Staff":
            if index == 1:
                QMessageBox.warning(self, "Access Denied", "Only Admins can access Stocks & Inventory.")
                return
            if index == 5:
                QMessageBox.warning(self, "Access Denied", "Only Admins can access Staff Management.")
                return
        self.pages.setCurrentIndex(index); self.back_btn.setVisible(index != 0); self.logout_btn.setVisible(index == 0)
        if index == 1: self.refresh_table()
        if index == 2: self.refresh_queue()
        if index == 3: self.refresh_history()
        if index == 4: self.refresh_returns()
        if index == 5: self.refresh_user_table()

    def create_placeholder_page(self, text):
        page = QLabel(text); page.setAlignment(Qt.AlignmentFlag.AlignCenter); page.setStyleSheet("background-color: white; color: black;"); page.setFont(QFont("Arial", 18)); return page
