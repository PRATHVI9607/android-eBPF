"""
BPFtrace Orchestrator - Manages BPFtrace execution and data collection
"""
import subprocess
import json
import os
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import threading
import queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BPFtraceOrchestrator:
    """Orchestrates BPFtrace execution on devices"""
    
    def __init__(self, output_dir: str = "./output", scripts_dir: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get scripts directory - use provided path or derive from backend location
        if scripts_dir:
            self.scripts_dir = Path(scripts_dir)
        else:
            # Get parent of backend directory and find bpftrace_scripts
            backend_dir = Path(__file__).parent
            self.scripts_dir = backend_dir.parent / "bpftrace_scripts"
        
        self.active_traces: Dict[str, Dict] = {}
        self.adb_binary = "adb"
    
    def _push_script_to_device(self, device_id: str, script_path: str, remote_path: str) -> bool:
        """
        Push a BPFtrace script to the device
        
        Args:
            device_id: Target device ID
            script_path: Local path to BPFtrace script
            remote_path: Path on device where script will be stored
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = [self.adb_binary, '-s', device_id, 'push', script_path, remote_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                logger.error(f"Failed to push script: {result.stderr}")
                return False
            
            logger.info(f"Script pushed to {device_id}:{remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error pushing script: {e}")
            return False
    
    def _run_command_on_device(
        self,
        device_id: str,
        command: List[str],
        output_callback: Optional[Callable[[str], None]] = None,
        timeout: int = 300
    ) -> tuple[bool, str]:
        """
        Run a command on device via ADB shell
        
        Args:
            device_id: Target device ID
            command: Command parts to execute
            output_callback: Optional callback for streaming output
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (success: bool, output: str)
        """
        try:
            full_cmd = [self.adb_binary, '-s', device_id, 'shell'] + command
            
            process = subprocess.Popen(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            try:
                for line in iter(process.stdout.readline, ''):
                    if not line:
                        break
                    output_lines.append(line)
                    if output_callback:
                        output_callback(line)
                
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                logger.error(f"Command timed out on {device_id}")
                return False, "Command timed out"
            
            output = ''.join(output_lines)
            success = process.returncode == 0
            
            if not success:
                stderr = process.stderr.read() if process.stderr else ""
                logger.error(f"Command failed on {device_id}: {stderr}")
            
            return success, output
        
        except Exception as e:
            logger.error(f"Error running command on device: {e}")
            return False, str(e)
    
    def execute_bpftrace(
        self,
        device_id: str,
        script_path: str,
        trace_name: str,
        duration: int = 60,
        json_output: bool = True
    ) -> Dict:
        """
        Execute a BPFtrace script on device
        
        Args:
            device_id: Target device ID
            script_path: Path to local BPFtrace script
            trace_name: Name for this trace session
            duration: Trace duration in seconds
            json_output: Whether to request JSON output
            
        Returns:
            Dictionary with trace execution results
        """
        try:
            if not os.path.exists(script_path):
                return {
                    'success': False,
                    'error': f"Script not found: {script_path}",
                    'trace_name': trace_name,
                    'device_id': device_id
                }
            
            # Generate remote path
            script_name = os.path.basename(script_path)
            remote_script = f"/data/local/tmp/{script_name}"
            
            # Push script to device
            if not self._push_script_to_device(device_id, script_path, remote_script):
                return {
                    'success': False,
                    'error': 'Failed to push script to device',
                    'trace_name': trace_name,
                    'device_id': device_id
                }
            
            # Build BPFtrace command
            output_file = self.output_dir / f"{trace_name}_{device_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            cmd = ['bpftrace']
            if json_output:
                cmd.extend(['-f', 'json'])
            cmd.append(remote_script)
            
            # Create timeout command wrapper
            full_cmd = f"timeout {duration} {' '.join(cmd)}"
            
            logger.info(f"Executing BPFtrace on {device_id}: {full_cmd}")
            
            # Store trace metadata
            trace_id = f"{device_id}_{trace_name}_{datetime.now().timestamp()}"
            self.active_traces[trace_id] = {
                'device_id': device_id,
                'trace_name': trace_name,
                'output_file': str(output_file),
                'status': 'running',
                'start_time': datetime.now().isoformat(),
                'duration': duration
            }
            
            # Run command
            success, output = self._run_command_on_device(
                device_id,
                [full_cmd],
                timeout=duration + 10
            )
            
            # Save output to file
            if output:
                with open(output_file, 'w') as f:
                    f.write(output)
            
            # Update trace status
            self.active_traces[trace_id]['status'] = 'completed'
            self.active_traces[trace_id]['end_time'] = datetime.now().isoformat()
            self.active_traces[trace_id]['output_size'] = len(output)
            
            logger.info(f"Trace completed: {trace_name} on {device_id}")
            
            return {
                'success': success,
                'trace_id': trace_id,
                'trace_name': trace_name,
                'device_id': device_id,
                'output_file': str(output_file),
                'output_lines': len(output.split('\n')),
                'status': 'completed'
            }
        
        except Exception as e:
            logger.error(f"Error executing BPFtrace: {e}")
            return {
                'success': False,
                'error': str(e),
                'trace_name': trace_name,
                'device_id': device_id
            }
    
    def execute_syscall_trace(
        self,
        device_id: str,
        process_name: Optional[str] = None,
        duration: int = 60
    ) -> Dict:
        """
        Execute syscall tracing
        
        Args:
            device_id: Target device ID
            process_name: Optional process to filter
            duration: Trace duration in seconds
            
        Returns:
            Trace execution result
        """
        trace_name = f"syscall_trace_{process_name or 'all'}"
        script_path = str(self.scripts_dir / "syscall_trace.bt")
        
        if not os.path.exists(script_path):
            logger.warning(f"Syscall trace script not found at {script_path}")
            return {'success': False, 'error': 'Trace script not found'}
        
        return self.execute_bpftrace(
            device_id, script_path, trace_name, duration, json_output=True
        )
    
    def execute_file_access_trace(
        self,
        device_id: str,
        duration: int = 60
    ) -> Dict:
        """
        Execute file access tracing
        
        Args:
            device_id: Target device ID
            duration: Trace duration in seconds
            
        Returns:
            Trace execution result
        """
        trace_name = "file_access_trace"
        script_path = str(self.scripts_dir / "file_access.bt")
        
        if not os.path.exists(script_path):
            logger.warning(f"File access trace script not found at {script_path}")
            return {'success': False, 'error': 'Trace script not found'}
        
        return self.execute_bpftrace(
            device_id, script_path, trace_name, duration, json_output=True
        )
    
    def execute_memory_trace(
        self,
        device_id: str,
        duration: int = 60
    ) -> Dict:
        """
        Execute memory tracing
        
        Args:
            device_id: Target device ID
            duration: Trace duration in seconds
            
        Returns:
            Trace execution result
        """
        trace_name = "memory_trace"
        script_path = str(self.scripts_dir / "memory_trace.bt")
        
        if not os.path.exists(script_path):
            logger.warning(f"Memory trace script not found at {script_path}")
            return {'success': False, 'error': 'Trace script not found'}
        
        return self.execute_bpftrace(
            device_id, script_path, trace_name, duration, json_output=True
        )
    
    def list_active_traces(self) -> List[Dict]:
        """
        List all active and completed traces
        
        Returns:
            List of trace metadata
        """
        return list(self.active_traces.values())
    
    def get_trace_result(self, trace_id: str) -> Optional[Dict]:
        """
        Get results of a specific trace
        
        Args:
            trace_id: ID of the trace
            
        Returns:
            Trace result dictionary or None if not found
        """
        return self.active_traces.get(trace_id)
