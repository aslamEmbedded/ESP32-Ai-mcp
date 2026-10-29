# ESP32 Bridge MCP Server

A powerful local Python Model Context Protocol (MCP) server that connects your AI assistant (Google Antigravity IDE, Claude Desktop, Cursor, etc.) directly to your physical ESP32 microcontroller over USB serial.

Communicate, flash compiled binaries, upload MicroPython code, stream live serial logs, and perform hardware resets through natural chat conversations!

---

## 🚀 Quick Setup Guide (Any PC in Under 2 Minutes)

### 1. Prerequisites
- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/).
  > ⚠️ **Important**: During installation, ensure you check **"Add Python to PATH"**.
- **USB Driver**: Ensure your computer recognizes your board's USB chip (CH340, CP2102, or FTDI).
- **USB Cable**: Make sure to use a **data-capable** USB cable (not charge-only).

### 2. 1-Click Automated Installation
1. Clone or download this repository to your computer:
   ```bash
   git clone https://github.com/aslamEmbedded/ESP32-Ai-mcp.git
   cd ESP32-Ai-mcp
   ```
2. Double-click **`setup.bat`** (or run it from the command line).

**What `setup.bat` does automatically:**
- Auto-detects standard Windows Python (bypassing incomplete MinGW/MSYS2 environments).
- Creates a clean virtual environment (`.venv`).
- Installs all dependencies (`mcp`, `pyserial`, `esptool`).
- Automatically generates `.agents/mcp_config.json` configured for your PC.
- Runs a self-test and checks for connected ESP32 boards.

### 3. Open in Antigravity IDE
1. Open Antigravity IDE.
2. Select **File > Open Folder...** and choose this project folder.
3. Reload the window to mount the MCP server:
   - Press **`Ctrl + Shift + P`**
   - Type and select: **`Developer: Reload Window`**
4. Done! Type `@` in chat or start prompting.

---

## 🌐 Optional: Global PC Setup (Use in ANY Project)

By default, the server is available whenever you open this folder. If you want the ESP32 tools accessible across **every workspace/project** on your machine:

1. Open or create your global Antigravity config file:
   `%USERPROFILE%\.gemini\config\mcp_config.json`
2. Add the `esp32-bridge` server block:
   ```json
   {
     "mcpServers": {
       "esp32-bridge": {
         "command": "C:\\path\\to\\ESP32_AI_MCP\\.venv\\Scripts\\python.exe",
         "args": [
           "C:\\path\\to\\ESP32_AI_MCP\\esp32_mcp.py"
         ],
         "env": {}
       }
     }
   }
   ```
   *(Replace `C:\\path\\to\\ESP32_AI_MCP` with your actual project directory path using double backslashes `\\`)*.
3. Reload Antigravity Window (`Ctrl + Shift + P` -> `Developer: Reload Window`).

---

## 💬 Example Chat Prompts

Once set up, the AI handles port discovery, connection, flashing, and monitoring automatically:

- *"Check connected ports and find my ESP32"*
- *"Show me what the ESP32 is printing right now"*
- *"Get my chip model, MAC address, and flash specs"*
- *"Send the command 'PING' to the board and show the response"*
- *"Restart my ESP32 board"*
- *"Compile and upload a blink sketch to the board"*
- *"Upload this Python code to `main.py` on the ESP32 flash"*
- *"Wipe the flash completely"*

---

## ✨ Features & Architecture

- 🔌 **Universal ESP32 Support**: Works across all variants (ESP32 Classic, ESP32-S2, ESP32-S3, ESP32-C3, ESP32-C6, ESP32-H2).
- 📜 **Continuous Serial Monitor**: Asynchronous background thread captures logs into a thread-safe ring buffer without blocking the AI.
- 🔄 **Smart Port Lock Sharing**: Automatically pauses the serial monitor before flashing/uploading, preventing Windows COM port collisions (`Access Denied`), and resumes listening immediately after.
- ⚡ **MicroPython Raw REPL Engine**: Direct script uploads (`main.py`, `boot.py`), file reading, directory listing, and in-memory Python execution.
- 🔥 **C++ / Arduino Flashing**: Firmware flashing via `esptool.py` at standard offsets (e.g., `0x10000`).
- 🛑 **Full Flash Erase**: Safe full-chip erase with confirmation safeguards.

---

## 🛠️ Exposed MCP Tools

| Tool | Purpose | Parameters |
| :--- | :--- | :--- |
| `list_serial_ports` | Lists all detected serial ports on the host | None |
| `connect_esp32` | Connects serial monitor to port | `port: str = ""`, `baudrate: int = 115200` |
| `disconnect_esp32` | Closes serial port | None |
| `read_serial_output` | Returns recent serial logs from buffer | `lines: int = 50`, `clear_buffer: bool = False` |
| `send_serial_input` | Sends string command to the microcontroller | `text: str`, `append_newline: bool = True` |
| `reset_esp32` | Triggers hardware reset via DTR/RTS | None |
| `erase_esp32_flash` | Completely wipes all flash memory | `confirm: bool = False`, `port: str = ""` |
| `get_chip_info` | Reads MAC, chip model, flash info via esptool | `port: str = ""` |
| `upload_micropython_code` | Writes file to ESP32 flash & soft reboots | `remote_path: str`, `code: str` |
| `read_micropython_code` | Reads file from ESP32 internal flash | `remote_path: str` |
| `list_micropython_files` | Lists files on ESP32 storage | `dir_path: str = "/"` |
| `run_micropython_code` | Runs Python code in raw REPL on ESP32 | `code: str` |
| `flash_firmware_binary` | Flashes precompiled `.bin` via esptool | `bin_path: str`, `address: str = "0x10000"`, `baudrate: int = 460800` |
| `read_workspace_file` | Reads source file from local workspace | `file_path: str` |
| `write_workspace_file` | Writes source file to local workspace | `file_path: str`, `content: str` |

---

## 📂 Repository Structure

```
ESP32_AI_MCP/
├── .agents/
│   └── mcp_config.json          # Workspace MCP configuration
├── .gitignore                   # Ignores .venv and build artifacts
├── AGENTS.md                    # Autonomous agent rules for natural chat interaction
├── esp32_manager.py             # Serial manager, MicroPython REPL, and esptool flasher
├── esp32_mcp.py                 # FastMCP / MCPServer definition and tool handlers
├── setup.bat                    # 1-click automated installer for Windows
├── HOW_TO_SETUP_NEW_PC.txt      # Text-only setup guide for quick reference
├── requirements.txt             # Python dependencies (mcp, pyserial, esptool)
├── README.md                    # Project documentation
├── examples/
│   ├── micropython_echo_demo.py # MicroPython test script
│   └── arduino_echo_demo/       # Interactive Arduino sketch
└── sketches/
    └── blink/                   # Default ESP32 blink sketch
```

---

## ❓ Troubleshooting

- **No ESP32 detected?** Check that your USB cable supports data transfer (some cheap cables only deliver power).
- **Driver missing?** Check Windows Device Manager under "Ports (COM & LPT)". If a yellow warning appears, install the driver for your board's chip (CH340 or CP2102).
- **Tools not appearing in chat?** Press `Ctrl + Shift + P` and select `Developer: Reload Window`.
