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

/* Namespace for core functionality related to DataTables. */
horizon.datatables = {
  update: function () {
    if (horizon.datatables.timeout) {
      clearTimeout(horizon.datatables.timeout);
      horizon.datatables.timeout = false;
    }
    var $rows_to_update = $('tr.warning.ajax-update');
    var $table = $rows_to_update.closest('table');
    var interval = $rows_to_update.attr('data-update-interval');
    var decay_constant = $table.attr('decay_constant');
    var requests = [];

    // do nothing if there are no rows to update.
    if($rows_to_update.length <= 0) { return; }

    // Do not update this row if the action column is expanded
    if ($rows_to_update.find('.actions_column .btn-group.open').length) {
      // Wait and try to update again in next interval instead
        horizon.datatables.timeout = false;
      // Remove interval decay, since this will not hit server
      $table.removeAttr('decay_constant');
      return;
    }

    $rows_to_update.each(function() {
      var $row = $(this);
      var $table = $row.closest('table.datatable');
            // Performance optimization - disable row refresh to reduce
            // platform load since we already have periodic page refresh.
            // This row update is now used solely to do an immediate rendering
            // of progress bars
            var $new_row = $row;

            if ($new_row.hasClass('warning')) {
              var $container = $(document.createElement('div'))
                .addClass('progress-text horizon-loading-bar');

              var $progress = $(document.createElement('div'))
                .addClass('progress progress-striped active')
                .appendTo($container);

              // CGCS: incomplete progress bar addition
              $width = $new_row.find('[percent]:first').attr('percent') || "100%";

              $(document.createElement('div'))
                .addClass('progress-bar')
                .css("width", $width)
                .appendTo($progress);

              // if action/confirm is required, show progress-bar with "?"
              // icon to indicate user action is required
              if ($new_row.find('.btn-action-required').length > 0) {
                $(document.createElement('span'))
                  .addClass('fa fa-question-circle progress-bar-text')
                  .appendTo($container);
              }
              $new_row.find("td.warning:last").prepend($container);
            }
    });
  },

  update_actions: function() {
    var $actions_to_update = $('.btn-launch.ajax-update, .btn-create.ajax-update');
    $actions_to_update.each(function() {
      var $action = $(this);
      horizon.ajax.queue({
        url: $action.attr('data-update-url'),
        error: function () {
          console.log(gettext("An error occurred while updating."));
        },
        success: function (data) {
          var $new_action = $(data);

          // Only replace row if the html content has changed
          if($new_action.html() != $action.html()) {
            $action.replaceWith($new_action);
            // Recompile if it has AngularJS controller
            if(typeof($new_action.attr('ng-controller')) !== "undefined") {
              recompileAngularContent($new_action);
            }
          }
        }
      });
    });
  },

  validate_button: function ($form, disable_button) {
    // Enable or disable table batch action buttons and more actions dropdown based on row selection.
    $form = $form || $(".table_wrapper > form");
    $("table.datatable thead .multi_select_column").each(function (i, thead) {
      var table = $(thead).parents("table");
      var checkboxes = $(table).find('tbody :checkbox');
      var buttons = $(table).find('.table_actions button[data-batch-action="true"]');
      var menu = $(table).find('.table_actions .table_actions_menu > a.dropdown-toggle');

      if(!checkboxes.length) {
        if(menu.length) {
          menu.hide();
        }
        buttons.hide();
        return;
      }
      buttons.removeClass("disabled");
      buttons.show();
      menu.removeClass("disabled");
      menu.show();
      if(!checkboxes.filter(":checked").length) {
        buttons.addClass("disabled");
        menu.addClass("disabled");
      }
    });
  },

  initialize_checkboxes_behavior: function() {
    // Bind the "select all" checkbox action.
    $('.table_wrapper, #modal_wrapper')
      .on('change', '.table-row-multi-select', function() {
        var $this = $(this);
        var $table = $this.closest('table');
        var is_checked = $this.prop('checked');

        if ($this.hasClass('multi-select-header')) {

          // Only select / deselect the visible rows
          $table.find('tbody tr:visible .table-row-multi-select')
            .prop('checked', is_checked);

        } else {

          // Find the master checkbox
          var $multi_select_checkbox = $table.find('.multi-select-header');

          // Determine if there are any unchecked checkboxes in the table
          var $checkboxes = $table.find('tbody .table-row-multi-select');
          var not_checked = $checkboxes.not(':checked').length;
          is_checked = $checkboxes.length != not_checked;

          // If there are none, then check the master checkbox
          $multi_select_checkbox.prop('checked', not_checked == 0);
        }

        // Pass in whether it should be visible, no point in doing this twice
        horizon.datatables.validate_button($this.closest('form'), !is_checked);
      });
  },

  initialize_table_tooltips: function() {
    $('div.table_wrapper').tooltip({selector: '[data-toggle="tooltip"]', container: 'body'});
  },

  disable_actions_on_submit: function($form) {
    // This applies changes to the table form when a user takes an action that
    // submits the form. It relies on the form being re-rendered after the
    // submit is completed to remove these changes.
    $form = $form || $(".table_wrapper > form");
    $form.on("submit", function () {
      var $this = $(this);
      // Add the 'submitted' flag to the form so the row update interval knows
      // not to update the row and therefore re-enable the actions that we are
      // disabling here.
      $this.attr('data-submitted', 'true');
      // Disable row action buttons. This prevents multiple form submission.
      $this.find('td.actions_column button[type="submit"]').addClass("disabled");
      // Use CSS to update the cursor so it's very clear that an action is
      // in progress.
      $this.addClass('wait');
    });
  }
};

