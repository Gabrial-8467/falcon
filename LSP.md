# Vyom Language Server Protocol (LSP)

The Vyom language includes a built-in Language Server Protocol implementation that provides rich IDE features for Vyom development.

## Features

- **Text Synchronization**: Real-time document synchronization
- **Auto-completion**: Intelligent code completion for keywords, functions, and types
- **Hover Information**: Documentation on hover for keywords and built-in functions
- **Error Diagnostics**: Real-time syntax and type checking with error highlighting
- **Go to Definition**: Navigate to symbol definitions (planned)
- **Document Symbols**: Outline view of document structure (planned)

## Installation

The LSP server is included with the Vyom installation:

```bash
pip install -e .
```

## Usage

### Command Line

Start the LSP server directly:

```bash
vyom lsp
```

Or use the standalone script:

```bash
vyom-lsp
```

### Editor Configuration

#### Visual Studio Code

Add to your `settings.json`:

```json
{
  "languageserver": {
    "vyom": {
      "command": "vyom",
      "args": ["lsp"],
      "filetypes": ["vyom"],
      "rootPatterns": [".git", "pyproject.toml"]
    }
  }
}
```

#### Neovim (with nvim-lspconfig)

```lua
require'lspconfig'.vyom_lsp.setup{
  cmd = {'vyom', 'lsp'},
  filetypes = {'vyom'},
  root_dir = lspconfig.util.root_pattern('.git', 'pyproject.toml'),
}
```

#### Vim (with coc.nvim)

Add to `coc-settings.json`:

```json
{
  "client": {
    "vyom-lsp": {
      "command": ["vyom", "lsp"],
      "filetypes": ["vyom"],
      "root": "."
    }
  }
}
```

#### Emacs (with lsp-mode)

```elisp
(lsp-register-client
  (make-lsp-client :new-connection (lsp-stdio-connection '("vyom" "lsp"))
                   :major-modes '(vyom-mode)
                   :server-id 'vyom-lsp))
```

## Supported Features

### Auto-completion

The LSP server provides completions for:

- **Keywords**: `fn`, `give`, `if`, `else`, `while`, `for`, `match`, `case`, `const`, `set`, `var`, etc.
- **Built-in Functions**: `len`, `type`, `show`, `str`, `int`, `bool`, etc.
- **Types**: `int`, `string`, `bool`, `list`, `dict`, `set`, `array`, `any`

### Hover Information

Hover over any keyword or built-in function to see:

- Documentation
- Usage examples
- Type information

### Error Diagnostics

Real-time error checking for:

- **Syntax Errors**: Invalid token sequences, malformed expressions
- **Parse Errors**: Grammar violations, unexpected tokens
- **Type Errors**: Type mismatches, invalid operations
- **Runtime Errors**: Division by zero, undefined variables

### Example

```vyom
fn calculate(x: int, y: int): int {
    // Hover over 'fn' to see function documentation
    // Auto-completion available for 'give', 'if', etc.
    give x + y;
}

set result = calculate(5, 3);  // Type checking ensures integers
show(result);                  // Built-in function documentation on hover
```

## Architecture

The LSP server is built on top of:

- **pygls**: Python Language Server implementation
- **lsprotocol**: LSP protocol types
- **Vyom Parser**: Existing lexer and parser for syntax analysis
- **Type Checker**: Runtime type checking integration

### Components

1. **VyomLanguageServer**: Main LSP server class
2. **VyomDocument**: Document management and change tracking
3. **Diagnostics**: Error detection and reporting
4. **Completion**: Intelligent code completion
5. **Hover**: Documentation and information display

## Development

### Running Tests

```bash
python -m pytest src/tests/test_lsp.py -v
```

### Debugging

Enable debug logging:

```bash
VYOM_LSP_DEBUG=1 vyom lsp
```

### Extending

The LSP server can be extended by:

1. Adding new completion providers
2. Implementing additional LSP methods (goto definition, references, etc.)
3. Enhancing diagnostic capabilities
4. Adding workspace-level features

## Troubleshooting

### Common Issues

1. **Server not starting**: Check that Vyom is properly installed
2. **No diagnostics**: Ensure file has `.vyom` extension
3. **Slow response**: Large files may take time to parse
4. **Missing features**: Some LSP features are still in development

### Logging

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Plans

- [ ] Go to Definition
- [ ] Find References
- [ ] Document Symbols
- [ ] Workspace Symbols
- [ ] Code Formatting
- [ ] Refactoring support
- [ ] Semantic Highlighting
- [ ] Inlay Hints

## Contributing

Contributions to the LSP server are welcome! Please:

1. Run existing tests before submitting
2. Add tests for new features
3. Follow the existing code style
4. Update documentation for new capabilities

## License

The LSP server is licensed under the same MIT license as Vyom.
