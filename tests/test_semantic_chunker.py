import pytest
from src.semantic_chunker import SemanticChunker

def test_semantic_chunker_basic():
    chunker = SemanticChunker()
    source_code = """
def standalone_func():
    return 42

class MyClass:
    def method_one(self):
        pass

    @property
    def decorated_method(self):
        return 1
"""
    chunks = chunker.extract_chunks(source_code, {"source": "test.py"})
    
    # We expect: standalone_func, MyClass, MyClass.method_one, MyClass.decorated_method
    # The actual order of traversal: standalone_func, MyClass, method_one, decorated_method
    assert len(chunks) == 4
    
    types = [c.metadata["node_type"] for c in chunks]
    names = [c.metadata["symbol_name"] for c in chunks]
    
    assert "function_definition" in types
    assert "class_definition" in types
    assert "decorated_definition" in types
    
    assert "standalone_func" in names
    assert "MyClass" in names
    assert "method_one" in names
    assert "decorated_method" in names

def test_semantic_chunker_script():
    chunker = SemanticChunker()
    source_code = "print('Hello World')\nx = 10"
    chunks = chunker.extract_chunks(source_code, {"source": "script.py"})
    
    # Needs to fallback to full text
    assert len(chunks) == 1
    assert chunks[0].metadata["node_type"] == "script"
    assert "print('Hello World')" in chunks[0].page_content
