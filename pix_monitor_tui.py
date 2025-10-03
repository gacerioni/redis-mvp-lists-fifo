import os
import redis
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.columns import Columns


class PIXMonitor:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.stream_name = os.getenv("REDIS_STREAM", "pix_payments")
        self.group_name = os.getenv("GROUP_NAME", "pix_consumers")
        self.backend_response_prefix = os.getenv("BACKEND_RESPONSE_PREFIX", "backend_bacen_response_")
        
        self.redis_client = redis.from_url(self.redis_url)
        self.console = Console()
        
        # Tracking variables
        self.start_time = datetime.now()
        self.last_processed_count = 0
        self.processing_rate = 0
        
    def get_redis_info(self) -> Dict[str, Any]:
        """Get various Redis metrics for monitoring"""
        try:
            # Test Redis connection first
            self.redis_client.ping()
            # Basic counters with proper error handling
            try:
                processed_count = self.redis_client.get("processed_count")
                processed_count = int(processed_count) if processed_count else 0
            except (ValueError, TypeError):
                processed_count = 0
            
            try:
                total_amount = self.redis_client.get("total_amount")
                total_amount = float(total_amount) if total_amount else 0.0
            except (ValueError, TypeError):
                total_amount = 0.0
            
            # Stream info
            try:
                stream_info = self.redis_client.xinfo_stream(self.stream_name)
                stream_length = stream_info.get("length", 0)
                last_generated_id = stream_info.get("last-generated-id", "N/A")
                first_entry = stream_info.get("first-entry", None)
                last_entry = stream_info.get("last-entry", None)
            except redis.exceptions.ResponseError:
                stream_length = 0
                last_generated_id = "N/A"
                first_entry = None
                last_entry = None
            
            # Consumer group info - enhanced with all groups
            consumer_groups = {}
            try:
                groups_info = self.redis_client.xinfo_groups(self.stream_name)
                for group in groups_info:
                    group_name = group["name"].decode()
                    consumer_groups[group_name] = {
                        "pending": group.get("pending", 0),
                        "last_delivered_id": group.get("last-delivered-id", b"N/A").decode(),
                        "consumers": group.get("consumers", 0),
                        "entries_read": group.get("entries-read", 0),
                        "lag": group.get("lag", 0)
                    }
                    
                    # Get individual consumer details for this group
                    try:
                        consumers = self.redis_client.xinfo_consumers(self.stream_name, group_name)
                        consumer_groups[group_name]["consumer_details"] = []
                        for consumer in consumers:
                            consumer_groups[group_name]["consumer_details"].append({
                                "name": consumer["name"].decode(),
                                "pending": consumer.get("pending", 0),
                                "idle": consumer.get("idle", 0)
                            })
                    except redis.exceptions.ResponseError:
                        consumer_groups[group_name]["consumer_details"] = []
                        
            except redis.exceptions.ResponseError:
                consumer_groups = {}
            
            # Calculate processing rate
            current_time = time.time()
            if hasattr(self, 'last_check_time'):
                time_diff = current_time - self.last_check_time
                count_diff = processed_count - self.last_processed_count
                if time_diff > 0:
                    self.processing_rate = count_diff / time_diff
            
            self.last_check_time = current_time
            self.last_processed_count = processed_count
            
            # Backend response streams info - dynamic discovery
            backend_streams = {}
            try:
                keys = self.redis_client.keys(f"{self.backend_response_prefix}*")
                for key in keys:
                    stream_name = key.decode()
                    backend_id = stream_name.replace(self.backend_response_prefix, "")
                    try:
                        info = self.redis_client.xinfo_stream(stream_name)
                        backend_streams[backend_id] = {
                            "length": info.get("length", 0),
                            "last_id": info.get("last-generated-id", "N/A"),
                            "stream_name": stream_name
                        }
                    except redis.exceptions.ResponseError:
                        backend_streams[backend_id] = {
                            "length": 0, 
                            "last_id": "N/A",
                            "stream_name": stream_name
                        }
            except Exception:
                pass
            
            return {
                "processed_count": processed_count,
                "total_amount": total_amount,
                "stream_length": stream_length,
                "last_generated_id": last_generated_id,
                "first_entry": first_entry,
                "last_entry": last_entry,
                "consumer_groups": consumer_groups,
                "processing_rate": self.processing_rate,
                "backend_streams": backend_streams,
                "uptime": datetime.now() - self.start_time
            }
            
        except redis.exceptions.ConnectionError:
            return {"error": "Cannot connect to Redis server"}
        except redis.exceptions.TimeoutError:
            return {"error": "Redis connection timeout"}
        except Exception as e:
            return {"error": f"Redis error: {str(e)}"}
    
    def create_header_panel(self) -> Panel:
        """Create header panel with title and connection info"""
        title = Text("PIX Payment System Monitor", style="bold magenta")
        subtitle = Text(f"Redis: {self.redis_url} | Stream: {self.stream_name}", style="dim")
        header_content = Align.center(Text.assemble(title, "\n", subtitle))
        return Panel(header_content, style="blue")
    
    def create_processor_panel(self, data: Dict[str, Any]) -> Panel:
        """Create panel showing PIX processor metrics"""
        if "error" in data:
            return Panel(f"Error: {data['error']}", title="PIX Processor", style="red")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Messages Processed", f"{data.get('processed_count', 0):,}")
        table.add_row("Total Amount", f"BRL {data.get('total_amount', 0.0):,.2f}")
        table.add_row("Processing Rate", f"{data.get('processing_rate', 0.0):.1f} msg/sec")
        table.add_row("Uptime", str(data.get('uptime', 'N/A')).split('.')[0])
        
        # Consumer group summary info
        consumer_groups = data.get('consumer_groups', {})
        if consumer_groups:
            main_group = consumer_groups.get(self.group_name, {})
            if main_group:
                table.add_row("", "")  # Spacer
                table.add_row("Pending Messages", str(main_group.get('pending', 0)))
                table.add_row("Active Consumers", str(main_group.get('consumers', 0)))
                table.add_row("Group Lag", str(main_group.get('lag', 0)))
        
        return Panel(table, title="PIX Processor Status", style="green")
    
    def create_stream_panel(self, data: Dict[str, Any]) -> Panel:
        """Create panel showing stream metrics"""
        if "error" in data:
            return Panel(f"Error: {data['error']}", title="Stream Info", style="red")
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Stream Length", f"{data.get('stream_length', 0):,}")
        
        last_generated_id = str(data.get('last_generated_id', 'N/A'))
        table.add_row("Last Generated ID", last_generated_id[:20] + "..." if len(last_generated_id) > 20 else last_generated_id)
        
        first_entry = data.get('first_entry')
        if first_entry and first_entry[0]:
            first_id = first_entry[0].decode() if isinstance(first_entry[0], bytes) else str(first_entry[0])
            table.add_row("First Entry ID", first_id[:20] + "..." if len(first_id) > 20 else first_id)
        
        last_entry = data.get('last_entry')
        if last_entry and last_entry[0]:
            last_id = last_entry[0].decode() if isinstance(last_entry[0], bytes) else str(last_entry[0])
            table.add_row("Last Entry ID", last_id[:20] + "..." if len(last_id) > 20 else last_id)
        
        return Panel(table, title=f"Stream: {self.stream_name}", style="yellow")
    
    def create_backend_panel(self, data: Dict[str, Any]) -> Panel:
        """Create panel showing backend response streams"""
        if "error" in data:
            return Panel(f"Error: {data['error']}", title="Backend Streams", style="red")
        
        table = Table(show_header=True, box=None)
        table.add_column("Backend ID", style="cyan")
        table.add_column("Messages", style="green")
        table.add_column("Last ID", style="dim")
        
        backend_streams = data.get('backend_streams', {})
        for backend_id, info in backend_streams.items():
            last_id = str(info['last_id'])
            if len(last_id) > 15:
                last_id = last_id[:15] + "..."
            table.add_row(
                str(backend_id),
                f"{info['length']:,}",
                last_id
            )
        
        return Panel(table, title="Backend Response Streams", style="magenta")
    
    def create_consumer_groups_panel(self, data: Dict[str, Any]) -> Panel:
        """Create panel showing detailed consumer group information"""
        if "error" in data:
            return Panel(f"Error: {data['error']}", title="Consumer Groups", style="red")
        
        consumer_groups = data.get('consumer_groups', {})
        if not consumer_groups:
            return Panel("No consumer groups found", title="Consumer Groups", style="dim")
        
        table = Table(show_header=True, box=None)
        table.add_column("Group", style="cyan")
        table.add_column("Pending", style="yellow")
        table.add_column("Consumers", style="green")
        table.add_column("Lag", style="red")
        table.add_column("Entries Read", style="blue")
        
        for group_name, group_info in consumer_groups.items():
            table.add_row(
                group_name,
                str(group_info.get('pending', 0)),
                str(group_info.get('consumers', 0)),
                str(group_info.get('lag', 0)),
                str(group_info.get('entries_read', 0))
            )
            
            # Add consumer details as sub-rows
            for consumer in group_info.get('consumer_details', []):
                idle_time = consumer.get('idle', 0) / 1000  # Convert to seconds
                table.add_row(
                    f"  └─ {consumer.get('name', 'Unknown')}",
                    str(consumer.get('pending', 0)),
                    f"{idle_time:.1f}s idle",
                    "",
                    ""
                )
        
        return Panel(table, title="Consumer Groups Detail", style="blue")
    
    def create_layout(self, data: Dict[str, Any]) -> Layout:
        """Create the main layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right"),
        )
        
        layout["left"].split_column(
            Layout(name="processor", ratio=2),
            Layout(name="stream", ratio=1),
        )
        
        layout["right"].split_column(
            Layout(name="consumer_groups", ratio=1),
            Layout(name="backend_streams", ratio=1),
        )
        
        layout["header"].update(self.create_header_panel())
        layout["processor"].update(self.create_processor_panel(data))
        layout["stream"].update(self.create_stream_panel(data))
        layout["consumer_groups"].update(self.create_consumer_groups_panel(data))
        layout["backend_streams"].update(self.create_backend_panel(data))
        
        return layout
    
    def run(self):
        """Run the monitoring interface"""
        self.console.print("[bold green]Starting PIX Monitor TUI...")
        self.console.print("[dim]Press Ctrl+C to exit[/dim]")
        
        # Test initial connection
        try:
            self.redis_client.ping()
            self.console.print("[green]✓ Connected to Redis[/green]")
        except Exception as e:
            self.console.print(f"[yellow]⚠ Redis connection warning: {e}[/yellow]")
            self.console.print("[dim]Will continue with error display...[/dim]")
        
        try:
            with Live(self.create_layout({"error": "Initializing..."}), refresh_per_second=2, screen=True) as live:
                while True:
                    data = self.get_redis_info()
                    live.update(self.create_layout(data))
                    time.sleep(0.5)
                    
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]Monitor stopped by user[/bold yellow]")
        except Exception as e:
            self.console.print(f"\n[bold red]Error: {e}[/bold red]")


if __name__ == "__main__":
    monitor = PIXMonitor()
    monitor.run()