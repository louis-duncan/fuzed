import re
import database_io
import wx
import webbrowser
import urllib.parse
from custom_globals import *
from wx.richtext import RichTextCtrl
from wx.lib import sized_controls
from copy import deepcopy
from database_structs import StockItem


class Launcher(wx.Frame):
    database: database_io.DatabaseHandler

    def __init__(self, parent, frame_id, title):
        super().__init__(parent,
                         frame_id,
                         title,
                         style=wx.DEFAULT_FRAME_STYLE,  # & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX),
                         )

        self.title = title

        self.stock_viewer = None
        self.events_viewer = None
        self.control_panel = None
        self.item_viewers = []
        self.show_viewers = []

        try:
            database_io.load_config(CONFIG_PATH)
        except KeyError as e:
            if e.args[0] == "DATABASE_PATH":
                database_io.DATABASE_PATH = self.select_database_path()
                if database_io.DATABASE_PATH is None:
                    self.Destroy()
                    return
                database_io.save_config(CONFIG_PATH)

        self.database = database_io.init()

        panel = wx.Panel(self, -1)

        self.upcoming_text_lbl = wx.StaticText(panel,
                                               label="Upcoming Events:")

        self.upcoming_text = RichTextCtrl(panel,
                                          -1,
                                          style=wx.TE_MULTILINE | wx.TE_READONLY,
                                          size=(300, 300))
        self.upcoming_text.Caret.Hide()

        self.stock_button = wx.Button(panel,
                                      label="Stock",
                                      size=(150, 50))

        self.events_button = wx.Button(panel,
                                       label="Events",
                                       size=(150, 50))

        self.control_panel_button = wx.Button(panel,
                                              label="Control Panel",
                                              size=(150, 50))
        self.control_panel_button.Disable()

        self.user_button = wx.Button(panel,
                                     label="Login",
                                     size=(150, 50))

        self.login_label = wx.StaticText(panel,
                                         wx.ID_ANY,
                                         "")
        self.login_label.SetForegroundColour((255, 255, 255))  # set text color
        self.login_label.SetBackgroundColour((255, 0, 0))  # set text back color

        button_sizer = wx.BoxSizer(wx.VERTICAL)
        button_sizer.AddSpacer(5)
        button_sizer.Add(self.stock_button, 0)
        button_sizer.Add(self.events_button, 0)
        button_sizer.Add(self.control_panel_button, 0)
        button_sizer.Add(0, 0, 1, flag=wx.EXPAND)
        button_sizer.Add(self.user_button, 0)
        button_sizer.AddSpacer(5)

        info_sizer = wx.BoxSizer(wx.VERTICAL)

        info_sizer.Add(self.upcoming_text_lbl)
        info_sizer.Add(self.upcoming_text, proportion=1, flag=wx.EXPAND)
        info_sizer.Add(self.login_label)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSpacer(5)
        main_sizer.Add(info_sizer, proportion=1, flag=wx.EXPAND)
        main_sizer.AddSpacer(5)
        main_sizer.Add(button_sizer, flag=wx.EXPAND)
        main_sizer.AddSpacer(5)

        panel.SetSizerAndFit(main_sizer)

        self.Fit()
        self.update_upcoming()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_TEXT_URL, self.event_clicked)
        self.Bind(wx.EVT_BUTTON, self.stock_button_clicked, self.stock_button)
        self.Bind(wx.EVT_BUTTON, self.events_button_clicked, self.events_button)
        self.Bind(wx.EVT_BUTTON, self.control_panel_button_clicked, self.control_panel_button)
        self.Bind(wx.EVT_BUTTON, self.user_button_clicked, self.user_button)

        # TODO: #### DELETE THIS ####
        with self.database.open_database_connection() as con:
            self.database.validate_user(con, "louis", "password", True)
            self.login()

        self.Show()

    def update_upcoming(self):
        with self.database.open_database_connection() as con:
            shows = self.database.get_shows(con)

        if len(shows) == 0:
            text = "No Upcoming Shows"
            self.upcoming_text.SetValue(text)
            bold_style = wx.TextAttr()
            bold_style.SetFontWeight(wx.FONTWEIGHT_BOLD)
            self.upcoming_text.SetStyle(0, len(text) - 1, bold_style)
        else:
            text = ""
            underlines = []
            headers = []
            bodies = []
            for s in shows:
                underline = [len(text), 0]
                text += "{:%d/%m/%Y %H:%M}".format(s.date_time) + "\n"
                underline[1] = len(text) - 1

                header = [len(text), 0]
                text += s.show_title + "\n"
                header[1] = len(text) - 1

                body = [len(text), 0]
                text += s.show_description
                body[1] = len(text) - 1

                text += "\n\n"

                underlines.append(underline)
                headers.append(header)
                bodies.append(body)

            self.upcoming_text.SetValue(text)

            for i, u in enumerate(underlines):
                new_style = wx.TextAttr()
                new_style.SetFontUnderlined(True)
                new_style.SetURL(str(shows[i].show_id))
                self.upcoming_text.SetStyle(u[0],
                                            u[1],
                                            new_style)

            head_style = wx.TextAttr()
            head_style.SetFontWeight(wx.FONTWEIGHT_BOLD)

            for h in headers:
                self.upcoming_text.SetStyle(h[0],
                                            h[1],
                                            head_style)

            body_style = wx.TextAttr()
            body_style.SetFontStyle(wx.FONTSTYLE_ITALIC)

            for b in bodies:
                self.upcoming_text.SetStyle(b[0],
                                            b[1],
                                            body_style)

    def event_clicked(self, e):
        self.view_show(int(e.String))

    def stock_button_clicked(self, e):
        if self.stock_viewer is not None and self.stock_viewer.open:
            self.stock_viewer.Show()
            self.stock_viewer.Restore()
            self.stock_viewer.Raise()
            self.stock_viewer.Refresh()
        else:
            self.stock_viewer = StockList(self,
                                          wx.ID_ANY,
                                          self.title,
                                          self.database)

    def events_button_clicked(self, e):
        if self.events_viewer is not None and self.events_viewer.open:
            self.events_viewer.Show()
            self.events_viewer.Restore()
            self.events_viewer.Raise()
            self.events_viewer.Refresh()
        else:
            self.events_viewer = ShowsList(self,
                                           wx.ID_ANY,
                                           self.title,
                                           self.database)

    def control_panel_button_clicked(self, e):
        print("Control Panel Button Clicked")

        if self.control_panel is not None and self.control_panel.open:
            self.Show()
            self.control_panel.Restore()
            self.control_panel.Raise()
        else:
            self.control_panel = ControlPanel(self,
                                              wx.ID_ANY,
                                              None,
                                              self.database)

    def user_button_clicked(self, e=None):
        if self.database.signed_in_user() is None:
            input_dlg = LoginDialog(self, title=self.title + " - Login")

            resp = input_dlg.ShowModal()

            if resp == wx.ID_OK:
                pass
            else:
                return

            credentials = input_dlg.GetValues()

            with self.database.open_database_connection() as con:
                valid = self.database.validate_user(con, credentials[0], credentials[1], True)

            if valid:
                print("Valid")
            else:
                print("Invalid")
                dlg = wx.MessageDialog(self, "Login Failed\n\n"
                                             "Invalid credentials.",
                                       style=wx.OK | wx.ICON_EXCLAMATION,
                                       caption="Login Failed")
                dlg.ShowModal()
                return
            self.login()
        else:
            self.logout()

    def login(self):
        assert self.database.signed_in_user() is not None
        if self.database.signed_in_user().auth_level <= 1:
            self.control_panel_button.Enable()
        self.user_button.SetLabelText("Logout")
        self.login_label.SetLabelText(" {} logged in. ".format(self.database.signed_in_user().name.title()))

    def logout(self):
        self.control_panel_button.Disable()
        self.database.sign_out()
        self.user_button.SetLabelText("Login")
        self.login_label.SetLabelText("")
        if self.control_panel is not None and self.control_panel.open:
            self.control_panel.on_close()
            self.control_panel.Destroy()

    def select_database_path(self):
        with wx.FileDialog(self,
                           "Select Database Path",
                           wildcard="Database Files (*.sqlite)|*.sqlite|All Files (*.*)|*.*",
                           style=wx.FD_OPEN) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            return fileDialog.GetPath()

    def purge_viewers(self):
        to_go = []
        for v in self.show_viewers:
            if not v.open:
                to_go.append(v)
        for v in to_go:
            self.show_viewers.remove(v)
        to_go = []
        for v in self.item_viewers:
            if not v.open:
                to_go.append(v)
        for v in to_go:
            self.item_viewers.remove(v)

    def view_show(self, show_id):
        self.purge_viewers()
        for v in self.show_viewers:
            if v.show_id == show_id:
                v.Restore()
                v.Raise()
                found = True
                break
            else:
                pass
        else:
            self.show_viewers.append(ShowViewer(self, wx.ID_ANY, database=self.database, show_id=show_id))

    def add_item_viewer(self, sku=None):
        self.purge_viewers()
        for v in self.item_viewers:
            if v.sku_val == sku:
                v.Restore()
                v.Raise()
                found = True
                break
            else:
                pass
        else:
            self.item_viewers.append(ItemViewer(self, wx.ID_ANY, title=None, database=self.database, sku=sku))

    def on_close(self, e=None):
        self.purge_viewers()
        if self.stock_viewer is not None:
            self.stock_viewer.Destroy()
        if self.events_viewer is not None:
            self.events_viewer.Destroy()
        if self.control_panel is not None:
            self.control_panel.Destroy()
        for v in self.item_viewers:
            v.Destroy()
        for v in self.show_viewers:
            v.Destroy()
        if e is not None:
            e.Skip()


