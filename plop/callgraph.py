from collections import Counter
import six
import os


class Node(object):
    def __init__(self, id, attrs=None):
        self.id = id
        self.attrs = attrs or {}
        self.weights = Counter()

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return 'Node(%s)' % (self.id,)

class Edge(object):
    def __init__(self, parent, child, weights):
        self.parent = parent
        self.child = child
        self.weights = Counter(weights)

    def key(self):
        return (self.parent, self.child)

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        return self.key() == other.key()

    def __repr__(self):
        return 'Edge(%s, %s, %r)' % (self.parent.id, self.child.id, self.weights)

    def __iadd__(self, other):
        self.weights += other.weights
        return self

class Stack(object):
    def __init__(self, nodes, weights):
        self.nodes = nodes
        self.weights = Counter(weights)


class CallGraph(object):
    def __init__(self):
        # map Node.id: Node
        self.nodes = {}
        self.edges = {}
        self.stacks = []

    def add_stack(self, nodes, weights):
        nodes = [self.nodes.setdefault(n.id, n) for n in nodes]
        weights = Counter(weights)
        self.stacks.append(Stack(nodes, weights))
        
        for i in range(len(nodes) - 1):
            parent = nodes[i]
            child = nodes[i + 1]
            edge = Edge(parent, child, weights)
            if edge.key() in self.edges:
                self.edges[edge.key()] += edge
            else:
                self.edges[edge.key()] = edge
        nodes[-1].weights += weights

    def get_top_edges(self, weight, num=10):
        # TODO: is there a partial sort in python?
        sorted_edges = sorted(six.itervalues(self.edges),
                              key=lambda e: e.weights.get(weight, 0),
                              reverse=True)
        return sorted_edges[:num]

    def get_top_nodes(self, weight, num=10):
        sorted_nodes = sorted(six.itervalues(self.nodes),
                              key=lambda n: n.weights.get(weight, 0),
                              reverse=True)
        return sorted_nodes[:num]

    @staticmethod
    def load(filename=None, data=None):
        import ast
        if data is None:
            assert filename
            with open(filename) as f:
                data = f.read()
        data = ast.literal_eval(data)
        graph = CallGraph()
        for stack, count in six.iteritems(data):
            stack_nodes = [Node(id=frame, attrs=dict(threadname=frame[0],
                                                     fullpath=frame[1],
                                                     filename=frame[1].rpartition('/')[-1],
                                                     lineno=frame[2],
                                                     funcname=frame[3]))
                           for frame in reversed(stack)]
            # TODO: this shouldn't be recorded as "calls"
            graph.add_stack(stack_nodes, weights=dict(calls=count))
        return graph
        
        
def profile_to_json(filename=None, data=None):
    if data is None:
        root = os.path.abspath(options.datadir) + os.path.sep
        abspath = os.path.abspath(os.path.join(root, filename))
        assert (abspath + os.path.sep).startswith(root)
        graph = CallGraph.load(filename=abspath)
    else:
        graph = CallGraph.load(data=data)

    total = sum(stack.weights['calls'] for stack in graph.stacks)
    top_stacks = graph.stacks
    #top_stacks = [stack for stack in graph.stacks if stack.weights['calls'] > total*.005]
    filtered_nodes = set()
    for stack in top_stacks:
        filtered_nodes.update(stack.nodes)
    nodes=[dict(attrs=node.attrs, weights=node.weights, id=node.id)
           for node in filtered_nodes]
    nodes = sorted(nodes, key=lambda n: -n['weights']['calls'])
    #index = {node['id']: i for i, node in enumerate(nodes)}
    index = dict([(node['id'], i) for i, node in enumerate(nodes)])


    # High-degree nodes are generally common utility functions, and
    # creating edges from all over the graph tends to obscure more than
    # it helps.
    degrees = Counter()
    dropped = set()
    for edge in six.itervalues(graph.edges):
        degrees[edge.child.id] += 1
        degrees[edge.parent.id] += 1
    for node, degree in six.iteritems(degrees):
        if degree > 6:
            dropped.add(node)

    edges = [dict(source=index[edge.parent.id],
                  target=index[edge.child.id],
                  weights=edge.weights)
             for edge in six.itervalues(graph.edges)
             if (edge.parent.id in index and
                 edge.child.id in index and
                 edge.parent.id not in dropped and
                 edge.child.id not in dropped)]
    stacks = [dict(nodes=[index[n.id] for n in stack.nodes],
                   weights=stack.weights)
              for stack in top_stacks]
    return dict(nodes=nodes, edges=edges, stacks=stacks)


if __name__ == '__main__':
    import sys
    graph = CallGraph.load(sys.argv[1])
