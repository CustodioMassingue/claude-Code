# REQUISITOS DE CERTIFICAÇÃO AT E SAF-T(MZ)
## Manual Técnico de Conformidade Fiscal para Software de Faturação

---

## 1. CERTIFICAÇÃO DE SOFTWARE AT

### 1.1 Base Legal
- **Decreto n.º 65/2020, de 17 de Agosto** - Regulamento do Código do IVA
- **Diploma Ministerial n.º 271/2013, de 30 de Dezembro** - Requisitos técnicos do software
- **Circular n.º 02/GAT/2021** - Procedimentos de certificação

### 1.2 Requisitos Obrigatórios para Certificação

#### A. Características do Software
1. **Integridade dos Dados**
   - Impossibilidade de eliminação de documentos emitidos
   - Impossibilidade de alteração de documentos validados
   - Log de todas as operações realizadas

2. **Numeração Sequencial**
   - Sem falhas ou saltos na numeração
   - Formato: TIPO/SERIE/ANO/NUMERO
   - Exemplo: FT/A/2025/000001

3. **Hash de Validação**
   - Algoritmo: SHA-256
   - Incluir hash do documento anterior
   - Assinatura digital de cada documento

4. **QR Code Obrigatório**
   - Dados mínimos no QR Code:
     - NUIT do emitente
     - NUIT do destinatário
     - Número do documento
     - Data de emissão
     - Total sem IVA
     - Total de IVA
     - Total com IVA
     - Hash do documento

#### B. Tipos de Documentos Certificados
1. **Fatura** (FT)
2. **Fatura Simplificada** (FS)
3. **Fatura-Recibo** (FR)
4. **Nota de Crédito** (NC)
5. **Nota de Débito** (ND)
6. **Venda a Dinheiro** (VD)
7. **Guia de Remessa** (GR)
8. **Guia de Transporte** (GT)
9. **Recibo** (RC)
10. **Orçamento** (OR)
11. **Proforma** (PF)

### 1.3 Estrutura do Hash

```python
def gerar_hash_at(documento_anterior_hash, dados_documento):
    """
    Gera hash SHA-256 conforme requisitos AT Moçambique
    """
    # Concatenar dados
    string_hash = (
        f"{documento_anterior_hash};"
        f"{dados_documento['data_hora']};"
        f"{dados_documento['numero_documento']};"
        f"{dados_documento['total_sem_iva']};"
    )
    
    # Gerar hash SHA-256
    hash_objeto = hashlib.sha256(string_hash.encode())
    hash_hex = hash_objeto.hexdigest()
    
    return hash_hex
```

### 1.4 Formato do QR Code

```
AT*NUIT_EMITENTE*NUIT_CLIENTE*TIPO_DOC*NUMERO*DATA*TOTAL_SEM_IVA*TOTAL_IVA*TOTAL_COM_IVA*HASH
```

Exemplo:
```
AT*123456789*987654321*FT*A/2025/000001*2025-01-15*10000.00*1600.00*11600.00*a3b5c7d9e1f3...
```

### 1.5 Campos Obrigatórios em Documentos

#### Fatura Completa:
1. **Cabeçalho:**
   - Denominação do documento
   - Número sequencial
   - Data e hora de emissão
   - NUIT do fornecedor
   - Nome e endereço do fornecedor
   - NUIT do cliente (se > 100 MT)
   - Nome e endereço do cliente

2. **Linhas:**
   - Descrição dos bens/serviços
   - Quantidade
   - Unidade de medida
   - Preço unitário sem IVA
   - Taxa de IVA aplicável
   - Valor do IVA por linha
   - Total da linha com IVA

3. **Rodapé:**
   - Base tributável por taxa
   - Total IVA por taxa
   - Total sem IVA
   - Total de IVA
   - Total com IVA
   - Hash do documento
   - QR Code
   - "Processado por programa certificado n.º XXX/AT/2025"

---

