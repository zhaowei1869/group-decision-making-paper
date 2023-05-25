import random
import networkx as nx
import time
import collections
import matplotlib.pyplot as plt
from PIL import Image

import matplotlib.colors as colors  # Add this line
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']   # Add this line


class Community:
    """ 定义一个社区类 方便计算操作"""

    def __init__(self, G, alpha=1.0):
        self._G = G
        # α为超参数 控制观察到社区的尺度 大的α值产生非常小的社区，小的α值反而提供大的社区
        self._alpha = alpha
        self._nodes = set()
        # k_in,k_out分别代表社区总的的内部度与外部度
        self._k_in = 0
        self._k_out = 0

    def add_node(self, node):
        """ 添加节点到社区 """
        # 获得节点的邻居集  因为两点维护一边  从邻居点可以得到它的内部、外部度
        neighbors = set(self._G.neighbors(node))
        # 这里使用了集合操作简化运算 节点的k_in就等于节点在社区内的节点数(也就是节点的邻居与已经在社区中的节点集的集合)
        node_k_in = len(neighbors & self._nodes)
        # k_out自然就等于邻居数(总边数) - k_in(内部边数)
        node_k_out = len(neighbors) - node_k_in
        # 更新社区的节点、k_in、k_out
        self._nodes.add(node)
        # 对于内部度 节点本身的内部度以及在社区内的邻居节点以前的外部度变为了内部度  所以度*2
        self._k_in += 2 * node_k_in
        # 对于外部度 邻居节点在社区外  只需要计算一次 但要减去一个内部度(因为添加节点后 该节点到了社区内，以前提供的外部度变为了内部度 应该减去)
        self._k_out = self._k_out + node_k_out - node_k_in

    def remove_node(self, node):
        """ 社区去除节点 """
        neighbors = set(self._G.neighbors(node))
        # 计算与添加相反
        # community_nodes = self._nodes
        # node_k_in = len(neighbors & community_nodes)
        node_k_in = len(neighbors & self._nodes)
        node_k_out = len(neighbors) - node_k_in
        self._nodes.remove(node)
        self._k_in -= 2 * node_k_in
        self._k_out = self._k_out - node_k_out + node_k_in

    def cal_add_fitness(self, node):
        """ 添加时计算适应度该变量 """
        neighbors = set(self._G.neighbors(node))
        old_k_in = self._k_in
        old_k_out = self._k_out
        vertex_k_in = len(neighbors & self._nodes)
        vertex_k_out = len(neighbors) - vertex_k_in
        new_k_in = old_k_in + 2 * vertex_k_in
        new_k_out = old_k_out + vertex_k_out - vertex_k_in
        # 分别用适应度公式计算
        new_fitness = new_k_in / (new_k_in + new_k_out) ** self._alpha
        old_fitness = old_k_in / (old_k_in + old_k_out) ** self._alpha
        return new_fitness - old_fitness

    def cal_remove_fitness(self, node):
        """ 删除时计算适应度该变量 """
        neighbors = set(self._G.neighbors(node))
        new_k_in = self._k_in
        new_k_out = self._k_out
        node_k_in = len(neighbors & self._nodes)
        node_k_out = len(neighbors) - node_k_in
        old_k_in = new_k_in - 2 * node_k_in
        old_k_out = new_k_out - node_k_out + node_k_in
        old_fitness = old_k_in / (old_k_in + old_k_out) ** self._alpha
        new_fitness = new_k_in / (new_k_in + new_k_out) ** self._alpha
        return new_fitness - old_fitness

    def recalculate(self):
        # 遍历社区中是否有适应度为负的节点
        for vid in self._nodes:
            fitness = self.cal_remove_fitness(vid)
            if fitness < 0.0:
                return vid
        return None

    def get_neighbors(self):
        """ 获得社区的邻居节点 方便后面遍历 """
        neighbors = set()
        # 统计社区内所有节点的邻居，其中不在社区内部的邻居节点 就是社区的邻居节点
        for node in self._nodes:
            neighbors.update(set(self._G.neighbors(node)) - self._nodes)
        return neighbors

    def get_fitness(self):
        return float(self._k_in) / ((self._k_in + self._k_out) ** self._alpha)