class StockList(wx.Frame):
    def __init__(self, parent, frame_id, title, database: database_io.DatabaseHandler):
        self.parent = parent
        self.title = title + " - Stock Viewer"
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE)
        self.title = title
        self.database = database
        self.open = True

        controls_panel = wx.Panel(self, -1)

        with self.database.open_database_connection() as con:
            self.categories = self.database.get_categories(con)
            self.classifications = self.database.get_classifications(con)
            self.categories_select = wx.CheckListBox(controls_panel,
                                                     wx.ID_ANY,
                                                     size=(200, 100),
                                                     choices=self.database.get_categories(con))

            self.classifications_select = wx.CheckListBox(controls_panel,
                                                          wx.ID_ANY,
                                                          size=(200, 75),
                                                          choices=self.database.get_classifications(con))
            self.stock_items = self.database.get_all_items(con)
        self.filtered_item_flags = [True for i in range(len(self.stock_items))]

        # Setup ListCtrl
        self.stock_list = wx.ListCtrl(self,
                                      size=(-1, -1),
                                      style=wx.LC_REPORT | wx.LC_HRULES)

        self.table_headers = {"SKU": ("sku", lambda x: str(x).zfill(6), 50),
                              "Product ID": ("product_id", lambda x: x, 70),
                              "Description": ("description", lambda x: x.replace("\n", " "), 250),
                              "Category": ("category", lambda x: self.categories[x], 70),
                              "Classification": ("classification", lambda x: self.classifications[x], 85),
                              "Unit Cost": ("unit_cost", lambda x: "£{:.2f}".format(x), 65),
                              "Unit Weight": ("unit_weight", lambda x: "{:.2f}kg".format(x), 80),
                              "NEC Weight": ("nec_weight", lambda x: "{:.2f}kg".format(x), 80),
                              "Calibre": ("calibre", lambda x: "{}mm".format(x), 75),
                              "Duration": ("duration", lambda x: "{}s".format(x), 60),
                              "Low Noise": ("low_noise", lambda x: "Yes" if x else "No", 70)}
        self.column_to_expand = 2

        for i, h in enumerate(self.table_headers.keys()):
            self.stock_list.InsertColumn(i, h)
            self.stock_list.SetColumnWidth(i, self.table_headers[h][2])

        # Create and populate the controls area.
        controls_sizer = wx.BoxSizer(wx.VERTICAL)

        padding = 5

        self.create_new_button = wx.Button(controls_panel,
                                           label="Create New Item",
                                           size=(200, 50))
        controls_sizer.Add(self.create_new_button, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding)

        self.edit_button = wx.Button(controls_panel,
                                     label="Edit Selected Item",
                                     size=(200, 50))
        controls_sizer.Add(self.edit_button, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding * 3)

        self.search_box = wx.SearchCtrl(controls_panel, size=(200, -1), style=wx.TE_PROCESS_ENTER)
        self.search_box.SetDescriptiveText("Filter...")
        controls_sizer.Add(self.search_box, 0, wx.LEFT | wx.RIGHT, padding)

        # Add filter boxes.
        controls_sizer.AddSpacer(padding * 3)

        categories_label = wx.StaticText(controls_panel,
                                         wx.ID_ANY,
                                         label="Categories:")
        controls_sizer.Add(categories_label, 0, wx.LEFT | wx.RIGHT, padding)
        controls_sizer.Add(self.categories_select, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, padding)

        controls_sizer.AddSpacer(padding / 2)

        cat_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.cat_select_all = wx.Button(controls_panel,
                                        wx.ID_ANY,
                                        label="Select All",
                                        size=(-1, 30))
        self.cat_clear_all = wx.Button(controls_panel,
                                       wx.ID_ANY,
                                       label="Clear All",
                                       size=(-1, 30))
        cat_buttons_sizer.Add(self.cat_select_all, 1, wx.EXPAND)
        cat_buttons_sizer.Add(self.cat_clear_all, 1, wx.EXPAND)
        controls_sizer.Add(cat_buttons_sizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, padding)

        controls_sizer.AddSpacer(padding * 2)
        classifications_label = wx.StaticText(controls_panel,
                                              wx.ID_ANY,
                                              label="Classifications:")
        controls_sizer.Add(classifications_label, 0, wx.LEFT | wx.RIGHT, padding)
        controls_sizer.Add(self.classifications_select, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding / 2)

        class_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.class_select_all = wx.Button(controls_panel,
                                          wx.ID_ANY,
                                          label="Select All",
                                          size=(-1, 30))
        self.class_clear_all = wx.Button(controls_panel,
                                         wx.ID_ANY,
                                         label="Clear All",
                                         size=(-1, 30))
        class_buttons_sizer.Add(self.class_select_all, 1, wx.EXPAND)
        class_buttons_sizer.Add(self.class_clear_all, 1, wx.EXPAND)
        controls_sizer.Add(class_buttons_sizer, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, padding)

        controls_sizer.AddSpacer(padding * 2)
        self.show_hidden_box = wx.CheckBox(controls_panel,
                                           wx.ID_ANY,
                                           label="Show hidden items.")
        controls_sizer.Add(self.show_hidden_box, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding)

        controls_panel.SetSizerAndFit(controls_sizer)

        # Add things to the main sizer, and assign it to a main panel.
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        main_sizer.Add(self.stock_list, 1, wx.EXPAND)

        main_sizer.Add(controls_panel, 0, wx.EXPAND)

        main_sizer.SetSizeHints(self)

        self.select_all_categories(None)
        self.select_all_classifications(None)

        self.SetSizerAndFit(main_sizer)
        self.Show()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.select_all_categories, self.cat_select_all)
        self.Bind(wx.EVT_BUTTON, self.clear_categories, self.cat_clear_all)
        self.Bind(wx.EVT_BUTTON, self.select_all_classifications, self.class_select_all)
        self.Bind(wx.EVT_BUTTON, self.clear_classifications, self.class_clear_all)
        self.Bind(wx.EVT_CHECKLISTBOX, self.apply_filters, self.categories_select)
        self.Bind(wx.EVT_CHECKLISTBOX, self.apply_filters, self.classifications_select)
        self.Bind(wx.EVT_LISTBOX, self.category_filter_highlight, self.categories_select)
        self.Bind(wx.EVT_LISTBOX, self.classification_filter_highlight, self.classifications_select)
        self.Bind(wx.EVT_BUTTON, self.create_button_clicked, self.create_new_button)
        self.Bind(wx.EVT_BUTTON, self.edit_button_clicked, self.edit_button)
        self.Bind(wx.EVT_SIZING, self.update_table_size)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edit_button_clicked, self.stock_list)
        self.Bind(wx.EVT_CHECKBOX, self.apply_filters, self.show_hidden_box)
        self.Bind(wx.EVT_TEXT, self.apply_filters, self.search_box)

        self.apply_filters()
        self.update_table_size(None)

    def create_button_clicked(self, e=None):
        self.parent.add_item_viewer(None)

    def edit_button_clicked(self, e=None):
        if self.stock_list.GetFirstSelected() == -1:
            return
        sku = self.stock_list.GetItem(self.stock_list.GetFirstSelected(), 0).GetText()
        self.parent.add_item_viewer(sku)

    def apply_filters(self, e=None):
        fields_to_text_filter = [("sku", lambda x: str(x).zfill(6)),
                                 ("description", lambda x: x.lower()),
                                 ("hse_no", lambda x: x.lower() if x is not None else ""),
                                 ("ce_no", lambda x: x.lower() if x is not None else ""),
                                 ("serial_no", lambda x: x.lower() if x is not None else ""),
                                 ("notes", lambda x: x.lower() if x is not None else ""),
                                 ("product_id", lambda x: x.lower() if x is not None else "")]
        text_filter = self.search_box.GetValue().strip().lower()
        search = re.compile(text_filter, re.MULTILINE)
        for i, s in enumerate(self.stock_items):
            show = True
            if text_filter is not "":
                show = False
                for f in fields_to_text_filter:
                    val = f[1](getattr(s, f[0]))
                    if search.search(val) is not None:
                        show = True
                        break
            elif s.category not in self.categories_select.GetCheckedItems():
                show = False
            elif s.classification not in self.classifications_select.GetCheckedItems():
                show = False
            elif s.hidden and not self.show_hidden_box.GetValue():
                show = False
            self.filtered_item_flags[i] = show
        self.populate_table()

    def category_filter_highlight(self, e):
        self.categories_select.Deselect(self.categories_select.GetSelection())

    def classification_filter_highlight(self, e):
        self.classifications_select.Deselect(self.classifications_select.GetSelection())

    def select_all_categories(self, e):
        for i in range(len(self.categories_select.Items)):
            self.categories_select.Check(i, True)
        self.apply_filters()

    def clear_categories(self, e):
        for i in range(len(self.categories_select.Items)):
            self.categories_select.Check(i, False)
        self.apply_filters()

    def select_all_classifications(self, e):
        for i in range(len(self.classifications_select.Items)):
            self.classifications_select.Check(i, True)
        self.apply_filters()

    def clear_classifications(self, e):
        for i in range(len(self.classifications_select.Items)):
            self.classifications_select.Check(i, False)
        self.apply_filters()

    def populate_table(self, e=None):
        self.stock_list.DeleteAllItems()
        for i, s in enumerate(self.stock_items):
            if self.filtered_item_flags[i]:
                self.stock_list.Append(["" if getattr(s, self.table_headers[h][0]) is None else
                                        self.table_headers[h][1](getattr(s, self.table_headers[h][0]))
                                        for h in self.table_headers])

    def update_table_size(self, e=None):
        list_size = self.stock_list.GetSize()
        taken_space = 0
        for c in range(len(self.table_headers)):
            taken_space += self.stock_list.GetColumnWidth(c) if c != self.column_to_expand else 0
        new_width = ((list_size[0] - taken_space) - 1) - 20
        self.stock_list.SetColumnWidth(self.column_to_expand, new_width)

    def on_close(self, e=None):
        self.parent.purge_viewers()

        self.open = False
        if e is not None:
            e.Skip()

    def Refresh(self, eraseBackground=True, rect=None):
        self.populate_table()
        super().Refresh(eraseBackground, rect)