## 2. SAF-T(MZ) - STANDARD AUDIT FILE FOR TAX

### 2.1 Estrutura do Ficheiro XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:MZ_1.01">
    <Header>...</Header>
    <MasterFiles>...</MasterFiles>
    <GeneralLedgerEntries>...</GeneralLedgerEntries>
    <SourceDocuments>...</SourceDocuments>
</AuditFile>
```

### 2.2 Secção Header

```xml
<Header>
    <AuditFileVersion>1.01_01</AuditFileVersion>
    <CompanyID>MZ123456789</CompanyID>
    <TaxRegistrationNumber>123456789</TaxRegistrationNumber>
    <TaxAccountingBasis>F</TaxAccountingBasis> <!-- F=Faturação, C=Caixa -->
    <CompanyName>Empresa Exemplo, Lda</CompanyName>
    <CompanyAddress>
        <AddressDetail>Av. 25 de Setembro, 1234</AddressDetail>
        <City>Maputo</City>
        <PostalCode>1100</PostalCode>
        <Province>Maputo</Province>
        <Country>MZ</Country>
    </CompanyAddress>
    <FiscalYear>2025</FiscalYear>
    <StartDate>2025-01-01</StartDate>
    <EndDate>2025-12-31</EndDate>
    <CurrencyCode>MZN</CurrencyCode>
    <DateCreated>2025-01-15</DateCreated>
    <TaxEntity>Sede</TaxEntity>
    <ProductCompanyTaxID>500123456</ProductCompanyTaxID>
    <SoftwareCertificateNumber>123/AT/2025</SoftwareCertificateNumber>
    <ProductID>OdooMZ</ProductID>
    <ProductVersion>18.0</ProductVersion>
</Header>
```

### 2.3 Secção MasterFiles

#### 2.3.1 GeneralLedgerAccounts
```xml
<GeneralLedgerAccounts>
    <Account>
        <AccountID>11101</AccountID>
        <AccountDescription>Caixa Principal</AccountDescription>
        <StandardAccountID>11</StandardAccountID>
        <GroupingCategory>GM</GroupingCategory>
        <GroupingCode>1</GroupingCode>
        <TaxonomyCode>1.1.1</TaxonomyCode>
        <OpeningDebitBalance>50000.00</OpeningDebitBalance>
        <OpeningCreditBalance>0.00</OpeningCreditBalance>
        <ClosingDebitBalance>75000.00</ClosingDebitBalance>
        <ClosingCreditBalance>0.00</ClosingCreditBalance>
    </Account>
</GeneralLedgerAccounts>
```

#### 2.3.2 Customer
```xml
<Customer>
    <CustomerID>C00001</CustomerID>
    <AccountID>31101</AccountID>
    <CustomerTaxID>987654321</CustomerTaxID>
    <CompanyName>Cliente Exemplo SA</CompanyName>
    <Contact>João Silva</Contact>
    <BillingAddress>
        <AddressDetail>Rua da Resistência, 456</AddressDetail>
        <City>Beira</City>
        <PostalCode>2100</PostalCode>
        <Province>Sofala</Province>
        <Country>MZ</Country>
    </BillingAddress>
    <Telephone>+258 84 123 4567</Telephone>
    <Email>cliente@exemplo.co.mz</Email>
    <Website>www.cliente.co.mz</Website>
    <SelfBillingIndicator>0</SelfBillingIndicator>
</Customer>
```

#### 2.3.3 Supplier
```xml
<Supplier>
    <SupplierID>F00001</SupplierID>
    <AccountID>32101</AccountID>
    <SupplierTaxID>456789123</SupplierTaxID>
    <CompanyName>Fornecedor Exemplo Lda</CompanyName>
    <Contact>Maria Santos</Contact>
    <BillingAddress>
        <AddressDetail>Av. Eduardo Mondlane, 789</AddressDetail>
        <City>Nampula</City>
        <PostalCode>3100</PostalCode>
        <Province>Nampula</Province>
        <Country>MZ</Country>
    </BillingAddress>
    <Telephone>+258 86 987 6543</Telephone>
    <Email>fornecedor@exemplo.co.mz</Email>
    <SelfBillingIndicator>0</SelfBillingIndicator>
