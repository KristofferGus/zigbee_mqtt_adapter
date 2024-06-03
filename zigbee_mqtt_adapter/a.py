import asyncio

async def my_coroutine():
    await asyncio.sleep(1)
    print("Coroutine finished")

async def main():
    asyncio.create_task(my_coroutine())  # Task created but not stored
    print("Task created")
    # Do other work here without awaiting the task

# Run the event loop
asyncio.run(main())
