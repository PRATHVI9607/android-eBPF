"""
Flask API Backend - RESTful endpoints for device management and tracing
"""
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import os
import logging
from datetime import datetime
from threading import Thread
from typing import Dict
import json
from pathlib import Path

from device_manager import DeviceManager
from bpftrace_orchestrator import BPFtraceOrchestrator
from trace_data_manager import TraceDataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize managers
device_manager = DeviceManager()
bpftrace_orchestrator = BPFtraceOrchestrator(output_dir="./output")
trace_data_manager = TraceDataManager(output_dir="./output")

# Store active jobs
active_jobs: Dict = {}


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'service': 'Android eBPF Profiling Backend'
    })


@app.route('/api/devices', methods=['GET'])
def list_devices():
    """
    List all connected Android devices
    
    Returns:
        JSON with list of devices and their properties
    """
    try:
        result = device_manager.list_devices_json()
        
        # Check capabilities for each device
        for device in result['devices']:
            if device['state'] == 'device':
                device['ebpf_supported'] = device_manager.check_ebpf_support(device['device_id'])
                device['root_access'] = device_manager.check_root_access(device['device_id'])
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/devices/<device_id>/info', methods=['GET'])
def get_device_info(device_id: str):
    """
    Get detailed information about a specific device
    
    Args:
        device_id: The device ID
        
    Returns:
        JSON with device information
    """
    try:
        device = device_manager.get_device(device_id)
        
        if not device:
            # Try to detect it
            device_manager.detect_devices()
            device = device_manager.get_device(device_id)
        
        if not device:
            return jsonify({'error': 'Device not found'}), 404
        
        info = device.to_dict()
        if device.state == 'device':
            info['ebpf_supported'] = device_manager.check_ebpf_support(device_id)
            info['root_access'] = device_manager.check_root_access(device_id)
        
        return jsonify(info), 200
    
    except Exception as e:
        logger.error(f"Error getting device info: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces', methods=['GET'])
def list_traces():
    """
    List all active and completed traces
    
    Returns:
        JSON with list of traces
    """
    try:
        traces = bpftrace_orchestrator.list_active_traces()
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'trace_count': len(traces),
            'traces': traces
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing traces: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/syscall', methods=['POST'])
def execute_syscall_trace():
    """
    Execute syscall trace on device
    
    Expected JSON payload:
    {
        "device_id": "device_serial",
        "duration": 60,
        "process_name": "optional_process_name"
    }
    
    Returns:
        JSON with trace execution result
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        duration = data.get('duration', 60)
        process_name = data.get('process_name')
        
        if not device_id:
            return jsonify({'error': 'device_id is required'}), 400
        
        # Run in background
        result = bpftrace_orchestrator.execute_syscall_trace(
            device_id=device_id,
            process_name=process_name,
            duration=duration
        )
        
        return jsonify(result), 200 if result.get('success') else 500
    
    except Exception as e:
        logger.error(f"Error executing syscall trace: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/file-access', methods=['POST'])
def execute_file_access_trace():
    """
    Execute file access trace on device
    
    Expected JSON payload:
    {
        "device_id": "device_serial",
        "duration": 60
    }
    
    Returns:
        JSON with trace execution result
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        duration = data.get('duration', 60)
        
        if not device_id:
            return jsonify({'error': 'device_id is required'}), 400
        
        result = bpftrace_orchestrator.execute_file_access_trace(
            device_id=device_id,
            duration=duration
        )
        
        return jsonify(result), 200 if result.get('success') else 500
    
    except Exception as e:
        logger.error(f"Error executing file access trace: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/memory', methods=['POST'])
def execute_memory_trace():
    """
    Execute memory trace on device
    
    Expected JSON payload:
    {
        "device_id": "device_serial",
        "duration": 60
    }
    
    Returns:
        JSON with trace execution result
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        duration = data.get('duration', 60)
        
        if not device_id:
            return jsonify({'error': 'device_id is required'}), 400
        
        result = bpftrace_orchestrator.execute_memory_trace(
            device_id=device_id,
            duration=duration
        )
        
        return jsonify(result), 200 if result.get('success') else 500
    
    except Exception as e:
        logger.error(f"Error executing memory trace: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/custom', methods=['POST'])
def execute_custom_trace():
    """
    Execute custom BPFtrace script on device
    
    Expected JSON payload:
    {
        "device_id": "device_serial",
        "script_name": "script_filename",
        "trace_name": "custom_trace",
        "duration": 60
    }
    
    Returns:
        JSON with trace execution result
    """
    try:
        data = request.get_json()
        device_id = data.get('device_id')
        script_name = data.get('script_name')
        trace_name = data.get('trace_name', 'custom_trace')
        duration = data.get('duration', 60)
        
        if not device_id or not script_name:
            return jsonify({'error': 'device_id and script_name are required'}), 400
        
        script_path = f"./bpftrace_scripts/{script_name}"
        
        if not os.path.exists(script_path):
            return jsonify({'error': f'Script not found: {script_path}'}), 404
        
        result = bpftrace_orchestrator.execute_bpftrace(
            device_id=device_id,
            script_path=script_path,
            trace_name=trace_name,
            duration=duration,
            json_output=True
        )
        
        return jsonify(result), 200 if result.get('success') else 500
    
    except Exception as e:
        logger.error(f"Error executing custom trace: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/<trace_id>', methods=['GET'])
def get_trace_result(trace_id: str):
    """
    Get results of a specific trace
    
    Args:
        trace_id: The trace ID
        
    Returns:
        JSON with trace result
    """
    try:
        result = bpftrace_orchestrator.get_trace_result(trace_id)
        
        if not result:
            return jsonify({'error': 'Trace not found'}), 404
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error getting trace result: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/<trace_id>/summary', methods=['GET'])
def get_trace_summary(trace_id: str):
    """
    Get summary of trace data
    
    Args:
        trace_id: The trace ID
        
    Returns:
        JSON with trace summary
    """
    try:
        trace = bpftrace_orchestrator.get_trace_result(trace_id)
        
        if not trace:
            return jsonify({'error': 'Trace not found'}), 404
        
        output_file = trace.get('output_file')
        if not output_file or not os.path.exists(output_file):
            return jsonify({'error': 'Output file not found'}), 404
        
        summary = trace_data_manager.summarize_trace(output_file)
        return jsonify(summary), 200
    
    except Exception as e:
        logger.error(f"Error getting trace summary: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/<trace_id>/download', methods=['GET'])
def download_trace(trace_id: str):
    """
    Download trace output file
    
    Args:
        trace_id: The trace ID
        
    Returns:
        File download or error
    """
    try:
        trace = bpftrace_orchestrator.get_trace_result(trace_id)
        
        if not trace:
            return jsonify({'error': 'Trace not found'}), 404
        
        output_file = trace.get('output_file')
        if not output_file or not os.path.exists(output_file):
            return jsonify({'error': 'Output file not found'}), 404
        
        return send_file(
            output_file,
            as_attachment=True,
            download_name=os.path.basename(output_file)
        )
    
    except Exception as e:
        logger.error(f"Error downloading trace: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/traces/<trace_id>/stats', methods=['GET'])
def get_trace_stats(trace_id: str):
    """
    Get detailed statistics from trace
    
    Args:
        trace_id: The trace ID
        
    Returns:
        JSON with trace statistics
    """
    try:
        trace = bpftrace_orchestrator.get_trace_result(trace_id)
        
        if not trace:
            return jsonify({'error': 'Trace not found'}), 404
        
        output_file = trace.get('output_file')
        if not output_file or not os.path.exists(output_file):
            return jsonify({'error': 'Output file not found'}), 404
        
        stats = trace_data_manager.get_trace_statistics(output_file)
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Error getting trace stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/scripts', methods=['GET'])
def list_scripts():
    """
    List available BPFtrace scripts
    
    Returns:
        JSON with list of available scripts
    """
    try:
        scripts_dir = Path("./bpftrace_scripts")
        scripts = []
        
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.bt"):
                scripts.append({
                    'name': script_file.name,
                    'path': str(script_file),
                    'size': script_file.stat().st_size
                })
        
        return jsonify({
            'script_count': len(scripts),
            'scripts': scripts
        }), 200
    
    except Exception as e:
        logger.error(f"Error listing scripts: {e}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    logger.info("Starting Android eBPF Profiling Backend API...")
    app.run(debug=True, host='0.0.0.0', port=5000)
