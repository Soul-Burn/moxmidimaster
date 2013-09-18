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
import multiprocessing
import Queue
import threading
import tkFileDialog
import pickle
import imp
import os
import time
import pygame.midi as pym

class Proxy(object):
    def __init__(self, name, queue):
        self._name = name
        self._queue = queue

    def __getattr__(self, attr):
        def proxy_method(*args, **kwargs):
            self._queue.put((self._name, attr, args, kwargs))
        return proxy_method


class MasterUI(Tk):
    def __init__(self, ui_to_main, main_to_ui, initial_data):
        Tk.__init__(self)
        self.main_to_ui = main_to_ui
        self.ui_to_main = ui_to_main
        self.modules = []
        self.modules_map = {}
        self.main_proxy = Proxy("main", ui_to_main)
        self.initial_data = initial_data

        button_frame = Frame(self)
        Button(button_frame, text="Load module", command=self.load_module_dialog).pack(side=LEFT, expand=1, fill=X)
        Button(button_frame, text="Remove module", command=self.remove_module).pack(side=LEFT, expand=1, fill=X)
        Button(button_frame, text="Load set", command=self.load_set_dialog).pack(side=LEFT, expand=1, fill=X)
        Button(button_frame, text="Save set", command=self.save_set_dialog).pack(side=LEFT, expand=1, fill=X)
        button_frame.pack(side=BOTTOM, fill=X)

        self.modules_frame = Frame(self)
        self.modules_frame.pack(side=TOP, expand=1, fill=BOTH)

        try:
            self.load_set("default_set.txt")
        except IOError:
            pass

        self.after(100, self.update)
        self.after(100, self.read_queue)

    def load_module_dialog(self):
        path = tkFileDialog.askopenfilename(filetypes=[("Python modules", "*.py")])
        if path:
           self.load_module(path)

    def load_module(self, path):
        module_name = os.path.splitext(os.path.split(path)[1])[0]
        py_module = imp.load_source(module_name, path)

        module_frame = Frame(self.modules_frame, relief=SUNKEN, borderwidth=4)
        module_frame.pack(fill=BOTH)

        controls_frame = Frame(module_frame)
        controls_frame.pack(side=TOP, fill=X)
        Label(controls_frame, text=module_name).pack(side=LEFT, fill=X, expand=1)

        module = py_module.UI(module_frame, self.initial_data, Proxy(module_name, self.ui_to_main))

        def hide():
            button["text"] = "Show"
            button["command"] = show
            module.pack_forget()

        def show():
            button["text"] = "Hide"
            button["command"] = hide
            module.pack(fill=X, side=BOTTOM)

        button = Button(controls_frame, command=hide)
        button.pack(side=RIGHT)
        show()

        module_frame.name = module_name
        module_frame.path = path
        module_frame.module = module
        self.modules.append(module_frame)
        self.modules_map[module_name] = module
        self.main_proxy.load_module(module_name, path)
        return module

    def remove_module(self):
        if self.modules:
            module_frame = self.modules.pop()
            module_frame.destroy()
            del self.modules_map[module_frame.name]
            self.main_proxy.remove_module()

    def save_set_dialog(self):
        path = tkFileDialog.asksaveasfilename(defaultextension="txt", filetypes=[("Text", "*.txt"), ("All files", "*")])
        if path:
            self.save_set(path)

    def save_set(self, path):
        with open(path, "wb") as out:
            pickle.dump([(path, module.dump()) for name, path, module in self.modules], out)

    def load_set_dialog(self):
        path = tkFileDialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All files", "*")])
        if path:
            self.load_set(path)

    def load_set(self, path):
        while self.modules:
            self.remove_module()
        
        with open(path, "rb") as infile:
            module_data = pickle.load(infile)

        for path, module_dump in module_data:
            self.load_module(path).load(module_dump)

    def read_queue(self):
        try:
            event_count = 0
            while True:
                module_name, function_name, args, kwargs = self.main_to_ui.get_nowait()
                getattr(self.modules_map[module_name], function_name)(*args, **kwargs)
                event_count += 1
                if event_count >= 15:
                    self.update_idletasks()
                    event_count -= 15
        except Queue.Empty:
            pass

        self.update_idletasks()
        self.after(100, self.read_queue)

    def update(self):
        for module_frame in self.modules:
            module_frame.module.update()
        self.after(1000, self.update)


class Logic(object):
    def __init__(self, mox, main_to_ui, ui_to_main):
        mox.logic = self
        self.mox = mox
        self.ui_proxy = Proxy("main", main_to_ui)
        self.modules_map = {"main": self}
        self.modules = [self]
        self.output = self.final_handle

        def message_loop_thread():
            while True:
                try:
                    message = ui_to_main.get()
                    if message is None:
                        return

                    module_name, function_name, args, kwargs = message
                    getattr(self.modules_map[module_name], function_name)(*args, **kwargs)
                except Queue.Empty:
                    pass
        self.message_loop_thread = threading.Thread(target=message_loop_thread)
        self.message_loop_thread.daemon = True
        self.message_loop_thread.start()

    def handle(self, nTimestamp, port, channel, code, data1, data2):
        self.output(nTimestamp, port, channel, code, data1, data2)

    def final_handle(self, nTimestamp, port, channel, code, data1, data2):
        self.mox.OutputMidiMsg(port, (code << 4) + channel, data1, data2)

    def load_module(self, module_name, path):
        py_module = imp.load_source(module_name, path)
        module = py_module.Server(self.modules[-1].output, Proxy(module_name, main_to_ui))
        module.name = module_name
        self.modules_map[module_name] = module
        self.modules[-1].output = module.handle
        self.modules.append(module)

    def remove_module(self):
        module = self.modules.pop()
        self.modules[-1].output = module.output
        del self.modules_map[module.name]


class Mox(object):
    def __init__(self):
        self.pin = {}
        self.pout = {}
        for i in xrange(pym.get_count()):
            info = pym.get_device_info(i)
            if info[2]:
                self.pin[i] = pym.Input(i)
            if info[3]:
                self.pout[i] = pym.Output(i)
                
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def _run(self):
        while True:
            any_handled = False
            for i, dev in self.pin.iteritems():
                if not dev.poll() or self.logic is None:
                    continue
                for event, timestamp in dev.read(10):
                    status, data1, data2, data3 = event
                    self.logic.handle(time.clock(), i , status & 0xF, status >> 4, data1, data2)

            if not any_handled:
                time.sleep(0.005)
    
    def OutputMidiMsg(self, port, status, data1, data2):
        self.pout[port].write_short(status, data1, data2)

def master_ui(ui_to_main, main_to_ui, initial_data):
    MasterUI(ui_to_main, main_to_ui, initial_data).mainloop()
    ui_to_main.put(None)


def create_initial_data(mox):
    pin = {}
    pout = {}
    for i in xrange(pym.get_count()):
        info = pym.get_device_info(i)
        name = info[1]
        if info[2]:
            pin[name] = i
        if info[3]:
            pout[name] = i
    
    return {"ports_in": pin, "ports_out": pout}


if __name__ == "__main__":
    pym.init()
    mox = Mox()
    
    ui_to_main = multiprocessing.Queue()
    main_to_ui = multiprocessing.Queue()
    ui_process = multiprocessing.Process(target=master_ui, args=(ui_to_main, main_to_ui, create_initial_data(mox)))
    ui_process.start()

    logic = Logic(mox, main_to_ui, ui_to_main)
    raw_input("Enter to stop...")
    sys.exit(0)