/**
 * Licensed under the Apache License, Version 2.0 (the "License"); you may
 * not use this file except in compliance with the License. You may obtain
 * a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */

horizon.metering = {
  init_create_usage_report_form: function() {

    // Bind usage report datepickers
    var now = new Date();
    var tz = $("#timezone").val(now.getTimezoneOffset());
    var datepicker_selector = '#id_date_from, #id_date_to';
    $(datepicker_selector).each(function(datetimepickerOptions) {
        $(this).datetimepicker();
    });

    horizon.metering.add_change_event_to_period_dropdown();
    horizon.metering.show_or_hide_date_fields();
  },
  init_stats_page: function() {
    if (typeof horizon.d3_line_chart !== 'undefined') {
      horizon.d3_line_chart.init("div[data-chart-type='line_chart']",
                                 {'auto_resize': true});
    }
    horizon.metering.add_change_event_to_stats_period_dropdown();
    horizon.metering.show_or_hide_stats_date_fields();
  },
  show_or_hide_date_fields: function() {
    // For usage report page
    $("#id_date_from, #id_date_to").val('');
    if ($("#id_period").find("option:selected").val() === "other"){
      $("#id_date_from, #id_date_to").parent().parent().show();
      return true;
    } else {
      $("#id_date_from, #id_date_to").parent().parent().hide();
      return false;
    }
  },
  show_or_hide_stats_date_fields: function() {
    // For stats page
    $("#stats_date_from, #stats_date_to").val('');
    if ($("#date_options").find("option:selected").val() === "other"){
      $("#stats_date_from, #stats_date_to").parent().parent().show();
      return true;
    } else {
      $("#stats_date_from, #stats_date_to").parent().parent().hide();
      return false;
    }
  },

  add_change_event_to_stats_period_dropdown: function() {
    // Stats page
    $("#date_options").change(function(evt) {
        if (horizon.metering.show_or_hide_stats_date_fields()) {
          evt.stopPropagation();
        }
    });
  },
  add_change_event_to_period_dropdown: function() {
    // Usage report page
    $("#id_period").change(function(evt) {
        if (horizon.metering.show_or_hide_date_fields()) {
          evt.stopPropagation();
        }
    });
  }
};