</Supplier>
```

#### 2.3.4 Product
```xml
<Product>
    <ProductType>P</ProductType> <!-- P=Produto, S=Serviço -->
    <ProductCode>PROD001</ProductCode>
    <ProductGroup>Informática</ProductGroup>
    <ProductDescription>Computador Desktop</ProductDescription>
    <ProductNumberCode>84713000</ProductNumberCode> <!-- Código Pautal -->
    <CustomsDetails>
        <CNCode>84713000</CNCode>
        <UNNumber>UN</UNNumber>
    </CustomsDetails>
</Product>
```

#### 2.3.5 TaxTable
```xml
<TaxTableEntry>
    <TaxType>IVA</TaxType>
    <TaxCountryRegion>MZ</TaxCountryRegion>
    <TaxCode>IVA16</TaxCode>
    <Description>IVA Taxa Normal</Description>
    <TaxPercentage>16.00</TaxPercentage>
</TaxTableEntry>
```

### 2.4 Secção GeneralLedgerEntries

```xml
<GeneralLedgerEntries>
    <NumberOfEntries>1500</NumberOfEntries>
    <TotalDebit>5000000.00</TotalDebit>
    <TotalCredit>5000000.00</TotalCredit>
    <Journal>
        <JournalID>VD</JournalID>
        <Description>Vendas a Dinheiro</Description>
        <Transaction>
            <TransactionID>2025010001</TransactionID>
            <Period>01</Period>
            <TransactionDate>2025-01-15</TransactionDate>
            <SourceID>user001</SourceID>
            <Description>Venda a dinheiro</Description>
            <DocArchivalNumber>FT A/2025/000001</DocArchivalNumber>
            <TransactionType>N</TransactionType> <!-- N=Normal -->
            <Lines>
                <DebitLine>
                    <RecordID>1</RecordID>
                    <AccountID>11101</AccountID>
                    <SourceDocumentID>FT A/2025/000001</SourceDocumentID>
                    <SystemEntryDate>2025-01-15T10:30:00</SystemEntryDate>
                    <Description>Venda produtos informáticos</Description>
                    <DebitAmount>11600.00</DebitAmount>
                </DebitLine>
                <CreditLine>
                    <RecordID>2</RecordID>
                    <AccountID>71101</AccountID>
                    <SourceDocumentID>FT A/2025/000001</SourceDocumentID>
                    <SystemEntryDate>2025-01-15T10:30:00</SystemEntryDate>
                    <Description>Venda produtos informáticos</Description>
                    <CreditAmount>10000.00</CreditAmount>
                </CreditLine>
                <CreditLine>
                    <RecordID>3</RecordID>
                    <AccountID>34201</AccountID>
                    <SourceDocumentID>FT A/2025/000001</SourceDocumentID>
                    <SystemEntryDate>2025-01-15T10:30:00</SystemEntryDate>
                    <Description>IVA 16%</Description>
                    <CreditAmount>1600.00</CreditAmount>
                    <TaxInformation>
                        <TaxType>IVA</TaxType>
                        <TaxCode>IVA16</TaxCode>
                        <TaxPercentage>16</TaxPercentage>
                        <TaxAmount>1600.00</TaxAmount>
                    </TaxInformation>
                </CreditLine>
            </Lines>
        </Transaction>
    </Journal>
