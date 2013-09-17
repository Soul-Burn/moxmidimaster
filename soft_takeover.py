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
import util

class UI(Frame):
    def __init__(self, parent, initial_data, server):
        Frame.__init__(self, parent)
        self.server = server
        
        self.table = Frame(self)
        self.table.pack()

        self.ports = util.MultiPort(self, [("Remotes", initial_data["ports_in"]), ("Returns", initial_data["ports_in"])])
        self.ports.pack(side=TOP, fill=X)

    def update(self):
        self.server.set_ports(*self.ports.get_selected_ports())

    def set_table(self, table):
        for child in self.table.children.values():
            child.destroy()
        
        def addrow(*values):
            last_row = self.table.grid_size()[1]
            for i, value in enumerate(values):
                Label(self.table, text=value).grid(row=last_row, column=i)
        
        addrow("channel", "cc#", "value")
        for key in sorted(table):
            addrow(key[0], key[1], table[key])

    def load(self, dump):
        self.ports.select_names(dump)

    def dump(self):
        return self.ports.get_selected_port_names()


class Server(object):
    def __init__(self, output, ui):
        self.output = output
        self.remote_ports = []
        self.return_ports = []        
        self.remote_table = {}
        self.return_table = {}
        self.ui = ui
    
    def handle(self, nTimestamp, port, channel, code, data1, data2):
        if self.should_send(port, channel, code, data1, data2):
            self.output(nTimestamp, port, channel, code, data1, data2)

    def should_send(self, port, channel, code, data1, data2):
        if code != 11:
            return True

        key = channel, data1
        if port in self.return_ports:
            if key not in self.remote_table or self.remote_table[key] != data2:
                self.return_table[key] = data2
                self.ui.set_table(self.return_table)
            return True
            
        if port not in self.remote_ports:
            return True
        
        old = self.remote_table[key] if key in self.remote_table else data2
        self.remote_table[key] = data2
        
        if key not in self.return_table:
            return True

        minv, maxv = sorted((old, data2))
        catch = 1
        if minv - catch <= self.return_table[key] <= maxv + catch:
            self.ui.set_table(self.return_table)
            del self.return_table[key]
            return True

        return False

    def set_ports(self, remote_ports, return_ports):
        self.remote_ports = remote_ports
        self.return_ports = return_ports