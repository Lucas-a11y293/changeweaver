from changeweaver.domain.graph import Graph
from changeweaver.domain.models import Edge, Node


def test_reverse_reachability_is_deterministic() -> None:
    nodes = (
        Node("a", "dart_library", "lib/a.dart", layer="presentation"),
        Node("b", "dart_library", "lib/b.dart", layer="data"),
        Node("c", "dart_library", "lib/c.dart", layer="domain"),
    )
    edges = (
        Edge("a", "b", "import", 1, "package:b"),
        Edge("b", "c", "import", 1, "package:c"),
    )
    graph = Graph(nodes, edges)

    affected, paths = graph.reverse_reachable(("c",), max_nodes=10, max_path_samples=8)

    assert affected == ("a", "b", "c")
    assert paths == (("c",), ("b", "c"), ("a", "b", "c"))
    assert graph.boundary_crossings(paths) == 2


def test_reverse_reachability_respects_limit() -> None:
    nodes = tuple(Node(str(index), "dart_library", f"lib/{index}.dart") for index in range(4))
    edges = tuple(Edge(str(index), str(index + 1), "import") for index in range(3))

    affected, paths = Graph(nodes, edges).reverse_reachable(("3",), max_nodes=2, max_path_samples=8)

    assert affected == ("2", "3")
    assert paths == (("3",), ("2", "3"))