</GeneralLedgerEntries>
```

### 2.5 Secção SourceDocuments

#### 2.5.1 SalesInvoices
```xml
<SalesInvoices>
    <NumberOfEntries>500</NumberOfEntries>
    <TotalDebit>0.00</TotalDebit>
    <TotalCredit>2500000.00</TotalCredit>
    <Invoice>
        <InvoiceNo>FT A/2025/000001</InvoiceNo>
        <ATCUD>0</ATCUD>
        <DocumentStatus>
            <InvoiceStatus>N</InvoiceStatus> <!-- N=Normal, A=Anulado -->
            <InvoiceStatusDate>2025-01-15T10:30:00</InvoiceStatusDate>
            <SourceID>user001</SourceID>
            <SourceBilling>P</SourceBilling> <!-- P=Programa -->
        </DocumentStatus>
        <Hash>a3b5c7d9e1f3g5h7j9k1l3m5n7p9q1r3s5t7v9w1x3y5z7</Hash>
        <HashControl>1</HashControl>
        <Period>01</Period>
        <InvoiceDate>2025-01-15</InvoiceDate>
        <InvoiceType>FT</InvoiceType>
        <SpecialRegimes>
            <SelfBillingIndicator>0</SelfBillingIndicator>
            <CashVATSchemeIndicator>0</CashVATSchemeIndicator>
            <ThirdPartiesBillingIndicator>0</ThirdPartiesBillingIndicator>
        </SpecialRegimes>
        <SourceID>user001</SourceID>
        <SystemEntryDate>2025-01-15T10:30:00</SystemEntryDate>
        <CustomerID>C00001</CustomerID>
        <Line>
            <LineNumber>1</LineNumber>
            <ProductCode>PROD001</ProductCode>
            <ProductDescription>Computador Desktop</ProductDescription>
            <Quantity>2.00</Quantity>
            <UnitOfMeasure>UN</UnitOfMeasure>
            <UnitPrice>5000.00</UnitPrice>
            <TaxPointDate>2025-01-15</TaxPointDate>
            <Description>Computador Desktop HP</Description>
            <CreditAmount>10000.00</CreditAmount>
            <Tax>
                <TaxType>IVA</TaxType>
                <TaxCountryRegion>MZ</TaxCountryRegion>
                <TaxCode>IVA16</TaxCode>
                <TaxPercentage>16.00</TaxPercentage>
            </Tax>
            <SettlementAmount>0.00</SettlementAmount>
        </Line>
        <DocumentTotals>
            <TaxPayable>1600.00</TaxPayable>
            <NetTotal>10000.00</NetTotal>
            <GrossTotal>11600.00</GrossTotal>
            <Currency>
                <CurrencyCode>MZN</CurrencyCode>
                <CurrencyAmount>11600.00</CurrencyAmount>
            </Currency>
        </DocumentTotals>
    </Invoice>
</SalesInvoices>
```

#### 2.5.2 MovementOfGoods
```xml
<MovementOfGoods>
    <NumberOfMovementLines>200</NumberOfMovementLines>
    <TotalQuantityIssued>1500.00</TotalQuantityIssued>
    <StockMovement>
        <DocumentNumber>GR/2025/000001</DocumentNumber>
        <ATCUD>0</ATCUD>
        <DocumentStatus>
            <MovementStatus>N</MovementStatus>
            <MovementStatusDate>2025-01-15T09:00:00</MovementStatusDate>
            <SourceID>user001</SourceID>
            <SourceBilling>P</SourceBilling>
        </DocumentStatus>
        <Hash>b4c6d8e0f2g4h6j8k0l2m4n6p8q0r2s4t6v8w0x2y4z6</Hash>
        <HashControl>1</HashControl>
        <Period>01</Period>
        <MovementDate>2025-01-15</MovementDate>
        <MovementType>GR</MovementType>
        <SystemEntryDate>2025-01-15T09:00:00</SystemEntryDate>
        <CustomerID>C00001</CustomerID>
        <SupplierID></SupplierID>
        <SourceID>user001</SourceID>
        <MovementStartTime>2025-01-15T09:00:00</MovementStartTime>
        <Line>
            <LineNumber>1</LineNumber>
            <ProductCode>PROD001</ProductCode>
            <ProductDescription>Computador Desktop</ProductDescription>
            <Quantity>2.00</Quantity>
            <UnitOfMeasure>UN</UnitOfMeasure>
            <UnitPrice>5000.00</UnitPrice>
            <Description>Entrega ao cliente</Description>
            <CreditAmount>10000.00</CreditAmount>
        </Line>
        <DocumentTotals>
            <TaxPayable>1600.00</TaxPayable>
            <NetTotal>10000.00</NetTotal>
            <GrossTotal>11600.00</GrossTotal>
        </DocumentTotals>
    </StockMovement>
