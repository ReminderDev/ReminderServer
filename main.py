import asyncio
from task import ConnectionManager, Task, TaskDate, TaskManager
from fastapi import FastAPI, WebSocket
from user import get_id_by_username, verify_user


taskManager = TaskManager(ConnectionManager())
taskManager.add_task(
    Task(0, 1, "Test Task", "This is a test task", TaskDate(2025, 5, 11, 16, 5)))

app = FastAPI()

def verify(websocket: WebSocket):
    return verify_user(websocket.query_params["username"], websocket.query_params["password"])

@app.get("/api/tasks")
async def get_tasks(username: str, password: str):
    if not verify_user(username, password):
        return {"error": "Invalid username or password"}
    return {"tasks": taskManager.get_tasks_by_user_id(get_id_by_username(username))}

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: int, username: str, password: str):
    if not verify_user(username, password):
        return {"error": "Invalid username or password"}
    
    task = taskManager.get_task(task_id)
    if task.user_id != get_id_by_username(username):
        return {"error": "You do not have permission to access this task"}
    
    return {"task": task}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not verify(websocket):
        await websocket.close()
        return
    await taskManager.connect(websocket)
