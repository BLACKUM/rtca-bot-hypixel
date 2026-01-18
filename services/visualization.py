import matplotlib.pyplot as plt
import io
import discord
from concurrent.futures import ThreadPoolExecutor
import asyncio

plt.switch_backend('Agg')

def _create_class_graph(class_data: dict, cata_level: float):
    classes = list(class_data.keys())
    levels = list(class_data.values())
    
    sorted_pairs = sorted(zip(classes, levels), key=lambda x: x[1])
    classes = [p[0] for p in sorted_pairs]
    levels = [p[1] for p in sorted_pairs]

    colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#3498db']
    colors = colors[:len(classes)]

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor('#2b2d31')
    ax.set_facecolor('#2b2d31')

    bars = ax.barh(classes, levels, color=colors, height=0.6)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#ffffff')
    ax.spines['left'].set_color('#ffffff')
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    
    ax.set_xlabel('Level', color='white', fontweight='bold')
    ax.set_title(f'Catacombs Level: {cata_level:.2f}', color='white', pad=20, fontsize=14, fontweight='bold')

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height()/2, 
                f'{width:.1f}', 
                ha='left', va='center', color='white', fontsize=10)

    ax.axvline(x=50, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    
    return buf

async def generate_dungeon_graph(class_data: dict, cata_level: float):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        buf = await loop.run_in_executor(pool, _create_class_graph, class_data, cata_level)
    
    return discord.File(buf, filename="dungeon_stats.png")
