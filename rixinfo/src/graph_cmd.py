import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
from matplotlib.patches import FancyArrowPatch
from collections import defaultdict

from common import init_node, fetch_system_info

# Visual style constants
COLORS = {
    "node": "#5BA3CF",
    "topic": "#6BBF6B",
    "service": "#E87474",
    "action": "#F0A64E",
}
LAYER = {
    "node": 0,
    "topic": 1,
    "service": 2,
    "action": 3,
}
FONT_SIZE = 10
BOX_PAD = 0.4


def _build_graph(system_info):
    G = nx.DiGraph()
    node_id_to_key: dict[int, str] = {}

    for n in system_info.nodes:
        key = f"node:{n.id}"
        G.add_node(key, node_type="node", display_name=n.name, subset=LAYER["node"])
        node_id_to_key[n.id] = key

    for t in system_info.topics:
        key = f"topic:{t.name}"
        G.add_node(key, node_type="topic", display_name=t.name, subset=LAYER["topic"])

    for srv in system_info.services:
        key = f"service:{srv.name}"
        G.add_node(key, node_type="service", display_name=srv.name, subset=LAYER["service"])
        host = node_id_to_key.get(srv.node_id)
        if host:
            G.add_edge(host, key)

    for act in system_info.actions:
        key = f"action:{act.name}"
        G.add_node(key, node_type="action", display_name=act.name, subset=LAYER["action"])
        host = node_id_to_key.get(act.node_id)
        if host:
            G.add_edge(host, key)

    topic_keys = {f"topic:{t.name}" for t in system_info.topics}

    for pub in system_info.publishers:
        src = node_id_to_key.get(pub.node_id)
        dst = f"topic:{pub.topic_info.name}"
        if src and dst in topic_keys:
            G.add_edge(src, dst)

    for sub in system_info.subscribers:
        src = f"topic:{sub.topic_info.name}"
        dst = node_id_to_key.get(sub.node_id)
        if dst and src in topic_keys:
            G.add_edge(src, dst)

    return G


def graph(args: list[str]) -> None:
    node = init_node()
    if not node:
        return

    system_info = fetch_system_info(node)
    if not system_info:
        return

    G = _build_graph(system_info)

    if G.number_of_nodes() == 0:
        print("No nodes to display.")
        return

    # Print entity summary
    counts = {}
    for n in G.nodes():
        ntype = G.nodes[n].get("node_type", "unknown")
        counts[ntype] = counts.get(ntype, 0) + 1
    parts = [f"{counts.get(t, 0)} {t}s" for t in ["node", "topic", "service", "action"] if counts.get(t, 0) > 0]
    print(f"Graph entities: {', '.join(parts)}")

    # Deterministic layered layout: nodes grouped by type in vertical columns
    pos = nx.multipartite_layout(G, subset_key="subset", align="horizontal")

    # Scale: wide horizontal gaps between layers, generous vertical spacing
    for k in pos:
        pos[k][0] *= 6.0
        pos[k][1] *= 3.0

    labels = {n: G.nodes[n].get("display_name", n) for n in G.nodes()}

    fig, ax = plt.subplots(figsize=(16, 9))

    # Set axis limits FIRST so data<->display transform is stable for bbox
    xvals = [pos[k][0] for k in pos]
    yvals = [pos[k][1] for k in pos]
    xmargin = (max(xvals) - min(xvals)) * 0.12 + 1.0
    ymargin = (max(yvals) - min(yvals)) * 0.12 + 1.0
    ax.set_xlim(min(xvals) - xmargin, max(xvals) + xmargin)
    ax.set_ylim(min(yvals) - ymargin, max(yvals) + ymargin)
    ax.axis("off")

    # --- Draw labelled boxes using text bbox (auto-sized to fit text) ---
    node_patches = {}
    for n in G.nodes():
        x, y = pos[n]
        label = labels[n]
        ntype = G.nodes[n].get("node_type", "unknown")
        color = COLORS.get(ntype, "#999999")

        txt = ax.text(
            x, y, label,
            fontsize=FONT_SIZE, fontweight="bold", fontfamily="sans-serif",
            ha="center", va="center", zorder=3,
            bbox=dict(
                boxstyle=f"round,pad={BOX_PAD}",
                facecolor=color, edgecolor="black",
                linewidth=1.5, alpha=0.92,
            ),
        )
        # Force a draw so the bbox patch is created and sized
        fig.canvas.draw()
        node_patches[n] = txt.get_bbox_patch()

    # --- Draw arrows that clip to patch boundaries ---
    # Group edges by undirected pair to spread parallel edges
    edge_groups: dict[tuple, list] = defaultdict(list)
    for u, v in G.edges():
        pair = (min(u, v), max(u, v))
        edge_groups[pair].append((u, v))

    for pair, edges in edge_groups.items():
        n_edges = len(edges)
        for idx, (u, v) in enumerate(edges):
            if n_edges == 1:
                rad = 0.0
            else:
                rad = 0.2 * (idx - (n_edges - 1) / 2)
            # Flip curvature for reversed direction relative to canonical pair
            if (u, v) != pair:
                rad = -rad

            arrow = FancyArrowPatch(
                posA=pos[u], posB=pos[v],
                arrowstyle="-|>",
                mutation_scale=20,
                color="#444444",
                linewidth=1.5,
                alpha=0.75,
                connectionstyle=f"arc3,rad={rad}",
                shrinkA=0, shrinkB=0,
                patchA=node_patches[u],
                patchB=node_patches[v],
                zorder=1,
            )
            ax.add_patch(arrow)

    # --- Legend ---
    legend_elements = [
        mlines.Line2D([], [], marker="s", color="w", markerfacecolor=COLORS["node"],
                       markersize=12, markeredgecolor="black", label="Nodes"),
        mlines.Line2D([], [], marker="s", color="w", markerfacecolor=COLORS["topic"],
                       markersize=10, markeredgecolor="black", label="Topics"),
        mlines.Line2D([], [], marker="s", color="w", markerfacecolor=COLORS["service"],
                       markersize=9, markeredgecolor="black", label="Services"),
        mlines.Line2D([], [], marker="s", color="w", markerfacecolor=COLORS["action"],
                       markersize=9, markeredgecolor="black", label="Actions"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", framealpha=0.9, fontsize=10)
    ax.set_title("RIX Runtime Graph", fontsize=16, fontweight="bold", pad=16)

    fig.tight_layout()

    print("Displaying RIX runtime graph. Close the window to exit.")
    plt.show()
