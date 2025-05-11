from task import ConnectionManager, Task, TaskDate, TaskManager
from fastapi import FastAPI, WebSocket
from user import get_id_by_username, verify_user


connection_manager = ConnectionManager()
task_manager = TaskManager(connection_manager)
task_manager.add_task(
    Task(0, 1, "Test Task", "This is a test task", TaskDate(2025, 5, 11, 18, 36)))

app = FastAPI()

def verify(websocket: WebSocket):
    return verify_user(websocket.query_params["username"], websocket.query_params["password"])

@app.get("/api/tasks")
async def get_tasks(username: str, password: str):
    if not verify_user(username, password):
        return {"error": "Invalid username or password"}
    return {"tasks": task_manager.get_tasks_by_user_id(get_id_by_username(username))}

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: int, username: str, password: str):
    if not verify_user(username, password):
        return {"error": "Invalid username or password"}
    
    task = task_manager.get_task(task_id)
    if task.user_id != get_id_by_username(username):
        return {"error": "You do not have permission to access this task"}
    
    return {"task": task}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if not verify(websocket):
        await websocket.close()
        return
    await task_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received data: {data}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        task_manager.disconnect(websocket)
