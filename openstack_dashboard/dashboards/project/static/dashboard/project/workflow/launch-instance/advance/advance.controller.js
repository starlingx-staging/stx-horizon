/*
 *   Copyright (c) 2013-2017 Wind River Systems, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
(function () {
  'use strict';

  angular
    .module('horizon.dashboard.project.workflow.launch-instance')
    .controller('LaunchInstanceAdvanceController', LaunchInstanceAdvanceController);

  /**
   * @ngdoc controller
   * @name LaunchInstanceAdvanceController
   * @description
   *
   * The `LaunchInstanceAdvabceController` controller provides functions for
   * configuring the advabce step of the Launch Instance Wizard.
   *
   * @property {integer} min_inst_count, default to 0.
   */
  function LaunchInstanceAdvanceController() {
    var ctrl = this;

  }
})();