/* Generates a confirmation modal dialog for the given action. */
horizon.datatables.confirm = function(action) {
  var $action = $(action);

  if ($action.hasClass("disabled")) {
    return;
  }

  var $uibModal_parent = $action.closest('.modal');
  var name_array = [];
  var action_string = $action.text();
  var help_text = $action.attr("help_text") || "";
  var cancel_string, confirm_class;
  var name_string = "";

  // Assume that we are going from the "Network Topology" tab
  // If we trying perform an action on a port or subnet
  var $closest_tr = $action.closest("tr");
  var $data_display = $closest_tr.find('span[data-display]');
  if ($data_display.length > 0){
    name_string = ' "' + $data_display.attr("data-display") + '"';
    name_array = [name_string];
  } else {
    // Else we trying to perform an action on device
    var $device_window = $('div.topologyBalloon');
    var $device_table = $device_window.find('table.detailInfoTable').has('caption[data-display]');
    var $data_display = $device_table.find('caption[data-display]');
    if ($data_display.length > 0){
      name_string = ' "' + $data_display.attr("data-display") + '"';
      name_array = [name_string];
    }
  }

  // Add the display name defined by table.get_object_display(datum)
  var $closest_table = $action.closest("table");

  // Check if data-display attribute is available
  $data_display = $closest_table.find('tr[data-display]');
  if ($data_display.length > 0) {
    var $actions_div = $action.closest("div");
    if ($actions_div.hasClass("table_actions") || $actions_div.hasClass("table_actions_menu")) {
      // One or more checkboxes selected
      $data_display.has(".table-row-multi-select:checked").each(function() {
        name_array.push(" \"" + $(this).attr("data-display") + "\"");
      });
      name_string = name_array.join(", ");
    } else {
      // If no checkbox is selected
      name_string = " \"" + $action.closest("tr").attr("data-display") + "\"";
      name_array = [name_string];
    }
  } else{
    // Probably we are getting the action from a detail view, so we try to get
    // the data-display from a dd element instead
    $data_display = $('dd[data-display]');
    if($data_display.length > 0) {
      name_string = ' "' + $('dd[data-display]').attr("data-display") + '"';
      name_array = [name_string];
    }
  }

  var title = interpolate(gettext("Confirm %s"), [action_string]);

  // compose the action string using a template that can be overridden
  var template = horizon.templates.compiled_templates["#confirm_modal"],
  params = {
    selection: name_string,
    selection_list: name_array,
    help: help_text
  };

  var body;
  try {
    // Check for confirm message on the action.get_confirm_message,
    if ($action.is('[data-confirm]')) {
      body = $action.attr('data-confirm');
    }
    // Check for confirm message on the table.get_action_confirm(datum)
    else if ($action.closest('tr').is('[data-confirm]')) {
      body = body = $action.closest('tr').attr('confirm');
    }
    // Default to generic confirmation message
    else {
      body = $(template.render(params)).html();
    }
  } catch (e) {
    body = name_string + gettext("Please confirm your selection. ") + help_text;
  }

  cancel_string = gettext("Cancel")
  if($action.is('[data-confirm-class]')) {
    confirm_class = $action.attr('data-confirm-class');
  }
  // CGCS: get form before confirm modal making sure that form is valid
  //       as it may get changed after confirm modal is created
  $form = $action.closest('form');

  horizon.modals.confirm = horizon.modals.create(title, body, action_string, cancel_string, confirm_class);
  horizon.modals.confirm.modal();

  if ($uibModal_parent.length) {
    var child_backdrop = horizon.modals.confirm.next('.modal-backdrop');
    // re-arrange z-index for these stacking modal
    child_backdrop.css('z-index', $uibModal_parent.css('z-index')+10);
    horizon.modals.confirm.css('z-index', child_backdrop.css('z-index')+10);
  }

  horizon.modals.confirm.find('.btn-submit').click(function (evt) {
    var el = document.createElement("input");
    el.type = 'hidden';
    el.name = $action.attr('name');
    el.value = $action.attr('value');
    $form
      .append(el)
      .submit();

    horizon.modals.confirm.modal('hide');
    horizon.modals.confirm = null;
    horizon.modals.modal_spinner(gettext("Working"));
    return false;
  });

  return horizon.modals.confirm;
};

