define([
  "components/vue/dist/vue",
  "jsapi/v1/resources",
  "admin/vue-components/containers/StopContainerDialog"
], function(Vue, resources, StopContainerDialog) {
  "use strict";

    return {
      components: {
        'stop-container-dialog': StopContainerDialog
      },
      template: 
        '<div class="row">' +
        '  <div class="col-md-12">' +
        '    <div class="box">' +
        '      <div class="box-header with-border">Containers</div>' +
        '      <div class="box-body">' +
        '        <div class="alert alert-danger" v-if="communicationError">' +
        '          <strong>Error:</strong> {{communicationError}}' +
        '        </div>' +
        '        <table id="datatable" class="display dataTable">' +
        '          <thead>' +
        '          <tr>' +
        '              <th>User</th>' +
        '              <th>Image</th>' +
        '              <th>Docker ID</th>' +
        '              <th>Mapping ID</th>' +
        '              <th>URL ID</th>' +
        '              <th>Stop</th>' +
        '          </tr>' +
        '          </thead>' +
        '          <tbody>' +
        '            <tr v-for="(c, index) in containers">' +
        '              <td>{{ c.user }}</td>' +
        '              <td>{{ c.image_name }}</td>' +
        '              <td>{{ c.docker_id | truncate }}</td>' +
        '              <td>{{ c.mapping_id | truncate }}</td>' +
        '              <td>{{ c.identifier | truncate }}</td>' +
        '              <td><button class="btn btn-danger" @click="stopAction(index)">Stop</button></td>' +
        '            </tr>' +
        '          </tbody>' +
        '        </table>' +
        '        <stop-container-dialog ' +
        '          v-if="showStopContainerDialog"' +
        '          :containerToStop="containerToStop"' +
        '          @stopped="containerStopped"' +
        '          @closed="stopContainerDialogClosed"></stop-container-dialog>' +
        '      </div>' +
        '    </div>' +
        '  </div>' +
        '</div>',
      data: function () {
        return {
          containers: [],
          showStopContainerDialog: false,
          communicationError: null,
          containerToStop: null,
        };
      },
      mounted: function () {
        this.updateTable();
      },
      methods: {
        updateTable: function() {
          this.communicationError = null;
          resources.Container.items()
            .done(
              (function (identifiers, items) {
                var containers = [];
                identifiers.forEach(function(id) {
                  var item = items[id];
                  item.identifier = id;
                  containers.push(item);
                });
                this.containers = containers;
              }).bind(this))
            .fail(
              (function () {
                this.communicationError = "The request could not be executed successfully";
              }).bind(this)
            );
        },
        containerStopped: function() {
          this.showStopContainerDialog = false;
          this.updateTable();
        },
        stopAction: function(index) {
          this.containerToStop = this.containers[index].identifier;
          this.showStopContainerDialog = true;
        },
        stopContainerDialogClosed: function() {
          this.showStopContainerDialog = false;
          this.containerToStop = null;
        }
      }
    };
  });
