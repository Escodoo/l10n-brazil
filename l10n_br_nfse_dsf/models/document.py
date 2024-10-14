# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unicodedata import normalize

# Envio Lote RPS
from nfselib.dsf.bindings.req_envio_lote_rps import ReqEnvioLoteRps

# Tipos
from nfselib.dsf.bindings.tipos import TpDeducoes, TpItens, TpLote, TpRps

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_CANCELADA,
    SITUACAO_EDOC_REJEITADA,
)
from odoo.addons.l10n_br_nfse.models.document import filter_processador_edoc_nfse

from ..constants.dsf import CONSULTAR_SITUACAO_LOTE_RPS


def filter_dsf(record):
    """Filter records to only include those using the 'DSF' provider."""
    return record.company_id.provedor_nfse == "dsf"


class Document(models.Model):
    _inherit = "l10n_br_fiscal.document"

    def _serialize(self, edocs):
        """Serialize electronic documents for 'dsf' provider NFSe."""
        edocs = super()._serialize(edocs)
        nfse_records = self.filtered(filter_processador_edoc_nfse).filtered(filter_dsf)
        for record in nfse_records:
            edocs.append(record._serialize_nfse_dsf())
        return edocs

    def _prepare_itens(self, itens):
        """Prepare items for NFSe serialization."""
        for line in self.fiscal_line_ids:
            itens.append(
                TpItens(
                    DiscriminacaoServico=normalize(
                        "NFKD", str(line.name[:120] or "")
                    ).encode("ASCII", "ignore"),
                    Quantidade=line.quantity,
                    ValorUnitario=f"{line.price_unit:.2f}",
                    ValorTotal=f"{line.price_gross:.2f}",
                    Tributavel=None,
                )
            )

    def _prepare_deducoes(self, deducoes):
        """Prepare deductions for NFSe serialization."""
        return TpDeducoes(
            DeducaoPor=None,
            TipoDeducao=None,
            CPFCNPJReferencia=None,
            NumeroNFReferencia=None,
            ValorTotalReferencia=None,
            PercentualDeduzir=None,
            ValorDeduzir=None,
        )

    def _serialize_nfse_dsf(self):
        """Serialize NFSe using 'dsf' specific configuration."""
        lista_rps = []
        itens, deducoes = [], []

        dict_servico = self._prepare_dados_servico()
        dict_tomador = self._prepare_dados_tomador()
        dict_rps = self._prepare_lote_rps()

        self._prepare_itens(itens)
        self._prepare_deducoes(deducoes)

        lista_rps.append(
            TpRps(
                Id=dict_rps["id"],
                Assinatura=None,
                InscricaoMunicipalPrestador=dict_tomador["inscricao_municipal"] or None,
                RazaoSocialPrestador=(dict_tomador["razao_social"] or "")[:120],
                TipoRPS="RPS",
                SerieRPS="NF",
                NumeroRPS=dict_rps["numero"],
                DataEmissaoRPS=dict_rps["data_emissao"],
                SituacaoRPS="N",  # "N"-Normal, "C"-Cancelada
                SeriePrestacao=99,
                InscricaoMunicipalTomador=dict_tomador["inscricao_municipal"],
                CPFCNPJTomador=dict_tomador["cnpj"] or dict_tomador["cpf"] or None,
                RazaoSocialTomador=dict_tomador.get("razao_social"),
                LogradouroTomador=dict_tomador.get("endereco"),
                NumeroEnderecoTomador=dict_tomador.get("numero"),
                ComplementoEnderecoTomador=dict_tomador.get("complemento"),
                TipoBairroTomador="Bairro",
                BairroTomador=dict_tomador.get("bairro"),
                CidadeTomador=dict_tomador["codigo_municipio"],
                CidadeTomadorDescricao=dict_tomador["codigo_municipio"],
                CEPTomador=dict_tomador["cep"],
                EmailTomador=dict_tomador["email"],
                CodigoAtividade="412040000",
                AliquotaAtividade=5.00,
                TipoRecolhimento="A",
                MunicipioPrestacao="0006291",
                MunicipioPrestacaoDescricao="CAMPINAS",
                Operacao="A",
                Tributacao="T",
                ValorPIS=f"{dict_servico['valor_pis']:.2f}",
                ValorCOFINS=f"{dict_servico['valor_cofins']:.2f}",
                DescricaoRPS="Descricao do RPS",
                Deducoes=deducoes,
                Itens=itens,
            )
        )

        return ReqEnvioLoteRps(
            Cabecalho=ReqEnvioLoteRps.Cabecalho(
                CodCidade=int(self.company_id.partner_id.city_id.ibge_code),
                transacao=True,
            ),
            Lote=TpLote(RPS=lista_rps),
        )

    def cancel_document_dfs(self):
        """Cancel NFSe document using 'dsf' provider."""
        for record in self.filtered(filter_processador_edoc_nfse).filtered(filter_dsf):
            processador = record._processador_erpbrasil_nfse()
            processo = processador.cancela_documento(record.document_number)
            resposta = processo.resposta

            if resposta.lista_mensagem_retorno:
                formatted_messages = [
                    f"Code: {msg.codigo} Message: {msg.mensagem} Correction: {msg.correcao}"
                    for msg_lista in resposta.lista_mensagem_retorno
                    for msg in msg_lista.mensagem_retorno
                ]
                all_msg = _(
                    f"It was not possible to cancel the NFS-e {record.document_number} \n"
                ) + "\n".join(formatted_messages)
                raise UserError(all_msg)

            record.cancel_event_id = record.event_ids.create_event_save_xml(
                company_id=record.company_id,
                environment=(
                    EVENT_ENV_PROD if self.nfse_environment == "1" else EVENT_ENV_HML
                ),
                event_type="2",
                xml_file=processo.envio_xml,
                document_id=record,
            )
            record.state_edoc = SITUACAO_EDOC_CANCELADA
            record.cancel_event_id.set_done(file_response_xml=processo.retorno)

    def _document_status(self):
        """Check and update the status of the NFSe document."""
        status = super()._document_status()
        for doc in self.filtered(filter_processador_edoc_nfse).filtered(filter_dsf):
            processador = doc._processador_erpbrasil_nfse()
            processo = processador.consulta_nfse_rps(
                rps_number=doc.rps_number,
                rps_serie=doc.document_serie,
                rps_type=doc.rps_type,
            )
            if doc.state_edoc != SITUACAO_EDOC_AUTORIZADA:
                doc._save_nfse_data(processo.resposta.compl_nfse, processo.retorno)
            status = _("Normal Status")
        return status

    def _eletronic_document_send(self):
        """Send electronic document to NFSe 'dsf' provider."""
        super()._eletronic_document_send()
        for record in self.filtered(filter_processador_edoc_nfse).filtered(filter_dsf):
            processador = record._processador_erpbrasil_nfse()
            vals = {}
            for edoc in record.serialize():
                processo = None
                for p in processador.processar_documento(edoc):
                    processo = p

                    if processo.webservice in CONSULTAR_SITUACAO_LOTE_RPS:
                        if processo.resposta.lista_mensagem_retorno:
                            mensagens = [
                                f"{mr.codigo} - {mr.mensagem} - Correção: {mr.correcao or ''}"
                                for mr in processo.resposta.lista_mensagem_retorno.mensagem_retorno
                            ]
                            vals["edoc_error_message"] = "\n".join(mensagens)
                            record._change_state(SITUACAO_EDOC_REJEITADA)

                        if processo.resposta.lista_nfse.compl_nfse:
                            record._save_nfse_data(
                                processo.resposta.lista_nfse.compl_nfse[0],
                                processo.retorno,
                            )
            record.write(vals)

    def _save_nfse_data(self, compl_nfse, xml_file):
        """Save NFSe data after successful emission."""
        self.ensure_one()
        self.document_number = compl_nfse.nfse.inf_nfse.numero
        self.authorization_date = (
            compl_nfse.nfse.inf_nfse.data_emissao.to_datetime().replace(tzinfo=None)
        )
        self.verify_code = compl_nfse.nfse.inf_nfse.codigo_verificacao
        self.nfse_preview_link = compl_nfse.nfse.inf_nfse.outras_informacoes
        self.authorization_event_id.set_done(
            response="NFS-e issued successfully.",
            file_response_xml=xml_file,
        )
        self._change_state(SITUACAO_EDOC_AUTORIZADA)

    def _exec_before_SITUACAO_EDOC_CANCELADA(self, old_state, new_state):
        """Perform actions before changing the state to 'Canceled'."""
        super()._exec_before_SITUACAO_EDOC_CANCELADA(old_state, new_state)
        return self.cancel_document_dfs()
