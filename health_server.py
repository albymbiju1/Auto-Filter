"""
Simple HTTP health check server for Koyeb
Runs alongside the Telegram bot to pass health checks
"""

import asyncio
from aiohttp import web
import logging

logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="OK", status=200)

async def start_health_server(port=8000):
    """Start the health check HTTP server"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    logger.info(f"Health check server started on port {port}")

    # Keep the server running
    while True:
        await asyncio.sleep(3600)
