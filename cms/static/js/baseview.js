define(
    [
        'jquery',
        'underscore',
        'backbone'
    ],
    function ($, _, Backbone) {
        var BaseView = function (options) {
            this.bindings = [];
            return Backbone.View.apply(this, [options]);
        };

        _.extend(BaseView.prototype, Backbone.View.prototype, {

            initialize: function(options) {
            _.bindAll(this, 'beforeRender', 'render', 'afterRender');
                var _this = this;
                this.render = _.wrap(this.render, function(render) {
                    _this.beforeRender();
                    render();
                    _this.afterRender();
                    return _this;
                });
            },

            beforeRender: function() {
            },

            render: function() {
                return this;
            },

            afterRender: function() {
                this.handle_iframe_binding();
            },

            handle_iframe_binding: function() {
                $(document).ready(function() {
                    $("iframe").each(function(){
                        var ifr_source = $(this).attr('src');
                        var wmode = "wmode=transparent";
                        if(ifr_source.indexOf('?') != -1) {
                            var getQString = ifr_source.split('?');
                            var oldString = getQString[1];
                            var newString = getQString[0];
                            $(this).attr('src',newString+'?'+wmode+'&'+oldString);
                        }
                        else $(this).attr('src',ifr_source+'?'+wmode);
                    });
                });
            }
        });

        BaseView.extend = Backbone.View.extend;

        return BaseView;

    });