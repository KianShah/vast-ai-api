import select
import logging
import socketserver as SocketServer

logger = logging.getLogger('vast')

"""
    Source: https://github.com/paramiko/paramiko/blob/main/demos/forward.py
"""
class Handler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.ssh_transport.open_channel(
                "direct-tcpip",
                (self.chain_host, self.chain_port),
                self.request.getpeername()
            )
        except Exception as e:
            logger.debug(f"Incoming request to {self.chain_host}:{self.chain_port} failed: {repr(e)}")
            return
        if chan is None:
            logger.debug(f"Incoming request to {self.chain_host}:{self.chain_port} was rejected by the SSH server.")
            return

        logger.debug(f"Connected!  Tunnel open {self.request.getpeername()} -> {chan.getpeername()} -> {(self.chain_host, self.chain_port)}")
        while True:
            r, w, x = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        logger.debug(f"Tunnel closed from {peername}")

class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

def forward_tunnel(local_port, remote_host, remote_port, transport):
    # this is a little convoluted, but lets me configure things for the Handler
    # object.  (SocketServer doesn't give Handlers any way to access the outer
    # server normally.)
    class SubHander(Handler):
        chain_host = remote_host
        chain_port = remote_port
        ssh_transport = transport

    ForwardServer(("", local_port), SubHander).serve_forever()
