# ESP32 Bridge MCP Server

A local Python Model Context Protocol (MCP) server that empowers Antigravity to communicate with, flash, read code from, and control your ESP32 microcontroller directly from this chat conversation.

---

## Features

- 🔌 **Serial Port Discovery & Connection**: Auto-detects CH340, CP210x, FTDI, and native ESP32 USB ports.
- 📜 **Continuous Serial Monitor**: Asynchronous ring buffer captures logs in the background without blocking conversation.
- 💬 **Bidirectional Serial I/O**: Read logs on demand and transmit commands/data back to the ESP32.
- ⚡ **MicroPython Raw REPL Engine**:
  - Upload `.py` files (e.g. `main.py`) directly to flash storage with soft reboot.
  - Read any script from the board's internal flash.
  - List files and directories stored on the microcontroller.
  - Execute arbitrary Python snippets in-memory and receive stdout/stderr.
- 🔥 **C++ / Arduino / Binary Flashing**:
  - Read chip information (MAC address, flash size, chip model) via `esptool`.
  - Flash compiled binary images (`.bin`) at standard offsets (e.g., `0x10000`).
- 🔄 **Hardware Reset**: Pulses DTR/RTS lines to perform clean board restarts.

---

## File Structure

```
esp32+ai/
├── .venv/                         # Python virtual environment (CPython 3.11)
├── esp32_manager.py               # Serial manager, MicroPython REPL client, esptool bridge
├── esp32_mcp.py                   # MCP Server (MCPServer stdio protocol)
├── examples/
│   ├── micropython_echo_demo.py   # MicroPython test script
│   └── arduino_echo_demo/
│       └── arduino_echo_demo.ino  # Arduino C++ test sketch
└── README.md
```

---

## Exposed MCP Tools

| Tool | Purpose | Parameters |
| :--- | :--- | :--- |
| `list_serial_ports` | Lists all detected serial ports on the host | None |
| `connect_esp32` | Connects serial monitor to port | `port: str = ""`, `baudrate: int = 115200` |
| `disconnect_esp32` | Closes serial port | None |
| `read_serial_output` | Returns recent serial logs from buffer | `lines: int = 50`, `clear_buffer: bool = False` |
| `send_serial_input` | Sends string command to the microcontroller | `text: str`, `append_newline: bool = True` |
| `reset_esp32` | Triggers hardware reset via DTR/RTS | None |
| `erase_esp32_flash` | Completely wipes all flash memory (firmware, NVS, partitions) | `confirm: bool = False`, `port: str = ""` |
| `get_chip_info` | Reads MAC, chip model, flash info | `port: str = ""` |
| `upload_micropython_code` | Writes file to ESP32 flash & soft reboots | `remote_path: str`, `code: str` |
| `read_micropython_code` | Reads file from ESP32 flash | `remote_path: str` |
| `list_micropython_files` | Lists files on ESP32 storage | `dir_path: str = "/"` |
| `run_micropython_code` | Runs Python code in raw REPL on ESP32 | `code: str` |
| `flash_firmware_binary` | Flashes precompiled `.bin` via esptool | `bin_path: str`, `address: str = "0x10000"`, `baudrate: int = 460800` |
| `read_workspace_file` | Reads source file from local workspace | `file_path: str` |
| `write_workspace_file` | Writes source file to local workspace | `file_path: str`, `content: str` |

---

## Antigravity Configuration

The server can be configured at the workspace level in `.agents/mcp_config.json`:

```json
{
  "mcpServers": {
    "esp32-bridge": {
      "command": "${workspaceFolder}/.venv/Scripts/python.exe",
      "args": [
        "${workspaceFolder}/esp32_mcp.py"
      ],
      "env": {}
    }
  }
}
```

Or globally in `~/.gemini/config/mcp_config.json` replacing `${workspaceFolder}` with your absolute project folder path.

---

## Quick Testing

To run the self-test directly from PowerShell:

```powershell
.\.venv\Scripts\python.exe esp32_mcp.py --test
```

