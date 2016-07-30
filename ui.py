from burp import *

from javax.swing import JDialog, JTable, JButton, JPanel
from javax.swing import JComboBox, JLabel, JOptionPane
from javax.swing import DefaultCellEditor, JScrollPane
from javax.swing import DefaultComboBoxModel
from javax.swing.table import DefaultTableModel, TableColumn
from java.awt import GridBagLayout
from java.awt import Insets
from java.awt import BorderLayout
from java.awt.event import ActionListener
from java.awt import GridBagConstraints
from java.lang import String, Boolean

from model import *
from BurpExtender import attach_stack_trace

def _new_grid_bag(gridx, gridy, gridwidth=1):
    """Creates a new GridBagConstraints"""

    g = GridBagConstraints()
    g.gridx = gridx
    g.gridy = gridy
    g.gridwidth = gridwidth
    g.fill = GridBagConstraints.BOTH
    g.insets = Insets(2,2,5,5)

    return g

class SessionFromRequestDialog(JDialog):
    def should_use(self, name):
        """Suggests if parameter with provided name should be used"""

        suggestions = ["session",  "authenticity", "csrf", "xsrf"]
        name = name.lower()
        return any(map(lambda x: x in name, suggestions))

    def save(self, evt):
        model = self.table.getModel()
        session = self._parent._extender.sm.selected_session
        session.reset()
        for r in range(model.getRowCount()):
            use = bool(model.getValueAt(r, 0))
            type = str(model.getValueAt(r, 1))
            name = model.getValueAt(r, 2)
            value = model.getValueAt(r, 3)

            if use:
                param = Parameter(type, Parameter.ACTION_MODIFY, name, self._parent._extender.helpers.urlDecode(value))
                session.modify(param)
        self.setVisible(False)
        self.dispose()
        self._parent.refresh_sessions()
        self._parent.update_table()



    @attach_stack_trace
    def __init__(self, parent):
        self._parent = parent
        self.setTitle("Select Parameters/Headers for new Session")

        print "IN DIALOG!Q!!"

        self.table = JTable()

        columns = ["Use", "Type", "Name", "Value"]
        data = []

        headers = self._parent._extender.headers
        parameters = self._parent._extender.parameters

        for header in headers[1:]:
            name, val = header.split(": ")
            data.append([self.should_use(name), "Header", name, val])

        for param in parameters:
            data.append([self.should_use(param.getName()), Parameter.type_mapping[param.getType()], param.getName(), param.getValue()])

        class CheckBoxTableModel(DefaultTableModel):
            def getColumnClass(self, x):
                if x == 0:
                    return Boolean
                else:
                    return String

        data_model = CheckBoxTableModel(data, columns)
        self.table.setModel(data_model)
        self.table.getColumnModel().getColumn(0).setMaxWidth(30)
        self.table.getColumnModel().getColumn(1).setMaxWidth(50)


        gridBagLayout = GridBagLayout()
        gridBagLayout.columnWidths = [ 0, 0, 0]
        gridBagLayout.rowHeights = [0, 0, 0]
        gridBagLayout.columnWeights = [0.0, 0.0, 0.0]
        gridBagLayout.rowWeights = [0.0, 1.0, 0.0]
        self.setLayout(gridBagLayout)

        self.getContentPane().add(JLabel("Select Parameters/Headers for new session:"), _new_grid_bag(0, 0, 3))
        self.getContentPane().add(JScrollPane(self.table), _new_grid_bag(0, 1, 3))
        self.getContentPane().add(JButton("Save", actionPerformed=self.save), _new_grid_bag(1, 2))

        self.pack()
        self.setVisible(True)



