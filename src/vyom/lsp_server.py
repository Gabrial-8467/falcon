#!/usr/bin/env python3
"""Working Vyom LSP server for VS Code."""

import sys
import os
import json
import re
import threading
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vyom.lexer import Lexer
from vyom.parser import Parser
from vyom import type_checker

class WorkingVyomLSP:
    def __init__(self):
        self.documents = {}
        self.running = True
        
    def analyze_content(self, content):
        """Analyze Vyom content and return diagnostics."""
        diagnostics = []
        
        try:
            # Tokenize
            lex = Lexer(content)
            tokens = lex.lex()
            
            # Parse
            parser_instance = Parser(tokens)
            ast = parser_instance.parse()
            
            # Type check
            if ast and hasattr(ast, 'body'):
                checker = type_checker.TypeChecker()
                checker.check(ast)
                
        except Exception as e:
            # Extract line/column from error message
            error_msg = str(e)
            line_match = re.search(r'line (\d+)', error_msg)
            col_match = re.search(r'column (\d+)', error_msg)
            
            line = int(line_match.group(1)) - 1 if line_match else 0
            col = int(col_match.group(1)) - 1 if col_match else 0
            
            diagnostics.append({
                "range": {
                    "start": {"line": line, "character": col},
                    "end": {"line": line, "character": col + 10}
                },
                "message": error_msg,
                "severity": 1,  # Error
                "source": "vyom"
            })
        
        return diagnostics
    
    def send_response(self, response):
        """Send LSP response."""
        content = json.dumps(response)
        print(f"Content-Length: {len(content)}\r\n\r\n{content}", end="", flush=True)
    
    def handle_message(self, message):
        """Handle LSP message."""
        try:
            data = json.loads(message)
            method = data.get("method")
            params = data.get("params", {})
            msg_id = data.get("id")
            
            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "capabilities": {
                            "textDocumentSync": {
                                "openClose": True,
                                "change": 2,
                                "save": True
                            },
                            "completionProvider": {
                                "resolveProvider": False,
                                "triggerCharacters": [".", ":", " ", "\n"]
                            },
                            "hoverProvider": True,
                            "semanticTokensProvider": {
                                "legend": {
                                    "tokenTypes": [
                                        "keyword", "function", "variable", "string", "number", 
                                        "comment", "operator", "type", "class", "interface"
                                    ],
                                    "tokenModifiers": ["declaration", "definition", "readonly", "static"]
                                },
                                "full": True
                            }
                        }
                    }
                }
                self.send_response(response)
                
            elif method == "textDocument/didOpen":
                uri = params["textDocument"]["uri"]
                content = params["textDocument"]["text"]
                self.documents[uri] = content
                
                # Analyze and send diagnostics
                diagnostics = self.analyze_content(content)
                self.send_diagnostics(uri, diagnostics)
                
            elif method == "textDocument/didChange":
                uri = params["textDocument"]["uri"]
                for change in params["contentChanges"]:
                    if "text" in change:
                        self.documents[uri] = change["text"]
                
                # Analyze and send diagnostics
                content = self.documents[uri]
                diagnostics = self.analyze_content(content)
                self.send_diagnostics(uri, diagnostics)
                
            elif method == "textDocument/semanticTokens/full":
                return self._handle_semantic_tokens(msg, params)
                
            elif method == "shutdown":
                self.running = False
                if msg_id:
                    response = {"jsonrpc": "2.0", "id": msg_id, "result": None}
                    self.send_response(response)
                    
        except Exception as e:
            print(f"Error handling message: {e}", file=sys.stderr)
    
    def send_diagnostics(self, uri, diagnostics):
        """Send diagnostics notification."""
        notification = {
            "jsonrpc": "2.0",
            "method": "textDocument/publishDiagnostics",
            "params": {
                "uri": uri,
                "diagnostics": diagnostics
            }
        }
        self.send_response(notification)
    
    def _handle_semantic_tokens(self, msg, params):
        """Handle semantic tokens request."""
        uri = params["textDocument"]["uri"]
        content = self.documents.get(uri, "")
        
        tokens = self._get_semantic_tokens(content)
        
        response = {
            "jsonrpc": "2.0",
            "id": msg.id,
            "result": {
                "data": tokens
            }
        }
        return json.dumps(response)
    
    def _get_semantic_tokens(self, content):
        """Get semantic tokens for content."""
        tokens = []
        lines = content.split('\n')
        
        # Vyom keywords
        keywords = {
            'fn', 'give', 'if', 'else', 'while', 'for', 'loop', 'break',
            'match', 'case', 'when', 'const', 'var', 'show', 'true', 'false', 'null'
        }
        
        # Type keywords
        types = {'int', 'string', 'bool', 'list', 'dict', 'set', 'array'}
        
        for line_num, line in enumerate(lines):
            words = line.split()
            char_pos = 0
            
            for word in words:
                # Find actual position in line
                word_start = line.find(word, char_pos)
                if word_start == -1:
                    continue
                    
                word_end = word_start + len(word)
                char_pos = word_end
                
                # Determine token type
                token_type = None
                
                if word in keywords:
                    token_type = 0  # keyword
                elif word in types:
                    token_type = 7  # type
                elif word.startswith('//'):
                    token_type = 5  # comment
                elif word.startswith('"') and word.endswith('"'):
                    token_type = 3  # string
                elif word.replace('.', '').replace('-', '').isdigit():
                    token_type = 4  # number
                elif word == '(' or word == ')' or word == '{' or word == '}' or word == '[' or word == ']':
                    token_type = 6  # operator
                elif word == '+' or word == '-' or word == '*' or word == '/' or word == '=':
                    token_type = 6  # operator
                elif word == '==' or word == '!=' or word == '<=' or word == '>=':
                    token_type = 6  # operator
                
                if token_type is not None:
                    # LSP semantic token format: [line, char, length, tokenType, modifiers]
                    tokens.extend([
                        line_num,        # line number (0-based)
                        word_start,      # character start
                        len(word),       # length
                        token_type,      # token type
                        0                # modifiers
                    ])
        
        return tokens
    
    def run(self):
        """Run the LSP server."""
        try:
            while self.running:
                # Read Content-Length header
                line = sys.stdin.readline()
                if not line:
                    break
                
                if line.startswith("Content-Length:"):
                    content_length = int(line.split(":")[1].strip())
                    
                    # Read empty line
                    sys.stdin.readline()
                    
                    # Read message content
                    content = sys.stdin.read(content_length)
                    
                    # Handle message
                    self.handle_message(content)
                    
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Server error: {e}", file=sys.stderr)

if __name__ == "__main__":
    server = WorkingVyomLSP()
    server.run()
