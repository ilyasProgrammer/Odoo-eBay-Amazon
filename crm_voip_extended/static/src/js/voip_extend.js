odoo.define('crm_voip_extended.voip_extend', function(require) {
"use strict";
var voip_core = require('voip.core');
var core = require('web.core');
var Model = require('web.Model');
var real_session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var web_client = require('web.web_client');
var WebClient = require('web.WebClient');
var Widget = require('web.Widget');
require('web_enterprise.form_widgets'); // FieldPhone must be in the form_widget_registry

var dialing_panel = null;

var _t = core._t;
var QWeb = core.qweb;

var PhonecallWidget = Widget.extend({
    "template": "crm_voip.PhonecallWidget",
    events: {
        "click": "select_call",
        "click .oe_dial_remove_phonecall": "remove_phonecall"
    },
    init: function(parent, phonecall, formatCurrency) {
        this._super(parent);
        this.id = phonecall.id;
        if(phonecall.partner_name){
            this.partner_name = _.str.truncate(phonecall.partner_name,19);
        }else{
            this.partner_name = _t("Unknown");
        }
        this.state =phonecall.state;
        this.image_small = phonecall.partner_image_small;
        this.email =phonecall.partner_email;
        this.name =_.str.truncate(phonecall.name,23);
        this.opportunity_id = phonecall.opportunity_id;
        this.partner_id = phonecall.partner_id;
        this.opportunity_name = phonecall.opportunity_name;
        this.opportunity_planned_revenue = formatCurrency(phonecall.opportunity_planned_revenue, phonecall.opportunity_company_currency);
        this.partner_phone = phonecall.partner_phone;
        this.description = phonecall.description;
        this.opportunity_probability = phonecall.opportunity_probability;
        this.date= phonecall.date;
        this.duration = phonecall.duration;
        this.opportunity_date_action = phonecall.opportunity_date_action;
        this.display_opp_name = true;
        this.opportunity_title_action = phonecall.opportunity_title_action;
        if(!this.opportunity_name){
            this.opportunity_name = _t("No opportunity linked");
        }else if(this.opportunity_name === phonecall.name){
            this.display_opp_name = false;
        }
        this.max_priority = phonecall.max_priority;
        this.opportunity_priority = phonecall.opportunity_priority;
    },

    start: function(){
        var empty_star = parseInt(this.max_priority) - parseInt(this.opportunity_priority);
        //creation of the tooltip
        this.$el.popover({
            placement : 'right', // top, bottom, left or right
            title : QWeb.render("crm_voip_Tooltip_title", {
                name: this.name, priority: parseInt(this.opportunity_priority), empty_star:empty_star}), 
            html: 'true', 
            content :  QWeb.render("crm_voip_Tooltip",{
                display_opp_name: this.display_opp_name,
                opportunity: this.opportunity_name,
                partner_name: this.partner_name,
                phone: this.partner_phone,
                description: this.description,
                email: this.partner_email,
                title_action: this.opportunity_title_action,
                planned_revenue: this.opportunity_planned_revenue,
                probability: this.opportunity_probability,
                date: this.date,
            }),
        });
    },

    //select the clicked call, show options and put some highlight on it
    select_call: function(){
        this.trigger("select_call", this.id);
    },

    remove_phonecall: function(e){
        e.stopPropagation();
        e.preventDefault();
        this.trigger("remove_phonecall",this);
    },

    set_state: function(state){
        if(state !== this.state){
            this.state = state;
            if(state === 'in_call'){
                this.$('.oe_dial_phonecall_partner_name')
                    .after("<i style='margin-left:5px;' class='fa fa-microphone oe_dial_icon_inCall'></i>");
            }else if(state === 'pending' && !this.$('.oe_dial_state_icon_pending').length){
                this.$('.oe_dial_status_span')
                    .append('<i class="fa fa-stack oe_dial_state_icon" style="width:13px; height:15px;line-height: 13px;">'+
                            '<i class="fa fa-phone fa-stack-1x oe_dial_state_icon text-muted"></i>'+
                            '<i class="fa fa-times fa-stack-1x oe_dial_state_icon"'+
                            'style="color: LightCoral;font-size: 8px;left: 4px;position: relative;bottom: 4px;"></i>'+
                            '</i>');
                this.$('.oe_dial_icon_inCall').remove();
                if(this.$('.oe_dial_state_icon_done').length){
                    this.$('.oe_dial_state_icon_done').remove();
                }
            }else{
                this.$('.oe_dial_icon_inCall').remove();
            }
        }
    },

    schedule_call: function(){
        new Model("crm.phonecall").call('schedule_another_phonecall', [this.id]).then(function(action){
            web_client.action_manager.do_action(action);
        });
    },

    send_email: function(){
        if(this.opportunity_id){
            web_client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                src_model: 'crm.phonecall',
                multi: "True",
                target: 'new',
                key2: 'client_action_multi',
                context: {
                            'default_composition_mode': 'mass_mail',
                            'active_ids': [this.opportunity_id],
                            'default_model': 'crm.lead',
                            'default_partner_ids': [this.partner_id],
                            'default_use_template': true,
                        },
                views: [[false, 'form']],
            });
        }else if(this.partner_id){
            web_client.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: 'mail.compose.message',
                src_model: 'crm.phonecall',
                multi: "True",
                target: 'new',
                key2: 'client_action_multi',
                context: {
                            'default_composition_mode': 'mass_mail',
                            'active_ids': [this.partner_id],
                            'default_model': 'res.partner',
                            'default_partner_ids': [this.partner_id],
                            'default_use_template': true,
                        },
                views: [[false, 'form']],
            });
        }
    },

    to_lead: function(){
        var self = this;
        if(this.opportunity_id){
            //Call of the function xmlid_to_res_model_res_id to get the id of the opportunity's form view and not the lead's form view
            new Model("ir.model.data")
            .call("xmlid_to_res_model_res_id",["crm.crm_case_form_view_oppor"])
            .then(function(data){
                web_client.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: "crm.lead",
                    res_id: self.opportunity_id,
                    views: [[data[1], 'form']],
                    target: 'current',
                    context: {},
                    flags: {initial_mode: "edit",},
                });
            });
        }else{
            var phonecall_model = new Model("crm.phonecall");
            phonecall_model.call("action_button_to_opportunity", [[this.id]]).then(function(result){
                result.flags= {initial_mode: "edit",};
                web_client.action_manager.do_action(result);
            });
        }
    },

    to_client: function(){
        web_client.action_manager.do_action({
            type: 'ir.actions.act_window',
            res_model: "res.partner",
            res_id: this.partner_id,
            views: [[false, 'form']],
            target: 'current',
            context: {},
            flags: {initial_mode: "edit",},
        });
    },

});

