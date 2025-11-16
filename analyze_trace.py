#!/usr/bin/env python3
"""
Android eBPF Profiler - Trace Analysis Utility
Post-processing and analysis of collected trace data
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
import statistics

class TraceAnalyzer:
    """Analyze BPFtrace JSON output"""
    
    def __init__(self, trace_file):
        self.trace_file = Path(trace_file)
        self.events = self._load_events()
    
    def _load_events(self):
        """Load events from NDJSON file"""
        events = []
        try:
            with open(self.trace_file) as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Line {line_num}: Invalid JSON - {e}")
                        continue
        except FileNotFoundError:
            print(f"❌ File not found: {self.trace_file}")
            sys.exit(1)
        
        return events
    
    def summary(self):
        """Print trace summary"""
        if not self.events:
            print("❌ No events found in trace")
            return
        
        print(f"\n📊 Trace Summary: {self.trace_file.name}")
        print("=" * 60)
        
        # Basic stats
        event_types = Counter(e.get('event') for e in self.events if 'event' in e)
        pids = set(e.get('pid') for e in self.events if 'pid' in e)
        comms = set(e.get('comm') for e in self.events if 'comm' in e)
        
        print(f"Total Events:        {len(self.events)}")
        print(f"Unique PIDs:         {len(pids)}")
        print(f"Unique Processes:    {len(comms)}")
        print(f"Event Types:         {len(event_types)}")
        
        print(f"\n📈 Top Event Types:")
        for event_type, count in event_types.most_common(10):
            pct = (count / len(self.events)) * 100
            print(f"   {event_type:20} {count:6} ({pct:5.1f}%)")
        
        print(f"\n📱 Top Processes (by event count):")
        comm_counts = Counter(e.get('comm') for e in self.events if 'comm' in e)
        for comm, count in comm_counts.most_common(10):
            pct = (count / len(self.events)) * 100
            print(f"   {comm:30} {count:6} ({pct:5.1f}%)")
        
        print(f"\n⏱️  Timestamps:")
        timestamps = [e.get('timestamp') for e in self.events if 'timestamp' in e and isinstance(e.get('timestamp'), (int, float))]
        if timestamps:
            print(f"   Min: {min(timestamps)}")
            print(f"   Max: {max(timestamps)}")
            print(f"   Range: {max(timestamps) - min(timestamps)}")
        
        print()
    
    def filter_by_event(self, event_type):
        """Filter events by type"""
        return [e for e in self.events if e.get('event') == event_type]
    
    def filter_by_pid(self, pid):
        """Filter events by PID"""
        return [e for e in self.events if e.get('pid') == pid]
    
    def filter_by_comm(self, comm):
        """Filter events by process name"""
        return [e for e in self.events if comm in e.get('comm', '')]
    
    def export_csv(self, output_file):
        """Export events to CSV"""
        import csv
        
        if not self.events:
            print("❌ No events to export")
            return
        
        # Get all unique keys
        all_keys = set()
        for event in self.events:
            all_keys.update(event.keys())
        
        keys = sorted(list(all_keys))
        
        try:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.events)
            print(f"✅ Exported to {output_file}")
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def event_timeline(self, output_file):
        """Create event timeline"""
        if not self.events:
            print("❌ No events to analyze")
            return
        
        # Group by event type
        timeline = defaultdict(list)
        for event in self.events:
            event_type = event.get('event', 'unknown')
            timestamp = event.get('timestamp', 0)
            timeline[event_type].append(timestamp)
        
        try:
            with open(output_file, 'w') as f:
                f.write("Event Timeline\n")
                f.write("=" * 80 + "\n\n")
                
                for event_type in sorted(timeline.keys()):
                    timestamps = sorted(timeline[event_type])
                    f.write(f"{event_type}:\n")
                    f.write(f"  Count: {len(timestamps)}\n")
                    f.write(f"  First: {timestamps[0]}\n")
                    f.write(f"  Last: {timestamps[-1]}\n")
                    f.write(f"  Range: {timestamps[-1] - timestamps[0]}\n")
                    
                    if len(timestamps) > 1:
                        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
                        f.write(f"  Avg Interval: {statistics.mean(intervals):.2f}\n")
                        f.write(f"  Min Interval: {min(intervals):.2f}\n")
                        f.write(f"  Max Interval: {max(intervals):.2f}\n")
                    
                    f.write("\n")
            
            print(f"✅ Timeline saved to {output_file}")
        except Exception as e:
            print(f"❌ Failed to save timeline: {e}")
    
    def process_summary(self, output_file):
        """Generate detailed process summary"""
        try:
            process_data = defaultdict(lambda: {
                'pid': None,
                'event_count': 0,
                'event_types': Counter(),
                'total_time': 0
            })
            
            for event in self.events:
                comm = event.get('comm', 'unknown')
                pid = event.get('pid')
                event_type = event.get('event')
                
                if comm in process_data:
                    process_data[comm]['pid'] = pid
                else:
                    process_data[comm]['pid'] = pid
                
                process_data[comm]['event_count'] += 1
                process_data[comm]['event_types'][event_type] += 1
            
            with open(output_file, 'w') as f:
                f.write("Process Summary\n")
                f.write("=" * 80 + "\n\n")
                
                for comm in sorted(process_data.keys(), 
                                 key=lambda x: process_data[x]['event_count'], 
                                 reverse=True):
                    data = process_data[comm]
                    f.write(f"Process: {comm} (PID: {data['pid']})\n")
                    f.write(f"  Total Events: {data['event_count']}\n")
                    f.write(f"  Event Types:\n")
                    for event_type, count in data['event_types'].most_common(5):
                        f.write(f"    {event_type}: {count}\n")
                    f.write("\n")
            
            print(f"✅ Process summary saved to {output_file}")
        except Exception as e:
            print(f"❌ Failed to save process summary: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Android eBPF Profiler - Trace Analysis Utility'
    )
    parser.add_argument('trace_file', help='Input trace file (NDJSON format)')
    parser.add_argument('--summary', action='store_true', help='Print trace summary')
    parser.add_argument('--export-csv', metavar='FILE', help='Export to CSV')
    parser.add_argument('--timeline', metavar='FILE', help='Generate event timeline')
    parser.add_argument('--process-summary', metavar='FILE', help='Generate process summary')
    parser.add_argument('--filter-event', metavar='TYPE', help='Filter by event type')
    parser.add_argument('--filter-pid', type=int, metavar='PID', help='Filter by PID')
    parser.add_argument('--filter-comm', metavar='NAME', help='Filter by process name')
    parser.add_argument('--all', action='store_true', help='Generate all reports')
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = TraceAnalyzer(args.trace_file)
    
    if args.summary or args.all:
        analyzer.summary()
    
    if args.export_csv or args.all:
        output = args.export_csv or Path(args.trace_file).stem + '.csv'
        analyzer.export_csv(output)
    
    if args.timeline or args.all:
        output = args.timeline or Path(args.trace_file).stem + '_timeline.txt'
        analyzer.event_timeline(output)
    
    if args.process_summary or args.all:
        output = args.process_summary or Path(args.trace_file).stem + '_processes.txt'
        analyzer.process_summary(output)
    
    if args.filter_event:
        events = analyzer.filter_by_event(args.filter_event)
        print(f"\n✅ Found {len(events)} events of type '{args.filter_event}'")
    
    if args.filter_pid:
        events = analyzer.filter_by_pid(args.filter_pid)
        print(f"\n✅ Found {len(events)} events for PID {args.filter_pid}")
    
    if args.filter_comm:
        events = analyzer.filter_by_comm(args.filter_comm)
        print(f"\n✅ Found {len(events)} events for process '{args.filter_comm}'")


if __name__ == '__main__':
    main()
