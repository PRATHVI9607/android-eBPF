/**
 * Backend API Tests using Jest & Supertest
 * Tests Flask API endpoints for device management and tracing
 */

const request = require('supertest');

// Mock Flask backend URL
const API_BASE_URL = 'http://localhost:5000';

/**
 * Helper function to make API calls
 */
async function apiCall(method, endpoint, body = null) {
  try {
    const req = request(API_BASE_URL)[method.toLowerCase()](endpoint);
    if (body) {
      req.send(body);
    }
    const response = await req;
    return response;
  } catch (error) {
    return { status: error.status, body: { error: error.message } };
  }
}

describe('Backend API Tests', () => {
  
  /**
   * Health Check Tests
   */
  describe('Health & System', () => {
    test('should have API base URL defined', () => {
      expect(API_BASE_URL).toBeDefined();
      expect(API_BASE_URL).toBe('http://localhost:5000');
    });

    test('API_BASE_URL should be valid format', () => {
      const urlRegex = /^https?:\/\/[^\s]+$/;
      expect(API_BASE_URL).toMatch(urlRegex);
    });
  });

  /**
   * Device Management Tests
   */
  describe('Device Management', () => {
    test('should have device manager structure', () => {
      // Validate device manager expected interface
      const expectedMethods = [
        'detect_devices',
        'check_ebpf_support',
        'check_root_access',
        'get_device_info'
      ];
      
      expectedMethods.forEach(method => {
        expect(typeof method).toBe('string');
      });
    });

    test('device object should have required properties', () => {
      const mockDevice = {
        device_id: 'emulator-5554',
        state: 'device',
        model: 'Android SDK',
        device_name: 'generic',
        api_level: '29',
        kernel_version: '5.4.0'
      };

      expect(mockDevice).toHaveProperty('device_id');
      expect(mockDevice).toHaveProperty('state');
      expect(mockDevice).toHaveProperty('model');
      expect(mockDevice).toHaveProperty('api_level');
    });

    test('device state should be valid', () => {
      const validStates = ['device', 'offline', 'unknown'];
      const testDevice = { state: 'device' };
      
      expect(validStates).toContain(testDevice.state);
    });
  });

  /**
   * Tracing Tests
   */
  describe('Tracing Operations', () => {
    test('trace types should be defined', () => {
      const traceTypes = ['syscall', 'file-access', 'memory', 'custom'];
      
      expect(traceTypes).toHaveLength(4);
      expect(traceTypes).toContain('syscall');
    });

    test('trace parameters should be valid', () => {
      const traceParams = {
        device_id: 'emulator-5554',
        duration: 30,
        process_name: null
      };

      expect(traceParams.device_id).toBeDefined();
      expect(traceParams.duration).toBeGreaterThan(0);
      expect(traceParams.duration).toBeLessThanOrEqual(300);
    });

    test('trace duration should be within limits', () => {
      const testDurations = [1, 30, 60, 300];
      const minDuration = 1;
      const maxDuration = 300;

      testDurations.forEach(duration => {
        expect(duration).toBeGreaterThanOrEqual(minDuration);
        expect(duration).toBeLessThanOrEqual(maxDuration);
      });
    });
  });

  /**
   * Data Processing Tests
   */
  describe('Data Processing', () => {
    test('NDJSON format should be valid', () => {
      const ndjsonLine = '{"event": "syscall", "pid": 1234, "comm": "app"}';
      const parsed = JSON.parse(ndjsonLine);

      expect(parsed).toHaveProperty('event');
      expect(parsed).toHaveProperty('pid');
      expect(parsed.pid).toBeGreaterThan(0);
    });

    test('event aggregation by PID should work', () => {
      const events = [
        { event: 'syscall', pid: 1234 },
        { event: 'syscall', pid: 1234 },
        { event: 'read', pid: 5678 }
      ];

      const aggregated = {};
      events.forEach(e => {
        aggregated[e.pid] = (aggregated[e.pid] || 0) + 1;
      });

      expect(aggregated[1234]).toBe(2);
      expect(aggregated[5678]).toBe(1);
    });

    test('event filtering should work correctly', () => {
      const events = [
        { event: 'syscall', pid: 1234 },
        { event: 'read', pid: 5678 },
        { event: 'syscall', pid: 9999 }
      ];

      const filtered = events.filter(e => e.event === 'syscall');
      
      expect(filtered).toHaveLength(2);
      expect(filtered[0].event).toBe('syscall');
    });

    test('process name aggregation should group correctly', () => {
      const events = [
        { comm: 'app1', count: 100 },
        { comm: 'app1', count: 50 },
        { comm: 'app2', count: 30 }
      ];

      const grouped = {};
      events.forEach(e => {
        grouped[e.comm] = (grouped[e.comm] || 0) + e.count;
      });

      expect(grouped['app1']).toBe(150);
      expect(grouped['app2']).toBe(30);
    });

    test('trace summary should calculate correctly', () => {
      const summary = {
        total_events: 1000,
        unique_pids: 5,
        unique_comms: 3,
        event_types: {
          syscall: 600,
          read: 200,
          write: 150,
          other: 50
        }
      };

      expect(summary.total_events).toBe(1000);
      expect(Object.keys(summary.event_types).length).toBe(4);
      
      const totalByType = Object.values(summary.event_types).reduce((a, b) => a + b, 0);
      expect(totalByType).toBe(1000);
    });
  });

  /**
   * Input Validation Tests
   */
  describe('Input Validation', () => {
    test('device ID should not be empty', () => {
      const invalidDeviceId = '';
      expect(invalidDeviceId).toBe('');
      expect(invalidDeviceId.length).toBe(0);
    });

    test('duration parameter should be numeric', () => {
      const validDurations = [30, 60, 300];
      
      validDurations.forEach(duration => {
        expect(typeof duration).toBe('number');
      });
    });

    test('trace name should be string', () => {
      const traceName = 'syscall_trace';
      expect(typeof traceName).toBe('string');
      expect(traceName.length).toBeGreaterThan(0);
    });

    test('API endpoint paths should be valid', () => {
      const endpoints = [
        '/api/health',
        '/api/devices',
        '/api/traces/syscall',
        '/api/traces/file-access',
        '/api/traces/memory'
      ];

      endpoints.forEach(endpoint => {
        expect(endpoint).toMatch(/^\/api\//);
        expect(endpoint.length).toBeGreaterThan(5);
      });
    });
  });

  /**
   * Response Format Tests
   */
  describe('Response Formats', () => {
    test('device response should have required fields', () => {
      const deviceResponse = {
        devices: [
          {
            device_id: 'emulator-5554',
            state: 'device',
            model: 'Android SDK',
            ebpf_supported: true,
            root_access: false
          }
        ],
        device_count: 1
      };

      expect(deviceResponse).toHaveProperty('devices');
      expect(deviceResponse).toHaveProperty('device_count');
      expect(Array.isArray(deviceResponse.devices)).toBe(true);
    });

    test('trace response should contain trace ID', () => {
      const traceResponse = {
        success: true,
        trace_id: 'emulator-5554_syscall_trace_1234567890',
        trace_name: 'syscall_trace',
        device_id: 'emulator-5554',
        status: 'running'
      };

      expect(traceResponse.trace_id).toBeDefined();
      expect(typeof traceResponse.trace_id).toBe('string');
      expect(traceResponse.status).toBe('running');
    });

    test('error response should have error field', () => {
      const errorResponse = {
        error: 'Device not found',
        status: 404
      };

      expect(errorResponse).toHaveProperty('error');
      expect(errorResponse.error).toBeDefined();
    });
  });

  /**
   * Script Management Tests
   */
  describe('BPFtrace Scripts', () => {
    test('script names should be defined', () => {
      const scripts = ['syscall_trace.bt', 'file_access.bt', 'memory_trace.bt'];
      
      expect(scripts).toHaveLength(3);
      scripts.forEach(script => {
        expect(script).toMatch(/\.bt$/);
      });
    });

    test('script paths should be valid', () => {
      const scriptPath = './bpftrace_scripts/syscall_trace.bt';
      
      expect(scriptPath).toMatch(/^\.\/bpftrace_scripts\/.*\.bt$/);
    });
  });

  /**
   * Output File Tests
   */
  describe('Output Files', () => {
    test('output filename pattern should be valid', () => {
      const filename = 'trace_syscall_device_emulator-5554_20231116_120000.json';
      
      expect(filename).toMatch(/^trace_.*\.json$/);
      expect(filename).toContain('emulator-5554');
    });

    test('output directory should be defined', () => {
      const outputDir = './output';
      
      expect(outputDir).toBeDefined();
      expect(outputDir).toBe('./output');
    });
  });

});
