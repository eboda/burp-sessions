from burp import IParameter
from BurpExtender import attach_stack_trace

class Parameter:
    """Represents a modified parameter."""


    PARAM_COOKIE = IParameter.PARAM_COOKIE
    PARAM_BODY = IParameter.PARAM_BODY
    PARAM_URL = IParameter.PARAM_URL
    PARAM_HEADER = 1337

    ACTION_ADD = "insert"
    ACTION_REMOVE = "delete"
    ACTION_MODIFY = "replace"

    type_mapping = {
            PARAM_HEADER : "Header",
            PARAM_BODY : "POST",
            PARAM_URL : "GET",
            PARAM_COOKIE : "Cookie"
    }


    def __init__(self, type, action, key, val):
        self.type = -1
        if isinstance(type, int):
            self.type = type
        elif isinstance(type, str):
            for k, v in Parameter.type_mapping.items():
                if v == type:
                    self.type = k

        self.key = key
        self.val = val
        self.action = action

    def as_table_row(self):
        """Returns this parameter as a table row for a JTable"""

        return [Parameter.type_mapping[self.type], self.action, self.key, self.val]

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and 
                self.type == other.type and
                self.key == other.key)

    def __ne__(self, other):
        return not self.__eq__(other)

class SessionManagement(object):
    """Manages all created sessions."""

    def __init__(self):
        self.sessions = []
        self._selected_session = 0
        self.new_session("Original Request")

    @property
    def selected_session(self):
        return self._selected_session

    @selected_session.setter
    def selected_session(self, value):
        if isinstance(value, int): 
            self._selected_session = self.sessions[value]
        elif isinstance(value, Session):
            self._selected_session = value


    def new_session(self, name):
        session = Session(name)
        self.sessions.append(session)
        self.selected_session = len(self.sessions) - 1

    def remove_session(self):
        idx = self.sessions.index(self.selected_session)
        if idx > 0: # only remove if it is not the Original Session
            self.sessions.pop(idx)
            # Fix selected_session if removed session was last session
            if len(self.sessions) - 1 < idx:
                self.selected_session = len(self.sessions) - 1
                
    
    
class Session:
    """Represents a Session."""
        
    def __init__(self, name):
        self.name = name
        self.params = []

    def modify(self, par):
        """Modifies the session by appending a new Parameter."""

        if par in self.params:
            self.params.remove(par)
        self.params.append(par)

    def reset(self):
        self.params = []


    def __eq__(self, other):
        return (isinstance(other, self.__class__) and 
            self.name == other.name)
    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self.name
    def __repr__(self):
        return self.name
