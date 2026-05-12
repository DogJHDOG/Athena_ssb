import call_graph
import os

from abc import ABC, abstractmethod
from tree_sitter import Language, Parser


class CallParser():
    __metaclass__ = ABC
    src_code = ''   #A string containing all the source code of the filepath
    lines = []      #All the lines in the current file
    filepath = ''  #the path to the current file

    """A string holding the name of the language, ex: 'python' """
    @property
    @abstractmethod
    def language(self):
        pass

    """A string holding the file extension for the language, ex: '.java' """
    @property
    @abstractmethod
    def extension(self):
        pass

    """A tree-sitter Language object, build from build/my-languages.so """
    @property
    @abstractmethod
    def language_library(self):
        pass

    """A tree-sitter Parser object"""
    @property
    @abstractmethod
    def PARSER(self):
        pass

    """The query that finds the method definitions (including constructors) and import statements"""
    @property
    @abstractmethod
    def method_import_q(self):
        pass

    """The query that finds all the function calls in the file"""
    @property
    @abstractmethod
    def call_q(self):
        pass

    """Sets the current file and updates the src_code and lines"""
    def set_current_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors = 'ignore') as file:
                self.src_code = file.read()
                self.lines = self.src_code.split('\n')
                self.filepath = path
        except FileNotFoundError as err:
            print(err)

    """Takes in a tree-sitter node object and returns the code that it refers to"""
    def node_to_string(self, node) -> str:
        start_point = node.start_point
        end_point = node.end_point
        if start_point[0] == end_point[0]:
            return self.lines[start_point[0]][start_point[1]:end_point[1]]
        ret = self.lines[start_point[0]][start_point[1]:] + "\n"
        ret += "\n".join([line for line in self.lines[start_point[0] + 1:end_point[0]]])
        ret += "\n" + self.lines[end_point[0]][:end_point[1]]
        return ret

    """Takes in a call node and returns a tuple of the name of the method that was called and the number of arguments passed
    for example, if passed the call node 'add(3, 4)' the function will return '(add, 2)'. See the Python, Java, and Cpp parsers
    for example implementations and use https://tree-sitter.github.io/tree-sitter/playground to view the structre of
    a call node in the desired language"""
    @abstractmethod
    def get_call_print(self, call) -> tuple:
        pass

    """Takes in a method node and returns a tuple of the name of the method and the number of parameters passed for example,
    if passed the method node refering to 'def add(a,b)' the function will return '(add, 2)' see Java, Python, and Cpp parsers
    for an example implementation, and use https://tree-sitter.github.io/tree-sitter/playground to view the structre of
    a method call in the desired language"""
    @abstractmethod
    def get_method_print(self, method) -> tuple:
        pass

    """Takes in an import node and returns the path of the file that is imported
    don't wory about filtering out system libraries, as the program will check if the file exitsts before trying to add
    it to the project. You may need to override this method depending on how the language handles imports"""
    def get_import_file(self, imp):
        file_to_search = self.node_to_string(imp)
        return file_to_search.replace(".", os.sep) + self.extension


class CppParser(CallParser):
    pass


