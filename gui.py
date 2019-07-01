import _thread
import time

import database_io
import wx
from globals import *
from wx.richtext import RichTextCtrl
from wx.lib import sized_controls


class Launcher(wx.Frame):
    database: database_io.DatabaseHandler

    def __init__(self, parent, frame_id, title, database):
        super().__init__(parent,
                         frame_id,
                         title,
                         style=wx.DEFAULT_FRAME_STYLE, #& ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX),
                         )

        self.title = title

        self.stock_viewer = None
        self.events_viewer = None
        self.control_panel = None

        self.database = database

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

        self.edit_label = wx.StaticText(panel,
                                        wx.ID_ANY,
                                        "")
        self.edit_label.SetForegroundColour((255, 255, 255))  # set text color
        self.edit_label.SetBackgroundColour((255, 0, 0))  # set text back color

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
        info_sizer.Add(self.edit_label)

        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSpacer(5)
        main_sizer.Add(info_sizer, proportion=1, flag=wx.EXPAND)
        main_sizer.AddSpacer(5)
        main_sizer.Add(button_sizer, flag=wx.EXPAND)
        main_sizer.AddSpacer(5)

        panel.SetSizerAndFit(main_sizer)

        self.Fit()
        self.update_upcoming()

        self.Bind(wx.EVT_TEXT_URL, self.event_clicked)
        self.Bind(wx.EVT_BUTTON, self.stock_button_clicked, self.stock_button)
        self.Bind(wx.EVT_BUTTON, self.events_button_clicked, self.events_button)
        self.Bind(wx.EVT_BUTTON, self.control_panel_button_clicked, self.control_panel_button)
        self.Bind(wx.EVT_BUTTON, self.user_button_clicked, self.user_button)

        _thread.start_new_thread(self.keep_label_updated, tuple())

        self.Show()

    def update_upcoming(self):
        with self.database.open_database_connection() as con:
            shows = self.database.get_shows(con)

        text = ""
        underlines = []
        headers = []
        bodies = []
        for s in shows:
            underline = [len(text), 0]
            text += s.date_time.ctime() + "\n"
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

    def keep_label_updated(self):
        while True:
            time.sleep(1)
            if self.database.signed_in_user() is None:
                text = ""
            else:
                text = " {} signed in. ".format(self.database.signed_in_user().name)
            self.edit_label.SetLabelText(text)

    def event_clicked(self, e):
        print("Clicked:", e.String)

    def stock_button_clicked(self, e):
        print("Stock Button Clicked")
        if self.stock_viewer is not None and self.stock_viewer.open:
            self.stock_viewer.Restore()
            self.stock_viewer.Raise()
        else:
            self.stock_viewer = StockViewer(self,
                                            wx.ID_ANY,
                                            self.title,
                                            self.database)

    def events_button_clicked(self, e):
        print("Events Button Clicked")

    def control_panel_button_clicked(self, e):
        print("Control Panel Button Clicked")

        if self.control_panel is not None and self.control_panel.open:
            self.control_panel.Restore()
            self.control_panel.Raise()
        else:
            self.control_panel = ControlPanel(self,
                                              wx.ID_ANY,
                                              self.title,
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
        self.control_panel_button.Enable()

    def logout(self):
        self.control_panel_button.Disable()
        self.database.sign_out()


class StockViewer(wx.Frame):
    def __init__(self, parent, frame_id, title, database: database_io.DatabaseHandler):
        self.title = title + " - Stock Viewer"
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE)
        self.title = title
        # self.Maximize(True)
        self.database = database
        self.open = True

        # Setup ListCtrl
        self.stock_list = wx.ListCtrl(self,
                                      size=(-1, -1),
                                      style=wx.LC_REPORT | wx.LC_HRULES)

        self.table_headers = {"SKU": ("sku", lambda x: str(x).zfill(6), 50),
                              "Product ID": ("product_id", lambda x: x, 70),
                              "Description": ("description", lambda x: x, 235),
                              "Category": ("category", lambda x: x, 70),
                              "Classification": ("classification", lambda x: x, 85),
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

        controls_panel = wx.Panel(self, -1)

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

        self.search_box = wx.SearchCtrl(controls_panel, size=(200, -1))
        self.search_box.SetDescriptiveText("Filter...")
        controls_sizer.Add(self.search_box, 0, wx.LEFT | wx.RIGHT, padding)

        # Add filter boxes.
        controls_sizer.AddSpacer(padding * 3)

        with self.database.open_database_connection() as con:
            self.categories_select = wx.CheckListBox(controls_panel,
                                                     wx.ID_ANY,
                                                     size=(200, 100),
                                                     choices=self.database.get_categories(con))

            self.classifications_select = wx.CheckListBox(controls_panel,
                                                          wx.ID_ANY,
                                                          size=(200, 75),
                                                          choices=self.database.get_classifications(con))

        self.select_all_categories(None)
        self.select_all_classifications(None)

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

        self.SetSizerAndFit(main_sizer)

        self.Show()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_BUTTON, self.select_all_categories, self.cat_select_all)
        self.Bind(wx.EVT_BUTTON, self.clear_categories, self.cat_clear_all)
        self.Bind(wx.EVT_BUTTON, self.select_all_classifications, self.class_select_all)
        self.Bind(wx.EVT_BUTTON, self.clear_classifications, self.class_clear_all)
        self.Bind(wx.EVT_LISTBOX, self.category_filter_changed, self.categories_select)
        self.Bind(wx.EVT_LISTBOX, self.classification_filter_changed, self.classifications_select)
        self.Bind(wx.EVT_BUTTON, self.create_button_clicked, self.create_new_button)
        self.Bind(wx.EVT_SIZING, self.update_table_size)
        # self.Bind(wx.EVT_MAXIMIZE, self.update_table_size)

        self.populate_table(None)
        self.update_table_size(None)

    def create_button_clicked(self, e=None):
        for i, h in enumerate(self.table_headers):
            print(h, ":", self.stock_list.GetColumnWidth(i))
        self.WarpPointer(-10, -10)

    def category_filter_changed(self, e):
        # Do stuff

        # Stop items being highlighted.
        self.categories_select.Deselect(self.categories_select.GetSelection())

    def classification_filter_changed(self, e):
        # Do stuff

        # Stop items being highlighted.
        self.classifications_select.Deselect(self.classifications_select.GetSelection())

    def select_all_categories(self, e):
        for i in range(len(self.categories_select.Items)):
            self.categories_select.Check(i, True)

    def clear_categories(self, e):
        for i in range(len(self.categories_select.Items)):
            self.categories_select.Check(i, False)

    def select_all_classifications(self, e):
        for i in range(len(self.classifications_select.Items)):
            self.classifications_select.Check(i, True)

    def clear_classifications(self, e):
        for i in range(len(self.classifications_select.Items)):
            self.classifications_select.Check(i, False)

    def populate_table(self, e=None):
        with self.database.open_database_connection() as con:
            stock_items = self.database.get_all_items(con)

        for i in stock_items:
            self.stock_list.Append(["" if getattr(i, self.table_headers[h][0]) is None else
                                    self.table_headers[h][1](getattr(i, self.table_headers[h][0]))
                                    for h in self.table_headers])

    def update_table_size(self, e=None):
        list_size = self.stock_list.GetSize()
        taken_space = 0
        for c in range(len(self.table_headers)):
            taken_space += self.stock_list.GetColumnWidth(c) if c != self.column_to_expand else 0
        new_width = (list_size[0] - taken_space) - 1
        self.stock_list.SetColumnWidth(self.column_to_expand, new_width)

    def on_close(self, e):
        self.open = False
        e.Skip()


class ControlPanel(wx.Frame):
    def __init__(self, parent, frame_id, title, database: database_io.DatabaseHandler):
        self.title = title + " - Control Panel"
        super().__init__(parent,
                         frame_id,
                         self.title,
                         style=wx.DEFAULT_FRAME_STYLE)
        self.database = database
        self.open = True

        if database.signed_in_user() is None:
            dlg = wx.MessageDialog(self, "YOU SHOULDN'T BE HERE!!!!\n\n"
                                         "The control panel tried to open without a user being signed in.",
                                   style=wx.OK | wx.ICON_EXCLAMATION,
                                   caption=">:(")
            dlg.ShowModal()
            self.open = False
            self.Destroy()
            return

        self.Show()

        # Bindings
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_close(self, e=None):
        self.open = False
        if e is not None:
            e.Skip()


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
