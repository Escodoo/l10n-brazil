## Caixa de entrada

Acesse **Faturamento > Fiscal > Consultas DF-e > Third-party NFS-e**.

A listagem mostra as NFS-e em que a empresa é tomadora. O painel superior usa os campos `nfse_*` da empresa (último NSU, próxima consulta e ambiente).

Em cada documento:

1. **XML**: baixa o arquivo nacional recebido do ADN.
2. **Importar**: abre o assistente de importação com o XML completo. O assistente cria um `l10n_br_fiscal.document` do tipo `SE` (entrada), com o prestador como emitente e uma linha de serviço. O produto e a operação fiscal podem ser ajustados antes de confirmar. Se `l10n_br_account` estiver instalado, a confirmação existente do assistente gera a fatura de fornecedor.

A pesquisa específica aceita a chave de acesso de 50 dígitos ou um NSU. Não há manifestação do destinatário neste fluxo: a NFS-e nacional já chega com o XML da nota.
