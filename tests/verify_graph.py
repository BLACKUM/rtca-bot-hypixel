import asyncio
import os
import sys

sys.path.append(os.getcwd())

from services.visualization import generate_dungeon_graph

async def test_graph():
    print("Testing Graph Generation...")
    data = {
        "Archer": 50,
        "Berserk": 42.5,
        "Healer": 30,
        "Mage": 50,
        "Tank": 48
    }
    
    try:
        import discord
        file = await generate_dungeon_graph(data, 45.5)
        print(f"Graph generated successfully: {file.filename}")
        
    except Exception as e:
        print(f"Graph generation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_graph())