var DialingPanel = Widget.extend({
    template: "crm_voip.DialingPanel",
    events:{
        "keyup .oe_dial_searchbox": "input_change",
        "click .oe_dial_close_icon": function(ev){ev.preventDefault();this.toggle_display();},
        "click .oe_dial_call_button":  "call_button",
        "click .oe_dial_search_icon": function(ev){ev.preventDefault();this.search_phonecalls_status(false);},
        "click .oe_dial_refresh_icon": function(ev){ev.preventDefault();this.search_phonecalls_status(true);},
        "click .oe_dial_keypad_icon": function(ev){ev.preventDefault();this.toggle_keypad();},
        "click .oe_dial_keypad_button": function(ev){ev.preventDefault();this.keypad_button(ev.currentTarget.textContent);},
        "click .oe_dial_keypad_backspace": "keypad_backspace",
        "click .oe_dial_keypad_call_button": "keypad_call_button",
        "click .oe_dial_hangup_button": "hangup_button",
        "click .oe_dial_schedule_call": "schedule_call",
        "click .oe_dial_email": "send_email",
        "click .oe_dial_to_client": "to_client",
        "click .oe_dial_to_lead": "to_lead",
        "click .oe_dial_transfer_button": "transfer_button",
        "click .oe_dial_autocall_button": function(ev){ev.preventDefault();this.auto_call_button();},
        "click .oe_dial_stop_autocall_button": "stop_automatic_call",
    },
    init: function(parent, formatCurrency) {
        if(dialing_panel){
            return dialing_panel;
        }   
        this._super(parent);
        //phonecalls in the queue 
        this.widgets = {};
        this.in_call = false;
        this.in_automatic_mode = false;
        this.current_phonecall = null;
        this.shown = false;
        this.optional_buttons_animated = false;
        this.optional_buttons_shown = false;
        this.formatCurrency = formatCurrency;
        //phonecalls which will be called in automatic mode.
        //To avoid calling already done calls
        this.phonecalls_auto_call = [];
        this.selected_phonecall = null;
        //create the sip user agent and bind actions
        this.sip_js = new voip_core.UserAgent();
        this.sip_js.on('sip_ringing',this,this.sip_ringing);
        this.sip_js.on('sip_accepted',this,this.sip_accepted);
        this.sip_js.on('sip_cancel',this,this.sip_cancel);
        this.sip_js.on('sip_rejected',this,this.sip_rejected);
        this.sip_js.on('sip_bye',this,this.sip_bye);
        this.sip_js.on('sip_error',this,this.sip_error);
        this.sip_js.on('sip_error_resolved',this,this.sip_error_resolved);
        this.sip_js.on('sip_customer_unavailable',this,this.sip_customer_unavailable);
        this.sip_js.on('sip_incoming_call',this,this.sip_incoming_call);
        this.sip_js.on('sip_end_incoming_call',this,this.sip_end_incoming_call);

        //bind the bus trigger with the functions
        core.bus.on('reload_panel', this, this.search_phonecalls_status);
        core.bus.on('transfer_call',this,this.transfer_call);
        core.bus.on('select_call',this,this.select_call);
        core.bus.on('next_call',this,this.next_call);
        core.bus.on('voip_toggle_display',this,this.toggle_display);

        dialing_panel = this;
        this.appendTo(web_client.$el);
    },

    start: function(){
        this.$el.css("bottom", -this.$el.outerHeight());
        this.$big_call_button = this.$('.oe_dial_big_call_button');
        this.$hangup_button = this.$('.oe_dial_hangup_button');
        this.$hangup_transfer_buttons = this.$(".oe_dial_transfer_button, .oe_dial_hangup_button");
        this.$dial_display_pannel = this.$(".oe_dial_display_pannel");
        this.$dial_keypad = this.$(".oe_dial_keypad");
        this.$dial_keypad_optional = this.$(".oe_dial_keypad_optional");
        this.$dial_dial_keypad_input = this.$(".oe_dial_keypad_input");
        var self = this;
        $.get("https://ipinfo.io", function(response) {
            if (response.country == 'US' || response.country == 'CN'){
                this.$dial_dial_keypad_input.val(1);
            }else {
                new Model('res.country').call('search_read', [[['code', '=', response.country]]]).then(function(country) {
                    var str1 = country[0].phone_code.toString();
                    var str2 = '011'.concat(str1);
                    for (var i = 0, len = str2.length; i < len; i++) {
                        var val = self.$dial_dial_keypad_input.val();
                        self.$dial_dial_keypad_input.val(val + str2[i]);
                    }
                });
            }
        }, "jsonp");
    },

    toggle_display: function(){
        if (this.shown) {
            this.$el.animate({
                "bottom": -this.$el.outerHeight(),
            });
        } else {
            // update the list of user status when show the dialing panel
            this.search_phonecalls_status();
            this.$el.animate({
                "bottom": 0,
            });
        }
        this.shown = ! this.shown;
    },

    //Hide the optional buttons when the panel is reloaded or a phonecall unselected
    slide_down_optional_buttons: function(){
        var self = this;
        if(this.optional_buttons_shown && !this.optional_buttons_animated){
            this.optional_buttons_animated = true;
            this.$(".oe_dial_phonecalls").animate({
                height: (this.$(".oe_dial_phonecalls").height() + this.$(".oe_dial_optionalbuttons").outerHeight()),
            }, 300,function(){
                self.optional_buttons_shown = false;
                self.optional_buttons_animated = false;
                if(self.button_down_deferred){
                    self.button_down_deferred.resolve();
                }
            });
        }
    },

    //Slide up the optional buttons when a phonecall is selected
    slide_up_optional_buttons: function(){
        var self = this;
        if(!this.optional_buttons_shown && !this.optional_buttons_animated){
            this.optional_buttons_animated = true;
            this.$(".oe_dial_phonecalls").animate({
                height: (this.$(".oe_dial_phonecalls").height() - this.$(".oe_dial_optionalbuttons").outerHeight()),
            }, 300,function(){
                self.optional_buttons_animated = false;
                self.optional_buttons_shown = true;
                if(self.button_up_deferred){
                    self.button_up_deferred.resolve();
                }
            });
        }
    },

    toggle_keypad: function(){
        this.toggle_keypad_optional();
        if (this.$dial_keypad.hasClass("oe_dial_pannel_displayed")){
            this.$dial_display_pannel.addClass("oe_dial_keypad_displayed");
            this.$dial_keypad.removeClass("oe_dial_pannel_displayed");
        }else{
            this.$dial_display_pannel.removeClass("oe_dial_keypad_displayed");
            this.$dial_keypad.addClass("oe_dial_pannel_displayed");
        }
    },

    toggle_keypad_optional: function(){
        if(this.in_call){
            this.$dial_keypad_optional.addClass("oe_dial_keypad_incall");
        }else{
            this.$dial_keypad_optional.removeClass("oe_dial_keypad_incall");
        }
    },

    keypad_button: function(number){
        if(this.in_call){
            this.sip_js.send_dtmf(number);
        }else{
            var val = this.$dial_dial_keypad_input.val();
            this.$dial_dial_keypad_input.val(val + number);
        }
    },

    keypad_backspace: function(){
        if(!this.in_call){
            var val = this.$dial_dial_keypad_input.val();
            this.$dial_dial_keypad_input.val(val.slice(0, -1));
        }
    },

    keypad_call_button: function(){
        if(!this.in_call){
            var self = this;
            var number = this.$dial_dial_keypad_input.val();
            new Model("crm.phonecall").call("get_new_phonecall", [number]).then(
                function(result){
                    var phonecall = result.phonecall[0];
                    self.toggle_keypad();
                    self.display_in_queue(phonecall);
                    self.select_call(phonecall.id);
                    self.make_call(phonecall.id);
                    self.$dial_dial_keypad_input.val("");

            });
        }
    },

    //Modify the phonecalls list when the search input changes
    input_change: function(event) {
        var search = $(event.target).val().toLowerCase();
        //for each phonecall, check if the search is in phonecall name or the partner name
        _.each(this.widgets,function(phonecall){
            var flag = phonecall.partner_name.toLowerCase().indexOf(search) === -1 && 
                phonecall.name.toLowerCase().indexOf(search) === -1;
            phonecall.$el.toggle(!flag);
        });
    },

    sip_ringing: function(){
        this.$big_call_button.html(_t("Calling..."));
        this.$hangup_button.removeAttr('disabled');
        this.widgets[this.current_phonecall].set_state('in_call');
    },

    sip_accepted: function(){
        new Model("crm.phonecall").call("init_call", [this.current_phonecall]);
        this.$('.oe_dial_transfer_button').removeAttr('disabled');
    },

    sip_incoming_call: function(){
        this.in_call = true;
        this.$big_call_button.html(_t("Calling..."));
        this.$hangup_transfer_buttons.removeAttr('disabled');
    },

    sip_end_incoming_call: function(){
        this.in_call = false;
        this.$big_call_button.html(_t("Call"));
        this.$hangup_transfer_buttons.attr('disabled','disabled');
    },

    sip_cancel: function(){
        this.in_call = false;
        this.widgets[this.current_phonecall].set_state('pending');
        new Model("crm.phonecall").call("rejected_call",[this.current_phonecall]);
        if(this.in_automatic_mode){
            this.next_call();
        }else{
            this.$big_call_button.html(_t("Call"));
            this.$hangup_transfer_buttons.attr('disabled','disabled');
            this.$(".popover").remove();
        }
    },

    sip_customer_unavailable: function(){
        this.do_notify(_t('Customer unavailable'),_t('The customer is temporary unavailable. Please try later.'));
    },

    sip_rejected: function(){
        this.in_call = false;
        new Model("crm.phonecall").call("rejected_call",[this.current_phonecall]);
        this.widgets[this.current_phonecall].set_state('pending');
        if(this.in_automatic_mode){
            this.next_call();
        }else{
            this.$big_call_button.html(_t("Call"));
            this.$hangup_transfer_buttons.attr('disabled','disabled');
            this.$(".popover").remove();
        }
    },

    sip_bye: function(){
        this.in_call = false;
        this.$big_call_button.html(_t("Call"));
        this.$hangup_transfer_buttons.attr('disabled','disabled');
        this.$(".popover").remove();
        new Model("crm.phonecall")
            .call("hangup_call", [this.current_phonecall])
            .then(_.bind(this.hangup_call,this));
    },

    hangup_call: function(result){
        var duration = parseFloat(result.duration).toFixed(2);
        this.log_call(duration);
        this.selected_phonecall = false;
    },

    sip_error: function(message, temporary){
        var self = this;
        this.in_call = false;
        this.$big_call_button.html(_t("Call"));
        this.$hangup_transfer_buttons.attr('disabled','disabled');
        this.$(".popover").remove();
        if(temporary){
            this.$().block({message: message});
            this.$('.blockOverlay').on("click",function(){self.sip_error_resolved();});
            this.$('.blockOverlay').attr('title',_t('Click to unblock'));
        }else{
            this.$().block({message: message + '<br/><button type="button" class="btn btn-danger btn-sm btn-configuration">Configuration</button>'});
            this.$('.btn-configuration').on("click",function(){
                //Call in order to get the id of the user's preference view instead of the user's form view
                new Model("ir.model.data").call("xmlid_to_res_model_res_id",["base.view_users_form_simple_modif"]).then(function(data){
                    web_client.action_manager.do_action(
                        {
                            name: "Change My Preferences",
                            type: "ir.actions.act_window",
                            res_model: "res.users",
                            res_id: real_session.uid,
                            target: "new",
                            xml_id: "base.action_res_users_my",
                            views: [[data[1], 'form']],
                        }
                    );
                });
            });
        }
    },

    sip_error_resolved: function(){
        this.$().unblock();
    },

    log_call: function(duration){
        var value = duration;
        var pattern = '%02d:%02d';
        var min = Math.floor(value);
        var sec = Math.round((value % 1) * 60);
        if (sec === 60){
            sec = 0;
            min = min + 1;
        }
        this.widgets[this.current_phonecall].duration = _.str.sprintf(pattern, min, sec);
        web_client.action_manager.do_action({
                name: _t('Log a call'),
                type: 'ir.actions.act_window',
                key2: 'client_action_multi',
                src_model: "crm.phonecall",
                res_model: "crm.phonecall.log.wizard",
                multi: "True",
                target: 'new',
                context: {'phonecall_id': this.current_phonecall,
                'default_opportunity_id': this.widgets[this.current_phonecall].opportunity_id,
                'default_name': this.widgets[this.current_phonecall].name,
                'default_duration': this.widgets[this.current_phonecall].duration,
                'default_description' : this.widgets[this.current_phonecall].description,
                'default_opportunity_name' : this.widgets[this.current_phonecall].opportunity_name,
                'default_opportunity_planned_revenue' : this.widgets[this.current_phonecall].opportunity_planned_revenue,
                'default_opportunity_title_action' : this.widgets[this.current_phonecall].opportunity_title_action,
                'default_opportunity_date_action' : this.widgets[this.current_phonecall].opportunity_date_action,
                'default_opportunity_probability' : this.widgets[this.current_phonecall].opportunity_probability,
                'default_partner_id': this.widgets[this.current_phonecall].partner_id,
                'default_partner_name' : this.widgets[this.current_phonecall].partner_name,
                'default_partner_phone' : this.widgets[this.current_phonecall].partner_phone,
                'default_partner_email' : this.widgets[this.current_phonecall].partner_email,
                'default_partner_image_small' : this.widgets[this.current_phonecall].image_small,
                'default_in_automatic_mode': this.in_automatic_mode,},
                views: [[false, 'form']],
                flags: {
                    'headless': true,
                },
            });
    },

    make_call: function(phonecall_id){
        if(!this.in_call){
            this.current_phonecall = phonecall_id;
            var number;
            if(!this.widgets[this.current_phonecall].partner_phone){
                this.do_notify(_t('The phonecall has no number'),_t('Please check if a phone number is given for the current phonecall'));
                return;
            }
            number = this.widgets[this.current_phonecall].partner_phone;
            //Select the current call if not already selected
            if(!this.selected_phonecall || this.selected_phonecall.id !== this.current_phonecall ){
                this.select_call(this.current_phonecall);
            }
            this.in_call = true;
            this.sip_js.make_call(number);
        }
    },

    next_call: function(){
        if(this.phonecalls_auto_call.length){
            if(!this.in_call){
                this.make_call(this.phonecalls_auto_call.shift());
            }
        }else{
            this.stop_automatic_call();
        }
    },

    stop_automatic_call: function(){
        this.in_automatic_mode = false;
        this.$(".oe_dial_split_call_button").show();
        this.$(".oe_dial_stop_autocall_button").hide();
        if(!this.in_call){
            this.$big_call_button.html(_t("Call"));
            this.$hangup_transfer_buttons.attr('disabled','disabled');
            this.$(".popover").remove();
        }else{
            this.$big_call_button.html(_t("Calling..."));
        }
    },

    //Get the phonecalls and create the widget to put inside the panel
    search_phonecalls_status: function(refresh_by_user) {
        var self = this;
        //get the phonecalls' information and populate the queue
        new Model("crm.phonecall").call("get_list").then(_.bind(self.parse_phonecall,self,refresh_by_user));
    },

    parse_phonecall: function(refresh_by_user,result){
        var self = this;
        _.each(self.widgets, function(w) {
            w.destroy();
        });                
        self.widgets = {};
        
        var phonecall_displayed = false;
        //for each phonecall display it only if the date is lower than the current one
        //if the refresh is done by the user, retrieve the phonecalls set as "done"
        _.each(result.phonecalls, function(phonecall){
            phonecall_displayed = true;
            if(refresh_by_user){
                if(phonecall.state !== "done"){
                    self.display_in_queue(phonecall);
                }else{
                    new Model("crm.phonecall").call("remove_from_queue",[phonecall.id]);
                }
            }else{
                self.display_in_queue(phonecall);
            }
        });
        if(!this.in_call){
            this.$hangup_transfer_buttons.attr('disabled','disabled');
        }

        if(!phonecall_displayed){
            this.$(".oe_dial_call_button, .oe_call_dropdown").attr('disabled','disabled');
        }else{
            this.$(".oe_dial_call_button, .oe_call_dropdown").removeAttr('disabled');
        }
        //select again the selected phonecall before the refresh
        if(this.selected_phonecall){
            this.select_call(this.selected_phonecall.id);
        }else{
            this.slide_down_optional_buttons();
        }
        if(this.current_call_deferred){
            this.current_call_deferred.resolve();
        }

    },

    //function which will add the phonecall in the queue and create the tooltip
    display_in_queue: function(phonecall){
        //Check if the current phonecall is currently done to add the microphone icon

        var widget = new PhonecallWidget(this, phonecall, this.formatCurrency);
        if(this.in_call && phonecall.id === this.current_phonecall){
            widget.set_state('in_call');
        }
        widget.appendTo(this.$(".oe_dial_phonecalls"));
        widget.on("select_call", this, this.select_call);
        widget.on("remove_phonecall",this,this.remove_phonecall);
        this.widgets[phonecall.id] = widget;
    },

    //action to change the main view to go to the opportunity's view
    to_lead: function() {
        this.widgets[this.selected_phonecall.id].to_lead();
    },

    //action to change the main view to go to the client's view
    to_client: function() {
        this.widgets[this.selected_phonecall.id].to_client();
    },

    //action to select a call and display the specific actions
    select_call: function(phonecall_id){
        var selected_phonecall = this.widgets[phonecall_id];
        if(!selected_phonecall){
            selected_phonecall = false;
            this.slide_down_optional_buttons();
            return;
        }
        if(this.optional_buttons_animated){
            return;
        }
        var selected = selected_phonecall.$el.hasClass("oe_dial_selected_phonecall");
        this.$(".oe_dial_selected_phonecall").removeClass("oe_dial_selected_phonecall");
        if(!selected){
            //selection of the phonecall
            selected_phonecall.$el.addClass("oe_dial_selected_phonecall");
            //if the optional buttons are not up, they are displayed
            this.slide_up_optional_buttons();
            //check if the phonecall has an email to display the send email button or not
            if(selected_phonecall.email){
                this.$(".oe_dial_email").show();
                this.$(".oe_dial_schedule_call").removeClass("oe_dial_schedule_full_width");
            }else{
                this.$(".oe_dial_email").hide();
                this.$(".oe_dial_schedule_call").addClass("oe_dial_schedule_full_width");
            }
        }else{
            //unselection of the phonecall
            selected_phonecall = false;
            this.slide_down_optional_buttons();
        }
        this.selected_phonecall = selected_phonecall;
    },

    //remove the phonecall from the queue
    remove_phonecall: function(phonecall_widget){
        var phonecall_model = new Model("crm.phonecall");
        var self = this;
        phonecall_model.call("remove_from_queue", [phonecall_widget.id]).then(function(){
            self.search_phonecalls_status();
            self.$(".popover").remove();
        });
    },

    //action done when the button "call" is clicked
    call_button: function(){
        if(this.selected_phonecall){
            this.make_call(this.selected_phonecall.id);
        }else{
            var next_call = _.filter(this.widgets, function(widget){return widget.state !== "done";}).shift();
            if(next_call){
                this.make_call(next_call.id);
            }
        }
    },

    auto_call_button: function(){
        var self = this;
        if(this.in_call){
            return;
        }
        this.$(".oe_dial_split_call_button").hide();
        this.$(".oe_dial_stop_autocall_button").show();
        this.in_automatic_mode = true;
        this.phonecalls_auto_call = [];
         _.each(this.widgets,function(phonecall){
            if(phonecall.state !== "done"){
                self.phonecalls_auto_call.push(phonecall.id);
            }
        });
        if(this.phonecalls_auto_call.length){
            this.make_call(this.phonecalls_auto_call.shift());
        }else{
            this.stop_automatic_call();
        }
    },

    //action done when the button "Hang Up" is clicked
    hangup_button: function(){
        this.sip_js.hangup();
    },

    //action done when the button "Transfer" is clicked
    transfer_button: function(){
        //Launch the transfer wizard
        web_client.action_manager.do_action({
            type: 'ir.actions.act_window',
            key2: 'client_action_multi',
            src_model: "crm.phonecall",
            res_model: "crm.phonecall.transfer.wizard",
            multi: "True",
            target: 'new',
            context: {},
            views: [[false, 'form']],
            flags: {
                'headless': true,
            },
        });
    },

    //action done when the transfer_call action is triggered
    transfer_call: function(number){
        this.sip_js.transfer(number);
    },

    //action done when the button "Reschedule Call" is clicked
    schedule_call: function(){
        this.widgets[this.selected_phonecall.id].schedule_call();
    },

    //action done when the button "Send Email" is clicked
    send_email: function(){
        this.widgets[this.selected_phonecall.id].send_email();
    },

    call_partner: function(number, partner_id){
        var partner_model = new Model("res.partner");
        var self = this;
        partner_model.call("create_call_in_queue", [partner_id, number]).then(function(phonecall_id){
            self.current_call_deferred = $.Deferred();
            self.search_phonecalls_status();
            self.current_call_deferred.done(function(){
                self.make_call(phonecall_id);
                if(!self.optional_buttons_shown){
                    self.button_up_deferred = $.Deferred();
                    self.button_up_deferred.done(function(){
                        self.scroll_down();
                    });
                }else{
                    self.scroll_down();
                }
            });
        });
    },

    scroll_down: function(){
        this.$('.oe_dial_phonecalls').animate({
            scrollTop: this.$('.oe_dial_phonecalls').prop('scrollHeight') - this.$('.oe_dial_phonecalls').innerHeight(),
        },1000);
    },
});
    
