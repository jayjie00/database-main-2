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

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.pages = QStackedWidget()
        
        # Adding all pages in correct index order
        self.pages.addWidget(self.create_welcome_screen())      # 0
        self.pages.addWidget(self.create_category_screen())     # 1
        self.pages.addWidget(self.create_selection_screen())    # 2
        self.pages.addWidget(self.create_ris_form_page())       # 3
        self.pages.addWidget(self.create_waiting_screen())      # 4
        self.pages.addWidget(self.create_printing_sub_screen()) # 5

        self.main_layout.addWidget(self.pages)

    def create_top_bar(self, title_text, back_to_index):
        bar = QFrame(); 
        bar.setFixedHeight(80); 
        bar.setStyleSheet("background-color: #1B4D2E;")

        layout = QHBoxLayout(bar)

        back_btn = QPushButton("BACK")
        back_btn.setFixedSize(100, 40)
        back_btn.setStyleSheet("""
            color: white;
            border: 1px solid white;
            font-weight: bold;
            border-radius: 10px;
        """)
        
        if title_text == "REQUISITION & ISSUANCE SLIP":
            back_btn.clicked.connect(self.handle_back_from_ris)
        else:
            back_btn.clicked.connect(
                lambda: self.pages.setCurrentIndex(back_to_index)
            )
            
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 22, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: white;
            border: none;
        """)
        
        layout.addWidget(back_btn)
        layout.addStretch()
        layout.addWidget(title)
        layout.addStretch()
        layout.addSpacing(100)
        return bar

    def handle_back_from_ris(self):
        is_printing = any("PRINTING:" in key for key in self.cart.keys())
        if is_printing:
            self.pages.setCurrentIndex(5)
        else:
            self.pages.setCurrentIndex(2)

    def create_welcome_screen(self):
        page = QFrame()
        page.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1B4D2E, stop:0.4 #1B4D2E, stop:0.41 white, stop:1 white);")

        lay = QVBoxLayout(page)

        btn = QPushButton("TOUCH TO\nSTART ")
        btn.setFixedSize(400, 200)
        btn.setStyleSheet("""
            background-color: #E0E4D9;
            color: #1B4D2E;
            border-radius: 25px;
            font-size: 32px;
            font-weight: bold;
        """)
        btn.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )
        lay.addStretch()
        lay.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()
        return page

    def create_category_screen(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.create_top_bar("REQUEST CATEGORIES", 0))
        content = QWidget()
        content_lay = QVBoxLayout(content)
        content_lay.addStretch(1)
        row = QHBoxLayout()
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cats = [("Equipment\nBorrowing", "Equipment"), ("Sound System\nSetup", "Sound"), ("Office/School\nSupplies", "Supplies"), ("Mass\nPrinting", "Printing")]
        
        for display, code in cats:
            container = QWidget(); v = QVBoxLayout(container)
            btn = QPushButton(); btn.setFixedSize(170, 170)
            btn.setStyleSheet("""
                background-color: #4B8B3B; 
                border-radius: 85px;
                border: 5px solid #E0E4D9;
            """)
            btn.clicked.connect(lambda ch, c=code: self.show_filtered(c))

            lbl = QLabel(display)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("""
                color: black; 
                font-weight: bold; 
                font-size: 13px;
            """)
            v.addWidget(btn)
            v.addWidget(lbl)
            row.addWidget(container)

        content_lay.addLayout(row)
        content_lay.addStretch(1)
        lay.addWidget(content)

        return page

    def create_selection_screen(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.create_top_bar("SELECT ITEMS", 1))

        main_content = QHBoxLayout()

        self.cart_area = QFrame()
        self.cart_area.setFixedWidth(320)
        self.cart_area.setStyleSheet("background-color: #F4F6F1; border-right: 2px solid #DDD;")

        cart_lay = QVBoxLayout(self.cart_area)
        h = QHBoxLayout()
        t = QLabel("SELECTED ITEMS")
        t.setStyleSheet("color: black; font-weight: bold; font-size: 16px;")

        r = QPushButton("RESET")
        r.setStyleSheet("color: #A32A2A; font-weight: bold; border: none;")
        r.clicked.connect(self.reset_cart)
        h.addWidget(t)
        h.addStretch()
        h.addWidget(r)

        cart_lay.addLayout(h)
        self.cart_list = QVBoxLayout()
        self.cart_list.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_c = QScrollArea()

        sc_w = QWidget()
        sc_w.setLayout(self.cart_list)

        scroll_c.setWidget(sc_w)
        scroll_c.setWidgetResizable(True)
        scroll_c.setStyleSheet("""
            background: transparent; 
            border: none;
        """)
        cart_lay.addWidget(scroll_c)

        proc = QPushButton("PROCEED TO CHECKOUT")
        proc.setStyleSheet("""
            background-color: #1B4D2E; 
            color: white; 
            padding: 15px; 
            font-weight: bold; 
            border-radius: 10px;
        """)
        proc.clicked.connect(self.proceed_to_ris)
        cart_lay.addWidget(proc)

        scroll_g = QScrollArea()
        scroll_g.setWidgetResizable(True)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)

        scroll_g.setWidget(self.grid_widget)

        main_content.addWidget(self.cart_area)
        main_content.addWidget(scroll_g)

        lay.addLayout(main_content)
        return page

    def create_ris_form_page(self):
        page = QWidget()
        page.setStyleSheet("background-color: white; color: black;")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.create_top_bar("REQUISITION & ISSUANCE SLIP", 2))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        container = QWidget(); container.setStyleSheet("background-color: white;")

        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(20, 10, 20, 20)

        lbl_s = "background-color: #1B4D2E; color: white; padding: 4px; font-weight: bold; font-size: 11px;"
        in_s = "background-color: #E0E4D9; color: black; border-radius: 12px; padding: 5px; border: 1px solid #1B4D2E;"

        top_grid = QGridLayout()

        self.ris_div = QLineEdit("CDM")
        self.ris_resp_center = QLineEdit()
        self.ris_office = QLineEdit()
        self.ris_code = QLineEdit()
        self.ris_date = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        self.ris_no = QLineEdit()
        fields = [("DIVISION:", self.ris_div, 0, 0), ("RESPONSIBLE CENTER:", self.ris_resp_center, 0, 2), ("DATE:", self.ris_date, 0, 4), ("OFFICE:", self.ris_office, 1, 0), ("CODE/CL # :", self.ris_code, 1, 2), ("RIS NO:", self.ris_no, 1, 4)]

        for txt, w, r, c in fields:
            l = QLabel(txt)
            l.setStyleSheet(lbl_s)
            w.setStyleSheet(in_s)
            top_grid.addWidget(l, r, c)
            top_grid.addWidget(w, r, c+1)

        self.ris_table = QTableWidget(5, 6)
        self.ris_table.setHorizontalHeaderLabels(["STOCK NO", "UNIT", "DESCRIPTION", "QUANTITY", "QUANTITY", "REMARKS"])
        self.ris_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ris_table.setStyleSheet("QHeaderView::section { background-color: #1B4D2E; color: white; border: 1px solid white; font-weight: bold; } QTableWidget { gridline-color: #1B4D2E; background-color: white; color: black; }")

        self.purpose_in = QLineEdit()
        self.purpose_in.setStyleSheet(in_s)
        self.sig_widgets = {}
        sections = ["REQUESTED BY:", "APPROVED BY:", "ISSUED BY:", "RECEIVED BY:"]; row_labels = ["NAME:", "DATE:", "SIGNATURE:"]

        bot_grid = QGridLayout()

        for i, text in enumerate(sections):
            lbl = QLabel(text)
            lbl.setStyleSheet(lbl_s)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bot_grid.addWidget(lbl, 0, i+1)

        for r, txt in enumerate(row_labels):
            bot_grid.addWidget(QLabel(txt), r+1, 0)

            for c in range(4):
                w = QLineEdit()
                w.setStyleSheet(in_s)
                bot_grid.addWidget(w, r+1, c+1)
                self.sig_widgets[f"{txt}_{sections[c]}"] = w

        next_b = QPushButton("NEXT ->")
        next_b.setStyleSheet("""
                background-color: #4B6344; 
                color: white;
                font-weight: bold;
                padding: 10px 30px;
                border-radius: 20px;
        """)

        next_b.clicked.connect(self.handle_final_submit)

        c_lay.addLayout(top_grid)
        c_lay.addSpacing(10)
        c_lay.addWidget(self.ris_table)
        c_lay.addSpacing(10)
        c_lay.addWidget(QLabel("PURPOSE:"))
        c_lay.addWidget(self.purpose_in)
        c_lay.addSpacing(10)
        c_lay.addLayout(bot_grid)
        c_lay.addSpacing(20)
        c_lay.addWidget(next_b)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        return page

    # --- UPDATED SCREEN 4: WAITING WITH PRINT ---
    def create_waiting_screen(self):
        page = QFrame()
        page.setStyleSheet("background-color: #1B4D2E;")

        lay = QVBoxLayout(page)

        msg = QLabel("WAITING FOR VERIFICATION...")
        msg.setStyleSheet("""
            color: white;
            font-size: 30px; 
            font-weight: bold;
        """)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Please wait while the PSO Admin reviews your request.")
        sub.setStyleSheet("""
            color: #E0E4D9;
            font-size: 18px;
        """)

        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # NEW PRINT BUTTON
        self.print_ris_btn = QPushButton("PRINT RIS FORM NOW")
        self.print_ris_btn.setFixedSize(300, 60)
        self.print_ris_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E4D9; 
                color: #1B4D2E; 
                font-weight: bold; 
                font-size: 18px; 
                border-radius: 15px;
            }
        """)
        self.print_ris_btn.clicked.connect(self.print_current_ris)
        
        lay.addStretch()
        lay.addWidget(msg)
        lay.addWidget(sub)
        lay.addSpacing(30)
        lay.addWidget(self.print_ris_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addStretch()

        return page

    def create_printing_sub_screen(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.create_top_bar("MASS PRINTING SELECTION", 1))

        content = QHBoxLayout()
        content.setContentsMargins(50, 20, 50, 50)
        content.setSpacing(40) 
        self.print_left_panel = QFrame()
        self.print_left_panel.setStyleSheet("""
            background-color: #F4F6F1;
            border-radius: 20px;
            border: 1px solid #1B4D2E;
        """)

        self.print_left_panel.setFixedWidth(350)

        left_lay = QVBoxLayout(self.print_left_panel)
        left_lay.setContentsMargins(25, 25, 25, 25)
        title = QLabel("PRINT DETAILS")
        title.setStyleSheet("""
            color: black; 
            font-weight: bold; 
            font-size: 22px;
        """)

        self.print_item_label = QLabel("Select Category ->")
        self.print_item_label.setStyleSheet("""
            background-color: #E0E4D9; 
            color: black; 
            border-radius: 10px; 
            padding: 10px; 
            font-weight: bold;
        """)

        input_style = """
            background-color: white; 
            color: black; 
            padding: 8px; 
            border: 1px solid #1B4D2E; 
            border-radius: 5px;
        """

        self.paper_type_in = QComboBox()
        self.paper_type_in.addItems(["Regular (70gsm)", "Premium (80gsm)", "Special Paper", "Glossy"])
        self.paper_type_in.setStyleSheet(input_style)
        self.paper_size_in = QComboBox()
        self.paper_size_in.addItems(["A4", "Long", "Short"])
        self.paper_size_in.setStyleSheet(input_style)
        self.print_qty_in = QLineEdit()
        self.print_qty_in.setPlaceholderText("Enter pages...")
        self.print_qty_in.setStyleSheet(input_style)
        proc_btn = QPushButton("PROCEED")
        proc_btn.setStyleSheet("""
            background-color: #1B4D2E; 
            color: white; 
            font-weight: bold; 
            padding: 15px; 
            border-radius: 25px;
        """)
        proc_btn.clicked.connect(self.handle_print_proceed)
        left_lay.addWidget(title)
        left_lay.addWidget(self.print_item_label)
        left_lay.addWidget(QLabel("Paper Type"))
        left_lay.addWidget(self.paper_type_in)
        left_lay.addWidget(QLabel("Paper Size"));
        left_lay.addWidget(self.paper_size_in)
        left_lay.addWidget(QLabel("Quantity"))
        left_lay.addWidget(self.print_qty_in)
        left_lay.addStretch()
        left_lay.addWidget(proc_btn)

        right_lay = QHBoxLayout()
        right_lay.setSpacing(30)

        print_cats = ["Instructional Materials", "Official Documents", "Examination Materials"]
        self.print_buttons = []

        for name in print_cats:
            box = QPushButton(name.replace(" ", "\n"))
            box.setFixedSize(180, 200)
            box.setStyleSheet("""
                background-color: #4B6344; 
                color: white; 
                font-weight: bold; 
                border-radius: 15px;
            """)
            box.clicked.connect(lambda ch, n=name, b=box: (self.select_print_type(b), self.print_item_label.setText(n)))

            self.print_buttons.append(box)
            right_lay.addWidget(box)
        content.addWidget(self.print_left_panel)
        content.addLayout(right_lay)

        lay.addLayout(content)
        return page

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

    def show_filtered(self, category_code):
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

    def refresh_grid(self):
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

    def add_to_cart(self, item):
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

    def update_cart_display(self):
        for i in reversed(range(self.cart_list.count())): 
            if self.cart_list.itemAt(i).widget(): self.cart_list.itemAt(i).widget().setParent(None)

        for name, qty in self.cart.items():
            row = QLabel(f"{name} x{qty}")
            row.setStyleSheet("""
                color: black; 
                font-weight: bold;
            """)
            
            self.cart_list.addWidget(row)

    def proceed_to_ris(self):
        self.ris_table.setRowCount(0)

        for name, qty in self.cart.items():
            r = self.ris_table.rowCount()
            self.ris_table.insertRow(r)

            for c, v in enumerate(["", "", name, str(qty), "", ""]):
                it = QTableWidgetItem(v)
                it.setForeground(QColor("black"))
                self.ris_table.setItem(r, c, it)

        self.pages.setCurrentIndex(3)

    def handle_final_submit(self):
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

    def reset_to_start(self):
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

    def reset_cart(self):
        self.cart = {}
        self.temp_stocks = {}
        self.update_cart_display()
        self.refresh_grid()

if __name__ == "__main__":
    app = QApplication(sys.argv) 
    k = StudentKiosk() 
    k.show()
    sys.exit(app.exec())
