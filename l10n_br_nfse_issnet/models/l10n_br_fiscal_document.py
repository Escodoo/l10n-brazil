# Copyright 2020 - TODAY, Marcel Savegnago - Escodoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from nfselib.issnet.v1_00.servico_enviar_lote_rps_envio import (
    EnviarLoteRpsEnvio,
)
from nfselib.issnet.v1_00.tipos_complexos import (
    TcCpfCnpj,
    TcDadosServico,
    TcDadosTomador,
    TcEndereco,
    TcIdentificacaoPrestador,
    TcIdentificacaoTomador,
    TcIdentificacaoRps,
    TcInfRps,
    TcLoteRps,
    TcRps,
    TcValores,
)

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.addons.l10n_br_fiscal.constants.fiscal import (
    EVENT_ENV_HML,
    EVENT_ENV_PROD,
    MODELO_FISCAL_NFSE,
    PROCESSADOR_OCA,
    SITUACAO_EDOC_AUTORIZADA,
    SITUACAO_EDOC_REJEITADA,
)

from ..constants.issnet import (
    RECEPCIONAR_LOTE_RPS,
    CONSULTAR_SITUACAO_LOTE_RPS,
)


def filter_processador_edoc_nfse(record):
    if (record.processador_edoc == PROCESSADOR_OCA and
            record.document_type_id.code in [
                MODELO_FISCAL_NFSE,
            ]):
        return True
    return False


def fiter_provedor_issnet(record):
    if record.company_id.provedor_nfse == 'issnet':
        return True
    return False


