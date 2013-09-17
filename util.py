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

class Port(Frame):
    def __init__(self, parent, label, mapping):
        Frame.__init__(self, parent)
        Label(self, text=label).pack(side=TOP, expand=1, fill=X)
        self.listbox = Listbox(self, selectmode=EXTENDED, exportselection=0)
        self.listbox.pack(side=BOTTOM, expand=1, fill=X)
        self.port_map = []
        for name, port in mapping.iteritems():
            self.port_map.append(port)
            self.listbox.insert(END, name)

    def get_selected_ports(self):
        return [self.port_map[int(x)] for x in self.listbox.curselection()]

    def get_selected_port_names(self):
        return [self.listbox.get(int(x)) for x in self.listbox.curselection()]
        
    def select_names(self, names):
        reverse_map = dict((name, i) for i, name in enumerate(self.listbox.get(0, END)))
        self.listbox.selection_clear(0, END)
        for name in names:
            if name in reverse_map:
                self.listbox.selection_set(reverse_map[name])


class MultiPort(Frame):
    def __init__(self, parent, labels_and_mappings):
        Frame.__init__(self, parent)
        self.ports = [Port(self, label, mapping) for label, mapping in labels_and_mappings]
        height = max(port.listbox.size() for port in self.ports)
        for port in self.ports:
            port.listbox["height"] = height
            port.pack(side=LEFT, expand=1, fill=X)

    def get_selected_ports(self):
        return [port.get_selected_ports() for port in self.ports]

    def get_selected_port_names(self):
        return [port.get_selected_port_names() for port in self.ports]

    def select_names(self, names_list):
        for port, names in itertools.izip(self.ports, names_list):
            port.select_names(names)