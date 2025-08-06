# PLANO DE EXECUÇÃO - MÓDULO CONTABILIDADE MOÇAMBICANA

## STATUS GERAL: 35% Concluído

## FASE 1: ESTRUTURA BASE (100% Concluído) ✅
- [x] Criação da estrutura de diretórios
- [x] Configuração do __manifest__.py
- [x] Estrutura inicial dos modelos

## FASE 2: MODELOS CORE DE CONTABILIDADE (100% Concluído) ✅

### 2.1 Plano de Contas (100% Concluído) ✅
- [x] moz_account.py - Modelo de contas contábeis
  - Estrutura hierárquica de contas
  - Classificação PGC-NIRF
  - Validações específicas de Moçambique
  - Integração com SAF-T

### 2.2 Diários Contábeis (100% Concluído) ✅
- [x] moz_journal.py - Modelo de diários
  - Tipos de diário (vendas, compras, banco, caixa, etc.)
  - Sequências automáticas
  - Configuração para certificação AT
  - Integração SAF-T

### 2.3 Movimentos Contábeis (100% Concluído) ✅
- [x] moz_move.py - Lançamentos contábeis
  - Estados do documento (rascunho, validado, publicado)
  - Validações de partidas dobradas
  - Integração com períodos fiscais
  - Hash SHA-256 para documentos certificados
  - Reversão de lançamentos
  - Integração com SAF-T

### 2.4 Linhas de Movimento (100% Concluído) ✅
- [x] moz_move_line.py - Linhas de lançamento
  - Débito/Crédito com precisão decimal
  - Reconciliação automática e manual
  - Análise por parceiro
  - Análise por centro de custo
  - Cálculo de saldos residuais
  - Aged partner balance

### 2.5 Períodos Fiscais (100% Concluído) ✅
- [x] moz_fiscal_year.py - Anos fiscais
  - Gestão de anos fiscais
  - Criação automática de períodos
  - Fechamento de ano
  - Exportação SAF-T
- [x] moz_fiscal_period.py - Períodos contábeis
  - Abertura/Fechamento de períodos
  - Controle de lançamentos por período
  - Declarações de IVA e IRPS
  - Validações de fechamento

## FASE 3: SISTEMA FISCAL (0% Concluído) ⏳

### 3.1 Impostos
- [ ] moz_tax.py - Modelo base de impostos
- [ ] moz_tax_group.py - Grupos de impostos
- [ ] moz_tax_report.py - Relatórios fiscais

### 3.2 Impostos Específicos de Moçambique
- [ ] moz_iva.py - IVA (16%)
- [ ] moz_irps.py - IRPS (tabelas progressivas)
- [ ] moz_irpc.py - IRPC (32%)
- [ ] moz_stamp_duty.py - Imposto de Selo
- [ ] moz_simplified_tax.py - ISPC

## FASE 4: FATURAÇÃO CERTIFICADA (0% Concluído) ⏳

### 4.1 Documentos Certificados
- [ ] moz_invoice.py - Faturas certificadas
- [ ] moz_invoice_line.py - Linhas de fatura
- [ ] moz_certification.py - Sistema de certificação AT

### 4.2 Sequências e Validação
- [ ] moz_sequence.py - Sequências certificadas
- [ ] moz_hash.py - Geração de hash AT
- [ ] moz_qrcode.py - Geração de QR Code

## FASE 5: RECONCILIAÇÃO E PAGAMENTOS (0% Concluído) ⏳

### 5.1 Reconciliação
- [ ] moz_reconciliation.py - Motor de reconciliação
- [ ] moz_reconciliation_model.py - Modelos de reconciliação

### 5.2 Pagamentos
- [ ] moz_payment.py - Pagamentos
- [ ] moz_payment_method.py - Métodos de pagamento
- [ ] moz_payment_term.py - Termos de pagamento

## FASE 6: RELATÓRIOS LEGAIS (0% Concluído) ⏳

### 6.1 Demonstrações Financeiras
- [ ] balance_sheet.py - Balanço
- [ ] profit_loss.py - Demonstração de Resultados
- [ ] cash_flow.py - Fluxo de Caixa

