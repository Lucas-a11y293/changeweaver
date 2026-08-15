"""Deterministic graph operations used by impact analysis and contract checks."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from changeweaver.domain.models import Edge, Node


@dataclass(frozen=True, slots=True)
class Graph:
    nodes: tuple[Node, ...]
    edges: tuple[Edge, ...]

    @property
    def node_map(self) -> dict[str, Node]:
        return {node.node_id: node for node in self.nodes}

    @property
    def outgoing(self) -> dict[str, tuple[Edge, ...]]:
        result: dict[str, list[Edge]] = {node.node_id: [] for node in self.nodes}
        for edge in self.edges:
            result.setdefault(edge.source, []).append(edge)
        return {key: tuple(sorted(value, key=lambda edge: edge.fact_key)) for key, value in result.items()}

    @property
    def incoming(self) -> dict[str, tuple[Edge, ...]]:
        result: dict[str, list[Edge]] = {node.node_id: [] for node in self.nodes}
        for edge in self.edges:
            result.setdefault(edge.target, []).append(edge)
        return {key: tuple(sorted(value, key=lambda edge: edge.fact_key)) for key, value in result.items()}

    def reverse_reachable(
        self,
        roots: tuple[str, ...],
        max_nodes: int,
        max_path_samples: int,
    ) -> tuple[tuple[str, ...], tuple[tuple[str, ...], ...]]:
        """Return nodes that can reach roots and stable paths ending at each root."""

        incoming = self.incoming
        queue: deque[str] = deque(sorted(set(roots)))
        visited = set(queue)
        paths: dict[str, tuple[str, ...]] = {root: (root,) for root in sorted(set(roots))}
        while queue and len(visited) < max_nodes:
            current = queue.popleft()
            for edge in incoming.get(current, ()):
                predecessor = edge.source
                if predecessor in visited:
                    continue
                visited.add(predecessor)
                paths[predecessor] = (predecessor, *paths[current])
                queue.append(predecessor)
                if len(visited) >= max_nodes:
                    break
        path_values = tuple(sorted(paths.values(), key=lambda path: (len(path), path))[:max_path_samples])
        return tuple(sorted(visited)), path_values

    def boundary_crossings(self, paths: tuple[tuple[str, ...], ...]) -> int:
        nodes = self.node_map
        transitions: set[tuple[str, str]] = set()
        for path in paths:
            layers = [nodes[node_id].layer for node_id in path if node_id in nodes]
            transitions.update(
                (left, right)
                for left, right in zip(layers, layers[1:], strict=False)
                if left and right and left != right
            )
        return len(transitions)

    def edges_for_nodes(self, node_ids: set[str]) -> tuple[Edge, ...]:
        return tuple(
            sorted(
                (edge for edge in self.edges if edge.source in node_ids and edge.target in node_ids),
                key=lambda edge: edge.fact_key,
            )
        )
