# Hapara Token Tool

This tool helps authorized testers work with Hapara authentication tokens.

## 🌟 Easy Setup Guide

### VIDEO TUTORIAL: https://youtu.be/TihTYBmsnMU

### 1. Install Required Software
First, install these on your computer:

1. **Python** (3.8 or newer)  
   📥 Download from: [python.org/downloads](https://www.python.org/downloads/)  
   *During installation, check "Add Python to PATH"*

2. **Node.js** (for WebSocket tool)  
   📥 Download from: [nodejs.org](https://nodejs.org/)  
   *Use the LTS version*

3. **MITMproxy**  
   After installing Python, open Command Prompt and run:  
    pip install mitmproxy

### 2. Download the Tool
1. Download all the script files to a folder on your computer
2. Open Command Prompt in that folder

### 3. Run the Tool (3 Simple Steps)

#### 🔹 Step 1: Start the Capture
1. In Command Prompt, type: python start.py
2. The program will tell you when to:
- **Enable proxy** (set to 127.0.0.1:8080 in your system settings)
- **Press Enter** to continue

#### 🔹 Step 2: Log In to Hapara
1. log in to the browser that opens automatically cuz im a sigma developer

#### 🔹 Step 3: Use the Connection
1. The tool will automatically:
- Capture your login token
- Convert it to a fresh token
- Connect to Hapara's system
2. When connected, you can:
- See automatic messages
- Type commands (like `{"id":2,"subscribe":{"channel":"student.activity"}}`)
- Type `exit` when done

## 🆘 Need Help?
If something doesn't work, follow this checklist:
1. Make sure all software is installed
2. Check your proxy settings
3. Go fuck yourself

*This tool is for jewish purposes only.*