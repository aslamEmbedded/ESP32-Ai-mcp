"""
ESP32 Hardware & Serial Manager
Handles bidirectional UART serial streaming, port synchronization,
MicroPython raw REPL protocol, and esptool flashing.
"""

import sys
import time
import base64
import subprocess
import threading
from collections import deque
from typing import List, Dict, Optional, Tuple

import serial
import serial.tools.list_ports


class ESP32Manager:
    def __init__(self):
        self.port: Optional[str] = None
        self.baudrate: int = 115200
        self.serial_inst: Optional[serial.Serial] = None
        
        # Thread-safe serial output buffer
        self.log_buffer: deque = deque(maxlen=2000)
        self.rx_thread: Optional[threading.Thread] = None
        self.running: bool = False
        self.lock = threading.RLock()
        self.paused_for_action = False

    def list_ports(self) -> List[Dict[str, str]]:
        """List all available serial COM ports with hardware details."""
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            desc = (p.description or "").lower()
            mfg = (p.manufacturer or "").lower()
            hwid = (p.hwid or "").lower()
            is_esp = any(
                keyword in desc or keyword in mfg or keyword in hwid
                for keyword in [
                    "cp210", "ch340", "ftdi", "usb serial", "esp", "espressif",
                    "silicon labs", "wch", "303a:", "jtag", "cdc"
                ]
            )
            result.append({
                "port": p.device,
                "description": p.description or "Unknown",
                "hardware_id": p.hwid or "",
                "is_likely_esp32": is_esp
            })
        return result

    def auto_detect_port(self) -> Optional[str]:
        """Automatically find the best candidate port."""
        ports = self.list_ports()
        likely = [p["port"] for p in ports if p["is_likely_esp32"]]
        if len(likely) == 1:
            return likely[0]
        if len(ports) == 1:
            return ports[0]["port"]
        return None

    def connect(self, port: Optional[str] = None, baudrate: int = 115200) -> Tuple[bool, str]:
        """Connect to the specified serial port and start background reader thread."""
        with self.lock:
            if not port:
                port = self.auto_detect_port()
                if not port:
                    return False, "No port specified and could not auto-detect a unique ESP32 port. Use list_ports to find COM port."

            if self.serial_inst and self.serial_inst.is_open:
                if self.port == port and self.baudrate == baudrate:
                    return True, f"Already connected to {port} @ {baudrate} baud."
                self.disconnect()

            try:
                self.serial_inst = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    timeout=0.1,
                    write_timeout=1.0
                )
                self.port = port
                self.baudrate = baudrate
                self.running = True
                self.paused_for_action = False

                self.rx_thread = threading.Thread(target=self._reader_loop, daemon=True)
                self.rx_thread.start()
                return True, f"Successfully connected to {port} at {baudrate} baud."
            except Exception as e:
                self.serial_inst = None
                return False, f"Failed to connect to {port}: {str(e)}"

    def disconnect(self) -> Tuple[bool, str]:
        """Disconnect and stop reader thread."""
        with self.lock:
            self.running = False
            if self.rx_thread and self.rx_thread.is_alive():
                self.rx_thread.join(timeout=1.0)
            
            if self.serial_inst and self.serial_inst.is_open:
                try:
                    self.serial_inst.close()
                except Exception:
                    pass
            self.serial_inst = None
            return True, f"Disconnected from {self.port}."

    def _reader_loop(self):
        """Continuously reads incoming UART data into the ring buffer."""
        line_accum = bytearray()
        while self.running:
            if self.paused_for_action or not self.serial_inst or not self.serial_inst.is_open:
                time.sleep(0.05)
                continue
            
            try:
                raw_bytes = self.serial_inst.read(256)
                if raw_bytes:
                    for b in raw_bytes:
                        if b == ord(b'\n'):
                            try:
                                decoded = line_accum.decode('utf-8', errors='replace').rstrip('\r')
                                self.log_buffer.append(decoded)
                            except Exception:
                                pass
                            line_accum.clear()
                        elif b != ord(b'\r'):
                            line_accum.append(b)
                else:
                    time.sleep(0.02)
            except (serial.SerialException, OSError):
                # Device was unplugged or port became unavailable
                try:
                    if self.serial_inst:
                        self.serial_inst.close()
                except Exception:
                    pass
                self.serial_inst = None
                time.sleep(0.5)
            except Exception:
                time.sleep(0.1)

    def ensure_connected(self, port: Optional[str] = None) -> Tuple[bool, str]:
        """Verify serial connection is active, or automatically connect if idle."""
        with self.lock:
            if self.serial_inst and self.serial_inst.is_open:
                return True, f"Connected to {self.port}"
            return self.connect(port=port)

    def read_logs(self, lines: int = 50, clear: bool = False, timeout_wait: float = 1.2) -> List[str]:
        """Retrieve recent lines from the serial monitor buffer.
        Automatically connects if not already active and waits briefly if buffer is empty.
        """
        # Auto-connect if needed
        self.ensure_connected()

        # If buffer is currently empty, give incoming serial data a moment to arrive
        start_wait = time.time()
        while len(self.log_buffer) == 0 and (time.time() - start_wait < timeout_wait):
            time.sleep(0.05)

        with self.lock:
            count = min(lines, len(self.log_buffer))
            if count == 0:
                return []
            recent = list(self.log_buffer)[-count:]
            if clear:
                self.log_buffer.clear()
            return recent

    def send_input(self, text: str, append_newline: bool = True) -> Tuple[bool, str]:
        """Send characters or commands to the ESP32 serial interface.
        Automatically connects if not yet open.
        """
        with self.lock:
            ok, conn_msg = self.ensure_connected()
            if not ok or not self.serial_inst or not self.serial_inst.is_open:
                return False, f"Could not connect to send data: {conn_msg}"
            
            data = text + ("\r\n" if append_newline else "")
            try:
                self.serial_inst.write(data.encode('utf-8'))
                self.serial_inst.flush()
                return True, f"Sent '{text}' ({len(data)} bytes) to {self.port}."
            except Exception as e:
                return False, f"Failed to send data: {str(e)}"

    def reset_board(self, hard_reset: bool = True) -> Tuple[bool, str]:
        """Hardware reset the ESP32 using DTR/RTS sequence.
        Automatically connects if not yet open.
        """
        with self.lock:
            ok, conn_msg = self.ensure_connected()
            if not ok or not self.serial_inst or not self.serial_inst.is_open:
                return False, f"Could not connect to trigger reset: {conn_msg}"
            
            try:
                # Classic ESP32 reset sequence (DTR=0, RTS=1 -> EN pulled low)
                self.serial_inst.setDTR(False)
                self.serial_inst.setRTS(True)
                time.sleep(0.15)
                self.serial_inst.setRTS(False)
                time.sleep(0.05)
                return True, f"ESP32 on {self.port} reset successfully."
            except Exception as e:
                return False, f"Reset failed: {str(e)}"

    def pause_serial(self):
        """Temporarily release serial port for external operations like flashing or raw REPL."""
        self.paused_for_action = True
        time.sleep(0.1)
        if self.serial_inst and self.serial_inst.is_open:
            self.serial_inst.close()

    def resume_serial(self):
        """Reopen serial port after flashing or raw REPL action."""
        if self.port and self.running:
            try:
                self.serial_inst = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=0.1,
                    write_timeout=1.0
                )
            except Exception:
                pass
        self.paused_for_action = False

    # -------------------------------------------------------------
    # MicroPython Raw REPL Operations
    # -------------------------------------------------------------
    def _enter_raw_repl(self, ser: serial.Serial) -> bool:
        """Interrupt current program and enter MicroPython raw REPL mode."""
        ser.reset_input_buffer()
        # Send Ctrl-C twice to break out of running loop
        ser.write(b'\r\x03\x03')
        time.sleep(0.2)
        # Flush response
        ser.read_all()
        # Send Ctrl-A to enter raw REPL
        ser.write(b'\x01')
        time.sleep(0.2)
        data = ser.read_all()
        return b'raw REPL; CTRL-B to exit' in data

    def _exit_raw_repl(self, ser: serial.Serial, soft_reboot: bool = True):
        """Exit raw REPL and optionally soft reboot."""
        if soft_reboot:
            ser.write(b'\x04')  # Ctrl-D soft reboot
            time.sleep(0.2)
        ser.write(b'\x02')  # Ctrl-B exit raw REPL
        time.sleep(0.1)

    def _exec_in_raw_repl(self, ser: serial.Serial, code: str, timeout: float = 10.0) -> Tuple[bool, str, str]:
        """Execute a string of Python code in raw REPL and return (success, stdout, stderr)."""
        ser.reset_input_buffer()
        # Send code followed by Ctrl-D (EOT)
        code_bytes = code.encode('utf-8')
        ser.write(code_bytes + b'\x04')
        
        start_time = time.time()
        buf = bytearray()
        
        # Read until header OK (\r\nOK)
        while time.time() - start_time < timeout:
            chunk = ser.read(64)
            if chunk:
                buf.extend(chunk)
                if b'OK' in buf:
                    break
            else:
                time.sleep(0.02)
        
        if b'OK' not in buf:
            return False, "", f"Timeout waiting for raw REPL confirmation. Output: {bytes(buf)}"

        # Strip up to 'OK'
        ok_idx = buf.find(b'OK')
        data_after = buf[ok_idx + 2:]
        
        # Now read stdout until next Ctrl-D (\x04), then stderr until second Ctrl-D (\x04)
        out_buf = bytearray(data_after)
        while time.time() - start_time < timeout:
            if out_buf.count(b'\x04') >= 2:
                break
            chunk = ser.read(64)
            if chunk:
                out_buf.extend(chunk)
            else:
                time.sleep(0.02)

        parts = out_buf.split(b'\x04')
        stdout_txt = parts[0].decode('utf-8', errors='replace') if len(parts) > 0 else ""
        stderr_txt = parts[1].decode('utf-8', errors='replace') if len(parts) > 1 else ""
        
        success = (len(stderr_txt.strip()) == 0)
        return success, stdout_txt, stderr_txt

    def micropython_run(self, code: str) -> Dict[str, any]:
        """Run Python code on the connected ESP32 via MicroPython Raw REPL."""
        if not self.port:
            return {"success": False, "error": "No ESP32 port configured."}
        
        with self.lock:
            self.pause_serial()
            try:
                ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=0.2)
                try:
                    if not self._enter_raw_repl(ser):
                        return {"success": False, "error": "Could not enter MicroPython raw REPL. Is MicroPython installed on the ESP32?"}
                    
                    ok, stdout, stderr = self._exec_in_raw_repl(ser, code)
                    self._exit_raw_repl(ser, soft_reboot=False)
                    return {
                        "success": ok,
                        "stdout": stdout,
                        "stderr": stderr
                    }
                finally:
                    ser.close()
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                self.resume_serial()

    def micropython_upload(self, remote_path: str, content: str) -> Dict[str, any]:
        """Upload a file (e.g. main.py) to ESP32 flash storage using base64 chunks."""
        if not self.port:
            return {"success": False, "error": "No ESP32 port configured."}
        
        b64_content = base64.b64encode(content.encode('utf-8')).decode('ascii')
        chunk_size = 512
        chunks = [b64_content[i:i + chunk_size] for i in range(0, len(b64_content), chunk_size)]
        
        with self.lock:
            self.pause_serial()
            try:
                ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=0.2)
                try:
                    if not self._enter_raw_repl(ser):
                        return {"success": False, "error": "Could not enter MicroPython raw REPL."}
                    
                    # Init file open in write mode
                    init_code = f"import ubinascii\nf = open('{remote_path}', 'wb')\n"
                    ok, _, err = self._exec_in_raw_repl(ser, init_code)
                    if not ok:
                        return {"success": False, "error": f"Failed to create file: {err}"}
                    
                    # Stream chunks
                    for chunk in chunks:
                        write_code = f"f.write(ubinascii.a2b_base64('{chunk}'))\n"
                        ok, _, err = self._exec_in_raw_repl(ser, write_code)
                        if not ok:
                            return {"success": False, "error": f"Failed writing chunk: {err}"}
                    
                    # Close and sync
                    close_code = "f.close()\n"
                    ok, _, err = self._exec_in_raw_repl(ser, close_code)
                    
                    # Soft reboot so new code (like main.py) takes effect
                    self._exit_raw_repl(ser, soft_reboot=True)
                    return {"success": True, "message": f"Successfully uploaded {len(content)} bytes to {remote_path} and soft-rebooted."}
                finally:
                    ser.close()
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                self.resume_serial()

    def micropython_read(self, remote_path: str) -> Dict[str, any]:
        """Read a file from ESP32 flash storage."""
        if not self.port:
            return {"success": False, "error": "No ESP32 port configured."}
        
        read_script = f"""
try:
    with open('{remote_path}', 'r') as f:
        print(f.read(), end='')
except Exception as e:
    import sys
    sys.stderr.write(str(e))
"""
        with self.lock:
            self.pause_serial()
            try:
                ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=0.2)
                try:
                    if not self._enter_raw_repl(ser):
                        return {"success": False, "error": "Could not enter MicroPython raw REPL."}
                    ok, stdout, stderr = self._exec_in_raw_repl(ser, read_script)
                    self._exit_raw_repl(ser, soft_reboot=False)
                    if not ok or stderr:
                        return {"success": False, "error": stderr or "Failed to read file."}
                    return {"success": True, "content": stdout}
                finally:
                    ser.close()
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                self.resume_serial()

    def micropython_list_files(self, dir_path: str = "/") -> Dict[str, any]:
        """List files and folders on ESP32 flash filesystem."""
        if not self.port:
            return {"success": False, "error": "No ESP32 port configured."}
        
        list_script = f"""
import os, sys
try:
    files = os.listdir('{dir_path}')
    print(repr(files))
except Exception as e:
    sys.stderr.write(str(e))
"""
        with self.lock:
            self.pause_serial()
            try:
                ser = serial.Serial(self.port, baudrate=self.baudrate, timeout=0.2)
                try:
                    if not self._enter_raw_repl(ser):
                        return {"success": False, "error": "Could not enter MicroPython raw REPL."}
                    ok, stdout, stderr = self._exec_in_raw_repl(ser, list_script)
                    self._exit_raw_repl(ser, soft_reboot=False)
                    if not ok or stderr:
                        return {"success": False, "error": stderr or "Failed to list files."}
                    return {"success": True, "files": eval(stdout.strip()) if stdout.strip() else []}
                finally:
                    ser.close()
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                self.resume_serial()

    # -------------------------------------------------------------
    # ESPTool Hardware / Flashing Operations
    # -------------------------------------------------------------
    def get_chip_info(self, port: Optional[str] = None) -> Dict[str, any]:
        """Query chip model, MAC address, and flash ID using esptool."""
        target_port = port or self.port or self.auto_detect_port()
        if not target_port:
            return {"success": False, "error": "No port available for chip detection."}
        
        with self.lock:
            was_connected = (self.serial_inst is not None and self.serial_inst.is_open)
            if was_connected:
                self.pause_serial()
            
            try:
                cmd = [sys.executable, "-m", "esptool", "--port", target_port, "chip_id"]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                cmd_flash = [sys.executable, "-m", "esptool", "--port", target_port, "flash_id"]
                res_flash = subprocess.run(cmd_flash, capture_output=True, text=True, timeout=10)
                
                output = (res.stdout + "\n" + res_flash.stdout).strip()
                err = (res.stderr + "\n" + res_flash.stderr).strip()
                return {
                    "success": (res.returncode == 0 or res_flash.returncode == 0),
                    "details": output,
                    "error": err if (res.returncode != 0 and res_flash.returncode != 0) else None
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                if was_connected:
                    self.resume_serial()

    def flash_binary(self, bin_path: str, address: str = "0x10000", baudrate: int = 460800) -> Dict[str, any]:
        """Flash a compiled binary (.bin) to ESP32 using esptool."""
        if not self.port:
            self.port = self.auto_detect_port()
            if not self.port:
                return {"success": False, "error": "No ESP32 COM port available."}
        
        with self.lock:
            was_connected = (self.serial_inst is not None and self.serial_inst.is_open)
            if was_connected:
                self.pause_serial()
            
            try:
                cmd = [
                    sys.executable, "-m", "esptool",
                    "--port", self.port,
                    "--baud", str(baudrate),
                    "write_flash",
                    address, bin_path
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return {
                    "success": proc.returncode == 0,
                    "output": proc.stdout,
                    "error": proc.stderr if proc.returncode != 0 else None
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                if was_connected:
                    self.resume_serial()

    def erase_flash(self, port: Optional[str] = None) -> Dict[str, any]:
        """Completely erase the entire SPI flash memory of the ESP32 using esptool."""
        target_port = port or self.port or self.auto_detect_port()
        if not target_port:
            return {"success": False, "error": "No ESP32 COM port available to erase flash."}

        with self.lock:
            was_connected = (self.serial_inst is not None and self.serial_inst.is_open)
            if was_connected:
                self.pause_serial()

            try:
                cmd = [
                    sys.executable, "-m", "esptool",
                    "--port", target_port,
                    "erase_flash"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                return {
                    "success": proc.returncode == 0,
                    "output": proc.stdout,
                    "error": proc.stderr if proc.returncode != 0 else None
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
            finally:
                if was_connected:
                    self.resume_serial()

