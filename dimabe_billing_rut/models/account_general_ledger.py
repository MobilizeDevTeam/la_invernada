from odoo import models, fields, api, _
from odoo.tools.misc import format_date, DEFAULT_SERVER_DATE_FORMAT
from datetime import timedelta
import logging
_logger = logging.getLogger('TEST GENERAL LEDGER')

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    @api.model
    def _get_query_currency_table(self, options):
        ''' Construct the currency table as a mapping company -> rate to convert the amount to the user's company
        currency in a multi-company/multi-currency environment.
        The currency_table is a small postgresql table construct with VALUES.
        :param options: The report options.
        :return:        The query representing the currency table.
        '''

        user_company = self.env['res.company'].sudo().browse(int(self._context.get('company_ids')[0]))
        user_currency = user_company.currency_id
        if options.get('multi_company', False):
            companies = self.env.companies
            conversion_date = options['date']['date_to']
            currency_rates = companies.mapped('currency_id')._get_rates(user_company, conversion_date)
        else:
            companies = user_company
            currency_rates = {user_currency.id: 1.0}

        conversion_rates = []
        for company in companies:
            conversion_rates.extend((
                company.id,
                currency_rates[user_company.currency_id.id] / currency_rates[company.currency_id.id],
                user_currency.decimal_places,
            ))
        query = '(VALUES %s) AS currency_table(company_id, rate, precision)' % ','.join('(%s, %s, %s)' for i in companies)
        return self.env.cr.mogrify(query, conversion_rates).decode(self.env.cr.connection.encoding)