$.tablesorter.addParser({
  // set a unique id
  id: 'sizeSorter',
  is: function() {
    // Not an auto-detected parser
    return false;
  },
  // compare int values
  format: function(s) {
    var sizes = {
      BYTE: 0,
      B: 0,
      KB: 1,
      MB: 2,
      GB: 3,
      TB: 4,
      PB: 5
    };
    var regex = /([\d\.,]+)\s*(byte|B|KB|MB|GB|TB|PB)+/i;
    var match = s.match(regex);
    if (match && match.length === 3){
      return parseFloat(match[1]) *
        Math.pow(1024, sizes[match[2].toUpperCase()]);
    }
    return parseInt(s, 10);
  },
  type: 'numeric'
});

$.tablesorter.addParser({
  // set a unique id
  id: 'timesinceSorter',
  is: function() {
    // Not an auto-detected parser
    return false;
  },
  // compare int values
  format: function(s, table, cell) {
    return $(cell).find('span').data('seconds');
  },
  type: 'numeric'
});

$.tablesorter.addParser({
  id: "timestampSorter",
  is: function() {
    return false;
  },
  format: function(s) {
    s = s.replace(/\-/g, " ").replace(/:/g, " ");
    s = s.replace("T", " ").replace("Z", " ");
    s = s.split(" ");
    return new Date(s[0], s[1], s[2], s[3], s[4], s[5]).getTime();
  },
  type: "numeric"
});

$.tablesorter.addParser({
  id: 'IPv4Address',
  is: function(s, table, cell) {
    // The first arg to this function is a string of all the cell's innertext smashed together
    // with no delimiters, so to make this work with the Instances and Ports tables where the
    // IP address cell content is an unordered list we need to check the content of the first
    // <li> element. In the Floating IPs and Subnets tables the cell content is not a list so
    // we just check the cell content directly.
    var a = $(cell).find('li').first().text().split('.');
    if (a.length === 1 && a[0] === '') {
      a = s.split('.');
    }
    if (a.length !== 4) {
      return false;
    }
    for (var i = 0; i < a.length; i++) {
      if (isNaN(a[i])) {
        return false;
      }
      if ((a[i] & 0xFF) != a[i]) {
        return false;
      }
    }
    return true;
  },
  format: function(s, table, cell) {
    var result = 0;
    var a = $(cell).find('li').first().text().split('.');
    if (a.length === 1 && a[0] === '') {
      a = s.split('.');
    }
    var last_index = a.length - 1;
    // inet_aton(3), Javascript-style.  The unsigned-right-shift operation is
    // needed to keep the result from flipping over to negative when suitably
    // large values are generated
    for (var i = 0; i < a.length; i++) {
      var shift = 8 * (last_index - i);
      result += ((parseInt(a[i], 10) << shift) >>> 0);
    }
    return result;
  },
  type: 'numeric'
});

$.tablesorter.addParser({
    id: 'portnameSorter',
    is: function(s) {

    },
    format: function(s) {
      var ethNum = s.replace( /^\D+/g, '');
      return parseInt(ethNum, 10);
    },
    type: 'numeric'
});

