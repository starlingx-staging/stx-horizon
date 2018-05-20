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

/*
  Draw pie charts in d3.

  To use, a div is required with the class .d3_pie_chart_usage or
  .d3_pie_chart_distribution, and a data-used attribute in the div
  that stores the data used to fill the chart.

  Example (usage):
    <div class="pie-chart-usage"
      data-used="{% widthratio current_val max_val 100 %}">
    </div>

  Example (distribution):
    <div class="pie-chart-distribution"
      data-used="Controller=1|Compute=2|Object Storage=3|Block Storage=4">
    </div>
*/

// Pie chart SVG internal dimensions
var WIDTH = 100;
var HEIGHT = 100;
var RADIUS = 45;

function create_vis(chart) {
  return d3.select(chart).append("svg:svg")
    .attr("class", "chart legacy-pie-chart")
    .attr("viewBox", "0 0 " + WIDTH + " " + HEIGHT)
    .append("g")
    .attr("transform",
      "translate(" + (WIDTH / 2) + "," + (HEIGHT / 2) + ")");
}

function create_arc() {
  return d3.svg.arc()
    .outerRadius(RADIUS)
    .innerRadius(0);
}

function create_pie(param) {
  return d3.layout.pie()
    .sort(null)
    .value(function(d){ return d[param]; });
}


horizon.d3_pie_chart_usage = {
  init: function() {
    var self = this;
    self.arc = create_arc();
    self.pie = create_pie("percentage");

    // Pie Charts
    var pie_chart_data = $(".pie-chart-usage");
    self.chart = d3.selectAll(".pie-chart-usage");

    for (var i = 0; i < pie_chart_data.length; i++) {
      var data = $(pie_chart_data[i]).data("used");
      // When true is passed in only show the number, not the actual pie chart
      if (data[1] === true) {
        self.data = data[0];
        self.pieChart(i, false);
      } else {
        var used = Math.min(parseInt(data, 10), 100);
        data = [{"percentage":used}, {"percentage":100 - used}];
        self.create(self.chart[0][i], data, true);
      }
    }
  },
  // Draw a pie chart
  create: function(chart, data, fill) {
    var self = this;
    var vis = create_vis(chart);

    // Draw an empty pie chart
    vis.selectAll(".arc")
      .data(self.pie([{"percentage":10}]))
      .enter()
      .append("path")
      .attr("class","arc")
      .attr("d", self.arc);

    // Animate filling the pie chart
    var animate = function(data) {
      vis.selectAll(".arc")
        .data(self.pie(data))
        .enter()
        .append("path")
        .attr("class", function() {
          var ret_val = "arc inner";
          if (data[0].percentage >= 100) {
            ret_val += " FULL";
          } else if (data[0].percentage >= 80) {
            ret_val += " NEARLY_FULL";
          }
          return ret_val;
        })
        .attr("d", self.arc)
        .transition()
        .duration(500)
        .attrTween("d", function(start) {
          start.endAngle = start.startAngle = 0;
          var end = {
            startAngle: 0,
            endAngle: 2 * Math.PI * (100 - start.value) / 100
          };
          var tween = d3.interpolate(start, end);
          return function(t) { return self.arc(tween(t)); };
        });
    };

    var show_numbers = function() {
      vis.append("text")
        .attr("class", "chart-numbers")
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .text(data);
    };

    if (fill) {
      animate(data);
    } else {

      // TODO: this seems to be very broken...
      // https://bugs.launchpad.net/horizon/+bug/1490787
      // It prints: [object Object] to the screen
      show_numbers(data);
    }

  },

  // Update a pie chart
  update: function(chart, old_data, data) {
      var self = this;

      // update fill color based on new percentage
      d3.select(chart).selectAll("path:nth-child(2)")
          .attr("class", function() {
            var ret_val = "arc inner";
            if (data[0].percentage >= 100) {
              ret_val += " FULL";
            } else if (data[0].percentage >= 80) {
              ret_val += " NEARLY_FULL";
            }
            return ret_val;
          })

      d3.select(chart).selectAll("path:nth-child(2)")
        .data(self.pie(data))
        .each(function(d) {return self.current = d;})
        .transition()
          .duration(500)
          .attrTween("d", function(a) {
            var start = {
              startAngle: 0,
              endAngle: 2 * Math.PI * (old_data[0].percentage) / 100
            };
            var tween = d3.interpolate(start, a);
            self.current = tween(0);
            return function(t) { return self.arc(tween(t)); }
          })
  }
};


