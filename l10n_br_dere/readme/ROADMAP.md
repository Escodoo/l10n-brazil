- Migrate `xml_builder` to [derelib](https://github.com/Escodoo/derelib)
  (xsdata binding for DeRE 1.2.0, same role nfelib plays for NF-e /
  CT-e / MDF-e): build, sign, batch and parse returns through the
  library, keeping business rules (`tpOper`, MS1135 / MS1147, PGCC
  checks) in this module. Do not introduce
  `spec_driven_model.StackedModel` before that migration.
- Do not inherit event mixins (D-1001 / D-1011 / D-1101 / D-1199) on
  `l10n_br_dere.declaration`, `l10n_br_dere.table.period` or
  `l10n_br_dere.event`: those abstracts share `dere12_id` and `dere12_tpOper`.
- Official `tpOper` 1/2/3 (and D-1121 `4` after the first D-1199) is
  implemented. D-1198 / D-1199 stay inclusion-only.
- D-1121 `infoImovel` and D-1021 (required before `motExcl` 1)
- Local replica of MS1155 (future `perApur`): the official rule does not
  interrupt processing, and the test suite uses future months
- Transactional events (D-3201 and remaining D-22xx / D-32xx) after CGIBS
  publishes a stable transactional layout
