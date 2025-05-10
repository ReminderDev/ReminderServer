from task import Task, TaskDate, TaskManager
import asyncio

async def main():
    taskManager = TaskManager()
    taskManager.add_task(Task("Test Task", "This is a test task", TaskDate(2025, 5, 10, 21, 31)))
    await asyncio.sleep(10)
    taskManager.close()
    await asyncio.sleep(1000)

if __name__ == "__main__":
    asyncio.run(main())