$.tablesorter.addParser({


    // set a unique id
    id: 'uptimeSorter',
    is: function(s) {
        // Not an auto-detected parser
        return false;
    },
    // compare int values
    format: function(s) {

    var timesSec = new Array();
    timesSec[0] = 31104000;
    timesSec[1] = 2592000;
    timesSec[2] = 86400;
    timesSec[3] = 3600;
    timesSec[4] = 60;

     var times = s.split(/[\s,]+/);

      if ((times[1].toUpperCase() == "YEARS") || (times[1].toUpperCase() == "YEAR")) {
         var years = times[0].replace( /[^\d.]/g, '' );
         if (times.length > 2){
            var months = times[2].replace( /[^\d.]/g, '' );
            var uptime_date = parseInt(years) * timesSec[0]  + parseInt(months) * timesSec[1];
         } else {
            var uptime_date = parseInt(years) * timesSec[0];
         }
      } else if ((times[1].toUpperCase() == "MONTHS") || (times[1].toUpperCase() == "MONTH")) {
         var months = times[0].replace( /[^\d.]/g, '' );
         if (times.length > 2){
            var days = times[2].replace( /[^\d.]/g, '' );
            var uptime_date = parseInt(months) * timesSec[1] + parseInt(days) * timesSec[2];
         } else {
            var uptime_date = parseInt(months) * timesSec[1];
         }

      } else if ((times[1].toUpperCase() == "DAYS") || (times[1].toUpperCase() == "DAY")){
          var days = times[0].replace( /[^\d.]/g, '' );
	  if (times.length > 2){
            var hours = times[2].replace( /[^\d.]/g, '' );
            var uptime_date = parseInt(days) * timesSec[2] + parseInt(hours) * timesSec[3];
           } else {
            var uptime_date = parseInt(days) * timesSec[2];
        }

      } else if ((times[1].toUpperCase() == "HOURS") || (times[1].toUpperCase() == "HOUR")){
	var hours = times[0].replace( /[^\d.]/g, '' );
        if (times.length > 2){
          var minuites = times[2].replace( /[^\d.]/g, '' );
          var uptime_date = parseInt(hours) * timesSec[3] + parseInt(minuites) * timesSec[4];

        } else {
          var uptime_date = parseInt(hours) * timesSec[3];
        }


      } else {
          var minuites = times[0].replace( /[^\d.]/g, '' );
	  var uptime_date = parseInt(minuites) * timesSec[4];
      }

     return uptime_date;

    },
    type: 'numeric'
});

horizon.datatables.disable_buttons = function() {
  $("table .table_actions").on("click", ".btn.disabled", function(event){
    event.preventDefault();
    event.stopPropagation();
  });
};

$.tablesorter.addParser({
  id: 'uuid',
  is: function() {
    return false;
  },
  format: function(s) {
    // Calculate a float that is based on the strings alphabetical position.
    //
    // Each character in the string has some significance in the
    // overall calculation, starting at 1.0 and is divided down by 2 decimal
    // places according to the chars position in the string.
    // For example the string "SO" would become 83.79 which is then
    // numerically comparable to other strings.
    s = s.toUpperCase();
    var value = 0.0;
    for(var i = 0; i < s.length; i++) {
      var char_offset = 1.0 / Math.pow(100, i);
      value = value + (s.charCodeAt(i) * char_offset);
    }
    return value;
  },
  type: 'numeric'
});

horizon.datatables.update_footer_count = function (el, modifier) {
  var $el = $(el),
    $browser, $header, $footer, row_count, footer_text_template, footer_text;
  if (!modifier) {
    modifier = 0;
  }
  // code paths for table or browser footers...
  $browser = $el.closest("#browser_wrapper");
  if ($browser.length) {
    $footer = $browser.find('.tfoot span.content_table_count');
  }
  else {
    $header = $el.find('thead span.table_count');
    $footer = $el.find('tfoot span.table_count');
  }
  row_count = $el.find('tbody tr:visible').length + modifier - $el.find('.empty').length;
  if (row_count) {
    footer_text_template = ngettext("Displaying %s item", "Displaying %s items", row_count);
    footer_text = interpolate(footer_text_template, [row_count]);
  } else {
    footer_text = '';
  }
  if ($header) {
    $header.text(footer_text);
  }
  $footer.text(footer_text);
  return row_count;
};

horizon.datatables.add_no_results_row = function (table) {
  // Add a "no results" row if there are no results.
  var template = horizon.templates.compiled_templates["#empty_row_template"];
  if (!table.find("tbody tr:visible").length && typeof(template) !== "undefined" && table.find("tbody:visible").length ) {
    var colspan = table.find('.table_column_header th').length;
    var params = {
        "colspan": colspan,
        no_items_label: gettext("No items to display.")
    };
    table.find("tbody").append(template.render(params));
  }
};

horizon.datatables.remove_no_results_row = function (table) {
  table.find("tr.empty").remove();
};

horizon.datatables.replace_row = function (old_row, new_row) {
    // Directly accessing the checked property of the element
    // is MUCH faster than using jQuery's helper method
    var $checkbox = old_row.find('.table-row-multi-select');
    if($checkbox.length && $checkbox[0].checked) {
      // Preserve the checkbox if it's already clicked
      new_row.find('.table-row-multi-select').prop('checked', true);
    }
    new_row.addClass("updated");
    old_row.replaceWith(new_row);
};

