"""Kotlin rule: enrich data class auto-generated methods, normalize top-level/extension identifiers."""

from __future__ import annotations

import os
from typing import List, Optional, Tuple

from ..entry import ChangeSetEntry
from .base import Rule


class KotlinRule(Rule):
    DATA_CLASS_VIRTUAL = ('copy', 'equals', 'hashCode', 'toString')

    def apply(self, raw_methods, software_repo) -> List[ChangeSetEntry]:
        # Lazy import: tree_sitter is only required at runtime.
        from call_graph.parsers import KotlinParser
        parser = KotlinParser()

        out: List[ChangeSetEntry] = []
        emitted_virtual: set = set()

        for r in raw_methods:
            abs_path = os.path.join(str(software_repo.repo_dir), r.file_path)
            source = self._read_bytes(abs_path)
            if source is None:
                # File missing at parent commit (e.g., newly added file) — passthrough.
                out.append(self._real_entry(r, identifier=r.method_name, class_name=None))
                continue

            tree = parser.PARSER.parse(source)
            method_node = self._find_method_node(tree.root_node, r.method_name, source)
            if method_node is None:
                out.append(self._real_entry(r, identifier=r.method_name, class_name=None))
                continue

            class_node = self._enclosing_class(method_node)
            if class_node is None:
                # Top-level or extension function — normalize identifier.
                identifier = self._top_level_identifier(method_node, r.file_path, source)
                out.append(self._real_entry(r, identifier=identifier, class_name=None))
                continue

            class_name = self._class_name(class_node, source)
            identifier = (f"{class_name}.{r.method_name}" if class_name else r.method_name)
            out.append(self._real_entry(r, identifier=identifier, class_name=class_name))

            if class_name is not None and self._is_data_class(class_node, source):
                key = (r.repo, r.parent_commit, r.file_path, class_name)
                if key in emitted_virtual:
                    continue
                emitted_virtual.add(key)
                for ve in self._data_class_virtual_methods(r, class_node, class_name, source):
                    out.append(ve)

        return out

    @staticmethod
    def _read_bytes(path: str) -> Optional[bytes]:
        try:
            with open(path, 'rb') as f:
                return f.read()
        except (FileNotFoundError, IsADirectoryError):
            return None

    @staticmethod
    def _node_text(node, source: bytes) -> str:
        return source[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')

    @classmethod
    def _find_method_node(cls, root, name: str, source: bytes):
        # Depth-first; return first function_declaration whose name matches.
        stack = [root]
        while stack:
            n = stack.pop()
            if n.type == 'function_declaration':
                for c in n.children:
                    if c.type == 'simple_identifier':
                        if cls._node_text(c, source) == name:
                            return n
                        break
            stack.extend(reversed(n.children))
        return None

    @staticmethod
    def _enclosing_class(node):
        cur = node.parent
        while cur is not None:
            if cur.type in ('class_declaration', 'object_declaration'):
                return cur
            cur = cur.parent
        return None

    @classmethod
    def _class_name(cls, class_node, source: bytes) -> Optional[str]:
        for child in class_node.children:
            if child.type in ('type_identifier', 'simple_identifier'):
                return cls._node_text(child, source)
        return None

    @classmethod
    def _is_data_class(cls, class_node, source: bytes) -> bool:
        for child in class_node.children:
            if child.type == 'modifiers':
                for sub in child.children:
                    text = cls._node_text(sub, source).strip()
                    if text == 'data' or 'data' in text.split():
                        return True
            else:
                # Some grammars expose 'data' as a leaf modifier directly.
                if cls._node_text(child, source).strip() == 'data':
                    return True
        return False

    @classmethod
    def _primary_constructor_params(cls, class_node, source: bytes) -> List[Tuple[Optional[str], str]]:
        pc = None
        for child in class_node.children:
            if child.type == 'primary_constructor':
                pc = child
                break
        if pc is None:
            return []
        params: List[Tuple[Optional[str], str]] = []
        for child in pc.children:
            if child.type != 'class_parameter':
                continue
            kind: Optional[str] = None
            name: Optional[str] = None
            for sub in child.children:
                text = cls._node_text(sub, source).strip()
                if text in ('val', 'var') and kind is None:
                    kind = text
                elif sub.type == 'simple_identifier' and name is None:
                    name = text
            if name is not None:
                params.append((kind, name))
        return params

    @classmethod
    def _top_level_identifier(cls, method_node, file_path: str, source: bytes) -> str:
        # Extension: function_declaration containing a receiver_type child before the name.
        receiver_type: Optional[str] = None
        for child in method_node.children:
            if child.type == 'simple_identifier':
                break
            if child.type in ('user_type', 'type_reference', 'receiver_type'):
                receiver_type = cls._node_text(child, source).strip()
                break
        method_name = None
        for child in method_node.children:
            if child.type == 'simple_identifier':
                method_name = cls._node_text(child, source)
                break
        if method_name is None:
            method_name = ''
        if receiver_type:
            return f"{receiver_type}.{method_name}"
        # Plain top-level: <FileName>Kt.method (Java interop convention)
        base = os.path.basename(file_path)
        stem = base[:-3] if base.endswith('.kt') else base
        return f"{stem.capitalize()}Kt.{method_name}"

    def _data_class_virtual_methods(self, raw, class_node, class_name: str, source: bytes) -> List[ChangeSetEntry]:
        params = self._primary_constructor_params(class_node, source)
        out: List[ChangeSetEntry] = []
        for idx, (kind, pname) in enumerate(params, start=1):
            out.append(self._virtual_entry(raw, class_name, f"component{idx}"))
            if pname:
                getter = f"get{pname[:1].upper()}{pname[1:]}"
                out.append(self._virtual_entry(raw, class_name, getter))
                if kind == 'var':
                    setter = f"set{pname[:1].upper()}{pname[1:]}"
                    out.append(self._virtual_entry(raw, class_name, setter))
        for vname in self.DATA_CLASS_VIRTUAL:
            out.append(self._virtual_entry(raw, class_name, vname))
        return out

    @staticmethod
    def _real_entry(raw, identifier: str, class_name: Optional[str]) -> ChangeSetEntry:
        return ChangeSetEntry(
            repo=raw.repo,
            parent_commit=raw.parent_commit,
            file_path=raw.file_path,
            identifier=identifier,
            kind='MODIFIED',
            source='real',
            class_name=class_name,
            child_commit=raw.child_commit,
            hunk_id=raw.hunk_id,
        )

    @staticmethod
    def _virtual_entry(raw, class_name: str, method: str) -> ChangeSetEntry:
        return ChangeSetEntry(
            repo=raw.repo,
            parent_commit=raw.parent_commit,
            file_path=raw.file_path,
            identifier=f"{class_name}.{method}",
            kind='VIRTUAL',
            source='implicit',
            class_name=class_name,
            child_commit=raw.child_commit,
            hunk_id=raw.hunk_id,
        )
