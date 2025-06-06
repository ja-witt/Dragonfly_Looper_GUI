# Dragonfly Looper GUI

Dragonfly Looper GUI is a python-based graphical interface for automating imaging protocols using Andor's Dragonfly microscope via Fusion's REST API. This version improves usability, supports nested and conditional logic, and handles timing more intelligently than earlier iterations.
  <img src="https://github.com/user-attachments/assets/30d590b8-b81a-48d4-858d-06e15f8234d8" width="750" title="Dragonfly Looper GUI" alt="Dragonfly Looper GUI"/>

## Features

- Graphical user interface for building and controlling protocol loops via the Fusion Rest API
- Handles loop timing similarly to Dragonfly Fusion: runs protocols as quickly as possible if timing is too tight, otherwise waits for the specified interval
- Nested loops and if-statements for slightly advanced protocol control (based on image intensity thresholds, but expandable)

---

## One-Time Setup

### 1. Enable REST API in Fusion Software

See: https://fusion-benchtop-software-guide.scrollhelp.site/fusionum/automation for details

- Open Fusion
- Go to Preferences (top right corner)
- Select "REST API" from the sidebar
- Toggle REST API to "On"
- Set port to `15120`
- Return to imaging

### 2. Install Required Python Packages

- Tested with python 3.13 and python 3.11
- Relies on several python packages available from pypi that can be installed via:

```
python -m pip install requests matplotlib h5py
```


## How to use it:

### Starting the GUI

1. Run `dragonfly_auto_GUI.py`
2. A GUI window and a black console window will open

### Protocol Setup (Top Buttons)

- **Add Protocol**  
  Adds an existing Fusion protocol by name (case-sensitive). The protocol name is case sensitive (e.g. `red_green` is not the same as `Red_green`) <br>
  <img src="https://github.com/user-attachments/assets/e116b329-86ff-4074-9b71-618cd045f734" width="500" title="Giving a correct protocol name" alt="Giving a correct protocol name"/>


- **Get Progress**  
  Prints progress updates to the console.

- **Show Z-Projection**  
  Displays the Z-projection of the last single-channel image.

- **Wait**  
  Add a fixed wait interval in seconds.

- **Start Inner Loop**  
  Creates a nested loop. Set number of repetitions and loop interval (in seconds). Optionally add a trigger function. <br>
  The trigger functions analyze the most recent 3D image (single-channel only)
  - `image_max_intensity_trigger`: Returns the maximum intensity value found in the most recent 3D image. This can be useful for detecting strong signals or sudden bright events.
  - `image_99_percentile_trigger`: Returns the 99th percentile intensity of the most recent 3D image. This is similar to the maximum, but less sensitive to outlier pixels or noise, making it a more stable trigger for consistent signals.
  - These functions are used with conditional triggers or to exit inner loops. You can apply logical conditions (>, <) with user-defined threshold values to control protocol execution based on image content.
  - It is possible to add trigger functions (functions that read in the last image and return a value based on that) in `trigger_functions.py`. All functions that are in this python file will be shown in the dropdown menu.

- **End Inner Loop**  
  Ends the current nested loop.

- **Add If Statement**  
  Adds a condition block. The block runs only if the intensity condition is met using the latest image.

- **Remove Last**  
  Removes the most recent protocol step from the list.

### Main Loop Controls (Bottom Buttons)

- **Main Repeats**  
  Sets how many times the entire loop should repeat.

- **Main Interval (s)**  
  Time between loop iterations. If protocol execution is faster, it waits; if slower, it continues with a warning.

- **Start Loop**  
  Starts the main loop execution.

- **Stop**  
  Stops the main loop after the current protocol finishes.

- **Clear Queue**  
  Clears all added protocol steps from the list.

---

## Trigger Examples

### Example 1: Conditional Imaging Based on Green Channel
<img src="https://github.com/user-attachments/assets/4e1089d0-0486-4324-87fc-5905c7559356" width="500" title="Example 1 loop" alt="Example 1 loop"/>
<img src="https://github.com/user-attachments/assets/e9d624c7-1f18-43cc-96a8-5ab51b55a3af" width="500" title="Example 1 trigger" alt="Example 1 trigger"/>

Objective: Image the red channel only if the green channel is bright.

- Interval: Every 5 minutes
- Repeat: 100 times
- Condition: If the 99 percentile intensity of the green channel > 150, then image the red channel

### Example 2: Wait for Red Channel Signal Before Imaging Everything
<img src="https://github.com/user-attachments/assets/fb225f19-4238-41d0-8599-65cc4edcd02f" width="500" title="Example 2 loop" alt="Example 2 loop"/>
<img src="https://github.com/user-attachments/assets/b90a402f-754e-420d-b300-20fe9a5a1134" width="500" title="Example 2 trigger" alt="Example 2 trigger"/>

Objective: Start full imaging only after red signal appears.

- Check red channel every 2 minutes
- When detected, start imaging all channels every 1 minute for 2 hours

---


## File Organization

Ensure all `.py` scripts are located in the same folder:

```
D:\Dragonfly_auto\
└── v2\
    ├── dragonfly_auto_GUI.py
    ├── ... (other dependent scripts)
```

---

## Known Issues

- Fusion sometimes falsely reports 100% protocol completion
- Only single-channel images are supported for image based 
- Protocol name mismatches cause silent failures

---

## Credits

Created using the Fusion REST API with GUI functionality mainly generated with the help of ChatGPT.

## Licence

This project is licensed under the MIT License. See the LICENSE file for details.