horizon.datatables.remove_row = function (table, row) {
    // Update the footer count and reset to default empty row if needed
    var row_count, colspan, template, params, empty_row;

    // existing count minus one for the row we're removing
    row_count = horizon.datatables.update_footer_count(table, -1);
    if(row_count === 0) {
        colspan = table.find('th[colspan]').attr('colspan');
        template = horizon.templates.compiled_templates["#empty_row_template"];
        params = {"colspan": colspan};
        empty_row = template.render(params);
        row.replaceWith(empty_row);
    } else {
        row.remove();
    }
};

/*
 * Fixes the striping of the table after filtering results.
 **/
horizon.datatables.fix_row_striping = function (table) {
  table.trigger('applyWidgetId', ['zebra']);
};

horizon.datatables.set_table_sorting = function (parent) {
// Function to initialize the tablesorter plugin strictly on sortable columns.
  $(parent).find("table.datatable").each(function () {
    var $table = $(this),
      header_options = {};
      $table.find("thead th[class!='table_header']").each(function (i) {
        var $th = $(this);
        if (!$th.hasClass('sortable')) {
          header_options[i] = {sorter: false};
        } else if ($th.data('type') === 'size'){
          header_options[i] = {sorter: 'sizeSorter'};
        } else if ($th.data('type') === 'ip'){
          header_options[i] = {sorter: 'IPv4Address'};
        } else if ($th.data('type') === 'timesince'){
          header_options[i] = {sorter: 'timesinceSorter'};
        } else if ($th.data('type') === 'timestamp'){
          header_options[i] = {sorter: 'timestampSorter'};
        } else if ($th.data('type') == 'uuid'){
          header_options[i] = {sorter: 'uuid'};
        } else if ($th.data('type') == 'uptime'){
            header_options[i] = {sorter: 'uptimeSorter'};
        } else if ($th.data('type') == 'portname'){
            header_options[i] = {sorter: 'portnameSorter'};
        }
      });
      $table.tablesorter({
        headers: header_options,
        widgets: ['zebra'],
        selectorHeaders: "thead th[class!='table_header']",
        cancelSelection: false,
        emptyTo: 'none',
        headerTemplate: '{content}{icon}',
        cssIcon: 'table-sort-indicator'
      });
  });
};

horizon.datatables.add_table_checkboxes = function($parent) {
  $($parent).find('table thead .multi_select_column').each(function() {
    var $thead = $(this);
    if (!$thead.find('.table-row-multi-select').length &&
      $thead.parents('table').find('tbody .table-row-multi-select').length) {

      // Build up the themable checkbox
      var $container = $(document.createElement('div'))
        .addClass('themable-checkbox');

      // Create the input checkbox
      var $input = $(document.createElement('input'))
        .attr('type', 'checkbox')
        .addClass('table-row-multi-select multi-select-header')
        .uniqueId()
        .appendTo($container);

      // Create the label
      $(document.createElement('label'))
        .attr('for', $input.attr('id'))
        .appendTo($container);

      // Append to the thead last, for speed
      $thead.append($container);
    }
  });
};

horizon.datatables.set_table_query_filter = function (parent) {
  horizon.datatables.qs = {};
  $(parent).find('table').each(function (index, elm) {
    var input = $($(elm).find('div.table_search.client input')),
        table_selector;
    if (input.length > 0) {
      // Disable server-side searching if we have client-side searching since
      // (for now) the client-side is actually superior. Server-side filtering
      // remains as a noscript fallback.
      // TODO(gabriel): figure out an overall strategy for making server-side
      // filtering the preferred functional method.
      input.on('keypress', function (evt) {
        if (evt.keyCode === 13) {
          return false;
        }
      });
      input.next('button.btn span.search-icon').on('click keypress', function () {
        return false;
      });

      // Enable the client-side searching.
      table_selector = 'table#' + $(elm).attr('id');
      var qs = input.quicksearch(table_selector + ' tbody tr', {
        'delay': 300,
        'loader': 'span.loading',
        'bind': 'keyup',
        'show': this.show,
        'hide': this.hide,
        onBefore: function () {
          var table = $(table_selector);
          horizon.datatables.remove_no_results_row(table);
        },
        onAfter: function () {
          var table = $(table_selector);
          horizon.datatables.update_footer_count(table);
          horizon.datatables.add_no_results_row(table);
          horizon.datatables.fix_row_striping(table);
        },
        prepareQuery: function (val) {
          return new RegExp(horizon.string.escapeRegex(val), "i");
        },
        testQuery: function (query, txt, _row) {
          return query.test($(_row).find('td:not(.hidden):not(.actions_column)').text());
        }
      });
      horizon.datatables.qs[$(elm).attr('id')] = qs;
    }
  });
};

