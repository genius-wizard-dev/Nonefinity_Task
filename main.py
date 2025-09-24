#!/usr/bin/env python3
"""
Main entry point for vector tasks system.
Usage:
  python main.py worker    # Start worker (default)
  python main.py flower    # Start monitoring
  python main.py --help    # Show help
"""

import os
import sys
import argparse
import subprocess
import threading
import time

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def start_worker():
    """Start Celery worker with AI tasks."""
    print("🚀 Starting AI Tasks Worker...")
    print("📋 Queues: embeddings, workflows, system")
    print("🔧 Concurrency: 2")
    print("📊 Monitor: http://localhost:5555 (flower)")
    print()

    # Import celery and tasks
    from src.infrastructure.celery import celery_app as celery

    # Import embedding tasks to ensure registration
    from src.tasks.ai import embedding

    # Print registered AI tasks
    print("📋 Registered AI tasks:")
    for task_name in sorted(celery.tasks.keys()):
        if not task_name.startswith('celery.'):
            queue = "embeddings" if "embeddings" in task_name else "ai_tasks"
            print(f"  ✅ {task_name} → {queue} queue")
    print()

    # Start worker with sensible defaults for all AI queues
    celery.worker_main([
        'worker',
        '--loglevel=info',
        '--queues=embeddings,workflows,system,ai_tasks',
        '--concurrency=2',
        '--events',  # Enable task events for monitoring
    ])


def start_flower():
    """Start Flower monitoring."""
    print("🌸 Starting Flower monitoring...")
    print("📊 Monitor: http://localhost:5555")
    try:
        subprocess.run([
            'uv', 'run', 'celery',
            '--app=src.infrastructure.celery:celery_app',
            'flower',
            '--port=5555'
        ])
    except KeyboardInterrupt:
        print("\n🛑 Flower monitoring stopped")
    except FileNotFoundError:
        print("❌ Error: 'uv' command not found. Please install uv or use 'celery flower' directly.")


def start_flower_background():
    """Start Flower monitoring in background thread."""
    def flower_runner():
        time.sleep(2)  # Give worker time to start
        print("🌸 Starting Flower monitoring in background...")
        print("📊 Monitor: http://localhost:5555")
        try:
            subprocess.run([
                'uv', 'run', 'celery',
                '--app=src.infrastructure.celery:celery_app',
                'flower',
                '--port=5555'
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            print("❌ Error: 'uv' command not found. Please install uv or use 'celery flower' directly.")

    flower_thread = threading.Thread(target=flower_runner, daemon=True)
    flower_thread.start()
    return flower_thread


def start_all():
    """Start both worker and flower monitoring."""
    print("🚀 Starting AI Tasks System (Worker + Flower)...")
    print("📋 Worker: embeddings, workflows, system queues")
    print("📊 Monitor: http://localhost:5555 (starting in 2 seconds)")
    print("💡 Use Ctrl+C to stop both services")
    print()



    # Import celery and tasks
    from src.infrastructure.celery import celery_app as celery

    # Import embedding tasks to ensure registration
    from src.tasks.ai import embedding

    # Print registered AI tasks
    print("📋 Registered AI tasks:")
    for task_name in sorted(celery.tasks.keys()):
        if not task_name.startswith('celery.'):
            queue = "embeddings" if "embeddings" in task_name else "ai_tasks"
            print(f"  ✅ {task_name} → {queue} queue")
    print()

    try:
        # Start worker (this will block)
        celery.worker_main([
            'worker',
            '--loglevel=info',
            '--queues=embeddings,workflows,system,ai_tasks',
            '--concurrency=2',
            '--events',  # Enable task events for monitoring
        ])
    except KeyboardInterrupt:
        print("\n🛑 Stopping AI Tasks System...")
        print("✅ Worker stopped")
        print("✅ Flower stopped")


def start_health_check():
    """Run system health check."""
    print("🏥 Running system health check...")
    try:
        from src.health import print_health_status
        print_health_status()
    except ImportError as e:
        print(f"❌ Error importing health check: {e}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")


def show_help():
    """Show help information."""
    print("🎯 AI Tasks System")
    print()
    print("Commands:")
    print("  worker    Start Celery worker for AI tasks (default)")
    print("  flower    Start Flower monitoring interface")
    print("  all       Start both worker and flower monitoring")
    print("  health    Run system health check")
    print("  --help    Show this help message")
    print()
    print("Examples:")
    print("  python main.py           # Start worker (default)")
    print("  python main.py worker    # Start worker explicitly")
    print("  python main.py flower    # Start monitoring")
    print("  python main.py all       # Start both worker and monitoring")
    print("  python main.py health    # Check system health")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="AI Tasks System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py           # Start worker (default)
  python main.py worker    # Start worker explicitly
  python main.py flower    # Start monitoring
  python main.py all       # Start both worker and monitoring
  python main.py health    # Check system health
        """
    )

    parser.add_argument(
        'command',
        nargs='?',
        default='worker',
        choices=['worker', 'flower', 'all', 'health'],
        help='Command to run (default: worker)'
    )

    # Handle --help manually for better formatting
    if '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return

    # If no arguments provided, default to worker
    if len(sys.argv) == 1:
        start_worker()
        return

    try:
        args = parser.parse_args()
    except SystemExit:
        # If argument parsing fails, show our custom help
        show_help()
        return

    command = args.command.lower()

    if command == "worker":
        start_worker()
    elif command == "flower":
        start_flower()
    elif command == "all":
        start_all()
    elif command == "health":
        start_health_check()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
