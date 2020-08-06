odoo.define('balance_sheet_clp.sincronize_button', function (require) {
    "use strict";
    var core = require('web.core');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');
    var session = require('web.session');
    var _t = core._t;
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.find('.oe_action_button').click(this.proxy('action_def'));
            }
        },
        action_def: function () {
            var self = this
            var user = session.uid;
            rpc.query({
                model: 'balance.sheet.clp',
                method: 'get_data',
                args: [[user], {'id': user}],

            }).then(function (e){
                self.do_action({
                    'name': _t('Balance de Situacion CLP'),
                    type:'ir.actions.act_window',
                    res_model : 'balance.sheet.clp',
                    views : [[false,'tree']],
                    view_mode : 'tree'
                });
                window.location
            });
            location.reload();
            this.trigger_up('reload');
        }
    });
}
)
