#!/usr/bin/env python3
"""
Celery Beat entrypoint для Cloud Run Service.

Запускает HTTP сервер на $PORT для health checks и Celery beat в фоне.
ВАЖНО: Beat должен быть в единственном экземпляре для избежания дублирования задач.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Глобальная переменная для процесса Celery Beat
celery_beat_process: subprocess.Popen | None = None
start_time = time.time()


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler для health checks beat сервиса."""

    def do_GET(self):
        """Handle GET requests."""
        global celery_beat_process, start_time

        path = urlparse(self.path).path

        if path == "/health":
            uptime = int(time.time() - start_time)

            # Проверяем что Celery Beat процесс жив
            beat_alive = (
                celery_beat_process is not None and celery_beat_process.poll() is None
            )

            status = {
                "status": "healthy" if beat_alive else "unhealthy",
                "celery_beat": {
                    "alive": beat_alive,
                    "pid": celery_beat_process.pid if celery_beat_process else None,
                },
                "uptime_seconds": uptime,
                "timestamp": int(time.time()),
            }

            status_code = 200 if beat_alive else 503
            response = json.dumps(status, indent=2)

            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())

        elif path == "/":
            response_data = {
                "service": "BotBalance Celery Beat",
                "status": "running",
                "health": "/health",
                "warning": "This service should run in SINGLE instance only",
            }
            response = json.dumps(response_data, indent=2)

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"HTTP: {format % args}")


def start_celery_beat():
    """Запускает Celery beat как subprocess."""
    global celery_beat_process

    logger.info("Starting Celery beat scheduler...")

    cmd = [
        "celery",
        "-A",
        "botbalance",
        "beat",
        "-l",
        "info",
        "--pidfile=/tmp/celerybeat.pid",
        "--schedule=/tmp/celerybeat-schedule",
    ]

    try:
        celery_beat_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        logger.info(f"Celery beat started with PID: {celery_beat_process.pid}")

        # Читаем вывод Celery Beat в отдельном потоке
        def log_celery_output():
            while celery_beat_process and celery_beat_process.poll() is None:
                try:
                    if celery_beat_process.stdout:
                        line = celery_beat_process.stdout.readline()
                        if line:
                            logger.info(f"[CELERY-BEAT] {line.strip()}")
                except Exception as e:
                    logger.error(f"Error reading Celery beat output: {e}")
                    break

        threading.Thread(target=log_celery_output, daemon=True).start()

    except Exception as e:
        logger.error(f"Failed to start Celery beat: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown."""
    global celery_beat_process

    logger.info(f"Received signal {signum}, shutting down...")

    if celery_beat_process:
        logger.info("Terminating Celery beat...")
        celery_beat_process.terminate()

        # Ждем 15 секунд для graceful shutdown (больше чем для worker)
        try:
            celery_beat_process.wait(timeout=15)
            logger.info("Celery beat terminated gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Celery beat didn't terminate, killing...")
            celery_beat_process.kill()
            celery_beat_process.wait()

    # Cleanup temp files
    try:
        for file in ["/tmp/celerybeat.pid", "/tmp/celerybeat-schedule"]:
            if os.path.exists(file):
                os.unlink(file)
                logger.info(f"Cleaned up {file}")
    except Exception as e:
        logger.warning(f"Cleanup failed: {e}")

    sys.exit(0)


def main():
    """Главная функция."""
    # Проверяем что это единственный экземпляр
    if os.path.exists("/tmp/celerybeat.pid"):
        logger.warning("Found existing beat pid file, removing...")
        try:
            os.unlink("/tmp/celerybeat.pid")
        except Exception as e:
            logger.error(f"Cannot remove beat pid file: {e}")
            sys.exit(1)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Получаем порт из переменной окружения
    port = int(os.getenv("PORT", 8080))

    logger.info(f"Starting beat entrypoint on port {port}")
    logger.info("WARNING: This service must run in SINGLE instance only!")

    # Запускаем Celery beat
    start_celery_beat()

    # Запускаем HTTP сервер
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        logger.info(f"HTTP server listening on 0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"HTTP server failed: {e}")
        signal_handler(signal.SIGTERM, None)


if __name__ == "__main__":
    main()
