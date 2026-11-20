"""Application entry point for AegisOPS Secure IT Monitoring Platform - Local Collector."""

import argparse
import sys
import threading
import time

from config.settings import get_settings
from collector.collector_service import CollectorService
from utils.logger import get_logger

logger = get_logger("Main")


def run_headless_daemon(service: CollectorService) -> None:
    """Run collector in headless CLI/daemon mode without desktop GUI."""
    logger.info("Running AegisOPS Collector in headless daemon mode. Press Ctrl+C to stop.")
    service.start()
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        logger.info("Stopping collector service...")
        service.stop()
        logger.info("Collector daemon stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisOPS Secure IT Monitoring Platform - Local Collector")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run collector in headless background mode without desktop GUI",
    )
    parser.add_argument(
        "--test-run",
        action="store_true",
        help="Run a single collection and sanitization cycle and exit (for CI/automated test)",
    )
    parser.add_argument(
        "--replay-file",
        type=str,
        default=None,
        help="Replay an external JSON/NDJSON telemetry stream file through sanitizer and queue into Tier 2",
    )
    args = parser.parse_args()

    settings = get_settings()
    service = CollectorService(settings)

    if args.replay_file:
        logger.info(f"Replaying external telemetry file: {args.replay_file}")
        count = service.replay_stream_file(args.replay_file)
        logger.info(f"Replay complete: {count} events processed through sanitizer and queued.")
        if args.headless or args.test_run:
            service.stop()
            sys.exit(0)

    if args.test_run:
        logger.info("Executing automated test verification cycle...")
        service.run_single_collection_cycle()
        logger.info(f"Test cycle complete. Status: {service.latest_transmission_status}")
        service.stop()
        sys.exit(0)

    if args.headless:
        run_headless_daemon(service)
        return

    # Start collector service in background
    service.start()

    # Launch CustomTkinter GUI
    try:
        from interface.app import AegisApp
        app = AegisApp(service=service)
        app.mainloop()
    except Exception as e:
        logger.error(f"Error launching desktop GUI: {e}")
        service.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