class ItemViewer(wx.Frame):
    def __init__(self, parent, frame_id, title, database: database_io.DatabaseHandler, sku):
        if title is None:
            self.title = TITLE + " - Stock Viewer - {}".format(sku)
        else:
            self.title = title
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE)

        self.title = title
        self.database = database
        self.open = True
        self.sku_val = sku
        self.unsaved_changes = False

        self.item = None
        self.live_item = None

        with self.database.open_database_connection() as con:
            category_choices = con.all("SELECT category_text FROM stock_categories") + [""]
            classification_choices = con.all("SELECT classification_text FROM stock_classifications") + [""]

        panel = wx.Panel(self)

        self.required_fields = ["description",
                                "category",
                                "classification",
                                "hidden",
                                "stock_on_hand"]

        # Controls in col 1
        self.column_one = {}

        self.sku = wx.StaticText(panel, name="none")
        self.column_one["SKU"] = self.sku

        self.product_id = wx.TextCtrl(panel, name="product_id")
        self.column_one["Manufacturer Product ID"] = self.product_id

        self.description = wx.TextCtrl(panel, name="description", size=(200, 100), style=wx.TE_MULTILINE)
        self.column_one["Description"] = self.description

        self.category = wx.Choice(panel, name="category", choices=category_choices)
        self.column_one["Type"] = self.category

        self.classification = wx.Choice(panel, name="classification", choices=classification_choices)
        self.column_one["Class"] = self.classification

        self.calibre = wx.SpinCtrlDouble(panel, name="calibre", value="", min=0, max=1000, inc=0.2)
        self.column_one["Calibre (mm)"] = self.calibre

        self.unit_cost = wx.SpinCtrlDouble(panel, name="unit_cost", value="", min=0, max=10000, inc=0.1)
        self.unit_cost.SetDigits(2)
        self.column_one["Unit Cost (£)"] = self.unit_cost

        self.unit_weight = wx.SpinCtrlDouble(panel, name="unit_weight", value="", min=0, max=10000, inc=0.1)
        self.column_one["Unit Weight (kg)"] = self.unit_weight

        self.nec_weight = wx.SpinCtrlDouble(panel, name="nec_weight", value="", min=0, max=10000, inc=0.1)
        self.column_one["NEC Weight (kg)"] = self.nec_weight

        self.case_size = wx.SpinCtrl(panel, name="case_size", value="", min=0, max=10000)
        self.column_one["Case Size"] = self.case_size

        self.ce_no = wx.TextCtrl(panel, name="ce_no")
        self.column_one["CE No'"] = self.ce_no

        self.serial_no = wx.TextCtrl(panel, name="serial_no")
        self.column_one["Serial No'"] = self.serial_no

        # Control in col 2
        self.column_two = {}

        self.shots = wx.SpinCtrl(panel, name="shots", value="", min=0, max=10000)
        self.column_two["Shots"] = self.shots

        self.duration = wx.SpinCtrl(panel, name="duration", value="", min=0, max=10000)
        self.column_two["Duration (secs)"] = self.duration

        self.notes = wx.TextCtrl(panel, name="notes", size=(200, 100), style=wx.TE_MULTILINE)
        self.column_two["Notes"] = self.notes

        self.low_noise = wx.Choice(panel, name="low_noise", choices=("No", "Yes", ""))
        self.column_two["Low Noise"] = self.low_noise

        self.preview_link = wx.TextCtrl(panel, name="preview_link")
        self.column_two["Preview Link"] = self.preview_link

        self.preview_button = wx.Button(panel, name="none", label="Open Preview")
        self.column_two["none1"] = self.preview_button

        self.hse_no = wx.TextCtrl(panel, name="hse_no")
        self.column_two["HSE No'"] = self.hse_no

        self.hidden = wx.Choice(panel, name="hidden", choices=("No", "Yes", ""))
        self.column_two["Hidden"] = self.hidden

        self.stock_on_hand = wx.SpinCtrl(panel, name="stock_on_hand", value="", min=0, max=10000)
        self.column_two["Stock on Hand"] = self.stock_on_hand

        self.available = wx.StaticText(panel, name="none")
        self.column_two["Stock Available"] = self.available

        col_two_gap = (20, 20)
        self.column_two["none_2"] = col_two_gap

        self.save_button = wx.Button(panel, name="none", size=(120, 35), label="Save Changes")
        self.save_button.Disable()
        self.column_two["none_3"] = self.save_button

        self.reset_button = wx.Button(panel, name="none", size=(120, 35), label="Clear Changes")
        self.reset_button.Disable()
        self.column_two["none_4"] = self.reset_button

        col_two_gap_two = (0, 0)
        self.column_two["none_5"] = col_two_gap_two

        # Add col 1 things
        column_one_sizer = wx.GridBagSizer(5, 5)
        for i, k in enumerate(self.column_one):
            if not k.startswith("none"):
                label = ("* " if self.column_one[k].GetName() in self.required_fields else "") + k + ":"
                column_one_sizer.Add(wx.StaticText(panel, label=label),
                                     (i, 0),
                                     flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
            if k == "Description":
                column_one_sizer.Add(self.column_one[k], (i, 1), flag=wx.EXPAND)
            else:
                column_one_sizer.Add(self.column_one[k], (i, 1))
        column_one_sizer.AddGrowableRow(2)
        column_one_sizer.AddGrowableCol(1)

        # Add col 2 things
        column_two_sizer = wx.GridBagSizer(5, 5)
        for i, k in enumerate(self.column_two):
            # Add label, if it doesn't start with 'none', allows for labels to be omitted.
            if not k.startswith("none"):
                label = ("* " if self.column_two[k].GetName() in self.required_fields else "") + k + ":"
                column_two_sizer.Add(wx.StaticText(panel, label=label),
                                     (i, 0),
                                     flag=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
            # Add control object.
            if k in ("Notes", "Preview Link"):
                column_two_sizer.Add(self.column_two[k], (i, 1), flag=wx.ALL | wx.EXPAND)
            else:
                if type(self.column_two[k]) is not tuple:
                    column_two_sizer.Add(self.column_two[k], (i, 1))
                else:
                    column_two_sizer.Add(self.column_two[k][0], self.column_two[k][1], pos=(i, 1))

        column_two_sizer.AddGrowableRow(2)
        column_two_sizer.AddGrowableCol(1)

        v_padding_sizer = wx.BoxSizer(wx.VERTICAL)
        h_padding_sizer = wx.BoxSizer(wx.HORIZONTAL)

        h_padding_sizer.AddSpacer(5)
        h_padding_sizer.Add(column_one_sizer, 1, flag=wx.EXPAND)
        h_padding_sizer.AddSpacer(10)
        h_padding_sizer.Add(column_two_sizer, 1, flag=wx.EXPAND)
        h_padding_sizer.AddSpacer(5)
        v_padding_sizer.AddSpacer(5)
        v_padding_sizer.Add(h_padding_sizer, 1, flag=wx.EXPAND)
        v_padding_sizer.AddSpacer(5)

        panel.SetSizerAndFit(v_padding_sizer)
        self.Fit()

        self.refresh_information()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.open_preview, self.preview_button)
        self.Bind(wx.EVT_TEXT, self.check_for_changes)
        self.Bind(wx.EVT_CHOICE, self.check_for_changes)
        self.Bind(wx.EVT_BUTTON, self.save_button_clicked, self.save_button)
        self.Bind(wx.EVT_BUTTON, self.refresh_information, self.reset_button)

        self.Show()

    def save_button_clicked(self, e=None):
        error = None
        if self.database.signed_in_user() is None:
            error = "You are not signed in, so cannot save.\nPlease sign in from the main window."
        elif self.database.signed_in_user().auth_level > 1:
            error = "You are not authorised to save changes to stock."
        else:
            for r in self.required_fields:
                val = getattr(self.live_item, r)
                if r == "hidden" and val != 2:
                    pass
                elif r == "classification" and val != (self.classification.GetCount() - 1):
                    pass
                elif r == "category" and val != (self.category.GetCount() - 1):
                    pass
                elif r == "description" and val.strip() != "":
                    pass
                elif r == "stock_on_hand" and val != "":
                    pass
                else:
                    name = ""
                    for c in self.column_one:
                        if hasattr(self.column_one[c], "Name") and self.column_one[c].Name == r:
                            name = c
                            break
                    else:
                        for c in self.column_two:
                            if hasattr(self.column_two[c], "Name") and self.column_two[c].Name == r:
                                name = c
                                break
                        else:
                            name = r

                    error = "All required fields (*) must be provided.\n{} missing.".format(name)
                    break

        if error is not None:
            dlg = wx.MessageDialog(self,
                                   "Cannot Save\n\n" + error,
                                   TITLE + " - Save")
            dlg.ShowModal()
            return

        with self.database.open_database_connection() as con:
            if self.sku_val is None:
                self.sku_val = self.database.add_item(con, self.live_item)
            else:
                self.database.update_item(con, self.live_item)

        self.refresh_information()
        self.check_for_changes()

    def check_for_changes(self, e=None):
        if e is not None:
            event_obj = e.GetEventObject()
            attr = event_obj.GetName()
            if attr in ("classification", "category"):
                value = event_obj.GetSelection()
            elif attr in ("low_noise", "hidden"):
                value = bool(event_obj.GetSelection())
            else:
                value = event_obj.GetValue()
            self.live_item.__setattr__(attr, value)

        for k in self.item.__dict__.keys():
            old = self.item.__dict__[k]
            new = self.live_item.__dict__[k]
            if old != new and not (old is None and new in (0, "")):
                self.unsaved_changes = True
                break
        else:
            self.unsaved_changes = False

        if self.unsaved_changes:
            self.save_button.Enable()
            self.reset_button.Enable()
        else:
            self.save_button.Disable()
            self.reset_button.Disable()

    def open_preview(self, e=None):
        if self.preview_link.GetValue().strip() == "":
            return
        webbrowser.open_new(self.preview_link.GetValue().strip())

    def refresh_information(self, e=None):
        if self.sku_val is not None:
            with self.database.open_database_connection() as con:
                self.item = self.database.get_item(con, self.sku_val)
                self.available.SetLabelText("  " + str(self.database.get_stock_levels(con, self.sku_val)[1]))

            if self.item is None:
                dlg = wx.MessageDialog(self, "Database Lookup Error\n\n"
                                             "Failed to find item {} in the database.".format(self.sku_val),
                                       style=wx.OK | wx.ICON_EXCLAMATION,
                                       caption="{} - Lookup Error".format(TITLE))
                dlg.ShowModal()
                self.Destroy()
                return
        else:
            self.item = StockItem("generated")

        self.live_item = deepcopy(self.item)

        self.sku.SetLabelText("  " + str(self.live_item.sku).zfill(6))

        all_controls = [c for c in self.column_one.values()] + [c for c in self.column_two.values()]

        for c in all_controls:
            try:
                attr = c.GetName()
            except AttributeError:
                continue
            if attr == "none":
                pass
            elif attr in ("classification", "category"):
                if self.item.__getattribute__(attr) is not None:
                    val = self.item.__getattribute__(attr)
                else:
                    val = c.GetCount() - 1
                c.SetSelection(val)
            elif attr in ("low_noise", "hidden"):
                if self.item.__getattribute__(attr) is not None:
                    val = self.item.__getattribute__(attr)
                else:
                    val = 2
                c.SetSelection(val)
            else:
                val = self.item.__getattribute__(attr)
                if val is not None:
                    pass
                else:
                    if type(c) is wx.TextCtrl:
                        val = ""
                    elif type(c) in (wx.SpinCtrl, wx.SpinCtrlDouble):
                        val = 0
                c.SetValue(val)

    def on_close(self, e=None):
        if self.unsaved_changes:
            dlg = wx.MessageDialog(self,
                                   "Unsaved Changes\n\n"
                                   "There are unsaved changes which will be lost.\n"
                                   "Would you like to close the window anyway?",
                                   TITLE + " - Save",
                                   style=wx.YES_NO | wx.ICON_EXCLAMATION)
            resp = dlg.ShowModal()
            if resp == wx.ID_NO:
                return

        self.open = False
        if e is not None:
            e.Skip()


class ControlPanel(wx.Frame):
    def __init__(self, parent, frame_id, title, database: database_io.DatabaseHandler):
        if title is None:
            self.title = TITLE + " - Control Panel"
        else:
            self.title = title
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX))
        self.database = database
        self.open = True

        self.users = []

        if database.signed_in_user() is None or database.signed_in_user().auth_level > 1:
            dlg = wx.MessageDialog(self, "YOU SHOULDN'T BE HERE!!!!\n\n"
                                         "The control panel tried to open without a user being signed in, "
                                         "or with a user who was not authorised.",
                                   style=wx.OK | wx.ICON_EXCLAMATION,
                                   caption=">:(")
            dlg.ShowModal()
            self.open = False
            self.Destroy()
            return

        main_panel = wx.Panel(self, -1)

        # Setup
        # User management
        user_controls_box = wx.StaticBox(main_panel, label="Users:")
        user_controls_sizer = wx.StaticBoxSizer(user_controls_box, wx.HORIZONTAL)
        user_controls_buttons_sizer = wx.BoxSizer(wx.VERTICAL)

        self.user_list = wx.ListCtrl(user_controls_box,
                                     size=(-1, -1),
                                     style=wx.LC_REPORT | wx.LC_HRULES)
        self.user_list.InsertColumn(0, "User")
        self.user_list.SetColumnWidth(0, 200)
        self.user_list.InsertColumn(1, "Privilege")
        self.user_list.SetColumnWidth(1, 200)

        self.new_user_button = wx.Button(user_controls_box,
                                         label="Add New User",
                                         size=(120, 30))
        self.change_username_button = wx.Button(user_controls_box,
                                                label="Change Username",
                                                size=(120, 30))
        self.change_username_button.Disable()
        self.reset_password_button = wx.Button(user_controls_box,
                                               label="Reset Password",
                                               size=(120, 30))
        self.reset_password_button.Disable()
        self.change_privilege_button = wx.Button(user_controls_box,
                                                 label="Change Privilege",
                                                 size=(120, 30))
        self.change_privilege_button.Disable()
        self.delete_user_button = wx.Button(user_controls_box,
                                            label="Delete User",
                                            size=(120, 30))
        self.delete_user_button.Disable()

        user_controls_buttons_sizer.Add(self.new_user_button)
        user_controls_buttons_sizer.Add(self.change_username_button)
        user_controls_buttons_sizer.Add(self.reset_password_button)
        user_controls_buttons_sizer.Add(self.change_privilege_button)
        user_controls_buttons_sizer.Add(self.delete_user_button)

        user_controls_sizer.Add(self.user_list)
        user_controls_sizer.AddSpacer(3)
        user_controls_sizer.Add(user_controls_buttons_sizer)

        # Database management.
        database_controls_box = wx.StaticBox(main_panel, label="Database Path:")
        database_controls_sizer = wx.StaticBoxSizer(database_controls_box, wx.VERTICAL)
        database_controls_sizer.Add(wx.StaticText(main_panel, label=self.database.database_path))

        # Add things to main sizer.

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        side_margin_sizer = wx.BoxSizer(wx.HORIZONTAL)

        main_sizer.AddSpacer(10)
        main_sizer.Add(user_controls_sizer)
        main_sizer.AddSpacer(10)
        main_sizer.Add(database_controls_sizer)
        main_sizer.AddSpacer(10)

        side_margin_sizer.AddSpacer(10)
        side_margin_sizer.Add(main_sizer)
        side_margin_sizer.AddSpacer(10)

        main_panel.SetSizerAndFit(side_margin_sizer)

        self.Fit()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # Button Bindings
        self.Bind(wx.EVT_BUTTON, self.add_new_user, self.new_user_button)
        self.Bind(wx.EVT_BUTTON, self.change_username, self.change_username_button)
        self.Bind(wx.EVT_BUTTON, self.reset_password, self.reset_password_button)
        self.Bind(wx.EVT_BUTTON, self.change_privilege, self.change_privilege_button)
        self.Bind(wx.EVT_BUTTON, self.delete_user, self.delete_user_button)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.user_selection_changed, self.user_list)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.user_selection_changed, self.user_list)

        self.refresh_user_list()
        self.Show()

    def user_selection_changed(self, e=None):
        if self.user_list.GetFirstSelected() == -1:
            self.change_username_button.Disable()
            self.reset_password_button.Disable()
            self.change_privilege_button.Disable()
            self.delete_user_button.Disable()
        else:
            self.change_username_button.Enable()
            self.reset_password_button.Enable()
            if self.users[self.user_list.GetFirstSelected()].user_id == self.database.signed_in_user().user_id:
                self.delete_user_button.Disable()
                self.change_privilege_button.Disable()
            else:
                self.delete_user_button.Enable()
                self.change_privilege_button.Enable()

    def add_new_user(self, e=None):
        if not self.validate_user():
            return

        with self.database.open_database_connection() as con:
            taken = con.all("SELECT name FROM users")

        dlg = NewUserDialog(self, title=self.title + " - New User", taken=taken)
        resp = dlg.ShowModal()
        if resp != wx.ID_OK:
            return

        username, password, auth_level = dlg.GetValues()

        with self.database.open_database_connection() as con:
            self.database.create_user(con, username, password, auth_level)

        self.refresh_user_list()

    def change_username(self, e=None):
        if not self.validate_user():
            return
        with self.database.open_database_connection() as con:
            taken = con.all("SELECT name FROM users")
        dlg = wx.TextEntryDialog(self,
                                 "Change username:",
                                 TITLE + " - Change Username",
                                 self.users[self.user_list.GetFirstSelected()].name)
        resp = dlg.ShowModal()
        if resp != wx.ID_OK:
            return
        new_username = dlg.GetValue().lower()
        error = False
        if len(new_username) < 3:
            error = "New username is too short."
        elif new_username in taken:
            error = "Username '{}' is not available.".format(new_username)
        else:
            pass
        if error is False:
            with self.database.open_database_connection() as con:
                self.database.change_username(con, self.users[self.user_list.GetFirstSelected()].user_id, new_username)
        else:
            dlg = wx.MessageDialog(self, "Invalid Username\n\n"
                                         "{}.".format(error),
                                   style=wx.OK | wx.ICON_EXCLAMATION,
                                   caption=TITLE + " - Invalid Username")
            dlg.ShowModal()
        self.refresh_user_list()

    def reset_password(self, e=None):
        if not self.validate_user():
            return
        selected_user = self.users[self.user_list.GetFirstSelected()]
        dlg = NewPasswordDialog(self,
                                title=self.title + " - Reset Password",
                                username=selected_user.name)
        resp = dlg.ShowModal()
        if resp != wx.ID_OK:
            return
        new_password = dlg.GetValue()
        assert new_password != ""

        with self.database.open_database_connection() as con:
            self.database.set_user_password(con, selected_user.user_id, new_password)

    def change_privilege(self, e=None):
        if not self.validate_user():
            return
        selected_user = self.users[self.user_list.GetFirstSelected()]
        dlg = wx.SingleChoiceDialog(self,
                                    "Select privilege level for {}".format(selected_user.name.title()),
                                    TITLE + " - Change Privilege",
                                    AUTH_LEVELS[1:])
        resp = dlg.ShowModal()
        if resp != wx.ID_OK:
            return
        new_auth = dlg.GetSelection() + 1
        assert new_auth in range(1, len(AUTH_LEVELS))
        with self.database.open_database_connection() as con:
            self.database.change_auth_level(con, selected_user.user_id, new_auth)
        self.refresh_user_list()

    # @is_user_validated
    def delete_user(self, e=None):
        assert self.users[self.user_list.GetFirstSelected()].user_id != self.database.signed_in_user().user_id
        if not self.validate_user():
            return
        selected_user = self.users[self.user_list.GetFirstSelected()]
        dlg = wx.MessageDialog(self,
                               "Are you sure you want to delete {}?".format(selected_user.name.title()),

                               TITLE,
                               wx.YES_NO)
        resp = dlg.ShowModal()
        if resp != wx.ID_YES:
            return
        with self.database.open_database_connection() as con:
            self.database.delete_user(con, selected_user.user_id)
        self.refresh_user_list()

    def on_close(self, e=None):
        self.open = False
        if e is not None:
            e.Skip()

    def refresh_user_list(self, e=None):
        self.user_list.DeleteAllItems()

        with self.database.open_database_connection() as con:
            self.users = self.database.get_users(con)

        for u in self.users:
            if u.user_id == 0:
                self.users.remove(u)
                break

        for u in self.users:
            self.user_list.Append(
                [u.name.title() + (" (you)" if self.database.signed_in_user().user_id == u.user_id else ""),
                 AUTH_LEVELS[u.auth_level]])

    def validate_user(self):
        dlg = wx.PasswordEntryDialog(self,
                                     "Enter password for {} to continue:".format(
                                         self.database.signed_in_user().name.title()),
                                     TITLE + " - Login")
        resp = dlg.ShowModal()

        if resp != wx.ID_OK:
            return False

        with self.database.open_database_connection() as con:
            valid = self.database.validate_user(con, self.database.signed_in_user().user_id, dlg.GetValue())

        if valid:
            return True
        else:
            dlg = wx.MessageDialog(self, "Login Failed\n\n"
                                         "Invalid credentials.",
                                   style=wx.OK | wx.ICON_EXCLAMATION,
                                   caption="Login Failed")
            dlg.ShowModal()
            return False