</MovementOfGoods>
```

#### 2.5.3 WorkingDocuments
```xml
<WorkingDocuments>
    <NumberOfEntries>50</NumberOfEntries>
    <TotalDebit>0.00</TotalDebit>
    <TotalCredit>150000.00</TotalCredit>
    <WorkDocument>
        <DocumentNumber>OR/2025/000001</DocumentNumber>
        <ATCUD>0</ATCUD>
        <DocumentStatus>
            <WorkStatus>N</WorkStatus>
            <WorkStatusDate>2025-01-14T15:00:00</WorkStatusDate>
            <SourceID>user001</SourceID>
            <SourceBilling>P</SourceBilling>
        </DocumentStatus>
        <Hash>c5d7e9f1g3h5j7k9l1m3n5p7q9r1s3t5v7w9x1y3z5</Hash>
        <HashControl>1</HashControl>
        <Period>01</Period>
        <WorkDate>2025-01-14</WorkDate>
        <WorkType>OR</WorkType>
        <SourceID>user001</SourceID>
        <SystemEntryDate>2025-01-14T15:00:00</SystemEntryDate>
        <CustomerID>C00001</CustomerID>
    </WorkDocument>
</WorkingDocuments>
```

#### 2.5.4 Payments
```xml
<Payments>
    <NumberOfEntries>450</NumberOfEntries>
    <TotalDebit>2400000.00</TotalDebit>
    <TotalCredit>0.00</TotalCredit>
    <Payment>
        <PaymentRefNo>RC/2025/000001</PaymentRefNo>
        <ATCUD>0</ATCUD>
        <Period>01</Period>
        <TransactionDate>2025-01-15</TransactionDate>
        <PaymentType>RC</PaymentType>
        <Description>Recebimento fatura FT A/2025/000001</Description>
        <SystemID>PAY001</SystemID>
        <DocumentStatus>
            <PaymentStatus>N</PaymentStatus>
            <PaymentStatusDate>2025-01-15T11:00:00</PaymentStatusDate>
            <SourceID>user001</SourceID>
            <SourcePayment>P</SourcePayment>
        </DocumentStatus>
        <PaymentMethod>
            <PaymentMechanism>NU</PaymentMechanism> <!-- NU=Numerário -->
            <PaymentAmount>11600.00</PaymentAmount>
            <PaymentDate>2025-01-15</PaymentDate>
        </PaymentMethod>
        <SourceID>user001</SourceID>
        <SystemEntryDate>2025-01-15T11:00:00</SystemEntryDate>
        <CustomerID>C00001</CustomerID>
        <Line>
            <LineNumber>1</LineNumber>
            <SourceDocumentID>
                <OriginatingON>FT A/2025/000001</OriginatingON>
                <InvoiceDate>2025-01-15</InvoiceDate>
            </SourceDocumentID>
            <SettlementAmount>0.00</SettlementAmount>
            <DebitAmount>11600.00</DebitAmount>
        </Line>
        <DocumentTotals>
            <TaxPayable>0.00</TaxPayable>
            <NetTotal>11600.00</NetTotal>
            <GrossTotal>11600.00</GrossTotal>
        </DocumentTotals>
    </Payment>
