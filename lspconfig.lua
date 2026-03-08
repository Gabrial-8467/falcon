require'lspconfig'.vyom_lsp.setup{
  cmd = {'vyom', 'lsp'},
  filetypes = {'vyom'},
  root_dir = lspconfig.util.root_pattern('.git', 'pyproject.toml'),
  settings = {}
}
