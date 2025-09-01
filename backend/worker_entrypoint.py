#!/usr/bin/env python3
"""
Celery Worker entrypoint для Cloud Run Service.

Запускает HTTP сервер на $PORT для health checks и Celery worker в фоне.
"""

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional
from urllib.parse import urlparse

# Настройка логирования  
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Глобальная переменная для процесса Celery
celery_process: Optional[subprocess.Popen] = None
start_time = time.time()


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler для health checks."""
    
    def do_GET(self):
        """Handle GET requests."""
        global celery_process, start_time
        
        path = urlparse(self.path).path
        
        if path == "/health":
            uptime = int(time.time() - start_time)
            
            # Проверяем что Celery процесс жив
            celery_alive = celery_process is not None and celery_process.poll() is None
            
            status = {
                "status": "healthy" if celery_alive else "unhealthy",
                "celery_worker": {
                    "alive": celery_alive,
                    "pid": celery_process.pid if celery_process else None,
                },
                "uptime_seconds": uptime,
                "timestamp": int(time.time())
            }
            
            status_code = 200 if celery_alive else 503
            response = json.dumps(status, indent=2)
            
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())
            
        elif path == "/":
            response_data = {
                "service": "BotBalance Celery Worker",
                "status": "running",
                "health": "/health"
            }
            response = json.dumps(response_data, indent=2)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(f"HTTP: {format % args}")


def start_celery_worker():
    """Запускает Celery worker как subprocess."""
    global celery_process
    
    logger.info("Starting Celery worker...")
    
    cmd = [
        "celery", "-A", "botbalance", "worker",
        "-l", "info",
        "--concurrency", "2",
        "--max-tasks-per-child", "1000"
    ]
    
    try:
        celery_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        logger.info(f"Celery worker started with PID: {celery_process.pid}")
        
        # Читаем вывод Celery в отдельном потоке  
        def log_celery_output():
            while celery_process and celery_process.poll() is None:
                try:
                    line = celery_process.stdout.readline()
                    if line:
                        logger.info(f"[CELERY] {line.strip()}")
                except Exception as e:
                    logger.error(f"Error reading Celery output: {e}")
                    break
        
        threading.Thread(target=log_celery_output, daemon=True).start()
        
    except Exception as e:
        logger.error(f"Failed to start Celery worker: {e}")
        sys.exit(1)


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown."""
    global celery_process
    
    logger.info(f"Received signal {signum}, shutting down...")
    
    if celery_process:
        logger.info("Terminating Celery worker...")
        celery_process.terminate()
        
        # Ждем 10 секунд для graceful shutdown
        try:
            celery_process.wait(timeout=10)
            logger.info("Celery worker terminated gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Celery worker didn't terminate, killing...")
            celery_process.kill()
            celery_process.wait()
    
    sys.exit(0)


def main():
    """Главная функция."""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Получаем порт из переменной окружения
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"Starting worker entrypoint on port {port}")
    
    # Запускаем Celery worker
    start_celery_worker()
    
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