class JavaParser(CallParser):
    language = 'java'
    extension = '.java'
    language_library = Language('call_graph/my-languages.so', 'java')
    PARSER = Parser()
    PARSER.set_language(language_library)
    method_import_q = language_library.query("""
            (method_declaration) @method
            (constructor_declaration) @method
            (import_declaration
                (identifier) @import)
            (import_declaration
                (scoped_identifier) @import)
            """)
    docstring_method_import_q = language_library.query("""
            (method_declaration) @method
            (constructor_declaration) @method
            (block_comment) @docstring
            (line_comment) @docstring
            (import_declaration
                (identifier) @import)
            (import_declaration
                (scoped_identifier) @import)
            """)

    call_q = language_library.query("""
            (method_invocation) @call
            """)

    method_in_q = language_library.query("""
            (local_variable_declaration) @lv
            (formal_parameter) @param
            (object_creation_expression) @new
            """)


    field_q = language_library.query("""
            (field_declaration) @field
            """)

    def get_call_print(self, node):
        try:
            object_name, class_name = None, None
            class_node, class_new_node = None, None
            object_node = node.child_by_field_name('object')
            method_name = self.node_to_string(node.child_by_field_name('name'))
            nargs = (len(node.child_by_field_name('arguments').children) - 1) // 2

            if object_node:
                if object_node.type == 'identifier':
                    object_name = self.node_to_string(object_node)
                    if object_name[0].isupper():
                        return (object_name, method_name, nargs)
                    else:
                        cur_node = node.parent
                        if cur_node:
                            while cur_node.parent.type != 'class_body' and cur_node.parent.type != 'enum_body' :
                                if cur_node.parent.type == 'interface_body' and cur_node.parent.parent.parent.type == 'program':
                                    break
                                cur_node = cur_node.parent

                        if cur_node.type == 'method_declaration':
                            for item_node in self.method_in_q.captures(cur_node):
                                if item_node[0].start_point[0] < node.start_point[0]:
                                    search_obj_node = None
                                    if item_node[1] == 'param':
                                        search_obj_node = item_node[0].child_by_field_name('name')
                                    elif item_node[1] == 'lv':
                                        search_obj_node = item_node[0].child_by_field_name('declarator').child_by_field_name('name')
                                    else:
                                        if item_node[0].prev_named_sibling and item_node[0].prev_named_sibling.type == 'identifier':
                                            if object_name == self.node_to_string(item_node[0].prev_named_sibling):
                                                class_new_node = item_node[0].child_by_field_name('type')
                                    if search_obj_node and object_name == self.node_to_string(search_obj_node):
                                        class_node = item_node[0].child_by_field_name('type')

                            if not class_new_node and not class_node:
                                cur_node = cur_node.parent
                                fields = [field[0] for field in self.field_q.captures(cur_node) if field[0].start_point[0] < node.start_point[0]]
                                for field in fields:
                                    field_node = None
                                    field_node = field.child_by_field_name('declarator').child_by_field_name('name')
                                    if field_node and self.node_to_string(field_node) == object_name:
                                        class_node = field.child_by_field_name('type')
                                        obj_create_node = None
                                        obj_create_node = field.child_by_field_name('declarator').child_by_field_name('value')
                                        if obj_create_node and obj_create_node.type == 'object_creation_expression':
                                            class_new_node = obj_create_node.child_by_field_name('type')

                elif object_node.type == 'object_creation_expression':
                    class_new_node=object_node.child_by_field_name('type')

                if class_new_node and class_new_node.type == 'type_identifier':
                    class_name = self.node_to_string(class_new_node)
                elif class_node and class_node.type == 'type_identifier':
                    class_name = self.node_to_string(class_node)

            else:
                cur_node = node.parent
                if cur_node:
                    while cur_node.type != 'program':
                        if cur_node.type == 'class_declaration':
                            class_name = self.node_to_string(cur_node.child_by_field_name('name'))
                            break
                        cur_node = cur_node.parent

        except Exception as e:
            pass
        
        return (class_name, method_name, nargs)

    def get_method_print(self, method):
        name = self.node_to_string(method.child_by_field_name('name'))
        nparams = (len(method.child_by_field_name('parameters').children) - 1) // 2

        return (name, nparams)


class PythonParser(CallParser):
    pass