class LFM:

    def __init__(self, G, alpha):
        self._G = G
        # α为超参数 控制观察到社区的尺度 大的α值产生非常小的社区，小的α值反而提供大的社区
        self._alpha = alpha

    def execute(self):
        communities = []
        # 统计还没被分配到社区的节点(初始是所有节点)
        # node_not_include = self._G.node.keys()[:]
        node_not_include = list(self._G.nodes())
        while len(node_not_include) != 0:
            # 初始化一个社区
            c = Community(self._G, self._alpha)
            # 随机选择一个种子节点
            seed = random.choice(node_not_include)
            # print(seed)
            c.add_node(seed)

            # 获得社区的邻居节点并遍历
            to_be_examined = c.get_neighbors()
            while to_be_examined:
                # 添加适应度最大的节点到社区
                m = {}
                for node in to_be_examined:
                    fitness = c.cal_add_fitness(node)
                    m[node] = fitness
                to_be_add = sorted(m.items(), key=lambda x: x[1], reverse=True)[0]

                # 当所有节点适应度为负  停止迭代
                if to_be_add[1] < 0.0:
                    break
                c.add_node(to_be_add[0])

                # 遍历社区中是否有适应度为负的节点 有则删除
                to_be_remove = c.recalculate()
                while to_be_remove is not None:
                    c.remove_node(to_be_remove)
                    to_be_remove = c.recalculate()

                to_be_examined = c.get_neighbors()

            # 还没被分配到社区的节点集中删除已经被添加到社区中的节点
            for node in c._nodes:
                if node in node_not_include:
                    node_not_include.remove(node)
            communities.append(c._nodes)
        return communities


def cal_EQ(cover, G):
    m = len(G.edges(None, False))  # 如果为真，则返回3元组（u、v、ddict）中的边缘属性dict。如果为false，则返回2元组（u，v）
    # 存储每个节点所在的社区
    vertex_community = collections.defaultdict(lambda: set())
    # i为社区编号(第几个社区) c为该社区中拥有的节点
    for i, c in enumerate(cover):
        # v为社区中的某一个节点
        for v in c:
            # 根据节点v统计他所在的社区i有哪些
            vertex_community[v].add(i)
    total = 0.0
    for c in cover:
        for i in c:
            # o_i表示i节点所同时属于的社区数目
            o_i = len(vertex_community[i])
            # k_i表示i节点的度数(所关联的边数)
            k_i = len(G[i])
            for j in c:
                t = 0.0
                # o_j表示j节点所同时属于的社区数目
                o_j = len(vertex_community[j])
                # k_j表示j节点的度数(所关联的边数)
                k_j = len(G[j])
                if G.has_edge(i, j):
                    t += 1.0 / (o_i * o_j)
                t -= k_i * k_j / (2 * m * o_i * o_j)
                total += t
    return round(total / (2 * m), 4)


def load_graph(path):
    G = nx.Graph()
    with open(path, 'r', encoding='utf-8') as text:
        for line in text:
            # vertices = line.strip().split(' ')
            vertices = line.split()
            '''source = int(vertices[0])
            target = int(vertices[1])'''
            source = vertices[0]
            target = vertices[1]
            G.add_edge(source, target)
    return G

# 源程序
'''if __name__ == "__main__":
    seed = 1024
    random.seed(seed)  # python的随机性
    # G = nx.karate_club_graph()
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight='bold', font_size=5)
    plt.show()
    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()
    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}' )

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')'''

# 不同社区显示不同的颜色
if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight='bold', font_size=5, width=0.4)  # Set edge width to 0.5
    # nx.draw(G, pos, with_labels=True, font_weight='bold', font_size=5, width=0.5)  # Set edge width to 0.5

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    # Assign different colors to nodes based on community membership
    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)  # Get a distinct color from the colormap
                node_colors.append(color)
                break

    # Draw the graph with different node colors
    nx.draw_networkx_nodes(G, pos, node_color=node_colors)

    dpi = 900
    plt.savefig('LFM_graph1.png', dpi=dpi)
    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')


# 设置节点的大小，节点字体大小
'''if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)
    nx.draw(G, pos, with_labels=False, font_weight='bold')

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    # Assign different colors to nodes based on community membership
    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)  # Get a distinct color from the colormap
                node_colors.append(color)
                break

    # Draw the graph with different node colors and adjust node size and label font size
    node_size = 100
    font_size = 5
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_size)
    nx.draw_networkx_labels(G, pos, font_size=font_size)

    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')
'''
# 节点的连线越多，则该节点越大
# 不同社区用不同的颜色表示
if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)

    # Calculate node sizes based on the number of edges
    node_sizes = [G.degree(node) * 20 for node in G.nodes()]

    # Calculate node label font sizes based on the number of edges
    font_sizes = {node: G.degree(node) * 4 for node in G.nodes()}

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)
                node_colors.append(color)
                break

    nx.draw_networkx_edges(G, pos, width=0.4)

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)

    nx.draw_networkx_labels(G, pos, font_size=4)  # Set the font size here

    dpi = 900
    plt.savefig('LFM_graph2.png', dpi=dpi)
    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')