horizon.datatables.set_table_fixed_filter = function (parent) {
  $(parent).find('table.datatable').each(function (index, elm) {
    $(elm).on('click', 'div.table_filter button', function(evt) {
      // Remove active class from all buttons
      $(elm).find('div.table_filter button').each(function(index, btn) {
        $(btn).removeClass('active');
      });
      var table = $(elm);
      var category = $(this).val();
      evt.preventDefault();
      horizon.datatables.remove_no_results_row(table);
      table.find('tbody tr').hide();
      table.find('tbody tr.category-' + category).show();
      horizon.datatables.update_footer_count(table);
      horizon.datatables.add_no_results_row(table);
      horizon.datatables.fix_row_striping(table);
    });
    $(elm).find('div.table_filter button').each(function (i, button) {
      // Select the first non-empty category
      if ($(button).text().indexOf(' (0)') === -1) {
        $(button).trigger('click');
        return false;
      }
    });
  });
};
horizon.datatables.set_table_fixedwithquery_filter = function (parent) {

  bind_buttons = function() {

          grpIt = function(srchstr, grpNo) {
                newSrch = srchstr.replace("div.table_filter_fixedwithquery","div.table_filter_fixedwithquery"+grpNo);
                return newSrch;
          }

          $(parent).find('table.datatable').each(function (index, elm) {

            var maxBtnGroup = 0;

            getMaxButtonGroups = function(elm) {
                var _maxBtnGroup = 0;
                while ( ($(elm).find(grpIt("div.table_filter_fixedwithquery button",_maxBtnGroup)).length) > 0) {
                    _maxBtnGroup++;
                }
                return _maxBtnGroup
            }

            maxBtnGroup = getMaxButtonGroups(elm);

            getValueFromGroup = function(grpNo, elm) {
                var val = $(elm).find(grpIt("div.table_filter_fixedwithquery button.active",grpNo)).val();
                return val;
            }

            getAllValuesFromGroups = function(_maxBtnGroup, elm) {
                values = [];
                for (var grpNo=0;grpNo<_maxBtnGroup;grpNo++) {
                    values.push( getValueFromGroup(grpNo, elm) );
                }
                result = values.join("|");
                return result;
            }

            // define the group binding functions
            createGrpBindFunction = function(grpNo, _maxBtnGroup, elm) {
               return function() {

                        $(elm).on('click', grpIt('div.table_filter_fixedwithquery button',grpNo), function(evt) {
                          // Remove active class from all buttons
                          var _grNo = grpNo;
                          $(elm).find(grpIt('div.table_filter_fixedwithquery button',grpNo)).each(function(index, btn) {
                            $(btn).removeClass('active');
                          });
                          var table = $(elm);

                          // hilite active button and indicate busy by changing its cursor

                          $(this).addClass('active');
                          $(this).css("cursor","wait");

                          //var selectedValue = $(this).val();
                          //var selectedValue = getValueFromGroup(grpNo);
                          var selectedValue = getAllValuesFromGroups(_maxBtnGroup, elm);

                          // ensure selectedValue sent down to server on form submit
                          $('div.table_filter_fixedwithquery_groups input[type="hidden"]').val(selectedValue)

                          formElm = this.closest('form');

                          formElm.submit();

                          evt.preventDefault();
                          return false;
                        });
                }
            }
            // now instantiate one group binding function per group and then run it
            for (var grpNo=0;grpNo<maxBtnGroup;grpNo++) {
                createGrpBindFunction(grpNo,maxBtnGroup,elm)();
            }

          });
  }

  bind_buttons();

  // Note: This code was mostly copied from function set_table_query_filter
  $(parent).find('table.datatable').each(function (index, elm) {

    var input = $($(elm).find('div.table_search_fixedwithquery.client input')),
        table_selector;
    if (input.length > 0) {

      // Disable server-side searching if we have client-side searching since
      // (for now) the client-side is actually superior. Server-side filtering
      // remains as a noscript fallback.
      // TODO(gabriel): figure out an overall strategy for making server-side
      // filtering the preferred functional method.
      input.on('keypress', function (evt) {
        if (evt.keyCode === 13) {
          return false;
        }
      });
      input.next('button.btn span.search-icon').on('click keypress', function (evt) {
        return false;
      });

      // Enable the client-side searching.
      table_selector = 'table#' + $(elm).attr('id');

      var qs = input.quicksearch(table_selector + ' tbody tr', {
        'delay': 300,
        'loader': 'span.loading',
        'bind': 'keyup click',
        'show': this.show,
        'hide': this.hide,
        onBefore: function () {
          var table = $(table_selector);
          horizon.datatables.remove_no_results_row(table);
        },
        onAfter: function () {
          var template, table, colspan, params;
          table = $(table_selector);
          horizon.datatables.update_footer_count(table);
          horizon.datatables.add_no_results_row(table);
          horizon.datatables.fix_row_striping(table);
        },
        prepareQuery: function (val) {
          return new RegExp(val, "i");
        },
        testQuery: function (query, txt, _row) {
          return query.test($(_row).find('td:not(.hidden):not(.actions_column)').text());
        }
      });
      horizon.datatables.qs[$(elm).attr('id')] = qs;
    }
  });


};


