(function () {
  var node = document.getElementById("chart-data");
  if (!node || typeof Chart === "undefined") {
    return;
  }

  var data = JSON.parse(node.textContent);
  Chart.defaults.font.family = '"Segoe UI", system-ui, sans-serif';
  Chart.defaults.color = "#64748B";

  var statusCanvas = document.getElementById("statusChart");
  if (statusCanvas) {
    var total = (data.statusCounts || []).reduce(function (sum, value) {
      return sum + value;
    }, 0);
    var empty = statusCanvas.parentElement.querySelector("[data-empty]");
    if (total === 0) {
      statusCanvas.hidden = true;
      if (empty) {
        empty.hidden = false;
      }
    } else {
      new Chart(statusCanvas, {
        type: "doughnut",
        data: {
          labels: data.statusLabels,
          datasets: [{
            data: data.statusCounts,
            backgroundColor: data.statusColors,
            borderWidth: 2,
            borderColor: "#ffffff",
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: "62%",
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                boxWidth: 10,
                padding: 14,
                usePointStyle: true
              }
            }
          }
        }
      });
    }
  }

  var trendCanvas = document.getElementById("trendChart");
  if (trendCanvas) {
    new Chart(trendCanvas, {
      type: "bar",
      data: {
        labels: data.monthLabels,
        datasets: [{
          label: "Applications",
          data: data.monthCounts,
          backgroundColor: "#2563EB",
          borderRadius: 8,
          maxBarThickness: 42
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (context) {
                var count = context.parsed.y;
                return count + (count === 1 ? " application" : " applications");
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            ticks: { precision: 0 },
            grid: { color: "#E2E8F0" }
          }
        }
      }
    });
  }
})();
