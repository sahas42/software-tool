import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from langchain_core.documents import Document

class SemanticChunker:
    """
    Parses Python code and chunks it dynamically into semantic boundaries
    such as classes and functions using Tree-sitter.
    """
    def __init__(self):
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)

    def extract_chunks(self, source_code: str, metadata: dict = None) -> list[Document]:
        """
        Parses the given source code and extracts top-level functions, classes,
        and methods as semantic chunks.
        """
        if not source_code.strip():
            return []

        tree = self.parser.parse(bytes(source_code, "utf8"))
        root_node = tree.root_node

        chunks = []
        
        # We want to traverse the AST and extract relevant chunk logic.
        # Queries or basic traversal can extract functions and classes.
        # Let's use basic traversal looking for function_definition, class_definition, etc.
        
        def traverse(node):
            if node.type in ('function_definition', 'class_definition', 'decorated_definition'):
                # get the node text
                chunk_text = node.text.decode("utf8")
                
                # get symbol name if possible, for better metadata
                symbol_name = "unknown"
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = child.text.decode("utf8")
                        break
                    elif node.type == 'decorated_definition' and child.type in ('function_definition', 'class_definition'):
                        # Look inside the decorated definition
                        for subchild in child.children:
                            if subchild.type == "identifier":
                                symbol_name = subchild.text.decode("utf8")
                                break
                        break
                
                chunk_meta = dict(metadata) if metadata else {}
                chunk_meta["node_type"] = node.type
                chunk_meta["symbol_name"] = symbol_name
                chunk_meta["start_line"] = node.start_point[0]
                chunk_meta["end_line"] = node.end_point[0]
                
                chunks.append(Document(page_content=chunk_text, metadata=chunk_meta))
                
                # We can choose not to traverse inside function_definition to avoid double counting,
                # but we probably want to traverse inside class_definition to get methods.
                if node.type == 'class_definition':
                    for child in node.children:
                        traverse(child)
            else:
                for child in node.children:
                    traverse(child)

        traverse(root_node)

        # Fallback if no classes or functions were found (it might be a script)
        if not chunks:
            chunk_meta = dict(metadata) if metadata else {}
            chunk_meta["node_type"] = "script"
            chunks.append(Document(page_content=source_code, metadata=chunk_meta))

        return chunks
