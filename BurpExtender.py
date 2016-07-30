from burp import *

import sys
import re
import traceback
 
from ui import *
from model import *

DEBUG = True


def attach_stack_trace(original_function):
    """Fixes the debugging output in BurpSuite"""

    def decorated_function(*args, **kwargs):
        try:
            return original_function(*args, **kwargs)
        except:
            if DEBUG:
                sys.stdout.write('\n\n*** PYTHON EXCEPTION\n')
                traceback.print_exc(file=sys.stdout)
            raise
    decorated_function.__name__ = original_function.__name__
    return decorated_function




class BurpExtender(IBurpExtender, IMessageEditorTabFactory):
    """Provides basic funcionality for the extension."""
 
    @attach_stack_trace
    def registerExtenderCallbacks(self, callbacks):
        # fix the debugging output
        if DEBUG:
            sys.stdout = callbacks.getStdout()

        self.callbacks = callbacks
        self.helpers = callbacks.getHelpers()
        callbacks.setExtensionName("Sessions")

        self._HTTP = ""
        self.sm = SessionManagement()

        callbacks.registerMessageEditorTabFactory(self)

    @property
    def HTTP(self):
        return self._HTTP

    @HTTP.setter
    def HTTP(self, value):
        request_info = self.helpers.analyzeRequest(value)
        self.headers = list(request_info.getHeaders())
        self.parameters = list(request_info.getParameters())

        self._HTTP = value


    def createNewInstance(self, controller, editable):
        """Creates a new instance of our tab."""

        return SessionRequestTab(self, controller, editable)


    @attach_stack_trace
    def remove_multi_part(self, name, request):
        """ Hacky solution for multipart POST data.

        There is a bug with burpsuite, which doesn't allow replacing
        parameters in multipart POST data correctly.
        """
        request = self.helpers.bytesToString(request)
        start, end = -1, -1
        boundary = re.search("boundary=(.*)\r\n", request).group(1)
        lines = request.split("\r\n")
        for i in range(len(lines)):
            if re.search("Content-Disposition: form-data; name=\"%s\"" % name, lines[i]) is not None:
                start = i
            if boundary in lines[i] and start != -1:
                end = i
                break
        request = '\r\n'.join(lines[:start] + lines[end+1:])
        length = len(request) - request.index(boundary)
        print length, start, end
        request = re.sub("(Content-Length:) .*(\r\n)", r"\1 %d\2" % length, request)
        return  self.helpers.stringToBytes(request)


 
    @attach_stack_trace
    def process_request(self, current_request):
        """Processes a HTTP request before submitting it

        The original HTTP request is modified by adding, removing or changing
        some of its headers and parameters according to the currently active
        session.
        """
        request_info = self.helpers.analyzeRequest(current_request)

        headers = list(request_info.getHeaders())
        parameters = list(request_info.getParameters())

        # Replace/remove old headers
        new_headers = []
        for header in  headers:
            for param in self.sm.selected_session.params:
                if param.type == Parameter.PARAM_HEADER and param.key == header.split(":")[0]:
                    if param.action == Parameter.ACTION_MODIFY:
                        new_headers.append(param.key + ": " + self.helpers.urlEncode(param.val))
                        break
                    if param.action == Parameter.REMOVE:
                        break
            else:   # header was not removed/modified, use original
                new_headers.append(header)

        # Add new headers
        for param in self.sm.selected_session.params:
            if param.action == Parameter.ACTION_ADD and param.type == Parameter.PARAM_HEADER:
                new_headers.append(param.key + ": " + self.helpers.urlEncode(param.val))

        # generate HTTP request with new headers
        body_bytes = current_request[request_info.getBodyOffset():]
        body_str = self.helpers.bytesToString(body_bytes)
        request = self.helpers.buildHttpMessage(new_headers, body_str)


        # Replace parameters
        new_params = { Parameter.ACTION_ADD : [],
                        Parameter.ACTION_MODIFY : [],
                        Parameter.ACTION_REMOVE : [] }
        multi_part_remove = []
        # Replace/remove old parameters
        for par in  parameters:
            # Iterate over modified parameters of active session
            for param in self.sm.selected_session.params:
                if param.type == par.getType() and param.key == par.getName():
                    new_params[param.action].append(self.helpers.buildParameter(param.key, self.helpers.urlEncode(param.val), param.type))
                    # *TODO* THIS IS A HACK, cause Burp API is broken....
                    if param.type == IParameter.PARAM_BODY and request_info.getContentType() == IRequestInfo.CONTENT_TYPE_MULTIPART:
                        request = self.remove_multi_part(param.key, request)


        # Add new parameters
        new_params[Parameter.ACTION_ADD] = []
        for param in self.sm.selected_session.params:
            if param.action == Parameter.ACTION_ADD:
                if param.type != Parameter.PARAM_HEADER:
                    new_params[Parameter.ACTION_ADD].append(self.helpers.buildParameter(param.key, self.helpers.urlEncode(param.val), param.type))

        # add modified parameters
        for param in new_params[Parameter.ACTION_MODIFY]:
            request = self.helpers.updateParameter(request, param)

        # add new parameters
        for param in new_params[Parameter.ACTION_ADD]:
            request = self.helpers.addParameter(request, param)

        # remove deleted parameters
        for param in new_params[Parameter.ACTION_REMOVE]:
            request = self.helpers.removeParameter(request, param)

        for param in multi_part_remove:
            request = self.helpers.removeParameter(request, param)

        return  request
