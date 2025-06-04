import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import time
import threading
from requests.adapters import ConnectionError
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
"""
from Andor on DF machine, but then modified
"""
import fusionrest  # import functionality provided by Andor (and expanded for loading the last image)
from get_current_image import get_current_image_2d  # import image loader functions
import trigger_functions  # import trigger functions


class PrintColors:
    # for printing_in_colors
    # from https://stackoverflow.com/questions/287871/how-do-i-print-colored-text-to-the-terminal 20th May 2025
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class IfTriggerDialog(simpledialog.Dialog):
    """
    Dialog asking for details on if trigger (trigger function, < or > and a trigger value).
    """
    def body(self, master):
        ttk.Label(master, text="Condition (e.g., < or >):").grid(row=0, column=0)
        ttk.Label(master, text="Threshold:").grid(row=1, column=0)
        ttk.Label(master, text="Trigger Function:").grid(row=2, column=0)

        self.condition = ttk.Entry(master, width=5)
        self.condition.insert(0, "<")
        self.condition.grid(row=0, column=1, padx=5)

        self.threshold = ttk.Entry(master, width=10)
        self.threshold.insert(0, "5.0")
        self.threshold.grid(row=1, column=1, padx=5)

        self.trigger_function_var = tk.StringVar()
        self.trigger_function_menu = ttk.Combobox(master, textvariable=self.trigger_function_var, width=30, state="readonly")
        self.trigger_function_menu.grid(row=2, column=1, padx=5)

        # Load functions only defined in trigger_functions.py (exclude imports)
        import trigger_functions
        import inspect
        import types
        self.trigger_funcs = {
            name: func for name, func in inspect.getmembers(trigger_functions, inspect.isfunction)
            if func.__module__ == trigger_functions.__name__
        }
        self.trigger_function_menu['values'] = list(self.trigger_funcs.keys())
        if self.trigger_funcs:
            self.trigger_function_menu.set(list(self.trigger_funcs.keys())[0])

        return self.condition  # initial focus

    def apply(self):
        try:
            condition = self.condition.get()
            threshold = float(self.threshold.get())
            trigger_func_name = self.trigger_function_var.get()
            if condition in ("<", ">") and trigger_func_name:
                self.result = {
                    "trigger": {
                        "condition": condition,
                        "threshold": threshold,
                        "function_name": trigger_func_name
                    }
                }
            else:
                raise ValueError
        except Exception:
            messagebox.showerror("Error", "Invalid input for trigger condition or threshold.")
            self.result = None


class LoopDialog(simpledialog.Dialog):
    """
    Dialog asking for details on nested loop (repeats, duration, if a trigger should be added and if yes,
    with what conditions (trigger function, < or > and a trigger value).
    """
    def body(self, master):
        ttk.Label(master, text="Repeats:").grid(row=0)
        ttk.Label(master, text="Interval (s):").grid(row=1)
        self.repeats = ttk.Entry(master)
        self.interval = ttk.Entry(master)
        self.trigger_var = tk.IntVar()
        self.trigger_frame = ttk.Frame(master)
        self.trigger_checkbox = ttk.Checkbutton(self.trigger_frame, text="Add Trigger", variable=self.trigger_var,
                                                command=self.toggle_trigger)
        self.trigger_checkbox.pack(side=tk.LEFT)

        # Load trigger functions from the trigger_functions module
        self.trigger_funcs = []
        for name, func in trigger_functions.__dict__.items():
            if callable(func) and func.__module__ == 'trigger_functions' and not name.startswith("_"):
                self.trigger_funcs.append(name)

        self.trigger_func_var = tk.StringVar(value=self.trigger_funcs[0] if self.trigger_funcs else "")

        self.trigger_func_menu = ttk.Combobox(self.trigger_frame, textvariable=self.trigger_func_var,
                                              values=self.trigger_funcs, state="readonly", width=40)
        self.condition = ttk.Entry(self.trigger_frame, width=5)
        self.threshold = ttk.Entry(self.trigger_frame, width=10)
        self.condition.insert(0, "<")
        self.threshold.insert(0, "5.0")
        self.trigger_func_menu.pack(side=tk.LEFT, padx=2)
        self.condition.pack(side=tk.LEFT, padx=2)
        self.threshold.pack(side=tk.LEFT, padx=2)

        self.repeats.grid(row=0, column=1)
        self.interval.grid(row=1, column=1)
        self.trigger_frame.grid(row=2, columnspan=2, pady=5)
        return self.repeats

    def toggle_trigger(self):
        state = tk.NORMAL if self.trigger_var.get() else tk.DISABLED
        self.condition.configure(state=state)
        self.threshold.configure(state=state)
        self.trigger_func_menu.configure(state=state)

    def apply(self):
        try:
            self.result = {
                "count": int(self.repeats.get()),
                "interval": float(self.interval.get()),
                "trigger": None
            }
            if self.trigger_var.get():
                threshold = float(self.threshold.get())
                condition = self.condition.get()
                trigger_func = self.trigger_func_var.get()
                if condition in ('<', '>') and trigger_func:
                    self.result["trigger"] = {
                        "function": trigger_func,
                        "threshold": threshold,
                        "condition": condition
                    }
        except ValueError:
            messagebox.showerror("Error", "Invalid input. Please check your values.")
            self.result = None


