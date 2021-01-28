# Copyright 2020 - TODAY Escodoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.spec_driven_model.models import spec_models


class NFeHotfix(spec_models.StackedModel):
    _name = 'l10n_br_fiscal.document'
    _inherit = ["l10n_br_fiscal.document", "nfe.40.infnfe"]
    _stacked = 'nfe.40.infnfe'
    _stack_skip = ('nfe40_veicTransp')
    _field_prefix = 'nfe40_'
    _schema_name = 'nfe'
    _schema_version = '4.0.0'
    _odoo_module = 'l10n_br_nfe'
    _spec_module = 'odoo.addons.l10n_br_nfe_spec.models.v4_00.leiauteNFe'
    _spec_tab_name = 'NFe'
    #    _concrete_skip = ('nfe.40.det',) # will be mixed in later
    _nfe_search_keys = ['nfe40_Id']

    # all m2o at this level will be stacked even if not required:
    _force_stack_paths = ('infnfe.total',)


    def _generate_nfe_binding(self):
        nfe_binding = super()._generate_nfe_binding()
        nfe_binding.infNFe.dest.xNome = 'NF-E EMITIDA EM AMBIENTE DE ' \
                                        'HOMOLOGACAO - SEM VALOR FISCAL'
        return nfe_binding
