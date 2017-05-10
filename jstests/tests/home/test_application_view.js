define([
    "home/models",
    "home/views/application_view",
    "components/vue/dist/vue",
    "vue/filters"
], function (models, application_view, Vue) {
    "use strict";

    QUnit.module("home.app_view");
    QUnit.test("rendering form", function (assert) {
        var done = assert.async();

        var model = new models.ApplicationListModel();

        var app_view = new application_view.ApplicationView({
            data: function() { return { model: model }; }
        }).$mount();

        model.update().done(function() { Vue.nextTick(function() {
            assert.equal(app_view.$el.children[0].tagName, 'DIV');
            assert.ok(app_view.$el.children[0].classList.contains('row'));

            // Simulate application starting
            model.app_list[0].status = 'STARTING';

            Vue.nextTick(function() {
                assert.ok(app_view.$el.querySelector('.start-button').disabled);

                done();
            });
        })});
    });

    // assert.equal(app_view.$el.children[0].tagName, 'IFRAME');
});