class SessionRequestTab(IMessageEditorTab):
    """UI of the extension."""

    def refresh_sessions(self):
        self._session_selector.setModel(DefaultComboBoxModel(self._extender.sm.sessions))
        self._session_selector.setSelectedItem(self._extender.sm.selected_session)

    def deleteSession(self, evt):
        """Listener for the Delete Session button."""

        if JOptionPane.showConfirmDialog(None, "Are you sure?", "", JOptionPane.YES_NO_OPTION) == JOptionPane.OK_OPTION:
            self._extender.sm.remove_session()
            self.refresh_sessions()
            self.update_table()
            self.parse_message()

    @attach_stack_trace
    def new_session(self, evt):
        """Listener for New Session button."""

        name = JOptionPane.showInputDialog(None, "Name the new session:", "Session name")
        if name != None:
            from_request = JOptionPane.showConfirmDialog(None, "Create session from current request?", "From current request?", JOptionPane.YES_NO_OPTION)
            self._extender.sm.new_session(name)
            self.refresh_sessions()

            # let user select parameters for new session
            if from_request == JOptionPane.OK_OPTION:
                dialog = SessionFromRequestDialog(self)
                dialog.setVisible(True)

    def changeSession(self, evt):
        """Listener for session combobox"""

        if evt.getStateChange() == 1:
            session = evt.getItem()
            self._extender.sm.selected_session = session
            self.update_table()
            self.parse_message()

    @attach_stack_trace
    def update_table(self):
        """Updates the table with new data"""

        columns = ["Type", "Action", "Name", "Value"]
        data = []
        for param in self._extender.sm.selected_session.params:
            data.append(param.as_table_row())

        data.append([Parameter.type_mapping[Parameter.PARAM_COOKIE], Parameter.ACTION_MODIFY, "", ""])
        data_model = DefaultTableModel(data, columns, tableChanged=self.tableChanged)
        self.modification_table.setModel(data_model)

        # type combobox
        type_combo = JComboBox(self._types)
        type_column = self.modification_table.getColumnModel().getColumn(0)
        type_column.setCellEditor(DefaultCellEditor(type_combo))
        type_column.setMaxWidth(75)

        # action combobox
        action_combo = JComboBox(self._actions)
        action_column = self.modification_table.getColumnModel().getColumn(1)
        action_column.setCellEditor(DefaultCellEditor(action_combo))
        action_column.setMaxWidth(75)
        action_combo.setSelectedItem("replace")

    @attach_stack_trace
    def tableChanged(self, evt):
        """Handles changes to table cells, i.e. Parameter changes."""
        if evt.getType() == 0:      # UPDATING a cell
            table_model = evt.getSource()
            row = evt.getFirstRow()
            col = evt.getColumn()

            # Removing a row was selected
            if col == 0 and "Remove Row" in table_model.getValueAt(row, col) and table_model.getRowCount() > 1:
                table_model.removeRow(row)

            # update the model
            session = self._extender.sm.selected_session
            session.reset()
            for r in range(table_model.getRowCount() - 1):
                type = str(table_model.getValueAt(r, 0))
                action = str(table_model.getValueAt(r, 1))
                name = table_model.getValueAt(r, 2)
                value = table_model.getValueAt(r, 3)

                if type != None and name != None and value != None:
                    param = Parameter(type, action, name, self._extender.helpers.urlDecode(value))
                    session.modify(param)


            # Check if there is an empty last row 
            has_empty_row = True
            for i in range(2, 4):
                val = table_model.getValueAt(table_model.getRowCount() - 1, i)
                if val != None and val != "":
                    has_empty_row = False
                    break

            # no empty last row, add one
            if not has_empty_row:
                table_model.addRow(["", Parameter.ACTION_MODIFY, "", ""])

            # update message editor
            self.parse_message()

    def parse_message(self):
        self._editor.setText(self._extender.process_request(self._extender.HTTP))

    def getTabCaption(self):
        return "Session"

    def getUiComponent(self):
        return self._panel

    def isEnabled(self, content, isRequest):
        return isRequest 

    def setMessage(self, content, isRequest):
        self._extender.HTTP = self._extender.helpers.bytesToString(content)
        self._editor.setText(content)
        self.refresh_sessions()
        self.update_table()


    def getMessage(self):
        return self._editor.getText()

    def isModified(self):
        return self._editor.isTextModified()

    def getSelectedData(self):
        return self._editor.getSelectedText()

    @attach_stack_trace
    def __init__(self, extender, controller, editable):
        self._extender = extender

        self._panel = JPanel()  # main panel

        # type combobox for tables
        self._types = Parameter.type_mapping.values() + ["- Remove Row -"]
        self._actions = ["replace", "insert", "delete"]

        # define the GridBagLayout ( 4x4 )
        gridBagLayout = GridBagLayout()
        gridBagLayout.columnWidths = [ 0, 0, 0, 0]
        gridBagLayout.rowHeights = [0, 0, 0, 0]
        gridBagLayout.columnWeights = [1.0, 0.0, 0.0, 0.0]
        gridBagLayout.rowWeights = [0.0, 1.0, 5.0, 0.0]
        self._panel.setLayout(gridBagLayout)

        # JComboBox for Session selection
        self._session_selector = JComboBox(extender.sm.sessions, itemStateChanged=self.changeSession)
        self._session_selector_model = self._session_selector.getModel()
        gbc_session_selector = _new_grid_bag(0, 0)
        self._panel.add(self._session_selector, gbc_session_selector)


        # "Delete Session" Button
        del_session = JButton("Delete Session", actionPerformed=self.deleteSession)
        gbc_del_session = _new_grid_bag(1, 0)
        self._panel.add(del_session, gbc_del_session)

        # "New Session" Button
        new_session = JButton("New Session", actionPerformed=self.new_session)
        gbc_new_session = _new_grid_bag(2, 0)
        self._panel.add(new_session, gbc_new_session)

        # Table containing modified parameters
        self.modification_table = JTable()
        self.update_table()

        gbc_modification_table = _new_grid_bag(0, 1, 3)
        self._panel.add(JScrollPane(self.modification_table), gbc_modification_table)
        self.modification_table.setPreferredScrollableViewportSize(self.modification_table.getPreferredSize());
        self.modification_table.setFillsViewportHeight(True)

        # HTTP message editor
        self._editor = self._extender.callbacks.createTextEditor()
        gbc_messageEditor = _new_grid_bag(0, 2, 3)
        self._panel.add(self._editor.getComponent(), gbc_messageEditor)