var VoipTopButton = Widget.extend({
    template:'crm_voip.switch_panel_top_button',
    events: {
        "click": "toggle_display",
    },

    // TODO remove and replace with session_info mechanism
    willStart: function(){
        var ready = this.session.user_has_group('base.group_user').then(
            function(is_employee){
                if (!is_employee) {
                    return $.Deferred().reject();
                }
            });
        return $.when(this._super.apply(this, arguments), ready);
    },

    toggle_display: function (ev){
        ev.preventDefault();
        core.bus.trigger('voip_toggle_display');
    },
});

// Put the ComposeMessageTopButton widget in the systray menu
SystrayMenu.Items.push(VoipTopButton);

//Trigger the client action "reload_panel" that will be catch by the widget to reload the panel
var reload_panel = function (parent, action) {
    var params = action.params || {};
    if(params.go_to_opp){
        //Call of the function xmlid_to_res_model_res_id to get the id of the opportunity's form view and not the lead's form view
        new Model("ir.model.data")
            .call("xmlid_to_res_model_res_id",["crm.crm_case_form_view_oppor"])
            .then(function(data){
                web_client.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: "crm.lead",
                    res_id: params.opportunity_id,
                    views: [[data[1], 'form']],
                    target: 'current',
                    context: {},
                    flags: {initial_mode: "edit",},
                });
            });
    }
    core.bus.trigger('reload_panel');

    if(params.in_automatic_mode){
        core.bus.trigger('next_call');
    }
    //Return an action to close the wizard after the reload of the panel
    return { type: 'ir.actions.act_window_close' };
};