class ShowsList(wx.Frame):
    def __init__(self, parent, frame_id, title, database: database_io.DatabaseHandler):
        self.parent = parent
        self.title = title + " - Shows Viewer"
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE)
        self.title = title
        self.database = database
        self.open = True
        self.show_viewers = []

        controls_panel = wx.Panel(self, -1)

        with self.database.open_database_connection() as con:
            self.shows = self.database.get_shows(con, False)
        self.filter_flags = [True] * len(self.shows)

        # Setup ListCtrl
        self.shows_list = wx.ListCtrl(self,
                                      size=(-1, -1),
                                      style=wx.LC_REPORT | wx.LC_HRULES)

        self.table_headers = {"Show ID": ("show_id", lambda x: str(x).zfill(6), 60),
                              "Title": ("show_title", lambda x: x, 250),
                              "Supervisor": ("supervisor", lambda x: x, 70),
                              "Date/Time": ("date_time", lambda x: "{:%d/%m/%y - %H:%M}".format(x), 150)
                              }
        self.column_to_expand = 2

        for i, h in enumerate(self.table_headers.keys()):
            self.shows_list.InsertColumn(i, h)
            self.shows_list.SetColumnWidth(i, self.table_headers[h][2])

        # Create and populate the controls area.
        controls_sizer = wx.BoxSizer(wx.VERTICAL)

        padding = 5

        self.create_new_button = wx.Button(controls_panel,
                                           label="Create New Show",
                                           size=(200, 50))
        controls_sizer.Add(self.create_new_button, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding)

        self.edit_button = wx.Button(controls_panel,
                                     label="View Selected Show",
                                     size=(200, 50))
        controls_sizer.Add(self.edit_button, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding * 3)

        self.search_box = wx.SearchCtrl(controls_panel, size=(200, -1), style=wx.TE_PROCESS_ENTER)
        self.search_box.SetDescriptiveText("Filter...")
        controls_sizer.Add(self.search_box, 0, wx.LEFT | wx.RIGHT, padding)

        # TODO: Add supervisor filter.

        controls_sizer.AddSpacer(padding * 2)
        self.show_complete_box = wx.CheckBox(controls_panel,
                                             wx.ID_ANY,
                                             label="Show closed shows.")
        controls_sizer.Add(self.show_complete_box, 0, wx.LEFT | wx.RIGHT, padding)

        controls_sizer.AddSpacer(padding)

        controls_panel.SetSizerAndFit(controls_sizer)

        # Add things to the main sizer, and assign it to a main panel.
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        main_sizer.Add(self.shows_list, 1, wx.EXPAND)

        main_sizer.Add(controls_panel, 0, wx.EXPAND)

        main_sizer.SetSizeHints(self)

        self.SetSizerAndFit(main_sizer)
        self.Show()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_TEXT, self.apply_filters, self.search_box)
        self.Bind(wx.EVT_CHECKBOX, self.apply_filters, self.show_complete_box)
        self.Bind(wx.EVT_BUTTON, self.view_show, self.edit_button)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.view_show, self.shows_list)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.populate_table()
        self.apply_filters()
        self.update_table_size(None)

    def view_show(self, e=None):
        if self.shows_list.GetFirstSelected() == -1:
            return
        show_id = self.shows_list.GetItem(self.shows_list.GetFirstSelected(), 0).GetText()
        self.parent.view_show(int(show_id))

    def apply_filters(self, e=None):
        fields_to_text_filter = [("show_id", lambda x: str(x).zfill(6)),
                                 ("show_title", lambda x: x.lower()),
                                 ("show_description", lambda x: x.lower() if x is not None else ""),
                                 ("supervisor", lambda x: x.lower() if x is not None else "")]
        text_filter = self.search_box.GetValue().strip().lower()
        search = re.compile(text_filter, re.MULTILINE)
        for i, s in enumerate(self.shows):
            show = True
            if text_filter is not "":
                show = False
                for f in fields_to_text_filter:
                    val = f[1](getattr(s, f[0]))
                    if search.search(val) is not None:
                        show = True
                        break
            elif s.complete and not self.show_complete_box.GetValue():
                show = False
            self.filter_flags[i] = show
        self.populate_table()

    def populate_table(self, e=None):
        self.shows_list.DeleteAllItems()
        for i, s in enumerate(self.shows):
            if self.filter_flags[i]:
                self.shows_list.Append(["" if getattr(s, self.table_headers[h][0]) is None else
                                        self.table_headers[h][1](getattr(s, self.table_headers[h][0]))
                                        for h in self.table_headers])

    def update_table_size(self, e=None):
        list_size = self.shows_list.GetSize()
        taken_space = 0
        for c in range(len(self.table_headers)):
            taken_space += self.shows_list.GetColumnWidth(c) if c != self.column_to_expand else 0
        new_width = (list_size[0] - taken_space) - 1
        self.shows_list.SetColumnWidth(self.column_to_expand, new_width)

    def on_close(self, e=None):
        self.open = False
        if e is not None:
            e.Skip()

    def Refresh(self, eraseBackground=True, rect=None):
        self.populate_table()
        super().Refresh(eraseBackground, rect)


