import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import random

# Parametri simulazione
NUM_NODES = 20
AREA_SIZE = 500  # metri
COMM_RADIUS = 120  # metri
FAILURE_PROB = 0.1
MOVE_STEP = 5  # massimo spostamento per tick

# Inizializzazione dei nodi
class Node:
    def __init__(self, node_id, x, y):
        self.id = node_id
        self.x = x
        self.y = y
        self.failed = random.random() < FAILURE_PROB
        self.position_log = [(x, y)]
        self.reached = False
        self.parent = None
        self.children = []
        self.responses_received = 0
        self.response_sent = False

    def move(self):
        dx = random.uniform(-MOVE_STEP, MOVE_STEP)
        dy = random.uniform(-MOVE_STEP, MOVE_STEP)
        self.x = max(0, min(AREA_SIZE, self.x + dx))
        self.y = max(0, min(AREA_SIZE, self.y + dy))
        self.position_log.append((self.x, self.y))

    def distance_to(self, other):
        return np.hypot(self.x - other.x, self.y - other.y)

# Inizializzazione
nodes = [Node(i, random.uniform(0, AREA_SIZE), random.uniform(0, AREA_SIZE)) for i in range(NUM_NODES)]
M = nodes[0]  # Nodo capogruppo
M.reached = True
M.parent = None

# Simulazione dinamica con nodi mobili
history = []

def simulate_step(step):
    for node in nodes:
        node.move()

    active_nodes = {node.id: node for node in nodes if not node.failed}
    
    # Propagazione messaggi
    queue = [M]
    for node in nodes:
        node.reached = False if node != M else True
        node.parent = None
        node.children = []

    while queue:
        current = queue.pop(0)
        for other in nodes:
            if other.reached or other.failed or other == current:
                continue
            if current.distance_to(other) <= COMM_RADIUS:
                other.reached = True
                other.parent = current.id
                current.children.append(other.id)
                queue.append(other)
    
    history.append([(node.x, node.y, node.reached, node.failed) for node in nodes])

# Visualizzazione
fig, ax = plt.subplots(figsize=(8, 8))
sc = ax.scatter([], [], s=100)
lines = []

def update(frame):
    simulate_step(frame)
    ax.clear()
    data = history[frame]
    x = [pos[0] for pos in data]
    y = [pos[1] for pos in data]
    colors = ['green' if r and not f else 'red' if f else 'gray' for _, _, r, f in data]
    sc = ax.scatter(x, y, c=colors, s=100)
    for node in nodes:
        if node.parent is not None:
            parent = nodes[node.parent]
            ax.plot([node.x, parent.x], [node.y, parent.y], 'k-', linewidth=0.5)
    ax.set_xlim(0, AREA_SIZE)
    ax.set_ylim(0, AREA_SIZE)
    ax.set_title(f"Step {frame + 1}")

ani = animation.FuncAnimation(fig, update, frames=10, interval=1000, repeat=False)
plt.show()
