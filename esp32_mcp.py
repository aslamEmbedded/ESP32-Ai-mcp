"""
ESP32 MCP Server
Provides model context protocol tools to interact with ESP32 hardware,
read/write code, stream serial output, send serial inputs, and flash firmware.
"""

import os
import sys
from typing import List, Dict, Any, Optional
from mcp.server.mcpserver import MCPServer

from esp32_manager import ESP32Manager

# Initialize Server and Hardware Manager
server = MCPServer(
    name="ESP32-Bridge",
    version="1.0.0",
    description="Bridge MCP server to control, upload, read code, and monitor ESP32 microcontrollers."
)
manager = ESP32Manager()
WORKSPACE_DIR = os.path.abspath(os.path.dirname(__file__))


@server.tool()
def list_serial_ports() -> List[Dict[str, Any]]:
    """List all available COM/serial ports on the system with device descriptions and ESP32 candidacy."""
    return manager.list_ports()


@server.tool()
def connect_esp32(port: str = "", baudrate: int = 115200) -> str:
    """Connect to the ESP32 serial interface and start the background serial reader.
    If port is empty, attempts auto-detection.
    """
    success, msg = manager.connect(port=port if port.strip() else None, baudrate=baudrate)
    return msg


@server.tool()
def disconnect_esp32() -> str:
    """Disconnect from the ESP32 and release the serial port."""
    success, msg = manager.disconnect()
    return msg


@server.tool()
def read_serial_output(lines: int = 50, clear_buffer: bool = False) -> str:
    """Read the latest log lines received from the ESP32 serial output buffer.
    Automatically discovers and connects to the board if not already connected.
    Args:
        lines: Maximum number of recent lines to retrieve (default: 50).
        clear_buffer: If True, flushes the retrieved lines from memory.
    """
    logs = manager.read_logs(lines=lines, clear=clear_buffer, timeout_wait=2.0)
    if not logs:
        if manager.port:
            return f"[Connected to {manager.port}, but no new serial output was received recently. The ESP32 may be idle or waiting for commands.]"
        return "[No ESP32 detected on serial ports. Please ensure your board is plugged into USB.]"
    return "\n".join(logs)


@server.tool()
def send_serial_input(text: str, append_newline: bool = True) -> str:
    """Send text, input commands, or data packets over serial to the ESP32.
    Args:
        text: The string command or payload to transmit.
        append_newline: Whether to append \\r\\n at the end (default: True).
    """
    success, msg = manager.send_input(text=text, append_newline=append_newline)
    return msg


@server.tool()
def reset_esp32() -> str:
    """Trigger a hardware reset on the ESP32 board using DTR/RTS serial control lines."""
    success, msg = manager.reset_board()
    return msg


@server.tool()
def get_chip_info(port: str = "") -> str:
    """Retrieve chip architecture, MAC address, and flash memory details using esptool.
    Args:
        port: COM port (e.g. 'COM3'). If empty, uses active or auto-detected port.
    """
    res = manager.get_chip_info(port=port if port.strip() else None)
    if res.get("success"):
        return res.get("details", "ESP32 chip detected successfully.")
    return f"Failed to get chip info: {res.get('error', 'Unknown error')}"


@server.tool()
def upload_micropython_code(remote_path: str, code: str) -> str:
    """Upload Python code directly to the ESP32 internal flash filesystem (e.g. 'main.py' or 'boot.py')
    via MicroPython raw REPL. Soft reboots the board after uploading.
    Args:
        remote_path: File name on ESP32 (e.g., 'main.py', 'sensor.py').
        code: Python source code string to write.
    """
    res = manager.micropython_upload(remote_path=remote_path, content=code)
    if res.get("success"):
        return res.get("message", "Uploaded successfully.")
    return f"Upload failed: {res.get('error', 'Unknown error')}"


@server.tool()
def read_micropython_code(remote_path: str) -> str:
    """Read source code of a file located on the ESP32 internal flash filesystem.
    Args:
        remote_path: Path to file on device (e.g., 'main.py', 'boot.py').
    """
    res = manager.micropython_read(remote_path=remote_path)
    if res.get("success"):
        return res.get("content", "")
    return f"Failed to read file: {res.get('error', 'Unknown error')}"