horizon.datatables.set_table_limit = function (parent) {
  $(parent).find('table').each(function (index, elm) {
    var limits = $(elm).find('div.table_limit ul.dropdown-menu > li > a').on('click', function(e) {
        e.preventDefault();

        var $limit = $(this);
        var $table = $limit.closest('table');

        var pagination_param = $table.data('pagination-param');
        var limit_param = $table.data('limit-param');
        var count = $limit.data('count');
        var title = $limit.attr('title');

        window.location.search = jQuery.query.remove(pagination_param).set(limit_param, count);
    });
  });
};

// Auto page refresh handler
horizon.datatables.refresh = function (html) {
    var refreshed = true;

    refresh_start_time = new Date().getTime();

    $(html).find('table.datatable').each(function(index, table) {
        var $new_table = $(this);
        var $old_table = $('table#' + $new_table.attr('id'));
        var changed = false;
        var row_changed = false;

        // Do not update the table if an action column is expanded
        if ($old_table.find('.actions_column .btn-group.open').length) {
            return true;
        }

        if (horizon.modals.confirm && horizon.modals.confirm.is(":visible")) {
            return true;
        }

        // Cleanup updated state
        $old_table.find('tr.updated').removeClass('updated flash');

        no_results_row_removed = false;

        // Remove old entries that no longer exist
        $old_table.find('tbody > tr[id]').not('.empty').each(function(index, row) {
            var $old_row = $(this);
            var $new_row = $new_table.find('tr#' + $old_row.attr('id').replace(/[!"#$%&'()*+,.\/:;<=>?@[\\\]^`{|}~]/g, "\\$&"));

            if (!$new_row.length) {
                // Remove stale entry from table
                $old_row.remove();
                changed = true;
            }
        });

        // Insert or update new entries
        $($new_table.find('tbody > tr[id]').get().reverse()).not('.empty').each(function(index, row) {
            row_changed = false;
            var $new_row = $(this);
            var $old_row = $old_table.find('tr#' + $new_row.attr('id').replace(/[!"#$%&'()*+,.\/:;<=>?@[\\\]^`{|}~]/g, "\\$&"));

            if ($old_row.length) {
                // Only replace row if the html content has changed, or it is in the warning state
                if($new_row.text() != $old_row.text() || $new_row.hasClass('warning')) {
                    horizon.datatables.replace_row($old_row, $new_row);
                    changed = true;
                    row_changed = true;
                }
            } else {
                // Append the new row since it does not exist in the current table
                if (!no_results_row_removed) {
                   no_results_row_removed = true;
                   horizon.datatables.remove_no_results_row($old_table);
                }
                $new_row.addClass("updated");
                $old_table.find('tbody').prepend($new_row);
                changed = true;
                row_changed = true;
            }
            if (row_changed) {
                // CGCS: The following code is from the upstream row update
                // functionality and must be kept up to date
                if ($new_row.hasClass('warning')) {
                  var $container = $(document.createElement('div'))
                    .addClass('progress-text horizon-loading-bar');

                  var $progress = $(document.createElement('div'))
                    .addClass('progress progress-striped active')
                    .appendTo($container);

                  // CGCS: incomplete progress bar addition
                  $width = $new_row.find('[percent]:first').attr('percent') || "100%";

                  $(document.createElement('div'))
                    .addClass('progress-bar')
                    .css("width", $width)
                    .appendTo($progress);

                  // if action/confirm is required, show progress-bar with "?"
                  // icon to indicate user action is required
                  if ($new_row.find('.btn-action-required').length > 0) {
                    $(document.createElement('span'))
                      .addClass('fa fa-question-circle progress-bar-text')
                      .appendTo($container);
                  }
                  $new_row.find("td.warning:last").prepend($container);
                }
            }
        });

        // Update the table actions (which can be affected by system state or quotas)
        $new_table.find('.table_actions').children('.btn').each(function(index, action) {
            var $new_action = $(this);
            var $old_action = $old_table.find('#' + $new_action.attr('id'));
            if (!$new_action.length || !$old_action.length) {
                return true;
            }
            if ($new_action[0].outerHTML != $old_action[0].outerHTML) {
                $old_action.replaceWith($new_action);
                changed = true;
            }
        });

        // Update table state if the table has been modified
        if (changed) {

            row_count = horizon.datatables.update_footer_count($old_table);
            if (row_count==0) {
               horizon.datatables.add_no_results_row($old_table);
            }

            // Reset tablesorter's data cache.
            $old_table.trigger("update");
            horizon.datatables.fix_row_striping($old_table);

            // Reset quicksearch filter cache.
            if ($new_table.attr('id') in horizon.datatables.qs) {
                horizon.datatables.qs[$new_table.attr('id')].cache();
            }

            // Revalidate the button check for the updated table
            horizon.datatables.validate_button();

            if($old_table.find('[ng-controller]').length) {
              recompileAngularContent($old_table);
            }

            // Flash updated rows
            $old_table.find('tr.updated').addClass("flash");
        }
    });

    refreshed_elapsed_time = new Date().getTime() - refresh_start_time;
    // uncomment to debug performance on browser log
    // Don't let this method take more than 1.5 sec 1500 millisecs
    // console.log("refresh elapsed time = "+ refreshed_elapsed_time);

    return refreshed;
};

horizon.addInitFunction(horizon.datatables.init = function() {
  horizon.datatables.validate_button();
  horizon.datatables.disable_buttons();
  $('table.datatable').each(function (idx, el) {
    horizon.datatables.update_footer_count($(el), 0);
  });
  horizon.datatables.initialize_checkboxes_behavior();
  horizon.datatables.initialize_table_tooltips();

  // Trigger run-once setup scripts for tables.
  var $body = $('body');
  horizon.datatables.add_table_checkboxes($body);
  horizon.datatables.set_table_sorting($body);
  horizon.datatables.set_table_query_filter($body);
  horizon.datatables.set_table_fixed_filter($body);
  horizon.datatables.set_table_fixedwithquery_filter($('body'));
  horizon.datatables.disable_actions_on_submit();
  horizon.datatables.set_table_limit($('body'));

  // Also apply on tables in modal views.
  horizon.modals.addModalInitFunction(horizon.datatables.add_table_checkboxes);
  horizon.modals.addModalInitFunction(horizon.datatables.set_table_sorting);
  horizon.modals.addModalInitFunction(horizon.datatables.set_table_query_filter);
  horizon.modals.addModalInitFunction(horizon.datatables.set_table_fixed_filter);
  horizon.modals.addModalInitFunction(horizon.datatables.set_table_fixedwithquery_filter);
  horizon.modals.addModalInitFunction(horizon.datatables.initialize_table_tooltips);
  horizon.modals.addModalInitFunction(function modalInitActionDisable(modal) {
    horizon.datatables.disable_actions_on_submit($(modal).find(".table_wrapper > form"));
  });

  // Also apply on tables in tabs views for lazy-loaded data.
  horizon.tabs.addTabLoadFunction(horizon.datatables.add_table_checkboxes);
  horizon.tabs.addTabLoadFunction(horizon.datatables.set_table_sorting);
  horizon.tabs.addTabLoadFunction(horizon.datatables.set_table_query_filter);
  horizon.tabs.addTabLoadFunction(horizon.datatables.set_table_fixed_filter);
  horizon.tabs.addTabLoadFunction(horizon.datatables.set_table_fixedwithquery_filter);
  horizon.tabs.addTabLoadFunction(horizon.datatables.set_table_limit);
  horizon.tabs.addTabLoadFunction(horizon.datatables.initialize_checkboxes_behavior);
  horizon.tabs.addTabLoadFunction(horizon.datatables.initialize_table_tooltips);
  horizon.tabs.addTabLoadFunction(function(tab) {
    horizon.datatables.validate_button($(tab).find(".table_wrapper > form"));
    horizon.datatables.disable_actions_on_submit($(tab).find(".table_wrapper > form"));
  });
  if ($('table.datatable').length > 0) {
      // Register callback handler to update the tables on page refresh
      horizon.refresh.addRefreshFunction(horizon.datatables.refresh);
  }
  else {
    horizon.tabs.addTabLoadFunction(function(tab) {
      if ($('table.datatable').length > 0) {
        // Register callback handler to update the tables on page refresh
        horizon.refresh.addRefreshFunction(horizon.datatables.refresh);
      }
    });
  }

  horizon.datatables.update();
});