class AccountGeneralLedgerReport(models.AbstractModel):
    _inherit = ['account.general.ledger', 'account.report']

    def _cr_execute(self, options, query, params=None):
        ''' Similar to self._cr.execute but allowing some custom behavior like shadowing the account_move_line table
        to another one like account_reports_cash_basis does.
        :param options: The report options.
        :param query:   The query to be executed by the report.
        :param params:  The optional params of the _cr.execute method.
        '''
        return self._cr.execute(query, params)

    # @api.model
    # def _query_get(self, options, domain=None):
    #     domain = self._get_options_domain(options) + (domain or [])
    #     self.env['account.move.line'].check_access_rights('read')

    #     query = self.env['account.move.line']._where_calc(domain)

    #     # Wrap the query with 'company_id IN (...)' to avoid bypassing company access rights.
    #     self.env['account.move.line']._apply_ir_rules(query)

    #     return query.get_sql()

    @api.model
    def _force_strict_range(self, options):
        ''' Duplicate options with the 'strict_range' enabled on the filter_date.
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        new_options['date'] = new_options['date'].copy()
        new_options['date']['strict_range'] = True
        return new_options
    
    @api.model
    def _get_options_domain(self, options):
        domain = [
            ('display_type', 'not in', ('line_section', 'line_note')),
            ('move_id.state', '!=', 'cancel'),
        ]
        if options.get('multi_company', False):
            domain += [('company_id', 'in', self.env.companies.ids)]
        else:
            domain += [('company_id', '=', self.env['res.company'].sudo().browse(int(self._context.get('company_ids')[0])).id)]
        domain += self._get_options_journals_domain(options)
        domain += self._get_options_date_domain(options)
        domain += self._get_options_analytic_domain(options)
        domain += self._get_options_partner_domain(options)
        domain += self._get_options_all_entries_domain(options)
        if options.get('filter_accounts'):
            domain += [
                '|',
                ('account_id.name', 'ilike', options['filter_accounts']),
                ('account_id.code', 'ilike', options['filter_accounts'])
            ]
        return domain
    
    @api.model
    def _get_options_analytic_domain(self, options):
        domain = []
        if options.get('analytic_accounts'):
            analytic_account_ids = [int(acc) for acc in options['analytic_accounts']]
            domain.append(('analytic_account_id', 'in', analytic_account_ids))
        if options.get('analytic_tags'):
            analytic_tag_ids = [int(tag) for tag in options['analytic_tags']]
            domain.append(('analytic_tag_ids', 'in', analytic_tag_ids))
        return domain
    
    @api.model
    def _get_options_all_entries_domain(self, options):
        if not options.get('all_entries'):
            return [('move_id.state', '=', 'posted')]
        else:
            return [('move_id.state', '!=', 'cancel')]
    
    @api.model
    def _get_options_partner_domain(self, options):
        domain = []
        if options.get('partner_ids'):
            partner_ids = [int(partner) for partner in options['partner_ids']]
            domain.append(('partner_id', 'in', partner_ids))
        if options.get('partner_categories'):
            partner_category_ids = [int(category) for category in options['partner_categories']]
            domain.append(('partner_id.category_id', 'in', partner_category_ids))
        return domain
    
    @api.model
    def _get_options_date_domain(self, options):
        def create_date_domain(options_date):
            date_field = options_date.get('date_field', 'date')
            domain = [(date_field, '<=', options_date['date_to'])]
            if options_date['mode'] == 'range':
                strict_range = options_date.get('strict_range')
                if not strict_range:
                    domain += [
                        '|',
                        (date_field, '>=', options_date['date_from']),
                        ('account_id.user_type_id.include_initial_balance', '=', True)
                    ]
                else:
                    domain += [(date_field, '>=', options_date['date_from'])]
            return domain

        if not options.get('date'):
            return []
        return create_date_domain(options['date'])
    
    @api.model
    def _get_filter_journals(self):
        return self.env['account.journal'].search([
            ('company_id', 'in', self.env.user.company_ids.ids or [self.env.company.id])
        ], order="company_id, name")

    @api.model
    def _get_filter_journal_groups(self):
        journals = self._get_filter_journals()
        groups = self.env['account.journal.group'].search([], order='sequence')
        ret = self.env['account.journal.group']
        for journal_group in groups:
            # Only display the group if it doesn't exclude every journal
            if journals - journal_group.excluded_journal_ids:
                ret += journal_group
        return ret

    @api.model
    def _init_filter_journals(self, options, previous_options=None):
        if self.filter_journals is None:
            return

        previous_company = False
        if previous_options and previous_options.get('journals'):
            journal_map = dict((opt['id'], opt['selected']) for opt in previous_options['journals'] if opt['id'] != 'divider' and 'selected' in opt)
        else:
            journal_map = {}
        options['journals'] = []

        group_header_displayed = False
        default_group_ids = []
        for group in self._get_filter_journal_groups():
            journal_ids = (self._get_filter_journals() - group.excluded_journal_ids).ids
            if len(journal_ids):
                if not group_header_displayed:
                    group_header_displayed = True
                    options['journals'].append({'id': 'divider', 'name': _('Journal Groups')})
                    default_group_ids = journal_ids
                options['journals'].append({'id': 'group', 'name': group.name, 'ids': journal_ids})

        for j in self._get_filter_journals():
            if j.company_id != previous_company:
                options['journals'].append({'id': 'divider', 'name': j.company_id.name})
                previous_company = j.company_id
            options['journals'].append({
                'id': j.id,
                'name': j.name,
                'code': j.code,
                'type': j.type,
                'selected': journal_map.get(j.id, j.id in default_group_ids),
            })

    @api.model
    def _get_options_journals(self, options):
        return [
            journal for journal in options.get('journals', []) if
            not journal['id'] in ('divider', 'group') and journal['selected']
        ]

    @api.model
    def _get_options_journals_domain(self, options):
        # Make sure to return an empty array when nothing selected to handle archived journals.
        selected_journals = self._get_options_journals(options)
        return selected_journals and [('journal_id', 'in', [j['id'] for j in selected_journals])] or []

    @api.model
    def _get_options_sum_balance(self, options):
        ''' Create options used to compute the aggregated sums on accounts.
        The resulting dates domain will be:
        [
            ('date' <= options['date_to']),
            '|',
            ('date' >= fiscalyear['date_from']),
            ('account_id.user_type_id.include_initial_balance', '=', True)
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        fiscalyear_dates = self.env['res.company'].sudo().browse(int(self._context.get('company_ids')[0])).compute_fiscalyear_dates(fields.Date.from_string(new_options['date']['date_from']))
        new_options['date'] = {
            'mode': 'range',
            'date_from': fiscalyear_dates['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': options['date']['date_to'],
        }
        return new_options

    @api.model
    def _get_options_unaffected_earnings(self, options):
        ''' Create options used to compute the unaffected earnings.
        The unaffected earnings are the amount of benefits/loss that have not been allocated to
        another account in the previous fiscal years.
        The resulting dates domain will be:
        [
          ('date' <= fiscalyear['date_from'] - 1),
          ('account_id.user_type_id.include_initial_balance', '=', False),
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        fiscalyear_dates = self.env['res.company'].sudo().browse(int(self._context.get('company_ids')[0])).compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))
        new_date_to = fiscalyear_dates['date_from'] - timedelta(days=1)
        new_options['date'] = {
            'mode': 'single',
            'date_to': new_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
        }
        return new_options

    @api.model
    def _get_options_initial_balance(self, options):
        ''' Create options used to compute the initial balances.
        The initial balances depict the current balance of the accounts at the beginning of
        the selected period in the report.
        The resulting dates domain will be:
        [
            ('date' <= options['date_from'] - 1),
            '|',
            ('date' >= fiscalyear['date_from']),
            ('account_id.user_type_id.include_initial_balance', '=', True)
        ]
        :param options: The report options.
        :return:        A copy of the options.
        '''
        new_options = options.copy()
        fiscalyear_dates = self.env['res.company'].sudo().browse(int(self._context.get('company_ids')[0])).compute_fiscalyear_dates(fields.Date.from_string(options['date']['date_from']))
        new_date_to = fields.Date.from_string(new_options['date']['date_from']) - timedelta(days=1)
        new_options['date'] = {
            'mode': 'range',
            'date_from': fiscalyear_dates['date_from'].strftime(DEFAULT_SERVER_DATE_FORMAT),
            'date_to': new_date_to.strftime(DEFAULT_SERVER_DATE_FORMAT),
        }
        return new_options

    @api.model
    def _get_query_sums(self, options_list, expanded_account=None):
        ''' Construct a query retrieving all the aggregated sums to build the report. It includes:
        - sums for all accounts.
        - sums for the initial balances.
        - sums for the unaffected earnings.
        - sums for the tax declaration.
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :return:                    (query, params)
        '''
        options = options_list[0]
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        params = []
        queries = []

        # Create the currency table.
        # As the currency table is the same whatever the comparisons, create it only once.
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        # ============================================
        # 1) Get sums for all accounts.
        # ============================================

        domain = [('account_id', '=', expanded_account.id)] if expanded_account else []

        for i, options_period in enumerate(options_list):

            # The period domain is expressed as:
            # [
            #   ('date' <= options['date_to']),
            #   '|',
            #   ('date' >= fiscalyear['date_from']),
            #   ('account_id.user_type_id.include_initial_balance', '=', True),
            # ]

            new_options = self._get_options_sum_balance(options_period)
            tables, where_clause, where_params = self._query_get(new_options, domain=domain)
            params += where_params
            queries.append('''
                SELECT
                    account_move_line.account_id                            AS groupby,
                    'sum'                                                   AS key,
                    MAX(account_move_line.date)                             AS max_date,
                    %s                                                      AS period_number,
                    COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                    SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                    SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                    SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                FROM %s
                LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                WHERE %s
                GROUP BY account_move_line.account_id
            ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 2) Get sums for the unaffected earnings.
        # ============================================

        domain = [('account_id.user_type_id.include_initial_balance', '=', False)]
        if expanded_account:
            domain.append(('company_id', '=', expanded_account.company_id.id))

        # Compute only the unaffected earnings for the oldest period.

        i = len(options_list) - 1
        options_period = options_list[-1]

        # The period domain is expressed as:
        # [
        #   ('date' <= fiscalyear['date_from'] - 1),
        #   ('account_id.user_type_id.include_initial_balance', '=', False),
        # ]

        new_options = self._get_options_unaffected_earnings(options_period)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        params += where_params
        queries.append('''
            SELECT
                account_move_line.company_id                            AS groupby,
                'unaffected_earnings'                                   AS key,
                NULL                                                    AS max_date,
                %s                                                      AS period_number,
                COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
            FROM %s
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            WHERE %s
            GROUP BY account_move_line.company_id
        ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 3) Get sums for the initial balance.
        # ============================================

        domain = None
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        if domain is not None:
            for i, options_period in enumerate(options_list):

                # The period domain is expressed as:
                # [
                #   ('date' <= options['date_from'] - 1),
                #   '|',
                #   ('date' >= fiscalyear['date_from']),
                #   ('account_id.user_type_id.include_initial_balance', '=', True)
                # ]

                new_options = self._get_options_initial_balance(options_period)
                tables, where_clause, where_params = self._query_get(new_options, domain=domain)
                params += where_params
                queries.append('''
                    SELECT
                        account_move_line.account_id                            AS groupby,
                        'initial_balance'                                       AS key,
                        NULL                                                    AS max_date,
                        %s                                                      AS period_number,
                        COALESCE(SUM(account_move_line.amount_currency), 0.0)   AS amount_currency,
                        SUM(ROUND(account_move_line.debit * currency_table.rate, currency_table.precision))   AS debit,
                        SUM(ROUND(account_move_line.credit * currency_table.rate, currency_table.precision))  AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE %s
                    GROUP BY account_move_line.account_id
                ''' % (i, tables, ct_query, where_clause))

        # ============================================
        # 4) Get sums for the tax declaration.
        # ============================================

        journal_options = self._get_options_journals(options)
        if not expanded_account and len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
            for i, options_period in enumerate(options_list):
                tables, where_clause, where_params = self._query_get(options_period)
                params += where_params + where_params
                queries += ['''
                    SELECT
                        tax_rel.account_tax_id                  AS groupby,
                        'base_amount'                           AS key,
                        NULL                                    AS max_date,
                        %s                                      AS period_number,
                        0.0                                     AS amount_currency,
                        0.0                                     AS debit,
                        0.0                                     AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM account_move_line_account_tax_rel tax_rel, %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE account_move_line.id = tax_rel.account_move_line_id AND %s
                    GROUP BY tax_rel.account_tax_id
                ''' % (i, tables, ct_query, where_clause), '''
                    SELECT
                    account_move_line.tax_line_id               AS groupby,
                    'tax_amount'                                AS key,
                        NULL                                    AS max_date,
                        %s                                      AS period_number,
                        0.0                                     AS amount_currency,
                        0.0                                     AS debit,
                        0.0                                     AS credit,
                        SUM(ROUND(account_move_line.balance * currency_table.rate, currency_table.precision)) AS balance
                    FROM %s
                    LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
                    WHERE %s
                    GROUP BY account_move_line.tax_line_id
                ''' % (i, tables, ct_query, where_clause)]

        return ' UNION ALL '.join(queries), params

    @api.model
    def _do_query(self, options_list, expanded_account=None, fetch_lines=True):
        ''' Execute the queries, perform all the computation and return (accounts_results, taxes_results). Both are
        lists of tuple (record, fetched_values) sorted by the table's model _order:
        - accounts_values: [(record, values), ...] where
            - record is an account.account record.
            - values is a list of dictionaries, one per period containing:
                - sum:                              {'debit': float, 'credit': float, 'balance': float}
                - (optional) initial_balance:       {'debit': float, 'credit': float, 'balance': float}
                - (optional) unaffected_earnings:   {'debit': float, 'credit': float, 'balance': float}
                - (optional) lines:                 [line_vals_1, line_vals_2, ...]
        - taxes_results: [(record, values), ...] where
            - record is an account.tax record.
            - values is a dictionary containing:
                - base_amount:  float
                - tax_amount:   float
        :param options_list:        The report options list, first one being the current dates range, others being the
                                    comparisons.
        :param expanded_account:    An optional account.account record that must be specified when expanding a line
                                    with of without the load more.
        :param fetch_lines:         A flag to fetch the account.move.lines or not (the 'lines' key in accounts_values).
        :return:                    (accounts_values, taxes_results)
        '''
        # Execute the queries and dispatch the results.
        query, params = self._get_query_sums(options_list, expanded_account=expanded_account)

        groupby_accounts = {}
        groupby_companies = {}
        groupby_taxes = {}

        self._cr_execute(options_list[0], query, params)
        for res in self._cr.dictfetchall():
            # No result to aggregate.
            if res['groupby'] is None:
                continue

            i = res['period_number']
            key = res['key']
            if key == 'sum':
                groupby_accounts.setdefault(res['groupby'], [{} for n in range(len(options_list))])
                groupby_accounts[res['groupby']][i][key] = res
            elif key == 'initial_balance':
                groupby_accounts.setdefault(res['groupby'], [{} for n in range(len(options_list))])
                groupby_accounts[res['groupby']][i][key] = res
            elif key == 'unaffected_earnings':
                groupby_companies.setdefault(res['groupby'], [{} for n in range(len(options_list))])
                groupby_companies[res['groupby']][i] = res
            elif key == 'base_amount' and len(options_list) == 1:
                groupby_taxes.setdefault(res['groupby'], {})
                groupby_taxes[res['groupby']][key] = res['balance']
            elif key == 'tax_amount' and len(options_list) == 1:
                groupby_taxes.setdefault(res['groupby'], {})
                groupby_taxes[res['groupby']][key] = res['balance']

        # Fetch the lines of unfolded accounts.
        # /!\ Unfolding lines combined with multiple comparisons is not supported.
        if fetch_lines and len(options_list) == 1:
            options = options_list[0]
            unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
            if expanded_account or unfold_all or options['unfolded_lines']:
                query, params = self._get_query_amls(options, expanded_account)
                self._cr_execute(options, query, params)
                for res in self._cr.dictfetchall():
                    groupby_accounts[res['account_id']][0].setdefault('lines', [])
                    groupby_accounts[res['account_id']][0]['lines'].append(res)

        # Affect the unaffected earnings to the first fetched account of type 'account.data_unaffected_earnings'.
        # There is an unaffected earnings for each company but it's less costly to fetch all candidate accounts in
        # a single search and then iterate it.
        if groupby_companies:
            unaffected_earnings_type = self.env.ref('account.data_unaffected_earnings')
            candidates_accounts = self.env['account.account'].search([
                ('user_type_id', '=', unaffected_earnings_type.id), ('company_id', 'in', list(groupby_companies.keys()))
            ])
            for account in candidates_accounts:
                company_unaffected_earnings = groupby_companies.get(account.company_id.id)
                if not company_unaffected_earnings:
                    continue
                for i in range(len(options_list)):
                    unaffected_earnings = company_unaffected_earnings[i]
                    groupby_accounts.setdefault(account.id, [{} for i in range(len(options_list))])
                    groupby_accounts[account.id][i]['unaffected_earnings'] = unaffected_earnings
                del groupby_companies[account.company_id.id]

        # Retrieve the accounts to browse.
        # groupby_accounts.keys() contains all account ids affected by:
        # - the amls in the current period.
        # - the amls affecting the initial balance.
        # - the unaffected earnings allocation.
        # Note a search is done instead of a browse to preserve the table ordering.
        if expanded_account:
            accounts = expanded_account
        elif groupby_accounts:
            accounts = self.env['account.account'].search([('id', 'in', list(groupby_accounts.keys()))])
        else:
            accounts = []
        accounts_results = [(account, groupby_accounts[account.id]) for account in accounts]

        # Fetch as well the taxes.
        if groupby_taxes:
            taxes = self.env['account.tax'].search([('id', 'in', list(groupby_taxes.keys()))])
        else:
            taxes = []
        taxes_results = [(tax, groupby_taxes[tax.id]) for tax in taxes]
        return accounts_results, taxes_results

    @api.model
    def _get_columns_name(self, options):
        
        columns_names = [
            {'name': 'Cuentas'},
            {'name': _('Date'), 'class': 'date'},
            {'name': _('Communication')},
            {'name': _('C.Analítica')},
            {'name': _('Partner')},
            {'name': _('Debit'), 'class': 'number'},
            {'name': _('Credit'), 'class': 'number'},
            {'name': _('Balance'), 'class': 'number'}
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns_names.insert(4, {'name': _('Currency'), 'class': 'number'})
        return columns_names
    
    @api.model
    def _get_lines(self, options, line_id=None):
        # _logger.info('HOLAAAAAAAAAAA')
        offset = int(options.get('lines_offset', 0))
        remaining = int(options.get('lines_remaining', 0))
        balance_progress = float(options.get('lines_progress', 0))

        if offset > 0:
            # Case a line is expanded using the load more.
            return self._load_more_lines_(options, line_id, offset, remaining, balance_progress)
        else:
            # Case the whole report is loaded or a line is expanded for the first time.
            return self._get_general_ledger_lines_(options, line_id=line_id)
    
    @api.model
    def _load_more_lines_(self, options, line_id, offset, load_more_remaining, balance_progress):
        ''' Get lines for an expanded line using the load more.
        :param options: The report options.
        :param line_id: string representing the line to expand formed as 'loadmore_<ID>'
        :params offset, load_more_remaining: integers. Parameters that will be used to fetch the next aml slice
        :param balance_progress: float used to carry on with the cumulative balance of the account.move.line
        :return:        A list of lines, each one represented by a dictionary.
        '''
        lines = []
        expanded_account = self.env['account.account'].browse(int(line_id[9:]))

        load_more_counter = self.MAX_LINES

        # Fetch the next batch of lines.
        amls_query, amls_params = self._get_query_amls(options, expanded_account, offset=offset, limit=load_more_counter)
        self._cr_execute(options, amls_query, amls_params)
        for aml in self._cr.dictfetchall():
            # Don't show more line than load_more_counter.
            if load_more_counter == 0:
                break

            balance_progress += aml['balance']

            # account.move.line record line.
            lines.append(self._get_aml_line(options, expanded_account, aml, balance_progress))

            offset += 1
            load_more_remaining -= 1
            load_more_counter -= 1

        if load_more_remaining > 0:
            # Load more line.
            lines.append(self._get_load_more_line(
                options, expanded_account,
                offset,
                load_more_remaining,
                balance_progress,
            ))
        return lines
    
    @api.model
    def _get_options_periods_list_(self, options):
        ''' Get periods as a list of options, one per impacted period.
        The first element is the range of dates requested in the report, others are the comparisons.

        :param options: The report options.
        :return:        A list of options having size 1 + len(options['comparison']['periods']).
        '''
        periods_options_list = []
        if options.get('date'):
            periods_options_list.append(options)
        if options.get('comparison') and options['comparison'].get('periods'):
            for period in options['comparison']['periods']:
                period_options = options.copy()
                period_options['date'] = period
                periods_options_list.append(period_options)
        return periods_options_list
    
    @api.model
    def _get_general_ledger_lines_(self, options, line_id=None):
        ''' Get lines for the whole report or for a specific line.
        :param options: The report options.
        :return:        A list of lines, each one represented by a dictionary.
        '''
        _logger.info('HOLAAAAAAAAAAA')
        lines = []
        aml_lines = []
        options_list = self._get_options_periods_list_(options)
        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])
        date_from = fields.Date.from_string(options['date']['date_from'])
        _logger.info('LOG: -- user {} contex {}'.format(self.env.user, self._context.get('company_ids')[0]))
        # company_currency = self.env.company.currency_id
        company_currency = self.env['res.company'].sudo().browse(int(self._context.get('company_ids')[0])).currency_id

        expanded_account = line_id and self.env['account.account'].browse(int(line_id[8:]))
        accounts_results, taxes_results = self._do_query(options_list, expanded_account=expanded_account)

        total_debit = total_credit = total_balance = 0.0
        for account, periods_results in accounts_results:
            # No comparison allowed in the General Ledger. Then, take only the first period.
            results = periods_results[0]

            is_unfolded = 'account_%s' % account.id in options['unfolded_lines']

            # account.account record line.
            account_sum = results.get('sum', {})
            account_un_earn = results.get('unaffected_earnings', {})

            # Check if there is sub-lines for the current period.
            max_date = account_sum.get('max_date')
            has_lines = max_date and max_date >= date_from or False

            amount_currency = account_sum.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0)
            debit = account_sum.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
            credit = account_sum.get('credit', 0.0) + account_un_earn.get('credit', 0.0)
            balance = account_sum.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

            lines.append(self._get_account_title_line(options, account, amount_currency, debit, credit, balance, has_lines))

            total_debit += debit
            total_credit += credit
            total_balance += balance

            if has_lines and (unfold_all or is_unfolded):
                # Initial balance line.
                account_init_bal = results.get('initial_balance', {})

                cumulated_balance = account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

                lines.append(self._get_initial_balance_line(
                    options, account,
                    account_init_bal.get('amount_currency', 0.0) + account_un_earn.get('amount_currency', 0.0),
                    account_init_bal.get('debit', 0.0) + account_un_earn.get('debit', 0.0),
                    account_init_bal.get('credit', 0.0) + account_un_earn.get('credit', 0.0),
                    cumulated_balance,
                ))

                # account.move.line record lines.
                amls = results.get('lines', [])

                load_more_remaining = len(amls)
                load_more_counter = self._context.get('print_mode') and load_more_remaining or self.MAX_LINES

                for aml in amls:
                    # Don't show more line than load_more_counter.
                    if load_more_counter == 0:
                        break

                    cumulated_balance += aml['balance']
                    lines.append(self._get_aml_line(options, account, aml, company_currency.round(cumulated_balance)))

                    load_more_remaining -= 1
                    load_more_counter -= 1
                    aml_lines.append(aml['id'])

                if load_more_remaining > 0:
                    # Load more line.
                    lines.append(self._get_load_more_line(
                        options, account,
                        self.MAX_LINES,
                        load_more_remaining,
                        cumulated_balance,
                    ))

                if self.env.company.totals_below_sections:
                    # Account total line.
                    lines.append(self._get_account_total_line(
                        options, account,
                        account_sum.get('amount_currency', 0.0),
                        account_sum.get('debit', 0.0),
                        account_sum.get('credit', 0.0),
                        account_sum.get('balance', 0.0),
                    ))

        if not line_id:
            # Report total line.
            lines.append(self._get_total_line(
                options,
                total_debit,
                total_credit,
                company_currency.round(total_balance),
            ))

            # Tax Declaration lines.
            journal_options = self._get_options_journals(options)
            if len(journal_options) == 1 and journal_options[0]['type'] in ('sale', 'purchase'):
                lines += self._get_tax_declaration_lines(
                    options, journal_options[0]['type'], taxes_results
                )
        if self.env.context.get('aml_only'):
            return aml_lines
        return lines
    
    @api.model
    def _get_aml_line(self, options, account, aml, cumulated_balance):
        if aml['payment_id']:
            caret_type = 'account.payment'
        else:
            caret_type = 'account.move'

        if aml['ref'] and aml['name']:
            title = '%s - %s' % (aml['name'], aml['ref'])
        elif aml['ref']:
            title = aml['ref']
        elif aml['name']:
            title = aml['name']
        else:
            title = ''

        if (aml['currency_id'] and aml['currency_id'] != account.company_id.currency_id.id) or account.currency_id:
            currency = self.env['res.currency'].browse(aml['currency_id'])
        else:
            currency = False
        _logger.info('LOG: ___>>>>> {}'.format(aml))

        columns = [
            {'name': format_date(self.env, aml['date']), 'class': 'date'},
            {'name': self._format_aml_name(aml['name'], aml['ref'], aml['move_name']), 'title': title, 'class': 'whitespace_print o_account_report_line_ellipsis'},
            {'name': 'Holaaaaa', 'title': 'Holaaaaa', 'class': 'whitespace_print'},
            {'name': aml['partner_name'], 'title': aml['partner_name'], 'class': 'whitespace_print'},
            {'name': self.format_value(aml['debit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(aml['credit'], blank_if_zero=True), 'class': 'number'},
            {'name': self.format_value(cumulated_balance), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.insert(4, {'name': currency and aml['amount_currency'] and self.format_value(aml['amount_currency'], currency=currency, blank_if_zero=True) or '', 'class': 'number'})
        return {
            'id': aml['id'],
            'caret_options': caret_type,
            'class': 'top-vertical-align',
            'parent_id': 'account_%d' % aml['account_id'],
            'name': aml['move_name'],
            'columns': columns,
            'level': 2,
        }
    
    @api.model
    def _get_account_title_line(self, options, account, amount_currency, debit, credit, balance, has_lines):
        has_foreign_currency = account.currency_id and account.currency_id != account.company_id.currency_id or False
        unfold_all = self._context.get('print_mode') and not options.get('unfolded_lines')

        name = '%s %s' % (account.code, account.name)
        max_length = self._context.get('print_mode') and 100 or 60
        if len(name) > max_length and not self._context.get('no_format'):
            name = name[:max_length] + '...'
        columns = [
            {'name': self.format_value(debit), 'class': 'number'},
            {'name': self.format_value(credit), 'class': 'number'},
            {'name': self.format_value(balance), 'class': 'number'},
        ]
        if self.user_has_groups('base.group_multi_currency'):
            columns.insert(0, {'name': has_foreign_currency and self.format_value(amount_currency, currency=account.currency_id, blank_if_zero=True) or '', 'class': 'number'})
        return {
            'id': 'account_%d' % account.id,
            'name': name,
            'title_hover': name,
            'columns': columns,
            'level': 2,
            'unfoldable': has_lines,
            'unfolded': has_lines and 'account_%d' % account.id in options.get('unfolded_lines') or unfold_all,
            'colspan': 4,
            'class': 'o_account_reports_totals_below_sections' if self.env.company.totals_below_sections else '',
        }
    
    @api.model
    def _get_query_amls(self, options, expanded_account, offset=None, limit=None):
        ''' Construct a query retrieving the account.move.lines when expanding a report line with or without the load
        more.
        :param options:             The report options.
        :param expanded_account:    The account.account record corresponding to the expanded line.
        :param offset:              The offset of the query (used by the load more).
        :param limit:               The limit of the query (used by the load more).
        :return:                    (query, params)
        '''

        unfold_all = options.get('unfold_all') or (self._context.get('print_mode') and not options['unfolded_lines'])

        # Get sums for the account move lines.
        # period: [('date' <= options['date_to']), ('date', '>=', options['date_from'])]
        if expanded_account:
            domain = [('account_id', '=', expanded_account.id)]
        elif unfold_all:
            domain = []
        elif options['unfolded_lines']:
            domain = [('account_id', 'in', [int(line[8:]) for line in options['unfolded_lines']])]

        new_options = self._force_strict_range(options)
        tables, where_clause, where_params = self._query_get(new_options, domain=domain)
        ct_query = self.env['res.currency']._get_query_currency_table(options)
        query = '''
            SELECT
                account_move_line.id,
                account_move_line.date,
                account_move_line.date_maturity,
                account_move_line.name,
                account_move_line.ref,
                account_move_line.company_id,
                account_move_line.account_id,
                account_move_line.payment_id,
                account_move_line.partner_id,
                account_move_line.currency_id,
                account_move_line.amount_currency,
                account_move_line.analytic_account_id,
                ROUND(account_move_line.debit * currency_table.rate, currency_table.precision)   AS debit,
                ROUND(account_move_line.credit * currency_table.rate, currency_table.precision)  AS credit,
                ROUND(account_move_line.balance * currency_table.rate, currency_table.precision) AS balance,
                account_move_line__move_id.name         AS move_name,
                company.currency_id                     AS company_currency_id,
                partner.name                            AS partner_name,
                account_move_line__move_id.move_type         AS move_type,
                account.code                            AS account_code,
                account.name                            AS account_name,
                journal.code                            AS journal_code,
                journal.name                            AS journal_name,
                full_rec.name                           AS full_rec_name
            FROM account_move_line
            LEFT JOIN account_move account_move_line__move_id ON account_move_line__move_id.id = account_move_line.move_id
            LEFT JOIN %s ON currency_table.company_id = account_move_line.company_id
            LEFT JOIN res_company company               ON company.id = account_move_line.company_id
            LEFT JOIN res_partner partner               ON partner.id = account_move_line.partner_id
            LEFT JOIN account_account account           ON account.id = account_move_line.account_id
            LEFT JOIN account_journal journal           ON journal.id = account_move_line.journal_id
            LEFT JOIN account_full_reconcile full_rec   ON full_rec.id = account_move_line.full_reconcile_id
            WHERE %s
            ORDER BY account_move_line.date, account_move_line.id
        ''' % (ct_query, where_clause)

        if offset:
            query += ' OFFSET %s '
            where_params.append(offset)
        if limit:
            query += ' LIMIT %s '
            where_params.append(limit)

        return query, where_params

        # list = ['__abstractmethods__', '__call__', '__class__', '__contains__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getitem__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__iter__', '__le__', '__len__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__reversed__', '__setattr__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__weakref__', '_abc_cache', '_abc_negative_cache', '_abc_negative_cache_version', '_abc_registry', '_cache_key', '_do_in_mode', '_local', '_protected', 'add_todo', 'all', 'args', 'cache', 'cache_key', 'check_todo', 'clear', 'clear_upon_failure', 'context', 'cr', 'dirty', 'do_in_draft', 'do_in_onchange', 'envs', 'field_todo', 'get', 'get_todo', 'has_todo', 'in_draft', 'in_onchange', 'items', 'keys', 'lang', 'manage', 'norecompute', 'protected', 'protecting', 'recompute', 'ref', 'registry', 'remove_todo', 'reset', 'uid', 'user', 'values']
