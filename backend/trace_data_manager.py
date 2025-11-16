"""
Trace Data Manager - Parses and analyzes BPFtrace JSON output
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TraceDataManager:
    """Manages parsing and analysis of BPFtrace trace data"""
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_json_trace(self, trace_file: str) -> List[Dict]:
        """
        Parse NDJSON (newline-delimited JSON) trace file
        
        Args:
            trace_file: Path to trace output file
            
        Returns:
            List of parsed JSON objects
        """
        events = []
        try:
            with open(trace_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line: {line[:100]}... Error: {e}")
                        continue
            
            logger.info(f"Parsed {len(events)} events from {trace_file}")
            return events
        
        except Exception as e:
            logger.error(f"Error reading trace file {trace_file}: {e}")
            return []
    
    def filter_events(
        self,
        events: List[Dict],
        event_type: Optional[str] = None,
        pid: Optional[int] = None,
        comm: Optional[str] = None
    ) -> List[Dict]:
        """
        Filter events based on criteria
        
        Args:
            events: List of events to filter
            event_type: Filter by event type
            pid: Filter by process ID
            comm: Filter by process name (comm)
            
        Returns:
            Filtered events
        """
        filtered = events
        
        if event_type:
            filtered = [e for e in filtered if e.get('event') == event_type]
        
        if pid is not None:
            filtered = [e for e in filtered if e.get('pid') == pid]
        
        if comm:
            filtered = [e for e in filtered if comm in e.get('comm', '')]
        
        logger.info(f"Filtered to {len(filtered)} events")
        return filtered
    
    def aggregate_by_pid(self, events: List[Dict]) -> Dict[int, List[Dict]]:
        """
        Group events by process ID
        
        Args:
            events: List of events to aggregate
            
        Returns:
            Dictionary mapping PID to list of events
        """
        aggregated = defaultdict(list)
        for event in events:
            pid = event.get('pid')
            if pid is not None:
                aggregated[pid].append(event)
        
        return dict(aggregated)
    
    def aggregate_by_comm(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group events by process name (comm)
        
        Args:
            events: List of events to aggregate
            
        Returns:
            Dictionary mapping comm to list of events
        """
        aggregated = defaultdict(list)
        for event in events:
            comm = event.get('comm', 'unknown')
            aggregated[comm].append(event)
        
        return dict(aggregated)
    
    def count_events(self, events: List[Dict]) -> Dict[str, int]:
        """
        Count events by type
        
        Args:
            events: List of events to count
            
        Returns:
            Dictionary mapping event type to count
        """
        counts = defaultdict(int)
        for event in events:
            event_type = event.get('event', 'unknown')
            counts[event_type] += 1
        
        return dict(counts)
    
    def summarize_trace(self, trace_file: str) -> Dict:
        """
        Generate a summary of trace data
        
        Args:
            trace_file: Path to trace output file
            
        Returns:
            Dictionary with trace summary
        """
        try:
            events = self.parse_json_trace(trace_file)
            
            summary = {
                'file': trace_file,
                'timestamp': datetime.now().isoformat(),
                'total_events': len(events),
                'event_types': self.count_events(events),
                'unique_pids': len(set(e.get('pid') for e in events if 'pid' in e)),
                'unique_comms': len(set(e.get('comm') for e in events if 'comm' in e)),
                'events_by_pid': {
                    str(pid): len(evts)
                    for pid, evts in self.aggregate_by_pid(events).items()
                },
                'top_processes': self._get_top_processes(events, top_n=10)
            }
            
            return summary
        
        except Exception as e:
            logger.error(f"Error summarizing trace: {e}")
            return {'error': str(e)}
    
    def _get_top_processes(self, events: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        Get top N processes by event count
        
        Args:
            events: List of events
            top_n: Number of top processes to return
            
        Returns:
            List of top processes with counts
        """
        by_comm = self.aggregate_by_comm(events)
        top = sorted(
            [{'comm': comm, 'count': len(evts)} for comm, evts in by_comm.items()],
            key=lambda x: x['count'],
            reverse=True
        )
        return top[:top_n]
    
    def query_with_jq(self, trace_file: str, jq_filter: str) -> Dict:
        """
        Query trace file using jq
        
        Args:
            trace_file: Path to trace output file
            jq_filter: jq filter expression
            
        Returns:
            Query result as dictionary
        """
        try:
            # First convert NDJSON to JSON array
            events = self.parse_json_trace(trace_file)
            json_data = json.dumps(events)
            
            # Run jq filter
            result = subprocess.run(
                ['jq', jq_filter],
                input=json_data,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"jq query failed: {result.stderr}")
                return {'error': result.stderr}
            
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {'raw_output': result.stdout}
        
        except subprocess.TimeoutExpired:
            return {'error': 'jq query timed out'}
        except Exception as e:
            logger.error(f"Error running jq query: {e}")
            return {'error': str(e)}
    
    def export_trace_summary(self, trace_file: str, output_format: str = 'json') -> str:
        """
        Export trace summary to file
        
        Args:
            trace_file: Path to trace output file
            output_format: Output format (json, csv, etc.)
            
        Returns:
            Path to exported summary file
        """
        try:
            summary = self.summarize_trace(trace_file)
            
            # Generate output filename
            base_name = Path(trace_file).stem
            output_file = self.output_dir / f"{base_name}_summary.{output_format}"
            
            if output_format == 'json':
                with open(output_file, 'w') as f:
                    json.dump(summary, f, indent=2)
            else:
                # Default to JSON for now
                with open(output_file, 'w') as f:
                    json.dump(summary, f, indent=2)
            
            logger.info(f"Summary exported to {output_file}")
            return str(output_file)
        
        except Exception as e:
            logger.error(f"Error exporting summary: {e}")
            return ""
    
    def get_trace_statistics(self, trace_file: str) -> Dict:
        """
        Get detailed statistics from trace
        
        Args:
            trace_file: Path to trace output file
            
        Returns:
            Dictionary with detailed statistics
        """
        events = self.parse_json_trace(trace_file)
        
        stats = {
            'total_events': len(events),
            'event_types': self.count_events(events),
            'by_pid': {
                str(pid): {'count': len(evts), 'first_comm': evts[0].get('comm', 'unknown')}
                for pid, evts in self.aggregate_by_pid(events).items()
            },
            'by_comm': {
                comm: {'count': len(evts)}
                for comm, evts in self.aggregate_by_comm(events).items()
            }
        }
        
        return stats
