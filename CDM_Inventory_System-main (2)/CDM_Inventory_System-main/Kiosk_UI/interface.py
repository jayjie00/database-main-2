import sys
import os
from datetime import datetime
import traceback

# Ensure the database folder is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, #type:ignore
                             QStackedWidget, QFrame, QGridLayout, QScrollArea, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QLineEdit, QMessageBox, QComboBox) 
from PyQt6.QtGui import QFont, QPixmap, QColor #type:ignore
from PyQt6.QtCore import Qt, QTimer #type:ignore
from database.db_manager import get_all_items, add_request #type:ignore
import imgConv
from PyQt6 import uic #type:ignore -- Michelle UI

class StudentKiosk(QWidget):
    def __init__(self):
        super().__init__()

        uic.loadUi("KioskProject.ui", self)
        
        self.setWindowTitle("CDM Kiosk")
        self.setFixedSize(1024, 600)
        self.setStyleSheet("background-color: white; color: black;")
        
        self.cart = {} 
        self.temp_stocks = {} 
        self.current_cat = "Supplies"
        self.print_buttons = [] 

        self.setup_ui()
        self.connect_signals()

        
    def setup_ui(self): # -- ADDED
        # IMPORTANT: names must match Qt Designer objectName

        self.pages = self.findChild(QStackedWidget, "pages")

        self.btnPage1 = self.findChild(QPushButton, "btnPage1")

        self.cart_list = self.findChild(QVBoxLayout, "cart_list")
        self.grid_layout = self.findChild(QGridLayout, "grid_layout")

        self.ris_table = self.findChild(QTableWidget, "ris_table")

        self.print_ris_btn = self.findChild(QPushButton, "print_ris_btn")

        self.paper_size_in = self.findChild(QComboBox, "paper_size_in")
        self.print_qty_in = self.findChild(QLineEdit, "print_qty_in")
        self.print_item_label = self.findChild(QLabel, "print_item_label")


    def connect_signals(self):
        self.btnPage1.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )










    # def create_top_bar(self, title_text, back_to_index): -- REMOVED  

    def handle_back_from_ris(self):
        is_printing = any("PRINTING:" in key for key in self.cart.keys())
        if is_printing:
            self.pages.setCurrentIndex(5)
        else:
            self.pages.setCurrentIndex(2)

    # def create_welcome_screen(self):  -- REMOVED
    # def create_category_screen(self):  -- REMOVED
    # def create_selection_screen(self):  -- REMOVED
    # def create_ris_form_page(self):  -- REMOVED
    

    # --- UPDATED SCREEN 4: WAITING WITH PRINT ---
    # def create_waiting_screen(self): -- REMOVED
    # def create_printing_sub_screen(self): -- REMOVED

    def select_print_type(self, clicked_button):
        for btn in self.print_buttons: 
            btn.setStyleSheet("""
                background-color: #4B6344;
                color: white;
                font-weight: bold;
                border-radius: 15px;
            """)

        clicked_button.setStyleSheet("""
            background-color: #1B4D2E;
            color: white;
            font-weight: bold;
            border: 3px solid #E0E4D9;
            border-radius: 15px;
        """)

        self.print_item_label.setStyleSheet("""
            background-color: #1B4D2E; 
            color: white; 
            border-radius: 10px; 
            padding: 10px; 
            font-weight: bold;
        """)

    def handle_print_proceed(self):
        item_type = self.print_item_label.text()
        qty = self.print_qty_in.text().strip()

        if item_type == "Select Category ->" or not qty.isdigit(): 
            return

        self.cart = {
            f"PRINTING: {item_type} ({self.paper_size_in.currentText()})": int(qty)
            }
        
        self.proceed_to_ris()

    def show_filtered(self, category_code): # -- KEEP
        self.current_cat = category_code
        try:
            if category_code == "Printing":
                self.pages.setCurrentIndex(5)
            else:
                self.refresh_grid()
                self.pages.setCurrentIndex(2)
        except Exception as exc:
            QMessageBox.critical(self, "Category Error", f"Unable to open {category_code}: {exc}")

    def _set_card_image(self, label, img_path):
        try:
            if img_path and os.path.exists(img_path):
                pixmap = QPixmap(img_path)
                if not pixmap.isNull():
                    scaled_pix = pixmap.scaled(
                        160,
                        100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    label.setPixmap(scaled_pix)
                    return
        except Exception:
            pass

        label.setText("[IMG]")
        label.setStyleSheet("background-color: #EEE; color: #999; font-size: 40px; border-radius: 5px;")

    def refresh_grid(self): # -- KEEP
        # 1. Clear the current grid
        for i in reversed(range(self.grid_layout.count())): 
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        # 2. Get fresh data from database
        items = get_all_items()
        filtered = [item for item in items if item[5] == self.current_cat]

        for idx, item in enumerate(filtered):
            # item[0]=id, item[1]=name, item[3]=qty, item[6]=image_path
            item_id, name, db_qty, img_path = item[0], item[1], item[3], item[6]

            if item_id not in self.temp_stocks:
                self.temp_stocks[item_id] = int(db_qty)
            
            display_qty = self.temp_stocks.get(item_id, db_qty)
            
            card = QFrame()
            card.setFixedSize(180, 240)
            card.setStyleSheet("background: white; border: 2px solid #DDD; border-radius: 10px;")
            l = QVBoxLayout(card)

            # --- IMAGE LOADING LOGIC ---
            img_lbl = QLabel()
            img_lbl.setFixedSize(160, 100)
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_card_image(img_lbl, img_path)
            
            n_lbl = QLabel(name)
            n_lbl.setStyleSheet("color: black; font-weight: bold; border: none;")
            
            s_lbl = QLabel(f"Stocks: {display_qty}")
            s_lbl.setStyleSheet("color: #666; border: none;")
            
            add_btn = QPushButton("ADD")
            add_btn.setEnabled(display_qty > 0)
            add_btn.setStyleSheet("background-color: #4B8B3B; color: white; font-weight: bold; border-radius: 5px; padding: 5px;")
            add_btn.clicked.connect(lambda ch, i=item: self.add_to_cart(i))
            
            l.addWidget(img_lbl)
            l.addWidget(n_lbl)
            l.addWidget(s_lbl)
            l.addWidget(add_btn)
            
            self.grid_layout.addWidget(card, idx // 3, idx % 3)

    def add_to_cart(self, item): # --KEEP
        item_id = item[0]
        item_name = item[1]
        available_stock = int(self.temp_stocks.get(item_id, item[3]))
        requested_qty = self.cart.get(item_name, 0)

        if available_stock <= 0:
            QMessageBox.warning(self, "Out of Stock", f"{item_name} is no longer available.")
            return

        self.cart[item_name] = requested_qty + 1
        self.temp_stocks[item_id] = available_stock - 1
        self.update_cart_display()
        self.refresh_grid()

    def update_cart_display(self): # -- KEEP
        for i in reversed(range(self.cart_list.count())): 
            if self.cart_list.itemAt(i).widget(): self.cart_list.itemAt(i).widget().setParent(None)

        for name, qty in self.cart.items():
            row = QLabel(f"{name} x{qty}")
            row.setStyleSheet("""
                color: black; 
                font-weight: bold;
            """)
            
            self.cart_list.addWidget(row)

    def proceed_to_ris(self): # -- KEEP
        self.ris_table.setRowCount(0)

        for name, qty in self.cart.items():
            r = self.ris_table.rowCount()
            self.ris_table.insertRow(r)

            for c, v in enumerate(["", "", name, str(qty), "", ""]):
                it = QTableWidgetItem(v)
                it.setForeground(QColor("black"))
                self.ris_table.setItem(r, c, it)

        self.pages.setCurrentIndex(3)

    def handle_final_submit(self): # -- KEEP
        name_widget = self.sig_widgets.get("NAME:_REQUESTED BY:")
        name = name_widget.text().strip()
        purpose = self.purpose_in.text().strip()
        if not name or not purpose:
            msg = QMessageBox(self); msg.setText("Please fill in Name and Purpose."); msg.setStyleSheet("color: black;"); msg.exec(); return
        add_request(name, self.cart, purpose)
        self.pages.setCurrentIndex(4)
        # TIMER EXTENDED TO 15 SECONDS TO ALLOW TIME TO PRINT
        QTimer.singleShot(15000, self.reset_to_start)

    def print_current_ris(self):
        """Simulate sending the RIS to the printer."""
        QMessageBox.information(self, "Printing", "Sending RIS Form to Printer...\nPlease collect your slip at the station.")
        self.print_ris_btn.setEnabled(False)
        self.print_ris_btn.setText("RIS PRINTED")

    def reset_to_start(self): # -- KEEP
        self.cart = {}
        self.temp_stocks = {}
        self.ris_table.setRowCount(0)
        self.ris_table.setRowCount(5)
        self.ris_resp_center.clear()
        self.ris_office.clear()
        self.ris_code.clear()
        self.ris_no.clear()
        self.purpose_in.clear()

        for widget in self.sig_widgets.values(): 
            widget.clear()
            
        self.print_qty_in.clear()
        self.print_item_label.setText("Select Category ->")
        self.print_ris_btn.setEnabled(True)
        self.print_ris_btn.setText("PRINT RIS FORM NOW")

        self.update_cart_display()
        self.refresh_grid()
        self.pages.setCurrentIndex(0)

    def reset_cart(self): # -- KEEP
        self.cart = {}
        self.temp_stocks = {}
        self.update_cart_display()
        self.refresh_grid()

if __name__ == "__main__":
    app = QApplication(sys.argv) 
    k = StudentKiosk() 
    k.show()
    sys.exit(app.exec())
