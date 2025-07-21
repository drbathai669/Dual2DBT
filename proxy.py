"""
High Performance Proxy Server (Windows Compatible)
Hỗ trợ HTTP/HTTPS proxy cho các máy trong LAN
Tối ưu cho khả năng chịu tải cao với nhiều luồng truy cập
"""

import socket
import threading
import select
import time
import logging
from urllib.parse import urlparse
import sys
from concurrent.futures import ThreadPoolExecutor
import queue

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('proxy.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class HighPerformanceProxy:
    def __init__(self, host='0.0.0.0', port=8888, max_workers=100, buffer_size=8192):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.buffer_size = buffer_size
        self.running = False
        
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_connections = queue.Queue()
        
        self.stats = {
            'total_requests': 0,
            'active_connections': 0,
            'errors': 0
        }

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1000)
            
            self.running = True
            logging.info(f"Proxy server đang chạy tại {self.host}:{self.port}")
            logging.info(f"Số workers tối đa: {self.max_workers}")
            
            stats_thread = threading.Thread(target=self.print_stats, daemon=True)
            stats_thread.start()
            
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    logging.debug(f"Kết nối mới từ {addr}")
                    self.executor.submit(self.handle_client, client_socket, addr)
                except Exception as e:
                    if self.running:
                        logging.error(f"Lỗi accept connection: {e}")
                        
        except KeyboardInterrupt:
            logging.info("Đang dừng server...")
            self.stop()
        except Exception as e:
            logging.error(f"Lỗi khởi động server: {e}")
            self.stop()

    def handle_client(self, client_socket, addr):
        try:
            self.stats['active_connections'] += 1
            client_socket.settimeout(30)
            
            request = client_socket.recv(self.buffer_size).decode('utf-8', errors='ignore')
            if not request:
                return
                
            self.stats['total_requests'] += 1
            
            first_line = request.split('\r\n')[0]
            url = first_line.split(' ')[1]
            
            if first_line.startswith('CONNECT'):
                self.handle_https(client_socket, url)
            else:
                self.handle_http(client_socket, request, url)
                
        except Exception as e:
            logging.error(f"Lỗi xử lý client {addr}: {e}")
            self.stats['errors'] += 1
        finally:
            try:
                client_socket.close()
            except:
                pass
            self.stats['active_connections'] -= 1

    def handle_http(self, client_socket, request, url):
        try:
            if url.startswith('http://'):
                parsed_url = urlparse(url)
                host = parsed_url.hostname
                port = parsed_url.port or 80
            else:
                lines = request.split('\r\n')
                host_line = [line for line in lines if line.lower().startswith('host:')]
                if host_line:
                    host = host_line[0].split(':', 1)[1].strip()
                    port = 80
                else:
                    raise Exception("Không tìm thấy host")
            
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(10)
            server_socket.connect((host, port))
            server_socket.send(request.encode('utf-8'))
            
            self.relay_data(client_socket, server_socket)
            
        except Exception as e:
            logging.error(f"Lỗi xử lý HTTP: {e}")
            error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\n"
            client_socket.send(error_response.encode('utf-8'))

    def handle_https(self, client_socket, url):
        try:
            host, port = url.split(':')
            port = int(port)
            
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(10)
            server_socket.connect((host, port))
            
            response = "HTTP/1.1 200 Connection Established\r\n\r\n"
            client_socket.send(response.encode('utf-8'))
            
            self.relay_data(client_socket, server_socket)
            
        except Exception as e:
            logging.error(f"Lỗi xử lý HTTPS: {e}")
            error_response = "HTTP/1.1 500 Internal Server Error\r\n\r\n"
            client_socket.send(error_response.encode('utf-8'))

    def relay_data(self, client_socket, server_socket):
        try:
            sockets = [client_socket, server_socket]
            while True:
                ready_sockets, _, error_sockets = select.select(sockets, [], sockets, 1)
                if error_sockets:
                    break
                for sock in ready_sockets:
                    try:
                        data = sock.recv(self.buffer_size)
                        if not data:
                            return
                        if sock is client_socket:
                            server_socket.send(data)
                        else:
                            client_socket.send(data)
                    except Exception:
                        return
        except Exception as e:
            logging.debug(f"Relay data ended: {e}")
        finally:
            try:
                server_socket.close()
            except:
                pass

    def print_stats(self):
        while self.running:
            time.sleep(10)
            logging.info(f"Stats - Total requests: {self.stats['total_requests']}, "
                         f"Active connections: {self.stats['active_connections']}, "
                         f"Errors: {self.stats['errors']}")

    def stop(self):
        self.running = False
        try:
            self.server_socket.close()
        except:
            pass
        self.executor.shutdown(wait=True)
        logging.info("Proxy server đã dừng")

if __name__ == "__main__":
    PROXY_HOST = '0.0.0.0'
    PROXY_PORT = 8888
    MAX_WORKERS = 200
    BUFFER_SIZE = 16384

    proxy = HighPerformanceProxy(
        host=PROXY_HOST,
        port=PROXY_PORT,
        max_workers=MAX_WORKERS,
        buffer_size=BUFFER_SIZE
    )

    try:
        proxy.start()
    except KeyboardInterrupt:
        print("\nĐang tắt proxy server...")
        proxy.stop()
        sys.exit(0)
