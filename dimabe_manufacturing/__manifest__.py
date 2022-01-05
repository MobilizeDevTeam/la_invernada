# -*- coding: utf-8 -*-
{
    'name': "Fabricación Dimabe",

    'summary': """
        Módulo que modifica la fabricación actual y la adapta a la realidad de productos frutícolas.
        """,

    'description': "",

    'author': "Dimabe ltda",
    'website': "http://www.dimabe.cl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'web',
        'dimabe_reception',
        'mrp',
        'mrp_workorder',
        'dimabe_export_order',
        'dimabe_quality_integration',
        'mrp_plm'
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/update_data_from_upgrade.xml',
        'security/collection_groups.xml',
        'views/confirm_order_reserved.xml',
        'views/confirm_principal_order.xml',
        'views/mrp_workorder.xml',
        'views/stock_production_lot_serial.xml',
        'views/stock_production_lot.xml',
        'views/mrp_production.xml',
        'reports/lot_serial_label_report.xml',
        'reports/oven_use_label_report.xml',
        'reports/manufacturing_pallet_label_report.xml',
        'data/warehouse_notification_template.xml',
        'views/views.xml',
        'views/mrp_dispatched.xml',
        'views/mrp_workcenter.xml',
        'views/quality_analysis.xml',
        'views/product_category.xml',
        'views/potential_lot.xml',
        'views/templates.xml',
        'views/stock_picking.xml',
        'views/unpelled_dried.xml',
        'views/oven_use.xml',
        'views/dried_unpelled_history.xml',
        'views/manufacturing_pallet.xml',
        'views/product_product.xml',
        'views/stock_picking_type.xml',
        'views/res_partner.xml',
        'views/res_company.xml',
        'views/label_durability.xml',
        'views/dried_oven.xml',
        'views/res_config_settings.xml',
        'views/process_report_xlsx.xml',
        'views/update_quant_view.xml',
        'views/custom_dispatch_line.xml',
        'views/stock_report_xlsx.xml',
        'views/mrp_eco.xml',
        'views/generate_label_wizard.xml',
        'views/change_date_lot.xml',
        'views/custom_oven_manager_group.xml',
        'reports/stock/raw_report.xml',
        'reports/stock/raw_service_report.xml',
        'reports/stock/pt_report.xml',
        'reports/stock/match_report.xml',
        'reports/stock/washed_stock_report.xml',
        'reports/stock/calibrate_stock_report.xml',
        'reports/stock/discart_report.xml',
        'reports/stock/vain_report.xml',
        'reports/stock/washed_service_report.xml',
        'reports/process/packing_ncc.xml',
        'reports/process/packing_nsc.xml',
        'reports/process/calibre_process.xml',
        'reports/process/washed_process.xml',
        'reports/process/laser_process.xml',
        'reports/process/report_re_laser.xml',
        'reports/process/packing_ncc_service.xml',
        'reports/process/packing_nsc_service.xml',
        'reports/process/calibrate_service_process.xml',
        'reports/process/washed_process_service.xml',
        'reports/process/laser_service_process.xml',
        'reports/process/re_laser_process_service.xml',
        'reports/process/manual_process.xml',
        'reports/process/manual_service_process.xml',
        'reports/stock/match_report_service.xml',
        'reports/inventory/compare_inventory_report.xml',
        'reports/stock/match_report_service.xml',
        'reports/stock/discart_service_report.xml',
        'reports/stock/calibrate_service_report.xml',
        'reports/stock/vain_service.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ]
}
