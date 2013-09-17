"""
Copyright (c) 2013 by Tomer Altman <tomer.altman@gmail.com>

This file is part of moxmidimaster.

moxmidimaster is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

moxmidimaster is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with moxmidimaster.  If not, see <http://www.gnu.org/licenses/>.
"""

from Tkinter import *
import itertools
import util

class UI(Frame):
    def __init__(self, parent, initial_data, server):
        Frame.__init__(self, parent)
        self.ports = []
        self.server = server
        self.ports_in = initial_data["ports_in"]
        self.ports_out = initial_data["ports_out"]

        button_frame = Frame(self)
        Button(button_frame, text="Add mapping", command=self.add_port_mapping).pack(side=LEFT, expand=1, fill=X)
        Button(button_frame, text="Remove mapping", command=self.remove_port_mapping).pack(side=LEFT, expand=1, fill=X)
        button_frame.pack(side=TOP, fill=X)

    def add_port_mapping(self):
        multiport = util.MultiPort(self, [("From", self.ports_in), ("To", self.ports_out)])
        multiport.pack(side=TOP, expand=1, fill=X)
        self.ports.append(multiport)

    def remove_port_mapping(self):
        if self.ports:
            self.ports.pop().destroy()

    def update(self):
        self.server.set_port_mapping([multiport.get_selected_ports() for multiport in self.ports])

    def load(self, dump):
        while len(self.ports) < len(dump):
            self.add_port_mapping()
        while len(self.ports) > len(dump):
            self.remove_port_mapping()
        for multiport, names in itertools.izip(self.ports, dump):
            multiport.select_names(names)

    def dump(self):
        return [multiport.get_selected_port_names() for multiport in self.ports]



class Server(object):
    def __init__(self, output, ui):
        self.output = output
        self.port_mapping = []

    def handle(self, nTimestamp, port, channel, code, data1, data2):
        for ports_from, ports_to in self.port_mapping:
            if port in ports_from:
                for port_to in ports_to:
                    self.output(nTimestamp, port_to, channel, code, data1, data2)

    def set_port_mapping(self, port_mapping):
        self.port_mapping = port_mapping