class ShowViewer(wx.Frame):
    def __init__(self, parent, frame_id, show_id, database: database_io.DatabaseHandler):
        self.title = TITLE + " - Show: " + str(show_id).zfill(6)
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE)
        self.title = TITLE
        self.database = database
        self.show_id = show_id
        self.open = True
        self.show_item_viewers = []

        controls_panel = wx.Panel(self, -1)

        with self.database.open_database_connection() as con:
            self.categories = self.database.get_categories(con)
            self.classifications = self.database.get_classifications(con)
            self.show_items = self.database.get_show_items(con, self.show_id)

        # Setup ListCtrl
        self.stock_list = wx.ListCtrl(self,
                                      size=(-1, -1),
                                      style=wx.LC_REPORT | wx.LC_HRULES)

        self.table_headers = {"SKU": ("sku", lambda x: str(x).zfill(6), 50),
                              "Product ID": ("product_id", lambda x: x, 70),
                              "Description": ("description", lambda x: x.replace("\n", " "), 250)
                              }
        self.column_to_expand = 2

        for i, h in enumerate(self.table_headers.keys()):
            self.stock_list.InsertColumn(i, h)
            self.stock_list.SetColumnWidth(i, self.table_headers[h][2])

        # Create and populate the controls area.
        controls_sizer = wx.GridBagSizer(5, 5)

        controls_panel.SetSizerAndFit(controls_sizer)

        # Add things to the main sizer, and assign it to a main panel.
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(controls_panel, 0, wx.EXPAND)

        main_sizer.Add(self.stock_list, 1, wx.EXPAND)

        main_sizer.SetSizeHints(self)

        self.SetSizerAndFit(main_sizer)
        self.Show()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.item_clicked, self.stock_list)

        self.populate_table()

    def item_clicked(self, e=None):
        if self.stock_list.GetFirstSelected() == -1:
            return

        sku = self.stock_list.GetItem(self.stock_list.GetFirstSelected(), 0).GetText()

    def populate_table(self, e=None):
        self.stock_list.DeleteAllItems()
        for s in self.show_items:
            self.stock_list.Append(["" if getattr(s[0], self.table_headers[h][0]) is None else
                                    self.table_headers[h][1](getattr(s[0], self.table_headers[h][0]))
                                    for h in self.table_headers])

    def purge_viewers(self, e=None):
        for v in self.show_item_viewers:
            if not v.open:
                self.show_item_viewers.remove(v)

    def on_close(self, e=None):
        self.purge_viewers()
        if len(self.show_item_viewers) > 0:
            self.Hide()
        else:
            self.open = False
            if e is not None:
                e.Skip()


