import matplotlib.pyplot as plt
import io
import discord
from concurrent.futures import ThreadPoolExecutor
import asyncio
from services.xp_calculations import get_dungeon_level
from core.config import config

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

def _create_rtca_graph(current_xp_data: dict, simulation_results: dict, ign: str):
    classes = ["healer", "mage", "berserk", "archer", "tank"]
    
    labels = [c.capitalize() for c in classes]
    
    current_levels = []
    for c in classes:
        xp = current_xp_data.get(c, 0)
        current_levels.append(get_dungeon_level(xp))
        
    runs_needed = []
    for c in classes:
        res = simulation_results.get(c, {})
        runs = res.get("runs_done", 0)
        runs_needed.append(runs)
        
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor('#2b2d31')
    
    CLASS_COLORS = {
        'Archer': '#2ecc71', 
        'Berserk': '#e74c3c',
        'Healer': '#f1c40f', 
        'Mage': '#3498db',   
        'Tank': '#95a5a6'    
    }
    
    bar_colors = [CLASS_COLORS.get(l, '#ffffff') for l in labels]
    
    ax1.set_facecolor('#2b2d31')
    
    target = config.target_level
    ax1.barh(labels, [target]*5, color='#40444b', height=0.6, label='Target')
    
    bars1 = ax1.barh(labels, current_levels, color=bar_colors, height=0.6, label='Current')
    
    ax1.set_xlim(0, target * 1.05)
    
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['bottom'].set_color('#ffffff')
    ax1.spines['left'].set_color('#ffffff')
    ax1.tick_params(axis='x', colors='white')
    ax1.tick_params(axis='y', colors='white')
    ax1.grid(axis='x', color='white', alpha=0.1)
    
    ax1.set_title(f'Class Levels (Cata {get_dungeon_level(sum(current_xp_data.values())/len(classes) if current_xp_data else 0):.2f})', color='white', pad=15, fontsize=14, fontweight='bold')
    ax1.set_title(f"Class Levels ({ign})", color='white', pad=15, fontsize=14, fontweight='bold')
    
    for i, bar in enumerate(bars1):
        lvl = current_levels[i]
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{lvl:.2f}', 
                 ha='left', va='center', color='white', fontsize=10, fontweight='bold')

    ax2.set_facecolor('#2b2d31')
    
    bars2 = ax2.barh(labels, runs_needed, color=bar_colors, height=0.6)
    
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['bottom'].set_color('#ffffff')
    ax2.spines['left'].set_color('#ffffff')
    ax2.tick_params(axis='x', colors='white')
    ax2.tick_params(axis='y', colors='white')
    ax2.grid(axis='x', color='white', alpha=0.1)
    
    ax2.set_title('Runs Needed to Max', color='white', pad=15, fontsize=14, fontweight='bold')
    
    for bar in bars2:
        width = bar.get_width()
        val = int(width)
        if val > 0:
            ax2.text(width + (max(runs_needed)*0.01 if max(runs_needed) > 0 else 1), bar.get_y() + bar.get_height()/2, f'{val:,}', 
                     ha='left', va='center', color='white', fontsize=10, fontweight='bold')
        else:
             ax2.text(0.5, bar.get_y() + bar.get_height()/2, "DONE", 
                     ha='left', va='center', color='#2ecc71', fontsize=10, fontweight='bold')

    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

async def generate_rtca_graph(current_xp_data: dict, simulation_results: dict, ign: str):
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        buf = await loop.run_in_executor(pool, _create_rtca_graph, current_xp_data, simulation_results, ign)
    
    return discord.File(buf, filename="rtca_stats.png")
