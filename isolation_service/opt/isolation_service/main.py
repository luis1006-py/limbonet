#!/usr/bin/env python3
from fastapi import FastAPI
from routers import commands, status
import json, asyncio
from monitor import monitor_dhcp, monitor_subnets
from contextlib import asynccontextmanager

with open("data/config.json", "r") as f:
	data = json.load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
	monitor_task = asyncio.create_task(monitor_dhcp())
	subnet_task = asyncio.create_task(monitor_subnets())
	try:
		yield
	finally:
		monitor_task.cancel()
		subnet_task.cancel()
		try:
			await monitor_task
		except asyncio.CancelledError:
			pass
		try:
			await subnet_task
		except asyncio.CancelledError:
			pass
if data["dhcp_monitor"] == "yes":
	app = FastAPI(title="ISOLATION Daemon", lifespan=lifespan)
else:
	app = FastAPI(title="ISOLATION Daemon")

app.include_router(commands.router)
app.include_router(status.router)

if __name__ == '__main__':
	import uvicorn
	uvicorn.run(app, host="127.0.0.1", port=1234)