import asyncio
import json
from typing import Set, Dict, Any, List
from aiohttp import web
import aiohttp
from collections import deque


class WebSocketServer:
    """WebSocket server for real-time communication with frontend"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Set[web.WebSocketResponse] = set()
        self.app = web.Application()
        self.task_handler_func = None
        # Message buffer for polling (stores last 1000 messages)
        self.message_buffer: deque = deque(maxlen=1000)
        self.message_id_counter = 0
        # Event listeners for local terminal UI
        self.event_listeners: List = []
        self.setup_routes()

    def setup_routes(self):
        """Setup HTTP and WebSocket routes"""
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_post('/api/task', self.task_handler)
        self.app.router.add_get('/api/updates', self.polling_handler)
        # Enable CORS
        self.app.middlewares.append(self.cors_middleware)

    def set_task_handler(self, handler):
        """Set custom task handler function"""
        self.task_handler_func = handler

    def add_event_listener(self, listener_func):
        """Add an event listener that will be called for each broadcast"""
        self.event_listeners.append(listener_func)

    @web.middleware
    async def cors_middleware(self, request, handler):
        """CORS middleware to allow cross-origin requests"""
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            try:
                response = await handler(request)
            except web.HTTPException as ex:
                response = ex

        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    async def websocket_handler(self, request):
        """Handle WebSocket connections"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.clients.add(ws)
        # print(f"Client connected. Total clients: {len(self.clients)}")

        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        # Handle incoming messages if needed
                        data = json.loads(msg.data)
                        print(f"Received: {data}")
                    except Exception as e:
                        print(f"ERROR: Failed to process WebSocket message: {e}")
                        import traceback
                        traceback.print_exc()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    print(f"ERROR: WebSocket error: {ws.exception()}")
        except Exception as e:
            print(f"ERROR: WebSocket handler failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.clients.remove(ws)
            # print(f"Client disconnected. Total clients: {len(self.clients)}")

        return ws

    async def task_handler(self, request):
        """Handle task submission from frontend"""
        try:
            # If a custom task handler is set, use it
            if self.task_handler_func:
                return await self.task_handler_func(request)

            # Default handler
            data = await request.json()
            task = data.get('task')

            if not task:
                return web.json_response({'error': 'No task provided'}, status=400)

            # Broadcast task to all connected clients
            await self.broadcast({
                'type': 'task_submitted',
                'data': {'task': task}
            })

            # Here we would trigger the BossAgent to process the task
            # For now, just acknowledge receipt
            return web.json_response({
                'success': True,
                'message': 'Task received'
            })

        except Exception as e:
            print(f"ERROR: Task handler failed: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({'error': str(e)}, status=500)

    async def polling_handler(self, request):
        """Handle polling requests for updates"""
        try:
            # Get the last message ID the client has seen
            last_id = int(request.query.get('since', 0))

            # Get all messages after that ID
            new_messages = []
            for msg_data in self.message_buffer:
                if msg_data['id'] > last_id:
                    new_messages.append(msg_data)

            return web.json_response({
                'success': True,
                'messages': new_messages,
                'latest_id': self.message_id_counter
            })
        except Exception as e:
            print(f"ERROR: Polling handler failed: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({'error': str(e)}, status=500)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        # Assign message ID and add to buffer for polling
        self.message_id_counter += 1
        message_with_id = {
            'id': self.message_id_counter,
            'message': message
        }
        self.message_buffer.append(message_with_id)

        # Call event listeners (for terminal UI)
        for listener in self.event_listeners:
            try:
                listener(message)
            except Exception as e:
                print(f"ERROR: Event listener failed: {e}")
                import traceback
                traceback.print_exc()

        if not self.clients:
            return

        # Convert message to JSON
        json_message = json.dumps(message)

        # Send to all clients
        disconnected_clients = set()
        for ws in self.clients:
            try:
                await ws.send_str(json_message)
            except Exception as e:
                print(f"ERROR: Failed to send message to client: {e}")
                import traceback
                traceback.print_exc()
                disconnected_clients.add(ws)

        # Remove disconnected clients
        self.clients -= disconnected_clients

    def create_websocket_callback(self):
        """Create a callback function for agents to send updates"""
        def callback(message: Dict[str, Any]):
            """Synchronous callback that schedules async broadcast"""
            try:
                # Get the running event loop
                loop = asyncio.get_event_loop()
                # Create task to broadcast in the event loop
                asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
            except Exception as e:
                print(f"ERROR: Failed to schedule broadcast: {e}")
                import traceback
                traceback.print_exc()

        return callback

    async def start(self):
        """Start the WebSocket server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        print(f"WebSocket server started on ws://{self.host}:{self.port}")

    def run(self):
        """Run the server (blocking)"""
        web.run_app(self.app, host=self.host, port=self.port)


async def main():
    """Main function for testing"""
    server = WebSocketServer()
    await server.start()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
