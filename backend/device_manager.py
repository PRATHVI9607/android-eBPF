"""
Device Manager - Handles ADB device detection and communication
"""
import subprocess
import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AndroidDevice:
    """Represents an Android device connected via ADB"""
    device_id: str
    state: str  # device, offline, unknown
    model: Optional[str] = None
    device_name: Optional[str] = None
    api_level: Optional[str] = None
    kernel_version: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'device_id': self.device_id,
            'state': self.state,
            'model': self.model,
            'device_name': self.device_name,
            'api_level': self.api_level,
            'kernel_version': self.kernel_version,
        }


class DeviceManager:
    """Manages ADB device detection and properties"""
    
    def __init__(self):
        self.devices: Dict[str, AndroidDevice] = {}
    
    def _run_adb_command(self, command: List[str], device_id: Optional[str] = None) -> str:
        """
        Run an ADB command and return output
        
        Args:
            command: List of command parts (e.g., ['shell', 'getprop', 'ro.build.version.release'])
            device_id: Optional device ID to target specific device
            
        Returns:
            Command output as string
            
        Raises:
            RuntimeError: If ADB command fails
        """
        try:
            full_cmd = ['adb']
            if device_id:
                full_cmd.extend(['-s', device_id])
            full_cmd.extend(command)
            
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error(f"ADB command failed: {' '.join(full_cmd)}\nError: {result.stderr}")
                raise RuntimeError(f"ADB command failed: {result.stderr}")
            
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"ADB command timed out: {' '.join(command)}")
        except FileNotFoundError:
            raise RuntimeError("ADB not found in PATH. Please ensure ADB is installed and in PATH.")
    
    def detect_devices(self) -> List[AndroidDevice]:
        """
        Detect all connected Android devices
        
        Returns:
            List of connected AndroidDevice objects
        """
        try:
            output = self._run_adb_command(['devices', '-l'])
            
            devices = []
            lines = output.split('\n')[1:]  # Skip header
            
            for line in lines:
                if not line.strip() or line.startswith('*'):
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    device_id = parts[0]
                    state = parts[1]
                    
                    if state in ['device', 'offline', 'unknown']:
                        device = AndroidDevice(device_id=device_id, state=state)
                        
                        # Fetch additional device info
                        if state == 'device':
                            try:
                                device = self._fetch_device_info(device)
                            except Exception as e:
                                logger.warning(f"Could not fetch info for {device_id}: {e}")
                        
                        devices.append(device)
                        self.devices[device_id] = device
            
            logger.info(f"Detected {len(devices)} device(s)")
            return devices
        
        except Exception as e:
            logger.error(f"Error detecting devices: {e}")
            raise
    
    def _fetch_device_info(self, device: AndroidDevice) -> AndroidDevice:
        """
        Fetch additional device information
        
        Args:
            device: AndroidDevice to enrich
            
        Returns:
            Updated AndroidDevice with additional properties
        """
        try:
            # Get model name
            model = self._run_adb_command(
                ['shell', 'getprop', 'ro.product.model'],
                device.device_id
            )
            device.model = model if model else "Unknown"
            
            # Get device name
            device_name = self._run_adb_command(
                ['shell', 'getprop', 'ro.product.device'],
                device.device_id
            )
            device.device_name = device_name if device_name else "Unknown"
            
            # Get API level
            api_level = self._run_adb_command(
                ['shell', 'getprop', 'ro.build.version.sdk'],
                device.device_id
            )
            device.api_level = api_level if api_level else "Unknown"
            
            # Get kernel version
            kernel = self._run_adb_command(
                ['shell', 'uname', '-r'],
                device.device_id
            )
            device.kernel_version = kernel if kernel else "Unknown"
            
            logger.info(f"Device info fetched for {device.device_id}: {device.model}")
            return device
        
        except Exception as e:
            logger.warning(f"Failed to fetch device info: {e}")
            return device
    
    def check_ebpf_support(self, device_id: str) -> bool:
        """
        Check if device supports eBPF
        
        Args:
            device_id: Target device ID
            
        Returns:
            True if device supports eBPF, False otherwise
        """
        try:
            # Check if debugfs exists
            result = self._run_adb_command(
                ['shell', 'test', '-d', '/sys/kernel/debug/tracing', '&&', 'echo', 'yes'],
                device_id
            )
            
            has_tracing = 'yes' in result
            logger.info(f"Device {device_id} eBPF support: {has_tracing}")
            return has_tracing
        except Exception as e:
            logger.error(f"Failed to check eBPF support on {device_id}: {e}")
            return False
    
    def check_root_access(self, device_id: str) -> bool:
        """
        Check if device has root access
        
        Args:
            device_id: Target device ID
            
        Returns:
            True if device has root access, False otherwise
        """
        try:
            result = self._run_adb_command(
                ['shell', 'id', '-u'],
                device_id
            )
            
            uid = int(result.strip())
            has_root = uid == 0
            logger.info(f"Device {device_id} root access: {has_root} (uid: {uid})")
            return has_root
        except Exception as e:
            logger.error(f"Failed to check root access on {device_id}: {e}")
            return False
    
    def get_device(self, device_id: str) -> Optional[AndroidDevice]:
        """
        Get device by ID
        
        Args:
            device_id: Target device ID
            
        Returns:
            AndroidDevice if found, None otherwise
        """
        return self.devices.get(device_id)
    
    def list_devices_json(self) -> Dict:
        """
        Get all devices as JSON
        
        Returns:
            Dictionary with device information
        """
        self.detect_devices()
        return {
            'timestamp': datetime.now().isoformat(),
            'device_count': len(self.devices),
            'devices': [device.to_dict() for device in self.devices.values()]
        }
