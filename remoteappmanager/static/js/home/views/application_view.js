define([
    "urlutils",
    "utils",
    "../../components/vue/dist/vue",
    "admin/vue-components/toolkit/toolkit"
], function (urlUtils, utils, Vue) {
    "use strict";

    var ApplicationView = Vue.extend({
        template:
            '<!-- Application View -->' +
            '<section id="appview"' +
            '         v-if="currentApp !== null"' +
            '         :class="{ content: true, \'no-padding\': currentApp.isRunning() }">' +
            '  <!-- Error dialog -->' +
            '  <confirm-dialog v-if="startingError.show"' +
            '                  :title="\'Error when starting \' + startingError.appName"' +
            '                  :okCallback="closeDialog">' +
            '    <div class="alert alert-danger">' +
            '      <strong>Code: {{startingError.code}}</strong>' +
            '      <span>{{startingError.message}}</span>' +
            '    </div>' +
            '  </confirm-dialog>' +

            '  <!-- Start Form -->' +
            '  <transition name="fade" v-if="!currentApp.isRunning()">' +
            '  <div v-if="currentApp.isStopped()" class="row">' +
            '    <div class="col-md-offset-2 col-md-8">' +
            '      <div class="box box-primary">' +
            '        <div class="box-header with-border">' +
            '          <h3 class="box-title">{{ currentApp.appData.image | appName }}</h3>' +
            '          <div class="box-tools pull-right"></div>' +
            '        </div>' +
            '        <div class="box-body">' +
            '          <h4>Description</h4>' +
            '          <span id="app-description">{{ currentApp.appData.image.description }}</span>' +

            '          <h4>Policy</h4>' +

            '          <ul class="policy">' +
            '            <!-- Workspace -->' +
            '            <li v-if="appPolicy.allow_home">' +
            '                Workspace accessible' +
            '            </li>' +
            '            <li v-else>' +
            '                Workspace not accessible' +
            '            </li>' +

            '            <!-- Volume mounted -->' +
            '            <li v-if="appPolicy.volume_source && appPolicy.volume_target && appPolicy.volume_mode">' +
            '              Volume mounted: {{ appPolicy.volume_source }} &#x2192; {{ appPolicy.volume_target }} ({{ appPolicy.volume_mode }})' +
            '            </li>' +
            '            <li v-else>' +
            '              No volumes mounted' +
            '            </li>' +
            '          </ul>' +

            '          <h4>Configuration</h4>' +
            '          <form class="configuration">' +
            '            <fieldset v-if="currentApp.configurables.length === 0">No configurable options for this image</fieldset>' +
            '            <fieldset v-else :disabled="currentApp.isStarting()">' +
            '              <component v-for="configurable in currentApp.configurables"' +
            '                         :key="configurable.tag"' +
            '                         :is="configurable.tag + \'-component\'"' +
            '                         :configDict.sync="configurable.configDict"></component>' +
            '            </fieldset>' +
            '          </form>' +
            '        </div>' +

            '        <!-- Start Button -->' +
            '        <div class="box-footer">' +
            '          <button class="btn btn-primary pull-right start-button"' +
            '                  @click="startApplication()"' +
            '                  :disabled="currentApp.isStarting()">' +
            '            Start' +
            '          </button>' +
            '        </div>' +
            '      </div>' +
            '    </div>' +
            '  </div>' +
            '  </transition>' +

            '  <!-- Application View -->' +
            '  <iframe v-if="currentApp.isRunning()"' +
            '          id="application"' +
            '          frameBorder="0"' +
            '          :src="appSource"' +
            '          :style="{ minWidth: getIframeSize()[0] + \'px\', minHeight: getIframeSize()[1] + \'px\' }">' +
            '  </iframe>' +
            '</section>',

        data: function() {
            return {
                startingError: { show: false, appName: '', code: '', message: '' }
            };
        },

        computed: {
            currentApp: function() {
                return this.model.appList[this.model.selectedIndex] || null;
            },
            appPolicy: function() {
                return this.currentApp.appData.image.policy;
            },
            appSource: function() {
                var url = urlUtils.pathJoin(
                    window.apidata.base_url,
                    'containers',
                    this.currentApp.appData.container.url_id
                );
                var output = this.currentApp.delayed ? url : url + '/';

                this.currentApp.delayed = false;

                return output;
            }
        },

        methods: {
            startApplication: function() {
                var startingAppName = this.$options.filters.appName(this.currentApp.appData.image);
                this.$emit('startApplication', this.currentApp);
                this.model.startApplication().fail(function(error) {
                    this.startingError.code = error.code;
                    this.startingError.message = error.message;
                    this.startingError.appName = startingAppName;
                    this.startingError.show = true;
                }.bind(this));
            },
            closeDialog: function() {
                this.startingError.show = false;
            },
            getIframeSize: function() {
                return utils.maxIframeSize();
            },
            focusIframe: function() {
                var iframe = this.$el.querySelector('iframe');
                if(iframe !== null) {
                    iframe.focus();
                }
            }
        },

        updated: function() { this.focusIframe(); }
    });

    return {
        ApplicationView : ApplicationView
    };
});