class FunctionLooperApp(tk.Tk):
    """
    Main body with the function looper app interface in which loops and protocols can be added
    """
    def __init__(self):
        super().__init__()
        self.start_time_global = time.time()  # set a start time, it will be overwritten when the main loop is started
        self.title("Function Queue Looper with Adjusted Loop Timing")
        self.geometry("700x500")

        self.queue = []
        self.running = False

        self.current_nesting = 0

        self.repeat_count = tk.IntVar(value=1)
        self.main_interval = tk.DoubleVar(value=0.0)

        self.create_widgets()

    def create_widgets(self):
        # Function buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Add Protocol", command=self.add_protocol).pack(side=tk.LEFT, padx=5)
        """
            ttk.Button(button_frame, text="Wait until idle", command=lambda: self.add_to_queue(
            "func", self.wait_until_idle, label="Wait until idle")).pack(side=tk.LEFT, padx=5)
        """
        ttk.Button(button_frame, text="Get Progress", command=lambda: self.add_to_queue(
            "func", self.get_progress, label="Get progress")).pack(side=tk.LEFT, padx=5)
        # In the create_widgets method
        ttk.Button(button_frame, text="Show z-projection",
                   command=lambda: self.add_to_queue("func", self.show_z_projection,
                                                     label="Show z-projection")).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Wait", command=self.add_waiting_time).pack(side=tk.LEFT, padx=5)

        # Inner loop controls
        loop_frame = ttk.Frame(self)
        loop_frame.pack(pady=10)

        ttk.Button(loop_frame, text="Start Inner Loop", command=self.add_inner_loop_start).pack(side=tk.LEFT, padx=5)
        ttk.Button(loop_frame, text="End Inner Loop", command=self.add_inner_loop_end).pack(side=tk.LEFT, padx=5)
        ttk.Button(loop_frame, text="Add if Statement", command=self.add_if_trigger).pack(side=tk.LEFT, padx=5)
        ttk.Button(loop_frame, text="Remove Last", command=self.remove_last_item).pack(side=tk.LEFT, padx=5)

        # Queue display
        self.queue_display = tk.Text(self, height=14, width=90, state=tk.DISABLED)
        self.queue_display.pack(pady=10)

        # Main loop control
        control_frame = ttk.Frame(self)
        control_frame.pack()

        ttk.Label(control_frame, text="Main Repeats:").grid(row=0, column=0, padx=5)
        ttk.Spinbox(control_frame, from_=1, to=100, textvariable=self.repeat_count, width=5).grid(row=0, column=1)

        ttk.Label(control_frame, text="Main Interval (s):").grid(row=0, column=2)
        ttk.Entry(control_frame, textvariable=self.main_interval, width=5).grid(row=0, column=3, padx=5)

        # Action buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(pady=15)

        ttk.Button(action_frame, text="Start Loop", command=self.start_loop).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Stop", command=self.stop_loop).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Clear Queue", command=self.clear_queue).pack(side=tk.LEFT, padx=5)

    def add_protocol(self):
        protocol_text = simpledialog.askstring("Protocol Input", "Enter protocol name [case sensitive]:")
        if protocol_text:
            self.add_to_queue("func", lambda: self.set_protocol(protocol_text),
                              label=f"Protocol: {protocol_text}")

    def add_waiting_time(self):
        waiting_time = simpledialog.askfloat("Waiting time", "Enter the waiting time (s):")
        if waiting_time:
            self.add_to_queue("func", lambda: self.wait(waiting_time), label=f"Waiting for {str(waiting_time)} s")

    def add_inner_loop_start(self):
        dialog = LoopDialog(self, title="Start Inner Loop")
        if dialog.result:
            self.add_to_queue("loop_start", dialog.result)

    def add_inner_loop_end(self):
        self.add_to_queue("loop_end")

    def add_if_trigger(self):
        dialog = IfTriggerDialog(self, title="If Trigger")
        if dialog.result:
            self.add_to_queue("loop_start", {"trigger": dialog.result['trigger'], "is_conditional": True})

    def add_to_queue(self, item_type, value=None, label=None):
        self.queue.append({'type': item_type, 'value': value, 'label': label, 'is_conditional':False})
        self.update_queue_display()

    def remove_last_item(self):
        if self.queue:
            self.queue.pop()
            self.update_queue_display()

    def update_queue_display(self):
        # update the queue display by adding the next item correctly
        self.queue_display.config(state=tk.NORMAL)
        self.queue_display.delete("1.0", tk.END)
        indent = 0
        for item in self.queue:
            if item['type'] == 'loop_end':
                indent -= 2
            line = " " * indent
            if item['type'] == 'func':
                line += f"- {item.get('label', item['value'].__name__)}"
            elif item['type'] == 'trigger':
                line += f"- {item.get('label')}"
            elif item['type'] == 'loop_start':
                loop_info = item['value']
                if 'is_conditional' in loop_info and loop_info['is_conditional']:
                    trigger = loop_info['trigger']
                    line += f" If trigger: {trigger['condition']} {trigger['threshold']}"
                else:
                    line += f"[ Start Loop x{loop_info.get('count', 1)}, Interval {loop_info.get('interval', 0)}s ]"
                    if loop_info.get('trigger'):
                        trigger = loop_info['trigger']
                        line += f" Trigger: {trigger['condition']} {trigger['threshold']}"
                indent += 2
            elif item['type'] == 'loop_end':
                line += "[ End Loop ]"
            self.queue_display.insert(tk.END, line + "\n")
        self.queue_display.config(state=tk.DISABLED)

    def clear_queue(self):
        # reset the queue to be empty if the clear queue button is pressed
        self.queue = []
        self.update_queue_display()

    def start_loop(self):
        # if the queue is empty or something is already running, don't do anything when this button is pressed
        if not self.queue or self.running:
            return
        # otherwise start running the main loop queue
        self.running = True
        self.start_time_global = time.time()
        threading.Thread(target=self.run_main_loop, daemon=True).start()

    def stop_loop(self):
        # stop the main loop by setting self.running to false if the stop button is pressed
        self.running = False
        # also stop the microscope
        fusionrest.stop()

    def run_main_loop(self):
        # run the main loop: get the start time for each loop interval, run the complete queue, wait if necessary
        for _ in range(self.repeat_count.get()):
            if not self.running:
                break
            start_time = time.time()
            self.run_queue(self.queue)
            elapsed = time.time() - start_time
            wait_time = max(0, self.main_interval.get() - elapsed)
            if self.running and wait_time > 0:
                print(f"Waiting {wait_time:.2f} seconds to maintain main loop interval.")
                time.sleep(wait_time)
        self.running = False
        print(f"{PrintColors.OKGREEN}Main loop completed or stopped.{PrintColors.ENDC}")
        print(f"{PrintColors.OKGREEN}Running everything took "
              + str(round(time.time() - self.start_time_global, 1))
              + f" seconds{PrintColors.ENDC}")

    def check_trigger(self, func_name, condition, threshold):
        # check if the trigger condition was met, if yes return true
        try:
            func = getattr(trigger_functions, func_name)
            value = func()
            if (condition == '<' and value < threshold) or (condition == '>' and value > threshold):
                print("  " * self.current_nesting +
                      f"{PrintColors.OKCYAN}TRIGGER MET: {value:.2f} {condition} {threshold}{PrintColors.ENDC}")
                return True
            else:
                print("  " * self.current_nesting
                      + f"Trigger not met, trigger function {func_name} returned value: {value:.2f}")
            return False
        except Exception as e:
            print(f"{PrintColors.FAIL}Error executing trigger function {func_name}: {e}{PrintColors.ENDC}")
            return False

    def run_queue(self, queue, depth=0):
        # run the queue that was set up
        index = 0
        # if the index has not reached the queue length, execute the next item in the queue
        while index < len(queue):
            if not self.running:
                break

            # get the next item in the queue
            item = queue[index]

            # if the next item type is a function, execute it
            if item['type'] == 'func':
                self.current_nesting = depth
                print("  " * depth +
                      f"{PrintColors.BOLD}Executing: {item.get('label', item['value'].__name__)}{PrintColors.ENDC}, "
                      + f"start time: {time.strftime('%a %H:%M:%S')}")
                item['value']()


            elif item['type'] == 'loop_start':
                if item['value'].get('is_conditional'):
                    loop_info = item['value']
                    loop_body = []
                    nest = 1
                    index += 1
                    while index < len(queue) and nest > 0:
                        if queue[index]['type'] == 'loop_start':
                            nest += 1
                        elif queue[index]['type'] == 'loop_end':
                            nest -= 1
                        if nest > 0:
                            loop_body.append(queue[index])
                        index += 1
                    trigger = loop_info.get('trigger', {})

                    should_run = self.check_trigger(
                        trigger.get('function_name'),
                        trigger.get('condition'),
                        trigger.get('threshold')
                    )

                    if should_run:
                        self.run_queue(loop_body, depth + 1)

                    continue

                else:

                    # get loop count, interval, trigger [if any] and "nesting level"
                    loop_count = item['value'].get('count', 1)
                    loop_interval = item['value'].get('interval', 0)
                    loop_trigger = item['value'].get('trigger', None)
                    inner_queue = []
                    nest = 1
                    index += 1

                    # go to the next nesting level of the new loop
                    while index < len(queue) and nest > 0:
                        if queue[index]['type'] == 'loop_start':
                            nest += 1
                        elif queue[index]['type'] == 'loop_end':
                            nest -= 1
                        # if the loop is nested, add it to the list of inner queue
                        if nest > 0:
                            inner_queue.append(queue[index])
                        # increase the index as this item of the queue is handled (have to increase it here, as the
                        # inner loop uses continue, so it's not increased otherwise if there is an inner loop started
                        index += 1

                    # start the inner loop
                    for _ in range(loop_count):
                        # get the start time to keep track of time
                        start_time = time.time()
                        # run the inner queue (this is a recursive function call)
                        self.run_queue(inner_queue, depth + 1)

                        # check if the trigger condition was met
                        if loop_trigger and self.check_trigger(loop_trigger['function'], loop_trigger['condition'],
                                                               loop_trigger['threshold']):
                            break
                        # check how much time has elapsed since start, calculate the wait time (if any)
                        # if the loop took longer thant he outer loop says it should, immediately continue
                        # for this also have to add one indent to the depth level for printing, as otherwise it is less
                        # indented than the loop that was executed
                        elapsed = time.time() - start_time
                        wait_time = max(0, loop_interval - elapsed)
                        if self.running and wait_time > 0:
                            print("  " * (depth + 1)
                                  + f"Waiting {wait_time:.2f} seconds for nested loop interval.")
                            time.sleep(wait_time)
                        else:
                            print("  " * (depth + 1)
                                  + f"{PrintColors.WARNING}Not waiting, as this nested loop took",
                                  round(elapsed, 2),
                                  f"seconds{PrintColors.ENDC}")
                        if not self.running:
                            break
                    continue
            # increase the index for everything, except for loop start (this is handled above)
            index += 1

    def set_protocol(self, protocol):
        # using the Andor function to set a protocol given the protocol name as a string
        try:
            fusionrest.run_protocol_completely(protocol)
            # print(f"Running protocol: {protocol}")
        except ConnectionError:
            print("  " * self.current_nesting
                  + f"{PrintColors.FAIL}No connection to microscope.{PrintColors.ENDC}")

    def get_progress(self):
        # print the progress in the console window
        try:
            progress = fusionrest.get_protocol_progress()
            print(progress)
        except ConnectionError:
            print("  " * self.current_nesting +
                  f"{PrintColors.FAIL}No connection to microscope.{PrintColors.ENDC}")

    def wait(self, waiting_time):
        # wait for a certain amount of time (waiting time in s)
        time.sleep(waiting_time)
        return

    def display_z_projection(self, z_proj):
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.imshow(z_proj, cmap='gray')
        ax.set_title("z-projection of last image")
        ax.axis('off')
        if hasattr(self, 'image_canvas'):
            self.image_canvas.get_tk_widget().destroy()
        canvas = FigureCanvasTkAgg(fig, self)
        canvas.get_tk_widget().pack(pady=5)
        self.image_canvas = canvas
        canvas.draw()
        return

    def show_z_projection(self):
        # show the z-projection of the last image that was acquired
        try:
            z_proj = get_current_image_2d()
            # using after to run this 'after 0 ms' on the main thread to prevent instability issues as this thread
            # does not own the event loop, after also ensures that this is only done if the main thread is free.
            self.after(0, self.display_z_projection, z_proj)

        except ConnectionError:
            """
            # tested when there was no connection via:
            import numpy as np
            z_proj = np.random.rand(2, 2)
            self.after(0, self.display_z_projection, z_proj)
            """
            print("  " * self.current_nesting + f"{PrintColors.FAIL}No connection to microscope.{PrintColors.ENDC}")


if __name__ == "__main__":
    # set the colour display to work nicely
    os.system("color")
    app = FunctionLooperApp()
    app.mainloop()