class Document(models.Model):

    _inherit = 'l10n_br_fiscal.document'

    def _serialize(self, edocs):
        edocs = super(Document, self)._serialize(edocs)
        for record in self.filtered(
                filter_processador_edoc_nfse).filtered(
                    fiter_provedor_issnet):
            edocs.append(record.serialize_nfse_issnet())
        return edocs

    def _serialize_issnet_dados_servico(self):
        # self.line_ids.ensure_one()
        dados = self._prepare_dados_servico()
        return TcDadosServico(
            valores=TcValores(
                valor_servicos=self.convert_type_nfselib(
                    TcValores, 'ValorServicos', dados['valor_servicos']),
                valor_deducoes=self.convert_type_nfselib(
                    TcValores, 'ValorDeducoes', dados['valor_deducoes']),
                valor_pis=self.convert_type_nfselib(
                    TcValores, 'ValorPis', dados['valor_pis']),
                valor_cofins=self.convert_type_nfselib(
                    TcValores, 'ValorCofins', dados['valor_cofins']),
                valor_inss=self.convert_type_nfselib(
                    TcValores, 'ValorInss', dados['valor_inss']),
                valor_ir=self.convert_type_nfselib(
                    TcValores, 'ValorIr', dados['valor_ir']),
                valor_csll=self.convert_type_nfselib(
                    TcValores, 'ValorCsll', dados['valor_csll']),
                iss_retido=self.convert_type_nfselib(
                    TcValores, 'IssRetido', dados['iss_retido']),
                valor_iss=self.convert_type_nfselib(
                    TcValores, 'ValorIss', dados['valor_iss']),
                valor_iss_retido=self.convert_type_nfselib(
                    TcValores, 'ValorIssRetido', dados['valor_iss_retido']),
                outras_retencoes=self.convert_type_nfselib(
                    TcValores, 'OutrasRetencoes', dados['outras_retencoes']),
                base_calculo=self.convert_type_nfselib(
                    TcValores, 'BaseCalculo', dados['base_calculo']),
                aliquota=self.convert_type_nfselib(
                    TcValores, 'Aliquota', str(float(dados['aliquota'])*100)),
                valor_liquido_nfse=self.convert_type_nfselib(
                    TcValores, 'ValorLiquidoNfse',
                    dados['valor_liquido_nfse']),
                desconto_incondicionado=self.convert_type_nfselib(
                    TcValores, 'DescontoIncondicionado',
                    dados['valor_desconto_incondicionado']),
                desconto_condicionado=0,
            ),
            item_lista_servico=self.convert_type_nfselib(
                TcDadosServico, 'ItemListaServico',
                dados['item_lista_servico']),
            codigo_cnae=self.convert_type_nfselib(
                TcDadosServico, 'CodigoCnae', dados['codigo_cnae']),
            codigo_tributacao_municipio=self.convert_type_nfselib(
                TcDadosServico, 'CodigoTributacaoMunicipio',
                dados['codigo_tributacao_municipio']),
            discriminacao=self.convert_type_nfselib(
                TcDadosServico, 'Discriminacao', dados['discriminacao']),
            municipio_prestacao_servico=self.convert_type_nfselib(
                TcDadosServico, 'MunicipioPrestacaoServico', dados['codigo_municipio'])
            if self.company_id.nfse_environment == '1'
            else 999,
        )

    def _serialize_issnet_dados_tomador(self):
        dados = self._prepare_dados_tomador()
        return TcDadosTomador(
            identificacao_tomador=TcIdentificacaoTomador(
                cpf_cnpj=TcCpfCnpj(
                    cnpj=self.convert_type_nfselib(
                        TcCpfCnpj, 'Cnpj', dados['cnpj']),
                    cpf=self.convert_type_nfselib(
                        TcCpfCnpj, 'Cpf', dados['cpf']),
                ),
                inscricao_municipal=self.convert_type_nfselib(
                    TcIdentificacaoTomador, 'InscricaoMunicipal',
                    dados['inscricao_municipal'])
                if dados['codigo_municipio'] == int('%s' % (
                    self.company_id.partner_id.city_id.ibge_code
                )) else None,
            ),
            razao_social=self.convert_type_nfselib(
                TcDadosTomador, 'RazaoSocial', dados['razao_social']),
            endereco=TcEndereco(
                endereco=self.convert_type_nfselib(
                    TcEndereco, 'Endereco', dados['endereco']),
                numero=self.convert_type_nfselib(
                    TcEndereco, 'Numero', dados['numero']),
                complemento=self.convert_type_nfselib(
                    TcEndereco, 'Complemento', dados['complemento']),
                bairro=self.convert_type_nfselib(
                    TcEndereco, 'Bairro', dados['bairro']),
                cidade=self.convert_type_nfselib(
                    TcEndereco, 'Cidade', dados['codigo_municipio']),
                estado=self.convert_type_nfselib(TcEndereco, 'Estado', dados['uf']),
                cep=self.convert_type_nfselib(TcEndereco, 'Cep', dados['cep']),
            ) or None,
        )

    def _serialize_issnet_rps(self, dados):

        return TcRps(
            inf_rps=TcInfRps(
                id=dados['id'],
                identificacao_rps=TcIdentificacaoRps(
                    numero=self.convert_type_nfselib(
                        TcIdentificacaoRps, 'Numero', dados['numero']),
                    serie=self.convert_type_nfselib(
                        TcIdentificacaoRps, 'Serie', dados['serie']),
                    tipo=self.convert_type_nfselib(
                        TcIdentificacaoRps, 'Tipo', dados['tipo']),
                ),
                data_emissao=self.convert_type_nfselib(
                    TcInfRps, 'DataEmissao', dados['data_emissao']),
                natureza_operacao=self.convert_type_nfselib(
                    TcInfRps, 'NaturezaOperacao', dados['natureza_operacao']),
                regime_especial_tributacao=self.convert_type_nfselib(
                    TcInfRps, 'RegimeEspecialTributacao',
                    dados['regime_especial_tributacao']),
                optante_simples_nacional=self.convert_type_nfselib(
                    TcInfRps, 'OptanteSimplesNacional',
                    dados['optante_simples_nacional']),
                incentivador_cultural=self.convert_type_nfselib(
                    TcInfRps, 'IncentivadorCultural',
                    dados['incentivador_cultural']),
                status=self.convert_type_nfselib(
                    TcInfRps, 'Status', dados['status']),
                rps_substituido=self.convert_type_nfselib(
                    TcInfRps, 'RpsSubstituido', dados['rps_substitiuido']),
                servico=self._serialize_issnet_dados_servico(),
                prestador=TcIdentificacaoPrestador(
                    cpf_cnpj=TcCpfCnpj(
                        cnpj=self.convert_type_nfselib(
                            TcCpfCnpj, 'Cnpj', dados['cnpj']),
                    ),
                    inscricao_municipal=self.convert_type_nfselib(
                        TcIdentificacaoPrestador, 'InscricaoMunicipal',
                        dados['inscricao_municipal']),
                ),
                tomador=self._serialize_issnet_dados_tomador(),
                intermediario_servico=self.convert_type_nfselib(
                    TcInfRps, 'IntermediarioServico',
                    dados['intermediario_servico']),
                construcao_civil=self.convert_type_nfselib(
                    TcInfRps, 'ConstrucaoCivil', dados['construcao_civil']),
            )
        )

    def _serialize_issnet_lote_rps(self):
        dados = self._prepare_lote_rps()
        return TcLoteRps(
            cpf_cnpj=TcCpfCnpj(
                cpnj=self.convert_type_nfselib(
                    TcCpfCnpj, 'Cnpj', dados['cnpj']),
            ),
            inscricao_municipal=self.convert_type_nfselib(
                TcLoteRps, 'InscricaoMunicipal', dados['inscricao_municipal']),
            quantidade_rps=1,
            lista_rps=TcLoteRps.ListaRps(
                rps=[self._serialize_issnet_rps(dados)]
            )
        )

    def serialize_nfse_issnet(self):
        lote_rps = EnviarLoteRpsEnvio(
            lote_rps=self._serialize_issnet_lote_rps()
        )
        return lote_rps

    def cancel_document_issnet(self):
        for record in self.filtered(filter_processador_edoc_nfse):
            processador = record._processador_erpbrasil_nfse()
            processo = processador.cancela_documento(doc_numero=int(
                record.document_number))

            status, message = \
                processador.analisa_retorno_cancelamento(processo)

            if not status:
                raise UserError(_(message))

            record.cancel_event_id = record.event_ids.create_event_save_xml(
                company_id=record.company_id,
                environment=(
                    EVENT_ENV_PROD if self.nfe_environment == '1' else EVENT_ENV_HML),
                event_type='2',
                xml_file=processo.envio_xml,
                document_id=record,
            )

            return status

    def _document_status(self):
        for record in self.filtered(filter_processador_edoc_nfse):
            processador = record._processador_erpbrasil_nfse()
            processo = processador.consulta_nfse_rps(
                rps_number=int(record.rps_number),
                rps_serie=record.document_serie,
                rps_type=int(record.rps_type)
            )

            consulta = processador.analisa_retorno_consulta(
                processo,
                record.document_number,
                record.company_cnpj_cpf,
                record.company_legal_name)

            if self.status_code == '2':
                if isinstance(consulta, tuple):
                    record.write({
                        'verify_code': consulta[1]['codigo_verificacao'],
                        'document_number': consulta[1]['numero'],
                        'authorization_date': consulta[1]['data_emissao'],
                        'status_code': 4,
                        'status_name': _('Successfully Processed'),
                    })
                    record._compute_status_description()
                    record.authorization_event_id.set_done(
                        status_code=4, response=_('Successfully Processed'),
                        protocol_date=consulta[1]['data_emissao'],
                        protocol_number=record.authorization_protocol,
                        file_response_xml=processo.retorno)
                    if record.state_edoc != 'autorizada':
                        record._change_state(SITUACAO_EDOC_AUTORIZADA)
                        record.make_pdf()

                    return _(consulta[0])
            return consulta

    @api.multi
    def _eletronic_document_send(self):
        super(Document, self)._eletronic_document_send()
        edoc_nfse = self.filtered(filter_processador_edoc_nfse)
        for record in edoc_nfse.filtered(fiter_provedor_issnet):
            processador = record._processador_erpbrasil_nfse()

            protocolo = record.authorization_protocol
            vals = dict()

            if not protocolo:
                for edoc in record.serialize():
                    processo = None
                    for p in processador.processar_documento(edoc):
                        processo = p

                        if processo.webservice in RECEPCIONAR_LOTE_RPS:
                            if processo.resposta.Protocolo is None:
                                mensagem_completa = ''
                                if processo.resposta.ListaMensagemRetorno:
                                    lista_msgs = processo.resposta.\
                                        ListaMensagemRetorno
                                    for mr in lista_msgs.MensagemRetorno:

                                        correcao = ''
                                        if mr.Correcao:
                                            correcao = mr.Correcao

                                        mensagem_completa += (
                                            mr.Codigo + ' - ' +
                                            mr.Mensagem +
                                            ' - Correção: ' +
                                            correcao + '\n'
                                        )
                                vals['edoc_error_message'] = \
                                    mensagem_completa
                                record._change_state(SITUACAO_EDOC_REJEITADA)
                                record.write(vals)
                                return
                            protocolo = processo.resposta.Protocolo

                    if processo.webservice in CONSULTAR_SITUACAO_LOTE_RPS:
                        if processo.resposta.Situacao is None:
                            mensagem_completa = ''
                            if processo.resposta.ListaMensagemRetorno:
                                lista_msgs = processo.resposta. \
                                    ListaMensagemRetorno
                                for mr in lista_msgs.MensagemRetorno:

                                    correcao = ''
                                    if mr.Correcao:
                                        correcao = mr.Correcao

                                    mensagem_completa += (
                                        mr.Codigo + ' - ' +
                                        mr.Mensagem +
                                        ' - Correção: ' +
                                        correcao + '\n'
                                    )
                            vals['edoc_error_message'] = \
                                mensagem_completa
                            record._change_state(SITUACAO_EDOC_REJEITADA)
                            record.write(vals)
                            return
                        else:
                            vals['status_code'] = \
                                processo.resposta.Situacao
            else:
                vals['status_code'] = 4

            if vals.get('status_code') == 1:
                vals['status_name'] = _('Not received')

            elif vals.get('status_code') == 2:
                vals['status_name'] = _('Batch not yet processed')

            elif vals.get('status_code') == 3:
                vals['status_name'] = _('Processed with Error')

            elif vals.get('status_code') == 4:
                vals['status_name'] = _('Successfully Processed')
                vals['authorization_protocol'] = protocolo

            if vals.get('status_code') in (3, 4):
                processo = processador.consultar_lote_rps(protocolo)

                if processo.resposta:
                    mensagem_completa = ''
                    if processo.resposta.ListaMensagemRetorno:
                        lista_msgs = processo.resposta.ListaMensagemRetorno
                        for mr in lista_msgs.MensagemRetorno:

                            correcao = ''
                            if mr.Correcao:
                                correcao = mr.Correcao

                            mensagem_completa += (
                                mr.Codigo + ' - ' +
                                mr.Mensagem +
                                ' - Correção: ' +
                                correcao + '\n'
                            )
                    vals['edoc_error_message'] = mensagem_completa
                    if vals.get('status_code') == 3:
                        record._change_state(SITUACAO_EDOC_REJEITADA)

                if processo.resposta.ListaNfse:
                    xml_file = processo.retorno
                    for comp in processo.resposta.ListaNfse.CompNfse:
                        vals['document_number'] = comp.Nfse.InfNfse.Numero
                        vals['authorization_date'] = \
                            comp.Nfse.InfNfse.DataEmissao
                        vals['verify_code'] = \
                            comp.Nfse.InfNfse.CodigoVerificacao
                    record.authorization_event_id.set_done(
                        status_code=vals['status_code'],
                        response=vals['status_name'],
                        protocol_date=vals['authorization_date'],
                        protocol_number=protocolo,
                        file_response_xml=xml_file,
                    )
                    record._change_state(SITUACAO_EDOC_AUTORIZADA)

            record.write(vals)
            if record.status_code == '4':
                record.make_pdf()
        return

    def _exec_before_SITUACAO_EDOC_CANCELADA(self, old_state, new_state):
        super(Document, self)._exec_before_SITUACAO_EDOC_CANCELADA(
            old_state, new_state)
        return self.cancel_document_issnet()