var transfer_call = function(parent, action){
    var params = action.params || {};
    core.bus.trigger('transfer_call', params.number);
    return { type: 'ir.actions.act_window_close' };
};

core.action_registry.add("reload_panel", reload_panel);
core.action_registry.add("transfer_call", transfer_call);

// Redefinition of FieldPhone
core.form_widget_registry.get('phone').include({
    events: _.clone(core.form_widget_registry.get('phone').prototype.events),
    init: function() {
        this._super.apply(this, arguments);
        this.clickable = true;
        _.extend(this.events, {
            'click': function(e) {
                if(!this.get('effective_readonly') || this.getParent().dataset.model != 'res.partner') {
                    return;
                }

                e.preventDefault();
                var self = this;
                var phone_number = this.get('value');
                
                if(this.getParent().datarecord.phone === phone_number || this.getParent().datarecord.mobile === phone_number) {
                    this.do_notify(_t('Start Calling'),
                        _t('Calling ') + ' ' + phone_number);
                    if(this.DialingPanel) {
                        do_call();
                    } else {
                        // To get the formatCurrency function from the server
                        new Model("res.currency")
                            .call("get_format_currencies_js_function")
                            .then(function(data) {
                                var formatCurrency = new Function("amount, currency_id", data);
                                self.DialingPanel = new DialingPanel(web_client, formatCurrency);
                                do_call();
                            });
                    }
                }

                function do_call() {
                    self.DialingPanel.call_partner(phone_number, self.getParent().datarecord.id);
                }
            }
        });
    }
});

WebClient.include({
    show_application: function(){
        // To get the formatCurrency function from the server
        return this._super.apply(this, arguments).then(function () {
            new Model("res.currency")
                .call("get_format_currencies_js_function")
                .then(function(data) {
                    var formatCurrency = new Function("amount, currency_id", data);
                    self.DialingPanel = new DialingPanel(web_client, formatCurrency);
                });
        });
    },
});

return {
    voipTopButton: new VoipTopButton(),
};

});