### 6.2 Relatórios Fiscais
- [ ] saft_mz.py - SAF-T (MZ)
- [ ] modelo_10.py - Modelo 10
- [ ] modelo_20.py - Modelo 20
- [ ] declaracao_periodica_iva.py

## FASE 7: ANÁLISE E GESTÃO (0% Concluído) ⏳

### 7.1 Contabilidade Analítica
- [ ] moz_analytic_account.py
- [ ] moz_analytic_line.py
- [ ] moz_cost_center.py

### 7.2 Orçamentos
- [ ] moz_budget.py
- [ ] moz_budget_line.py

## FASE 8: ATIVOS FIXOS (0% Concluído) ⏳
- [ ] moz_asset.py - Ativos fixos
- [ ] moz_asset_depreciation.py - Depreciações
- [ ] moz_asset_category.py - Categorias

## FASE 9: BANCO E TESOURARIA (0% Concluído) ⏳
- [ ] moz_bank_statement.py
- [ ] moz_bank_reconciliation.py
- [ ] moz_cash_register.py

## FASE 10: VISTAS E INTERFACE (0% Concluído) ⏳

### 10.1 Vistas XML
- [ ] account_views.xml
- [ ] journal_views.xml
- [ ] move_views.xml
- [ ] invoice_views.xml
- [ ] report_views.xml

### 10.2 Menus e Ações
- [ ] account_menu.xml
- [ ] account_actions.xml

### 10.3 Dashboard
- [ ] dashboard_views.xml
- [ ] dashboard.js

## FASE 11: SEGURANÇA (0% Concluído) ⏳
- [ ] ir.model.access.csv
- [ ] account_security.xml
- [ ] record_rules.xml

## FASE 12: DADOS INICIAIS (0% Concluído) ⏳
- [ ] chart_of_accounts_pgc_nirf.xml
- [ ] tax_codes.xml
- [ ] fiscal_positions.xml
- [ ] payment_terms.xml

## FASE 13: WIZARDS E FERRAMENTAS (0% Concluído) ⏳
- [ ] account_opening_wizard.py
- [ ] period_closing_wizard.py
- [ ] vat_report_wizard.py
- [ ] bank_reconciliation_wizard.py

## FASE 14: TESTES (0% Concluído) ⏳
- [ ] test_account.py
- [ ] test_move.py
- [ ] test_tax.py
- [ ] test_invoice.py
- [ ] test_reconciliation.py
- [ ] test_reports.py

## FASE 15: DOCUMENTAÇÃO (0% Concluído) ⏳
- [ ] README.md
- [ ] INSTALL.md
- [ ] USER_GUIDE.md
- [ ] API_DOCUMENTATION.md

## PRÓXIMAS TAREFAS IMEDIATAS

1. **Criar estrutura base para impostos** - Diretório fiscal/
2. **Implementar moz_tax.py** - Modelo base de impostos
3. **Implementar moz_iva.py** - IVA Moçambicano (16%)
4. **Implementar moz_irps.py** - IRPS com tabelas progressivas
5. **Implementar moz_irpc.py** - IRPC (32%)
6. **Criar modelos de reconciliação** - Para reconciliação de contas
7. **Criar testes unitários** para modelos implementados

## NOTAS TÉCNICAS

### Princípios de Desenvolvimento:
- Código 100% original, sem cópia do Enterprise
- Nomenclatura própria com prefixo "moz_"
- Conformidade com PGC-NIRF e legislação moçambicana
- Type hints em todas as funções
- Docstrings completas
- Tratamento robusto de erros
- Logging adequado

### Padrões de Qualidade:
- PEP-8 compliance
- Odoo coding guidelines
- Testes com cobertura > 80%
- Documentação inline
- Validações de negócio

### Integração com AT (Autoridade Tributária):
- Hash SHA-256 para documentos
- QR Code obrigatório
- Sequências sem falhas
- Comunicação em tempo real (futuro)

## DEPENDÊNCIAS EXTERNAS
- python3-dev
- postgresql
- wkhtmltopdf
- python-dateutil
- python-cryptography
- python-qrcode
- python-xlsxwriter

## ESTIMATIVA DE TEMPO
- Desenvolvimento Core: 2-3 semanas
- Testes e Validação: 1 semana
- Documentação: 3 dias
- **Total Estimado: 4 semanas**

---
*Última Atualização: 2025-08-06*