class ShowItemViewer(wx.Frame):
    pass


class LoginDialog(sized_controls.SizedDialog):
    def __init__(self, *args, **kwargs):
        super(LoginDialog, self).__init__(*args, **kwargs)
        panel = self.GetContentsPane()

        user_prompt = wx.StaticText(panel,
                                    wx.ID_ANY,
                                    "Username:")
        self.user_entry = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PROCESS_ENTER)

        pass_prompt = wx.StaticText(panel,
                                    wx.ID_ANY,
                                    "Password:")
        self.pass_entry = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)

        main_sizer = wx.GridBagSizer(10, 10)

        main_sizer.Add(wx.StaticText(panel,
                                     wx.ID_OK,
                                     "Enter login credentials:"),
                       pos=(0, 0),
                       span=(1, 2),
                       flag=wx.ALIGN_CENTER)

        main_sizer.Add(user_prompt,
                       pos=(1, 0),
                       flag=wx.ALIGN_CENTRE_VERTICAL)
        main_sizer.Add(self.user_entry,
                       pos=(1, 1))
        main_sizer.Add(pass_prompt,
                       pos=(2, 0),
                       flag=wx.ALIGN_CENTRE_VERTICAL)
        main_sizer.Add(self.pass_entry,
                       pos=(2, 1))

        panel_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.button_ok = wx.Button(panel, wx.ID_OK, label='Login')
        panel_buttons.Add(self.button_ok)
        self.button_ok.Bind(wx.EVT_BUTTON, self.on_button)

        button_cancel = wx.Button(panel, wx.ID_CANCEL, label='Cancel')
        panel_buttons.Add(button_cancel)
        button_cancel.Bind(wx.EVT_BUTTON, self.on_button)

        main_sizer.Add(panel_buttons,
                       pos=(3, 0),
                       span=(1, 2),
                       flag=wx.ALIGN_CENTER)

        panel.SetSizerAndFit(main_sizer)

        self.Bind(wx.EVT_TEXT_ENTER, self.enter_in_username, self.user_entry)
        self.Bind(wx.EVT_TEXT_ENTER, self.enter_in_password, self.pass_entry)

        self.Fit()

    def enter_in_username(self, e=None):
        print("Enter in user box")
        self.pass_entry.SetFocus()

    def enter_in_password(self, e=None):
        if self.IsModal():
            self.EndModal(wx.ID_OK)
        else:
            self.Close()

    def on_button(self, event):
        if self.IsModal():
            self.EndModal(event.EventObject.Id)
        else:
            self.Close()

    def GetValues(self):
        return self.user_entry.GetLineText(0), self.pass_entry.GetLineText(0)