class KotlinParser(CallParser):
    language = 'kotlin'
    extension = '.kt'

    def __init__(self):
        # Lazy grammar load so importing this module doesn't require kotlin in the .so.
        self.language_library = Language('call_graph/my-languages.so', 'kotlin')
        self.PARSER = Parser()
        self.PARSER.set_language(self.language_library)
        self.method_import_q = self.language_library.query("""
                (function_declaration) @method
                (secondary_constructor) @method
                (anonymous_initializer) @method
                (import_header) @import
                """)
        self.docstring_method_import_q = self.language_library.query("""
                (function_declaration) @method
                (secondary_constructor) @method
                (anonymous_initializer) @method
                (multiline_comment) @docstring
                (line_comment) @docstring
                (import_header) @import
                """)
        self.call_q = self.language_library.query("""
                (call_expression) @call
                """)
        self.method_in_q = self.language_library.query("""
                (property_declaration) @lv
                (parameter) @param
                (call_expression) @new
                """)
        self.field_q = self.language_library.query("""
                (property_declaration) @field
                """)

    def get_import_file(self, imp):
        # import_header may contain identifier nodes and an optional 'as' alias
        # Use the first identifier-like child sequence joined by dots.
        parts = []
        for child in imp.children:
            if child.type == 'identifier':
                parts.append(self.node_to_string(child))
            elif child.type == 'import_alias':
                break
        if parts:
            dotted = '.'.join(parts)
        else:
            dotted = self.node_to_string(imp).strip()
            if dotted.startswith('import'):
                dotted = dotted[len('import'):].strip()
            dotted = dotted.split(' as ')[0].strip().rstrip(';')
        return dotted.replace('.', os.sep) + self.extension

    def _enclosing_function(self, node):
        cur = node.parent
        while cur is not None:
            if cur.type == 'function_declaration':
                return cur
            cur = cur.parent
        return None

    def _enclosing_class_name(self, node):
        cur = node.parent
        while cur is not None:
            if cur.type in ('class_declaration', 'object_declaration'):
                for c in cur.children:
                    if c.type in ('type_identifier', 'simple_identifier'):
                        return self.node_to_string(c)
                break
            cur = cur.parent
        return None

    def _resolve_local_type(self, node, object_name):
        scope = self._enclosing_function(node)
        if scope is None:
            return None
        for capture in self.method_in_q.captures(scope):
            item, tag = capture[0], capture[1]
            if item.start_point[0] >= node.start_point[0]:
                continue
            if tag == 'param':
                p_name = None
                p_type = None
                for c in item.children:
                    if c.type == 'simple_identifier' and p_name is None:
                        p_name = self.node_to_string(c)
                    elif c.type in ('user_type', 'type_reference', 'nullable_type'):
                        p_type = self.node_to_string(c)
                if p_name == object_name and p_type:
                    return p_type.split('<')[0].split('?')[0].split('.')[-1]
            elif tag == 'lv':
                # property_declaration: 'val'|'var' variable_declaration (':' type)? ('=' expr)?
                p_name = None
                p_type = None
                seen_colon = False
                for c in item.children:
                    if c.type == 'variable_declaration' and p_name is None:
                        for cc in c.children:
                            if cc.type == 'simple_identifier' and p_name is None:
                                p_name = self.node_to_string(cc)
                            elif cc.type in ('user_type', 'type_reference', 'nullable_type'):
                                p_type = self.node_to_string(cc)
                    elif c.type == ':':
                        seen_colon = True
                    elif seen_colon and c.type in ('user_type', 'type_reference', 'nullable_type'):
                        p_type = self.node_to_string(c)
                        seen_colon = False
                if p_name == object_name and p_type:
                    return p_type.split('<')[0].split('?')[0].split('.')[-1]
        return None

    def get_call_print(self, node):
        class_name = None
        method_name = None
        nargs = 0
        try:
            if not node.children:
                return (None, None, 0)
            callable_node = node.children[0]
            suffix_node = None
            for c in node.children[1:]:
                if c.type == 'call_suffix':
                    suffix_node = c
                    break
            if callable_node.type == 'simple_identifier':
                method_name = self.node_to_string(callable_node)
                class_name = self._enclosing_class_name(node)
            elif callable_node.type == 'navigation_expression':
                receiver = None
                for c in callable_node.children:
                    if c.type == 'navigation_suffix':
                        for cc in c.children:
                            if cc.type == 'simple_identifier' and method_name is None:
                                method_name = self.node_to_string(cc)
                    elif receiver is None:
                        receiver = c
                if receiver is not None:
                    if receiver.type == 'simple_identifier':
                        receiver_text = self.node_to_string(receiver)
                        if receiver_text and receiver_text[0].isupper():
                            class_name = receiver_text
                        else:
                            class_name = self._resolve_local_type(node, receiver_text)
                    elif receiver.type == 'call_expression':
                        # chained: foo().bar() — receiver type unknown without full analysis
                        class_name = None
            if suffix_node is not None:
                for c in suffix_node.children:
                    if c.type == 'value_arguments':
                        nargs = sum(1 for cc in c.children if cc.type == 'value_argument')
                        break
        except Exception:
            pass
        return (class_name, method_name, nargs)

    def get_method_print(self, method):
        name = None
        nparams = 0
        for child in method.children:
            if child.type == 'simple_identifier' and name is None:
                name = self.node_to_string(child)
            elif child.type == 'function_value_parameters':
                nparams = sum(1 for c in child.children if c.type == 'parameter')
                break
        return (name, nparams)