</Payments>
```

---

## 3. IMPLEMENTAÇÃO TÉCNICA NO ODOO 18

### 3.1 Modelo de Certificação

```python
class MozCertification(models.Model):
    _name = 'moz.certification'
    _description = 'Mozambique AT Certification'
    
    # Configuração de Certificação
    certificate_number = fields.Char(
        string='Certificate Number',
        required=True,
        help='AT Software Certificate Number (e.g., 123/AT/2025)'
    )
    
    hash_seed = fields.Char(
        string='Hash Seed',
        required=True,
        help='Initial hash seed for document chain'
    )
    
    last_hash = fields.Char(
        string='Last Document Hash',
        readonly=True,
        help='Hash of the last certified document'
    )
    
    def generate_document_hash(self, document_data):
        """Generate SHA-256 hash for document"""
        if not self.last_hash:
            self.last_hash = self.hash_seed
        
        hash_string = f"{self.last_hash};{document_data}"
        hash_bytes = hashlib.sha256(hash_string.encode('utf-8'))
        new_hash = hash_bytes.hexdigest()
        
        self.last_hash = new_hash
        return new_hash
    
    def generate_qr_code(self, invoice):
        """Generate QR code for certified document"""
        qr_data = (
            f"AT*{invoice.company_vat}*"
            f"{invoice.partner_vat or '999999999'}*"
            f"{invoice.document_type}*"
            f"{invoice.number}*"
            f"{invoice.date}*"
            f"{invoice.amount_untaxed}*"
            f"{invoice.amount_tax}*"
            f"{invoice.amount_total}*"
            f"{invoice.hash}"
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        
        return base64.b64encode(buffer.getvalue())
```

### 3.2 Validações de Integridade

```python
class MozInvoiceValidation(models.Model):
    _inherit = 'account.move'
    
    @api.constrains('state')
    def _check_document_integrity(self):
        """Ensure document cannot be modified after validation"""
        for move in self:
            if move.state == 'posted' and move.certified:
                # Check for any modification attempt
                if any(move._get_modified_fields()):
                    raise ValidationError(
                        "Documento certificado não pode ser alterado! "
                        "Emita uma nota de crédito para correções."
                    )
    
    @api.model
    def _check_sequence_integrity(self):
        """Verify no gaps in document numbering"""
        sequences = self.env['ir.sequence'].search([
            ('code', 'in', ['FT', 'FR', 'NC', 'ND', 'VD'])
        ])
        
        for seq in sequences:
            numbers = self.search([
                ('sequence_id', '=', seq.id)
            ]).mapped('number')
            
            # Extract numeric part and check for gaps
            numeric_parts = [int(n.split('/')[-1]) for n in numbers]
            numeric_parts.sort()
            
            for i in range(len(numeric_parts) - 1):
                if numeric_parts[i+1] - numeric_parts[i] != 1:
                    raise ValidationError(
                        f"Falha na sequência {seq.name}! "
                        f"Falta o número {numeric_parts[i] + 1}"
                    )
```

### 3.3 Exportação SAF-T

```python
class SaftExport(models.TransientModel):
    _name = 'saft.export.wizard'
    _description = 'SAF-T(MZ) Export Wizard'
    
    def generate_saft_xml(self):
        """Generate SAF-T(MZ) XML file"""
        root = ET.Element('AuditFile', 
                         xmlns="urn:OECD:StandardAuditFile-Tax:MZ_1.01")
        
        # Add Header
        header = self._generate_header()
        root.append(header)
        
        # Add MasterFiles
        master_files = self._generate_master_files()
        root.append(master_files)
        
        # Add GeneralLedgerEntries
        gl_entries = self._generate_gl_entries()
        root.append(gl_entries)
        
        # Add SourceDocuments
        source_docs = self._generate_source_documents()
        root.append(source_docs)
        
        # Generate XML string
        xml_string = ET.tostring(root, encoding='UTF-8', method='xml')
        
        # Pretty print
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent="  ")
        
        # Save to attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'SAF-T_MZ_{fields.Date.today()}.xml',
            'type': 'binary',
            'datas': base64.b64encode(pretty_xml.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/xml',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
```

---

## 4. PROCEDIMENTOS DE CERTIFICAÇÃO

### 4.1 Processo de Certificação AT

1. **Preparação da Documentação:**
   - Manual técnico do software
   - Declaração de conformidade
   - Casos de teste documentados
   - Comprovativo de pagamento da taxa

2. **Testes Obrigatórios:**
   - Teste de integridade de dados
   - Teste de numeração sequencial
   - Teste de geração de hash
   - Teste de QR code
   - Teste de exportação SAF-T

3. **Submissão à AT:**
   - Portal e-Tributação
   - Upload da documentação
   - Agendamento de demonstração

4. **Auditoria Técnica:**
   - Demonstração presencial ou remota
   - Verificação de requisitos
   - Testes de conformidade

5. **Certificação:**
   - Emissão do certificado
   - Atribuição do número de certificação
   - Validade: 2 anos
   - Renovação obrigatória

### 4.2 Manutenção da Certificação

1. **Actualizações Permitidas:**
   - Correções de bugs
   - Melhorias de interface
   - Novas funcionalidades não fiscais

2. **Actualizações que Requerem Nova Certificação:**
   - Alterações no cálculo de impostos
   - Mudanças na numeração
   - Modificações no hash
   - Alterações no QR code

3. **Obrigações Contínuas:**
   - Manter log de todas as operações
   - Backup diário dos dados
   - Impossibilitar acesso direto à base de dados
   - Garantir rastreabilidade de alterações

---

## 5. PENALIDADES POR NÃO CONFORMIDADE

### 5.1 Software Não Certificado
- **Multa:** 50% do valor das operações
- **Mínimo:** 50.000 MT
- **Máximo:** 500.000 MT
- **Suspensão:** Actividade comercial

### 5.2 Alteração de Documentos Certificados
- **Multa:** 100% do valor do documento
- **Processo Criminal:** Fraude fiscal
- **Responsabilidade:** Solidária (empresa e técnico)

### 5.3 Falhas na Numeração
- **Multa:** 5.000 MT por documento
- **Correcção:** Prazo de 5 dias úteis
- **Reincidência:** Cancelamento da certificação

### 5.4 Não Entrega de SAF-T
- **Multa:** 10.000 a 100.000 MT
- **Prazo adicional:** 5 dias úteis
- **Consequência:** Inspecção tributária

---

## 6. BOAS PRÁTICAS

### 6.1 Desenvolvimento
1. Usar controlo de versões (Git)
2. Documentar todas as alterações
3. Manter ambiente de testes
4. Realizar testes automáticos
5. Implementar logs detalhados

### 6.2 Segurança
1. Encriptação de dados sensíveis
2. Controlo de acesso por perfis
3. Autenticação de dois fatores
4. Backup automático diário
5. Plano de recuperação de desastres

### 6.3 Operacional
1. Formação contínua dos utilizadores
2. Manual de procedimentos actualizado
3. Suporte técnico disponível
4. Monitorização de erros
5. Actualizações regulares

---

## 7. CONTACTOS E RECURSOS

### Autoridade Tributária de Moçambique
- **Portal e-Tributação:** www.etributacao.gov.mz
- **Email Certificação:** certificacao@at.gov.mz
- **Telefone:** +258 21 344 200
- **WhatsApp Business:** +258 84 344 2000

### Documentação Técnica
- **Manual SAF-T(MZ):** www.at.gov.mz/saft
- **Requisitos Técnicos:** www.at.gov.mz/certificacao
- **FAQ:** www.at.gov.mz/perguntas-frequentes

### Ferramentas de Validação
- **Validador SAF-T:** www.at.gov.mz/validador
- **Teste de Hash:** www.at.gov.mz/hash-test
- **Verificador QR Code:** www.at.gov.mz/qr-verify

---

*Documento Técnico de Certificação AT e SAF-T(MZ)*
*Última Actualização: Janeiro 2025*
*Elaborado por: Contabilista Sénior Registado OCAM*