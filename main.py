from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, HTTPException, Depends
from pydantic import BaseModel

from task import ConnectionManager, Task, TaskDate, TaskManager
from user import get_id_by_username, verify_user

# 数据模型
class TaskCreate(BaseModel):
    """创建任务的请求模型"""
    name: str
    description: str
    year: int
    month: int
    day: int
    hour: int
    minute: int
    repeat_days: Optional[int] = None
    repeat_count: Optional[int] = None

class TaskResponse(BaseModel):
    """任务响应模型"""
    id: int
    user_id: int
    name: str
    description: str
    date: Dict
    repeat_days: Optional[int]
    repeat_count: Optional[int]

# 应用初始化
app = FastAPI(title="提醒服务器", description="一个简单的任务提醒服务器")
connection_manager = ConnectionManager()
task_manager = TaskManager(connection_manager)

# 依赖项
async def get_current_user_id(username: str, password: str) -> int:
    """验证用户并返回用户ID"""
    if not verify_user(username, password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user_id = get_id_by_username(username)
    if user_id is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user_id

# API路由
@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    user_id: int = Depends(get_current_user_id)
) -> Dict:
    """创建新任务"""
    task_date = TaskDate(
        task_data.year,
        task_data.month,
        task_data.day,
        task_data.hour,
        task_data.minute
    )
    
    # 生成新的任务ID
    existing_ids = {task.id for task in task_manager.get_tasks()}
    new_id = max(existing_ids, default=-1) + 1
    
    task = Task(
        id=new_id,
        user_id=user_id,
        name=task_data.name,
        description=task_data.description,
        date=task_date,
        repeat_days=task_data.repeat_days,
        repeat_count=task_data.repeat_count
    )
    
    task_manager.add_task(task)
    return task.to_dict()

@app.get("/api/tasks", response_model=List[TaskResponse])
async def get_tasks(user_id: int = Depends(get_current_user_id)) -> List[Dict]:
    """获取用户的所有任务"""
    return [task.to_dict() for task in task_manager.get_tasks_by_user_id(user_id)]

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id)
) -> Dict:
    """获取特定任务详情"""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="没有权限访问此任务")
    return task.to_dict()

@app.delete("/api/tasks/{task_id}")
async def delete_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id)
) -> Dict:
    """删除特定任务"""
    task = task_manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.user_id != user_id:
        raise HTTPException(status_code=403, detail="没有权限删除此任务")
    
    task_manager.remove_task(task_id)
    return {"message": "任务已删除"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket连接处理"""
    try:
        if not verify_user(
            websocket.query_params["username"],
            websocket.query_params["password"]
        ):
            await websocket.close(code=4001, reason="认证失败")
            return
        
        await task_manager.connect(websocket)
        while True:
            data = await websocket.receive_text()
            print(f"收到数据: {data}")
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        task_manager.disconnect(websocket)
