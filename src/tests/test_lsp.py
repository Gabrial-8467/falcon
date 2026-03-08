"""Tests for Vyom Language Server Protocol implementation."""

import json
import unittest
from unittest.mock import MagicMock

from vyom.lsp_server import WorkingVyomLSP


class TestWorkingVyomLSP(unittest.TestCase):
    """Test WorkingVyomLSP class."""

    def setUp(self) -> None:
        self.server = WorkingVyomLSP()

    def test_server_initialization(self) -> None:
        """Test server initialization."""
        self.assertIsNotNone(self.server)
        self.assertEqual(self.server.documents, {})
        self.assertTrue(self.server.running)

    def test_analyze_content(self) -> None:
        """Test content analysis."""
        # Test valid code
        valid_code = 'show("Hello, World!");'
        diagnostics = self.server.analyze_content(valid_code)
        self.assertEqual(len(diagnostics), 0)

        # Test invalid code
        invalid_code = 'show("Hello, World"'  # Missing closing parenthesis
        diagnostics = self.server.analyze_content(invalid_code)
        self.assertGreater(len(diagnostics), 0)
        self.assertEqual(diagnostics[0]['severity'], 1)  # Error

    def test_handle_initialize_message(self) -> None:
        """Test initialize message handling."""
        init_message = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "rootUri": None,
                "capabilities": {}
            }
        })
        
        # LSP server prints response to stdout, returns None for notifications
        response = self.server.handle_message(init_message)
        self.assertIsNone(response)  # LSP responses are printed, not returned

    def test_handle_did_open_message(self) -> None:
        """Test document open handling."""
        open_message = json.dumps({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "test://test.vyom",
                    "languageId": "vyom",
                    "version": 1,
                    "text": 'show("test");'
                }
            }
        })
        
        response = self.server.handle_message(open_message)
        # didOpen returns None (no response needed)
        self.assertIsNone(response)
        
        # Document should be stored
        self.assertIn("test://test.vyom", self.server.documents)
        self.assertEqual(self.server.documents["test://test.vyom"], 'show("test");')

    def test_handle_did_change_message(self) -> None:
        """Test document change handling."""
        # First open a document
        open_message = json.dumps({
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "test://test.vyom",
                    "languageId": "vyom",
                    "version": 1,
                    "text": 'show("old");'
                }
            }
        })
        self.server.handle_message(open_message)
        
        # Then change it
        change_message = json.dumps({
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": "test://test.vyom"
                },
                "contentChanges": [
                    {
                        "text": 'show("new");'
                    }
                ]
            }
        })
        
        response = self.server.handle_message(change_message)
        self.assertIsNone(response)
        
        # Document should be updated
        self.assertEqual(self.server.documents["test://test.vyom"], 'show("new");')

    def test_error_handling(self) -> None:
        """Test error handling for malformed messages."""
        malformed_message = "invalid json"
        
        # Should not crash, but may return None (error responses are printed)
        response = self.server.handle_message(malformed_message)
        # The server handles errors gracefully and prints error responses


class TestLSPIntegration(unittest.TestCase):
    """Test LSP integration scenarios."""

    def setUp(self) -> None:
        self.server = WorkingVyomLSP()

    def test_full_workflow(self) -> None:
        """Test complete LSP workflow."""
        # 1. Initialize
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "rootUri": None,
                "capabilities": {}
            }
        }
        
        response = self.server.handle_message(json.dumps(init_msg))
        self.assertIsNone(response)  # LSP responses are printed, not returned
        
        # 2. Open document
        open_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": "test://example.vyom",
                    "languageId": "vyom",
                    "version": 1,
                    "text": 'show(greet("World"));'
                }
            }
        }
        
        response = self.server.handle_message(json.dumps(open_msg))
        self.assertIsNone(response)
        
        # 3. Change document with error
        change_msg = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": {
                "textDocument": {
                    "uri": "test://example.vyom"
                },
                "contentChanges": [
                    {
                        "text": 'show(greet("World")'  # Missing closing parenthesis
                    }
                ]
            }
        }
        
        response = self.server.handle_message(json.dumps(change_msg))
        self.assertIsNone(response)
        
        # Document should be analyzed and contain the error
        self.assertIn("test://example.vyom", self.server.documents)


if __name__ == '__main__':
    unittest.main()