class NewUserDialog(sized_controls.SizedDialog):
    def __init__(self, *args, **kwargs):
        self.taken = kwargs.pop("taken")
        super(NewUserDialog, self).__init__(*args, **kwargs)
        panel = self.GetContentsPane()

        user_prompt = wx.StaticText(panel,
                                    wx.ID_ANY,
                                    "Username:")
        self.user_entry = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PROCESS_ENTER)

        pass_prompt_one = wx.StaticText(panel,
                                        wx.ID_ANY,
                                        "New Password:")
        self.pass_entry_one = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)

        pass_prompt_two = wx.StaticText(panel,
                                        wx.ID_ANY,
                                        "Re-enter Password:")
        self.pass_entry_two = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        self.auth_selector = wx.Choice(panel,
                                       choices=AUTH_LEVELS[1:])
        self.auth_selector.SetSelection(1)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(wx.StaticText(panel,
                                     wx.ID_OK,
                                     "Enter new user details:"),
                       flag=wx.ALIGN_CENTER)

        inputs_sizer = wx.GridBagSizer(10, 10)

        inputs_sizer.Add(user_prompt,
                         pos=(0, 0),
                         flag=wx.ALIGN_RIGHT)
        inputs_sizer.Add(self.user_entry,
                         pos=(0, 1))
        inputs_sizer.Add(pass_prompt_one,
                         pos=(1, 0),
                         flag=wx.ALIGN_RIGHT)
        inputs_sizer.Add(self.pass_entry_one,
                         pos=(1, 1))
        inputs_sizer.Add(pass_prompt_two,
                         pos=(2, 0),
                         flag=wx.ALIGN_RIGHT)
        inputs_sizer.Add(self.pass_entry_two,
                         pos=(2, 1))
        inputs_sizer.Add(self.auth_selector,
                         pos=(0, 2))

        main_sizer.AddSpacer(10)
        main_sizer.Add(inputs_sizer)

        panel_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.button_ok = wx.Button(panel, wx.ID_OK, label='Confirm')
        self.button_ok.Disable()
        panel_buttons.Add(self.button_ok)
        self.button_ok.Bind(wx.EVT_BUTTON, self.on_button)

        button_cancel = wx.Button(panel, wx.ID_CANCEL, label='Cancel')
        panel_buttons.Add(button_cancel)
        button_cancel.Bind(wx.EVT_BUTTON, self.on_button)

        main_sizer.AddSpacer(10)
        main_sizer.Add(panel_buttons,
                       flag=wx.ALIGN_CENTER)

        self.status_text = wx.StaticText(panel, label="", size=(250, 20), style=wx.ALIGN_CENTER_HORIZONTAL)
        self.status_text.SetBackgroundColour((200, 200, 200))
        main_sizer.AddSpacer(10)
        main_sizer.Add(self.status_text,
                       flag=wx.ALIGN_CENTRE)

        panel.SetSizerAndFit(main_sizer)

        self.Bind(wx.EVT_TEXT, self.change)

        self.Fit()

    def change(self, e=None):
        errors = []
        if len(self.user_entry.GetValue()) == 0:
            errors.append("Username required.")
        if self.user_entry.GetValue().lower() in self.taken:
            errors.append("Username not available.")
        if 0 < len(self.user_entry.GetValue()) < 3:
            errors.append("Username must have 3 of more characters.")
        if self.pass_entry_one.GetValue() == "":
            errors.append("Password required.")
        if self.pass_entry_two.GetValue() == "":
            errors.append("Re-enter password.")
        if self.pass_entry_one.GetValue() != self.pass_entry_two.GetValue():
            errors.append("Passwords do not match!")

        if len(errors) > 0:
            self.button_ok.Disable()
            self.status_text.SetLabelText(errors[0])
            self.status_text.SetBackgroundColour((255, 0, 0))
            self.status_text.SetForegroundColour((255, 255, 255))
        else:
            self.button_ok.Enable()
            self.status_text.SetLabelText("Details valid.")
            self.status_text.SetBackgroundColour((0, 200, 0))
            self.status_text.SetForegroundColour((255, 255, 255))

    def on_button(self, event):
        if self.IsModal():
            self.EndModal(event.EventObject.Id)
        else:
            self.Close()

    def GetValues(self):
        assert self.user_entry.GetValue() not in self.taken
        assert len(self.user_entry.GetValue()) >= 3
        assert self.pass_entry_one.GetValue() == self.pass_entry_two.GetValue()
        assert self.pass_entry_one.GetValue() != ""

        return self.user_entry.GetValue(), self.pass_entry_one.GetValue(), self.auth_selector.GetSelection() + 1