'''if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)

    # Calculate node sizes based on the number of edges
    node_sizes = [G.degree(node) * 80 for node in G.nodes()]

    # Calculate node label font sizes based on the number of edges
    font_sizes = {node: G.degree(node) * 4 for node in G.nodes()}

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)
                node_colors.append(color)
                break

    nx.draw_networkx_edges(G, pos)

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes)

    nx.draw_networkx_labels(G, pos, font_size=2)  # Set the font size here

    # Convert the plot to a PIL Image
    plt.gca().set_axis_off()
    plt.subplots_adjust(top=1, bottom=0, right=1, left=0, hspace=0, wspace=0)
    plt.margins(0, 0)
    plt.savefig('temp.png', dpi=900, bbox_inches='tight', pad_inches=0, transparent=True)
    plt.close()

    # Open the image using Pillow and display
    image = Image.open('temp.png')
    image.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')
'''
# 节点的连线越多，则该节点越大.字体大小也可以显示。字体不在节点中
# 不同社区用不同的颜色表示
# 调节节点大小
'''if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)

    # Calculate node sizes based on the number of edges
    node_sizes = [G.degree(node) * 10 for node in G.nodes()]

    # Calculate node label font sizes based on the number of edges and figure size
    fig_width, fig_height = 10, 10
    font_scale = min(fig_width, fig_height) * 0.02
    font_sizes = {node: G.degree(node) * font_scale for node in G.nodes()}

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)
                node_colors.append(color)
                break

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=600)

    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)

    for node, (x, y) in pos.items():
        node_label = node
        node_font_size = font_sizes[node]
        node_color = 'none'  # Transparent font color
        node_alpha = 0.5  # Transparency level
        ax.text(x, y, node_label, fontsize=node_font_size, ha='center', va='center', color=node_color, alpha=node_alpha)

    ax.set_xticks([])
    ax.set_yticks([])
    plt.box(False)
    plt.tight_layout()

    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')
'''

'''if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)

    # Calculate node sizes based on the number of edges
    node_sizes = [G.degree(node) * 10 for node in G.nodes()]  # Reduce scaling factor from 50 to 30

    # Calculate node label font sizes based on the number of edges and figure size
    fig_width, fig_height = 10, 10
    font_scale = min(fig_width, fig_height) * 0.02
    font_sizes = {node: G.degree(node) * font_scale for node in G.nodes()}

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)
                node_colors.append(color)
                break

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)

    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)

    for node, (x, y) in pos.items():
        node_label = node
        node_font_size = font_sizes[node]
        node_color = 'none'  # Transparent font color
        node_alpha = 0.5  # Transparency level
        ax.text(x, y, node_label, fontsize=node_font_size, ha='center', va='center', color=node_color, alpha=node_alpha)

    ax.set_xticks([])
    ax.set_yticks([])
    plt.box(False)
    plt.tight_layout()

    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')
'''


'''if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)

    # Calculate node sizes based on the number of edges
    node_sizes = [G.degree(node) * 30 for node in G.nodes()]  # Reduce scaling factor from 50 to 30

    # Calculate node label font sizes based on the number of edges and figure size
    fig_width, fig_height = 10, 10
    font_scale = min(fig_width, fig_height) * 0.02
    font_sizes = {node: G.degree(node) * font_scale for node in G.nodes()}

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)
                node_colors.append(color)
                break

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=300)

    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)

    for node, (x, y) in pos.items():
        node_label = node
        node_font_size = font_sizes[node]
        node_alpha = 0.5  # Transparency level
        node_bbox_props = dict(boxstyle="round", fc="none", ec="none", alpha=node_alpha)
        ax.text(x, y, node_label, fontsize=node_font_size, ha='center', va='center', bbox=node_bbox_props)

    ax.set_xticks([])
    ax.set_yticks([])
    plt.box(False)
    plt.tight_layout()

    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')
'''


'''
if __name__ == "__main__":
    seed = 1024
    random.seed(seed)
    G = load_graph('data/relation_result.txt')
    pos = nx.spring_layout(G)

    # Calculate node sizes based on the number of edges
    node_sizes = [G.degree(node) * 80 for node in G.nodes()]  # Reduce scaling factor from 50 to 30

    # Calculate font sizes for node labels
    font_sizes = {node: G.degree(node) * 0.8 for node in G.nodes()}  # Adjust scaling factor as needed

    start_time = time.time()
    algorithm = LFM(G, 0.9)
    communities = algorithm.execute()
    end_time = time.time()

    colormap = plt.cm.tab20
    node_colors = []
    for node in G.nodes():
        for i, community in enumerate(communities):
            if node in community:
                color = colormap(i % 20)
                node_colors.append(color)
                break

    fig, ax = plt.subplots(figsize=(10, 10))

    nx.draw_networkx_edges(G, pos, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, ax=ax)

    for node, (x, y) in pos.items():
        node_label = node
        node_font_size = font_sizes[node]
        node_alpha = 0.5  # Transparency level
        node_bbox_props = dict(boxstyle="round", facecolor="none", edgecolor="none", alpha=node_alpha)
        ax.text(x, y, node_label, fontsize=node_font_size, ha='center', va='center', bbox=node_bbox_props)

    ax.set_xticks([])
    ax.set_yticks([])
    plt.box(False)
    plt.tight_layout()

    plt.show()

    for i, c in enumerate(communities):
        print(f'社区{i},节点数目{len(c)},社区节点{sorted(c)}')

    print(cal_EQ(communities, G))
    print(f'算法执行时间{end_time - start_time}')
'''