@server.tool()
def list_micropython_files(dir_path: str = "/") -> str:
    """List all files and directories stored on the ESP32 internal flash filesystem."""
    res = manager.micropython_list_files(dir_path=dir_path)
    if res.get("success"):
        files = res.get("files", [])
        return f"Files in '{dir_path}':\n" + ("\n".join(f"- {f}" for f in files) if files else "(empty)")
    return f"Failed to list files: {res.get('error', 'Unknown error')}"


@server.tool()
def run_micropython_code(code: str) -> str:
    """Execute arbitrary Python code directly in the ESP32's raw REPL and return its output.
    Args:
        code: Python code statements to run on the microcontroller.
    """
    res = manager.micropython_run(code=code)
    if not res.get("success") and res.get("error"):
        return f"Execution error: {res['error']}"
    
    out = res.get("stdout", "")
    err = res.get("stderr", "")
    combined = []
    if out:
        combined.append(f"STDOUT:\n{out}")
    if err:
        combined.append(f"STDERR:\n{err}")
    return "\n".join(combined) if combined else "[Executed successfully with no output]"


@server.tool()
def flash_firmware_binary(bin_path: str, address: str = "0x10000", baudrate: int = 460800) -> str:
    """Flash a compiled binary firmware image (.bin) to the ESP32 flash memory using esptool.
    Args:
        bin_path: Absolute or workspace-relative path to the .bin file.
        address: Flash memory offset address (default: '0x10000').
        baudrate: Flashing baudrate (default: 460800 for high-speed upload).
    """
    if not os.path.isabs(bin_path):
        bin_path = os.path.join(WORKSPACE_DIR, bin_path)
    
    if not os.path.exists(bin_path):
        return f"Error: Binary file not found at '{bin_path}'"
    
    res = manager.flash_binary(bin_path=bin_path, address=address, baudrate=baudrate)
    if res.get("success"):
        return f"Flashing complete:\n{res.get('output', '')}"
    return f"Flashing failed:\n{res.get('error', 'Unknown error')}"


@server.tool()
def read_workspace_file(file_path: str) -> str:
    """Read a local source file from the project workspace.
    Args:
        file_path: Relative or absolute path in the workspace.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(WORKSPACE_DIR, file_path)
    
    if not os.path.exists(file_path):
        return f"Error: File not found at '{file_path}'"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@server.tool()
def erase_esp32_flash(confirm: bool = False, port: str = "") -> str:
    """Completely wipe and erase the entire SPI flash memory of the ESP32.
    WARNING: This permanently removes all bootloader, partitions, firmware, NVS, and stored files.
    Args:
        confirm: Must be set to True to execute the erase.
        port: COM port (e.g. 'COM3', '/dev/ttyUSB0'). If empty, uses active/auto-detected port.
    """
    if not confirm:
        return "Erasing flash aborted: 'confirm' parameter was False. Set confirm=True if you really want to wipe the flash."
    
    res = manager.erase_flash(port=port if port.strip() else None)
    if res.get("success"):
        return f"Flash erased successfully:\n{res.get('output', '')}"
    return f"Failed to erase flash:\n{res.get('error', 'Unknown error')}"


@server.tool()
def write_workspace_file(file_path: str, content: str) -> str:
    """Write or update a local source file in the project workspace.
    Args:
        file_path: Relative or absolute path in the workspace.
        content: Code content to write.
    """
    if not os.path.isabs(file_path):
        file_path = os.path.join(WORKSPACE_DIR, file_path)
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to '{file_path}'"
    except Exception as e:
        return f"Error writing file: {str(e)}"


if __name__ == "__main__":
    # If launched with --test, run a quick self-test
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print("Running ESP32 MCP Self-Test...")
        ports = manager.list_ports()
        print(f"Found {len(ports)} ports: {ports}")
        print("Self-test completed successfully.")
        sys.exit(0)
    
    # Run the MCP server over stdio
    server.run(transport="stdio")