class NewPasswordDialog(sized_controls.SizedDialog):
    def __init__(self, *args, **kwargs):
        username = kwargs.pop("username")
        super(NewPasswordDialog, self).__init__(*args, **kwargs)
        panel = self.GetContentsPane()

        pass_prompt_one = wx.StaticText(panel,
                                        wx.ID_ANY,
                                        "New Password:")
        self.pass_entry_one = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)

        pass_prompt_two = wx.StaticText(panel,
                                        wx.ID_ANY,
                                        "Re-enter Password:")
        self.pass_entry_two = wx.TextCtrl(panel, wx.ID_ANY, size=(200, -1), style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(wx.StaticText(panel,
                                     wx.ID_OK,
                                     "Enter new password for {}:".format(username.title())),
                       flag=wx.ALIGN_CENTER)

        inputs_sizer = wx.GridBagSizer(10, 10)

        inputs_sizer.Add(pass_prompt_one,
                         pos=(0, 0),
                         flag=wx.ALIGN_RIGHT)
        inputs_sizer.Add(self.pass_entry_one,
                         pos=(0, 1))
        inputs_sizer.Add(pass_prompt_two,
                         pos=(1, 0),
                         flag=wx.ALIGN_RIGHT)
        inputs_sizer.Add(self.pass_entry_two,
                         pos=(1, 1))

        main_sizer.AddSpacer(10)
        main_sizer.Add(inputs_sizer)

        panel_buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.button_ok = wx.Button(panel, wx.ID_OK, label='Confirm')
        self.button_ok.Disable()
        panel_buttons.Add(self.button_ok)
        self.button_ok.Bind(wx.EVT_BUTTON, self.on_button)

        button_cancel = wx.Button(panel, wx.ID_CANCEL, label='Cancel')
        panel_buttons.Add(button_cancel)
        button_cancel.Bind(wx.EVT_BUTTON, self.on_button)

        main_sizer.AddSpacer(10)
        main_sizer.Add(panel_buttons,
                       flag=wx.ALIGN_CENTER)

        self.status_text = wx.StaticText(panel, label="", size=(250, 20), style=wx.ALIGN_CENTER_HORIZONTAL)
        self.status_text.SetBackgroundColour((200, 200, 200))
        main_sizer.AddSpacer(10)
        main_sizer.Add(self.status_text,
                       flag=wx.ALIGN_CENTRE)

        panel.SetSizerAndFit(main_sizer)

        self.Bind(wx.EVT_TEXT, self.change)

        self.Fit()

    def change(self, e=None):
        errors = []
        if self.pass_entry_one.GetValue() == "":
            errors.append("Password required.")
        if self.pass_entry_two.GetValue() == "":
            errors.append("Re-enter password.")
        if self.pass_entry_one.GetValue() != self.pass_entry_two.GetValue():
            errors.append("Passwords do not match!")

        if len(errors) > 0:
            self.button_ok.Disable()
            self.status_text.SetLabelText(errors[0])
            self.status_text.SetBackgroundColour((255, 0, 0))
            self.status_text.SetForegroundColour((255, 255, 255))
        else:
            self.button_ok.Enable()
            self.status_text.SetLabelText("Details valid.")
            self.status_text.SetBackgroundColour((0, 200, 0))
            self.status_text.SetForegroundColour((255, 255, 255))

    def on_button(self, event):
        if self.IsModal():
            self.EndModal(event.EventObject.Id)
        else:
            self.Close()

    def GetValue(self):
        assert self.pass_entry_one.GetValue() == self.pass_entry_two.GetValue()
        assert self.pass_entry_one.GetValue() != ""
        return self.pass_entry_one.GetValue()


def call_if_callable(f, *args, **kwargs):
    if hasattr(f, "__call__"):
        return f(*args, **kwargs)
    else:
        return f


def launch_google_maps(location):
    base_url = "https://www.google.com/maps/search/?api=1&query={}"
    escaped = urllib.parse.quote(location)
    webbrowser.open(base_url.format(escaped))
