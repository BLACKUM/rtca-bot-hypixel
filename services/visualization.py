import matplotlib.pyplot as plt
import io
import discord
from concurrent.futures import ThreadPoolExecutor
import asyncio

plt.switch_backend('Agg')

def _create_combined_graph(class_data: dict, floors_data: dict, cata_level: float):
    classes = list(class_data.keys())
    levels = list(class_data.values())
    sorted_pairs = sorted(zip(classes, levels), key=lambda x: x[1])
    classes = [p[0] for p in sorted_pairs]
    levels = [p[1] for p in sorted_pairs]
    
    floor_order = ["M7", "M6", "M5", "M4", "M3", "M2", "M1", "F7", "F6", "F5", "F4", "F3", "F2", "F1", "Entrance"]
    floor_names = []
    run_counts = []
    
    for f in floor_order:
        if f in floors_data:
            count = floors_data[f]["runs"]
            if count > 0:
                floor_names.append(f)
                run_counts.append(count)
    
    floor_names.reverse()
    run_counts.reverse()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor('#2b2d31')
    CLASS_COLORS = {
        'Archer': '#2ecc71', 
        'Berserk': '#e74c3c',
        'Healer': '#f1c40f', 
        'Mage': '#3498db',   
        'Tank': '#95a5a6'    
    }
    
    bar_colors = [CLASS_COLORS.get(c, '#ffffff') for c in classes]
    
    ax1.set_facecolor('#2b2d31')
    bars1 = ax1.barh(classes, levels, color=bar_colors, height=0.6)
    
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_color('#ffffff')
    ax1.spines['left'].set_color('#ffffff')
    ax1.tick_params(axis='x', colors='white')
    ax1.tick_params(axis='y', colors='white')
    
    ax1.grid(axis='x', color='white', alpha=0.1)
    
    ax1.set_xlabel('Level', color='white', fontweight='bold')
    ax1.set_title(f'Class Levels (Cata {cata_level:.2f})', color='white', pad=20, fontsize=12, fontweight='bold', y=1.02)

    for bar in bars1:
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:.1f}', ha='left', va='center', color='white', fontsize=9)

    ax2.set_facecolor('#2b2d31')
    if floor_names:
        colors_runs = ['#d35400' if f.startswith('M') else '#9b59b6' for f in floor_names]
        bars2 = ax2.barh(floor_names, run_counts, color=colors_runs, height=0.6)
        
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['bottom'].set_color('#ffffff')
        ax2.spines['left'].set_color('#ffffff')
        ax2.tick_params(axis='x', colors='white')
        ax2.tick_params(axis='y', colors='white')
        
        ax2.grid(axis='x', color='white', alpha=0.1)
        
        ax2.set_xlabel('Runs', color='white', fontweight='bold')
        ax2.set_title('Floor Completions', color='white', pad=20, fontsize=12, fontweight='bold', y=1.02)
        
        for bar in bars2:
            width = bar.get_width()
            if width > 0:
                ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:.0f}', ha='left', va='center', color='white', fontsize=9)
    else:
        ax2.text(0.5, 0.5, "No Runs Data", color='white', ha='center', va='center')
        ax2.axis('off')

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

async def generate_dungeon_graph(class_data: dict, floors_data: dict, cata_level: float):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        buf = await loop.run_in_executor(pool, _create_combined_graph, class_data, floors_data, cata_level)
    
    return discord.File(buf, filename="dungeon_stats.png")
