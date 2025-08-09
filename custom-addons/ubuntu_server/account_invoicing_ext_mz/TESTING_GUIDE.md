# Balance Sheet Testing Guide

## Correções Aplicadas

### 1. JavaScript (balance_sheet.js)
- ✅ Corrigido o binding do contexto `this` em todos os métodos
- ✅ Removido import desnecessário (`loadJS`)
- ✅ Ajustado gerenciamento de estado para forçar re-render
- ✅ Corrigido tratamento de valores `undefined` e `null`

### 2. Template XML (balance_sheet.xml)
- ✅ Corrigida sintaxe do event handler `t-on-click`
- ✅ Removidos dropdowns complexos que causavam erros
- ✅ Simplificado controles para evitar conflitos com Bootstrap
- ✅ Adicionado `.stop` no click do botão expandir para evitar propagação

### 3. Estrutura do Módulo
- ✅ Modelo mudado para `TransientModel` (sem tabela no banco)
- ✅ Assets configurados corretamente no `__manifest__.py`
- ✅ Removido arquivo problemático `balance_sheet_assets.xml`

## Como Testar

### 1. Limpar Cache do Navegador
```
Ctrl + F5 (Windows/Linux)
Cmd + Shift + R (Mac)
```
Ou abra em modo incógnito/privado

### 2. Acessar o Balance Sheet
1. Login: http://localhost:8069
   - Usuário: `admin`
   - Senha: `admin`
2. Navegue para: **Accounting > Reporting > Statement Reports > Balance Sheet**

### 3. Funcionalidades para Testar

#### ✅ Expandir/Colapsar Seções
- Clique nos ícones ▶ / ▼ ao lado de:
  - ASSETS
  - Current Assets
  - LIABILITIES
  - Current Liabilities
  - EQUITY
  - Unallocated Earnings

#### ✅ Filtros de Data
- Use o campo de data para selecionar diferentes períodos

#### ✅ Botões de Exportação
- **PDF**: Deve abrir nova aba com o PDF
- **XLSX**: Deve baixar arquivo Excel

#### ✅ Toggles
- **Comparison**: Ativa modo comparação (se houver dados)
- **Analytic**: Filtro analítico (placeholder)
- **Posted Entries**: Filtra apenas lançamentos postados

## Verificação no Console do Navegador

Abra o console (F12) e verifique:

### Não deve haver erros como:
- ❌ "Cannot read properties of undefined"
- ❌ "Failed to execute 'getComputedStyle'"
- ❌ "TypeError: Cannot read properties of undefined (reading 'state')"

### Comandos úteis no console:
```javascript
// Verificar se o componente está carregado
console.log(window.odoo);

// Ver estado atual (se disponível)
document.querySelector('.o_balance_sheet_report').__owl__.component.state;
```

## Solução de Problemas

### Se ainda houver erros:

1. **Reiniciar o servidor Odoo:**
```bash
docker restart claude-code-odoo-1
```

2. **Forçar atualização do módulo:**
```bash
docker exec claude-code-odoo-1 sh -c "odoo -d teste --db_host=postgres --db_user=odoo --db_password=odoo -u account_invoicing_ext_mz --stop-after-init"
```

3. **Verificar logs:**
```bash
docker logs claude-code-odoo-1 --tail 50
```

## Status Atual

✅ **Módulo instalado e atualizado sem erros**
✅ **JavaScript corrigido com binding adequado**
✅ **Template XML com sintaxe OWL correta**
✅ **Estrutura de dados funcionando**

## Próximos Passos

Se tudo estiver funcionando:
1. Adicionar dados reais de contas
2. Implementar filtro de diários
3. Adicionar mais opções de comparação
4. Melhorar estilos visuais

## Reportar Problemas

Se encontrar algum erro:
1. Copie a mensagem de erro do console
2. Note qual ação causou o erro
3. Verifique os logs do servidor