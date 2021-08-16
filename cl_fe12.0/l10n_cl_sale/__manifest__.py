{
    'name': 'Personalizacion Chilena en Ventas',
    'version': '1.0.0.0',
    'category': 'Sales',
    'description': """""",
    'author': 'Carlos Lopez Mite(celm1990@hotmail.com)',
    'depends': [
        'base',
        'web',
        'delivery',
        'sale',
        'stock',
        'sales_team',
        'l10n_cl_fe',
        'l10n_cl_base',
        'dusal_sale',
        'generic_sale',
    ],
    'data': [
        'data/action_server_data.xml',
        'views/stock_warehouse_view.xml',
        'views/crm_team_view.xml',
        'report/sale_report.xml',
    ],
    'installable': True,
}