horizon.d3_pie_chart_distribution = {
  init: function() {
    var self = this;
    var pie_chart_data = $(".pie-chart-distribution");
    self.chart = d3.selectAll(".pie-chart-distribution");

    for (var i = 0; i < pie_chart_data.length; i++) {
      var parts = $(pie_chart_data[i]).data("used").split("|");
      self.data = [];
      self.keys = [];
      for (var j = 0; j < parts.length; j++) {
        var key_value = parts[j].split("=");
        var d = {
          key: key_value[0],
          value: key_value[1]
        };
        self.data.push(d);
        self.keys.push(key_value[0]);
      }
      self.pieChart(i, $(pie_chart_data[i]));
    }
  },
  // Draw a pie chart
  pieChart: function(i, $elem) {
    var self = this;
    var vis = create_vis(self.chart[0][i]);
    var arc = create_arc();
    var pie = create_pie("value");

    var total = 0;
    for (var j = 0; j < self.data.length; j++) {
      total = total + parseInt(self.data[j].value, 10);
    }

    var initial_data = [];
    if (total === 0) {
      initial_data = [{"value": 1}];
    }

    // Draw an empty pie chart
    vis.selectAll(".arc")
      .data(pie(initial_data))
      .enter()
      .append("path")
      .attr("class","arc")
      .attr("d", arc);

    // Animate filling the pie chart
    var animate = function(data) {
      vis.selectAll(".arc")
        .data(pie(data))
        .enter()
        .append("path")
        .attr("class","arc inner")
        .attr("d", arc)
        .transition()
        .duration(500)
        .attrTween("d", function(start) {
          start.endAngle = start.startAngle;
          var end = jQuery.extend({}, start);
          end.endAngle = end.startAngle + 2 * Math.PI / total * end.value;
          var tween = d3.interpolate(start, end);
          return function(t) { return arc(tween(t)); };
        });
    };

    if (total !== 0) {
      animate(self.data);
    }

    // The legend actually doesn't need to be an SVG element at all
    // By making it standard markup, we can allow greater customization
    var $legend = $(document.createElement('div')).addClass('legend');

    // This loop might seem wasteful, but we need to determine the total for the label
    var total = 0;
    for (var j = 0; j < self.data.length; j++) {

      // We need to use it as a float again later, convert it now and store ... its faster
      self.data[j].value = parseFloat(self.data[j].value);
      total += self.data[j].value;
    }

    for (var j = 0; j < self.data.length; j++) {
      var this_item = self.data[j];
      var $this_group = $(document.createElement('div'))
        .addClass('legend-group')
        .appendTo($legend);

      $(document.createElement('span'))
        .addClass('legend-symbol')
        .appendTo($this_group);

      $(document.createElement('span'))
        .addClass('legend-key')
        .text(this_item.key)
        .appendTo($this_group);

      var $this_value = $(document.createElement('span'))
        .addClass('legend-value');

      // If its zero, then we don't need to Math it.
      if (this_item.value === 0) {
        $this_item.text("0%");
      } else {
        $this_value.text(Math.round((this_item.value/total) * 100) + "%");
      }

      // Append it to the container
      $this_value.appendTo($this_group);
    }

    // Append the container last ... cause its faster
    $elem.append($legend);
  }
};

// Auto page refresh handler
horizon.d3_pie_chart_usage.refresh = function(html) {
    var refreshed = true;

    $(html).find('.pie-chart-usage').each(function(index, chart) {
        var $new_chart = $(this);
        var $old_chart = $('#' + $new_chart.attr('id'));

        if (!$old_chart.length) {
            // Page structure has changed, abort refresh
            refreshed = false;
            return false;
        }

        if ($old_chart.data('used') != $new_chart.data('used')) {
            // Update the used data attribute
            var used = parseInt($new_chart.data('used'));
            var old_used = parseInt($old_chart.data('used'));
            $old_chart.data('used', used);

            // Update the chart
            var chart = d3.select('#' + $new_chart.attr('id'));
            var data = [{"percentage":used}, {"percentage":100 - used}];
            var old_data = [{"percentage":old_used}, {"percentage":100 - old_used}];

            horizon.d3_pie_chart_usage.update(chart[0][0], old_data, data);

            // Update the caption (if present)
            var $new_bar = $new_chart.closest('.d3_quota_bar');
            var $old_bar = $old_chart.closest('.d3_quota_bar');
            $old_bar.find('.quota_subtitle').replaceWith($new_bar.find('.quota_subtitle'));
        }
    });

    return refreshed;
};


horizon.addInitFunction(function () {

  // Register callback handler to update the charts on page refresh
  if ($(".pie-chart-usage").length > 0) {
      horizon.refresh.addRefreshFunction(horizon.d3_pie_chart_usage.refresh);
  }

  horizon.d3_pie_chart_usage.init();
  horizon.d3_pie_chart_distribution.init();
});
