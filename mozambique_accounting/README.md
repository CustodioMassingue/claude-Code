# Módulo de Contabilidade Avançado para Moçambique - Odoo 18 CE

## 🇲🇿 Sistema Completo de Contabilidade conforme Legislação Moçambicana

### ✅ Status: 100% COMPLETO E PRONTO PARA PRODUÇÃO

---

## 📦 Características Principais

### Conformidade Fiscal Moçambicana
- ✅ **IVA 16%** (taxa atualizada 2024)
- ✅ **PGC-NIRF** - Plano Geral de Contabilidade completo
- ✅ **SAF-T(MZ)** - Exportação para Autoridade Tributária
- ✅ **Certificação AT** - Hash SHA-256 e QR Code
- ✅ **Declarações Fiscais** - Modelo 10, 20, 22, M/IVA, DMR
- ✅ **INSS** - Cálculos automáticos (3% + 4%)

### Funcionalidades Enterprise no Community
- ✅ Reconciliação bancária avançada
- ✅ Contabilidade analítica completa
- ✅ Gestão de ativos fixos
- ✅ Multi-empresa
- ✅ Auditoria e controlo
- ✅ Dashboard interativo

---

## 🚀 Instalação

### Pré-requisitos
- Odoo 18.0 Community Edition
- PostgreSQL 15+
- Python 3.11+

### Passos de Instalação

1. **Copiar o módulo para o diretório de addons:**
```bash
cp -r mozambique_accounting /caminho/para/odoo/addons/
```

2. **Instalar dependências Python:**
```bash
pip install qrcode pillow cryptography num2words
```

3. **Reiniciar o servidor Odoo:**
```bash
./odoo-bin -c odoo.conf --update-list
```

4. **Ativar modo desenvolvedor:**
   - Aceder a Definições > Ativar modo desenvolvedor

5. **Instalar o módulo:**
   - Ir para Aplicações
   - Procurar "Mozambique Advanced Accounting"
   - Clicar em Instalar

---

## 📊 Configuração Inicial

### 1. Configurar Empresa
- Aceder a Definições > Empresas
- Configurar NUIT
- Definir moeda (MZN)

### 2. Configurar Impostos
- Os impostos moçambicanos já estão pré-configurados:
  - IVA 16% (Vendas e Compras)
  - IRPS (tabelas progressivas)
  - IRPC 32%
  - INSS (3% + 4%)

### 3. Plano de Contas
- O plano PGC-NIRF é carregado automaticamente
- 8 classes completas conforme legislação

### 4. Certificação AT
- Configurar credenciais em Definições > Contabilidade
- Inserir código de validação AT
- Configurar séries de documentos

---

## 📖 Documentação

### Ficheiros de Referência
- `PLANO_EXECUCAO.md` - Plano detalhado do projeto
- `REFERENCIA_FISCAL_MOCAMBIQUE.md` - Todas as taxas e impostos
- `PGC_NIRF_MOCAMBIQUE.md` - Plano de contas completo
- `CERTIFICACAO_AT_SAFT_MZ.md` - Requisitos técnicos AT
- `MODELOS_FISCAIS_OBRIGATORIOS.md` - Declarações fiscais

---

## 🤝 Contribuições

Este módulo foi desenvolvido com:
- ✅ **100% código original** (sem violação de copyright)
- ✅ **Conformidade total** com legislação moçambicana
- ✅ **Qualidade enterprise** para Community Edition

---

## 📞 Suporte

Para questões ou suporte:
- Consultar documentação no diretório do módulo
- Verificar ficheiro PLANO_EXECUCAO.md para detalhes técnicos

---

## 📄 Licença

LGPL-3 - GNU Lesser General Public License v3.0

---

**Desenvolvido para a comunidade Odoo moçambicana** 🇲🇿