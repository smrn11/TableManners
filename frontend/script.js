// script.js
var url = "http://127.0.0.1:8000";
function openTab(evt, tabName) {
    // Declare all variables
    var i, tabcontent, tablinks;
  
    // Get all elements with class 'tabcontent' and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
      tabcontent[i].style.display = "none";
    }
  
    // Get all elements with class 'tablink' and remove the class 'active'
    tablinks = document.getElementsByClassName("tablink");
    for (i = 0; i < tablinks.length; i++) {
      tablinks[i].classList.remove("active");
    }
  
    // Show the current tab and add an 'active' class to the button that opened the tab
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.classList.add("active");
    
    console.log(`Switched to tab: ${tabName}`);
  }
  
  // Open the first tab by default
  document.addEventListener("DOMContentLoaded", function() {
    document.querySelector(".tablink").click();
  });

  // Function to fetch and render data for Tab 1
function fetchDataTab1() {
    const loader = document.getElementById("loader-1");
    const chartContainer = document.getElementById("chart-container-1");

    loader.classList.remove("hidden");
    chartContainer.innerHTML = "";

    const city = document.getElementById("city-select-1").value;
    console.log(`Fetching data for city: ${city}`);
    
    fetch(`${url}/api/daily-average-energy/${encodeURIComponent(city)}`)
      .then(response => response.json())
      .then(data => {
        console.log("Data received:", data);
        renderChartTab1(data);
      })
      .catch(error => {
        console.error("Error fetching data:", error);
      })
      .finally(() => {
        // Hide loader after rendering
        loader.classList.add("hidden");
      });
  }
  
  // Event listener for Fetch Data button
  document.getElementById("fetch-data-1").addEventListener("click", fetchDataTab1);
  
  // Function to render the line chart using D3.js
  function renderChartTab1(data) {
    // Clear previous chart
    // d3.select("#chart-container-1").html("");

    // Prepare data
    const dates = Object.keys(data);
    const onPeakData = dates.map(date => ({ date: new Date(date), value: data[date].on_peak }));
    const offPeakData = dates.map(date => ({ date: new Date(date), value: data[date].off_peak }));

    console.log("Processed data for chart:", { onPeakData, offPeakData });

    // Set dimensions
    const margin = { top: 20, right: 30, bottom: 100, left: 70 }, // Increased bottom margin
          width = 800 - margin.left - margin.right,
          height = 400 - margin.top - margin.bottom;

    // Create SVG element
    const svg = d3.select("#chart-container-1")
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Set scales
    const xScale = d3.scaleTime()
      .domain(d3.extent(dates, d => new Date(d)))
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain([0, d3.max([...onPeakData, ...offPeakData], d => d.value)])
      .range([height, 0]);

    // Define line generators
    const lineOnPeak = d3.line()
      .x(d => xScale(d.date))
      .y(d => yScale(d.value));

    const lineOffPeak = d3.line()
      .x(d => xScale(d.date))
      .y(d => yScale(d.value));

    // Add X-axis
    const xAxis = svg.append("g")
      .attr("transform", `translate(0,${height})`)
      .call(
        d3.axisBottom(xScale)
          .ticks(dates.length) // Ensure all dates are shown
          .tickFormat(d3.timeFormat("%b %d")) // Format as "Month Day"
      );

    xAxis.selectAll("text")
      .attr("transform", "rotate(45)")
      .style("text-anchor", "start");

    // Add Y-axis
    svg.append("g")
      .call(d3.axisLeft(yScale));

    // Add On Peak line
    svg.append("path")
      .datum(onPeakData)
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 2)
      .attr("d", lineOnPeak);

    // Add Off Peak line
    svg.append("path")
      .datum(offPeakData)
      .attr("fill", "none")
      .attr("stroke", "orange")
      .attr("stroke-width", 2)
      .attr("d", lineOffPeak);

    // Add Tooltip
    const tooltip = d3.select("#chart-container-1")
      .append("div")
      .style("position", "absolute")
      .style("background-color", "white")
      .style("border", "1px solid #ccc")
      .style("padding", "5px")
      .style("border-radius", "5px")
      .style("display", "none")
      .style("pointer-events", "none");

    // Add circles for On Peak data points
    svg.selectAll(".onPeakPoint")
      .data(onPeakData)
      .enter()
      .append("circle")
      .attr("class", "onPeakPoint")
      .attr("cx", d => xScale(d.date))
      .attr("cy", d => yScale(d.value))
      .attr("r", 4)
      .attr("fill", "steelblue")
      .on("mouseover", (event, d) => {
        tooltip.style("display", "block")
          .html(`Date: ${d3.timeFormat("%b %d")(d.date)}<br>On Peak: ${d.value.toFixed(2)} kWh`);
      })
      .on("mousemove", (event) => {
        tooltip.style("left", event.pageX + 10 + "px")
          .style("top", event.pageY - 20 + "px");
      })
      .on("mouseout", () => {
        tooltip.style("display", "none");
      });

    // Add circles for Off Peak data points
    svg.selectAll(".offPeakPoint")
      .data(offPeakData)
      .enter()
      .append("circle")
      .attr("class", "offPeakPoint")
      .attr("cx", d => xScale(d.date))
      .attr("cy", d => yScale(d.value))
      .attr("r", 4)
      .attr("fill", "orange")
      .on("mouseover", (event, d) => {
        tooltip.style("display", "block")
          .html(`Date: ${d3.timeFormat("%b %d")(d.date)}<br>Off Peak: ${d.value.toFixed(2)} kWh`);
      })
      .on("mousemove", (event) => {
        tooltip.style("left", event.pageX + 10 + "px")
          .style("top", event.pageY - 20 + "px");
      })
      .on("mouseout", () => {
        tooltip.style("display", "none");
      });

    // Add X-axis label
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 40)
      .style("text-anchor", "middle")
      .text("Date");

    // Add Y-axis label
    svg.append("text")
      .attr("x", -(height / 2))
      .attr("y", -margin.left + 20)
      .attr("transform", "rotate(-90)")
      .style("text-anchor", "middle")
      .text("Energy Usage (kWh)");

    // Add legend
    svg.append("text")
      .attr("x", width - 100)
      .attr("y", 20)
      .attr("fill", "steelblue")
      .text("On Peak");

    svg.append("text")
      .attr("x", width - 100)
      .attr("y", 40)
      .attr("fill", "orange")
      .text("Off Peak");

    console.log("Chart rendered successfully for Tab 1");
}

// Function to fetch and render data for Tab 2
// Function to fetch and render data for Tab 2
function fetchDataTab2() {
  console.log("Fetching cluster health data...");
  
  fetch(`${url}/api/cluster-health`)
    .then(response => response.json())
    .then(data => {
      console.log("Cluster health data received:", data);
      renderTableTab2(data);
    })
    .catch(error => {
      console.error("Error fetching cluster health data:", error);
    });
}

// Add an event listener to the "Fetch Cluster Health" button
document.getElementById("fetch-cluster-health").addEventListener("click", fetchDataTab2);

// Function to render the cluster health table
function renderTableTab2(data) {
  const table = document.getElementById("cluster-health-table");
  const tbody = table.querySelector("tbody");
  tbody.innerHTML = ""; // Clear previous data

  // Show the table
  table.classList.remove("hidden");

  // Populate the table with data
  data.nodes.forEach(node => {
      const row = document.createElement("tr");

      row.innerHTML = `
          <td>${node.name}</td>
          <td>${node.state}</td>
          <td>${node.health}</td>
          <td>${node.uptime}</td>
          <td>${node.last_heartbeat}</td>
          <td>${node.ping_ms || "Unknown"}</td>
      `;

      tbody.appendChild(row);
  });

  console.log("Cluster health table rendered successfully");
}

  // Function to fetch and render data for Tab 3
function fetchDataTab3() {

    const city = document.getElementById("city-select-3").value;
    const timePeriod = document.getElementById("time-period-select").value;
    
    console.log(`Fetching data for city: ${city}, time period: ${timePeriod}`);

    const loader = document.getElementById("loader-3");
    const chartContainer = document.getElementById("chart-container-3");

    // Show loader and hide chart container
    loader.classList.remove("hidden");
    chartContainer.innerHTML = "";    
    
    fetch(`${url}/api/average-energy-zip/${encodeURIComponent(city)}/${timePeriod}`)
      .then(response => response.json())
      .then(data => {
        console.log("Data received for Tab 3:", data);
        renderChartTab3(data, timePeriod);
      })
      .catch(error => {
        console.error("Error fetching data for Tab 3:", error);
      })
      .finally(() => {
        // Hide loader after rendering
        loader.classList.add("hidden");
      });

  }
  
  // Event listener for Fetch Data button
  document.getElementById("fetch-data-3").addEventListener("click", fetchDataTab3);
  
  // Function to render the chart using D3.js
  function renderChartTab3(data, timePeriod) {
    // Clear previous chart
    // d3.select("#chart-container-3").html("");

    // Prepare data
    const plotData = [];
    const zipCodes = Object.keys(data).map(zip => zip === "Unspecified" ? "Unspecified Postal Code" : zip);
    zipCodes.forEach(zip => {
        data[zip].dates.forEach(entry => {
            plotData.push({
                zip_code: zip,
                date: new Date(entry.date),
                average_energy: entry.average_energy
            });
        });
    });

    console.log("Processed data for heatmap:", plotData);

    // Set dimensions
    const margin = { top: 50, right: 200, bottom: 200, left: 200 },
          width = 1200 - margin.left - margin.right,
          height = Math.max(600, zipCodes.length * 20) - margin.top - margin.bottom;

    
    const xScale = d3.scaleBand()
          .domain([...new Set(plotData.map(d => d.date))].sort((a, b) => a - b))
          .range([0, width])
          .padding(0.05);
  
    const yScale = d3.scaleBand()
          .domain(zipCodes)
          .range([0, height])
          .padding(0.05);
    const cellWidth = xScale.bandwidth(); // Width of each cell
    const cellHeight = Math.min(30, height / zipCodes.length); // Adjust cell height dynamically

    // Create SVG element
    const svg = d3.select("#chart-container-3")
        .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
        .append("g")
        .attr("transform", `translate(${margin.left},${margin.top})`);

    // Set scales
    

    const colorScale = d3.scaleSequential(d3.interpolateYlGnBu)
        .domain([0, d3.max(plotData, d => d.average_energy)]);

    // Add X-axis
    svg.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(xScale).tickFormat(d3.timeFormat("%b %d")))
        .selectAll("text")
        .attr("transform", "rotate(45)")
        .style("text-anchor", "start");

    // Add Y-axis
    svg.append("g")
        .call(d3.axisLeft(yScale))
        .selectAll("text")
        .style("font-size", "12px"); // Adjust font size if necessary

    // Add axis labels
    svg.append("text")
        .attr("x", width / 2)
        .attr("y", height + margin.bottom - 10)
        .style("text-anchor", "middle")
        .text("Dates");

    svg.append("text")
        .attr("x", -height / 2)
        .attr("y", -margin.left + 20)
        .attr("transform", "rotate(-90)")
        .style("text-anchor", "middle")
        .text("Postal Codes");

    // Add heatmap cells
    svg.selectAll("rect")
        .data(plotData)
        .enter()
        .append("rect")
        .attr("x", d => xScale(d.date))
        .attr("y", d => yScale(d.zip_code))
        .attr("width", xScale.bandwidth())
        .attr("height", yScale.bandwidth())
        .style("fill", d => colorScale(d.average_energy))
        .style("stroke", "white")
        .style("stroke-width", 0.5)
        .on("mouseover", function (event, d) {
            d3.select(this).style("stroke", "black").style("stroke-width", 2);
            tooltip.style("display", "block")
                .html(`Postal Code: ${d.zip_code}<br>Date: ${d3.timeFormat("%b %d")(d.date)}<br>Energy: ${d.average_energy.toFixed(2)} kWh`);
        })
        .on("mousemove", function (event) {
            tooltip.style("left", event.pageX + 15 + "px")
                .style("top", event.pageY - 20 + "px");
        })
        .on("mouseout", function () {
            d3.select(this).style("stroke", "white").style("stroke-width", 0.5);
            tooltip.style("display", "none");
        });

    // Add tooltips
    const tooltip = d3.select("#chart-container-3")
        .append("div")
        .style("position", "absolute")
        .style("background-color", "white")
        .style("border", "1px solid #ccc")
        .style("padding", "5px")
        .style("border-radius", "5px")
        .style("display", "none")
        .style("pointer-events", "none");

    // Add color legend
    const legendHeight = 300;
    const legendWidth = 20;
    const legend = svg.append("g")
        .attr("transform", `translate(${width + 20}, 0)`);

    // Gradient definition
    const defs = svg.append("defs");
    const linearGradient = defs.append("linearGradient")
        .attr("id", "legend-gradient")
        .attr("x1", "0%")
        .attr("y1", "100%")
        .attr("x2", "0%")
        .attr("y2", "0%");
    linearGradient.append("stop").attr("offset", "0%").attr("stop-color", d3.interpolateYlGnBu(0));
    linearGradient.append("stop").attr("offset", "100%").attr("stop-color", d3.interpolateYlGnBu(1));

    legend.append("rect")
        .attr("width", legendWidth)
        .attr("height", legendHeight)
        .style("fill", "url(#legend-gradient)");

    // Legend scale
    const legendScale = d3.scaleLinear()
        .domain(colorScale.domain())
        .range([legendHeight, 0]);

    const legendAxis = d3.axisRight(legendScale).ticks(5);

    legend.append("g")
        .attr("transform", `translate(${legendWidth}, 0)`)
        .call(legendAxis);

    legend.append("text")
        .attr("x", legendWidth / 2)
        .attr("y", -10)
        .attr("text-anchor", "middle")
        .text("Energy Usage (kWh)");
}

// Function to fetch and render data for Tab 4
function fetchDataTab4() {
  const city = document.getElementById("city-select-4").value;
  const startDate = document.getElementById("start-date-4").value;
  const endDate = document.getElementById("end-date-4").value;
  
  if (!startDate) {
    alert("Please select a start date.");
    return;
  }
  
  console.log(`Fetching data for city: ${city}, start date: ${startDate}, end date: ${endDate}`);

  const loader = document.getElementById("loader-4");
  const chartContainer = document.getElementById("chart-container-4");

  // Show loader and hide chart container
  loader.classList.remove("hidden");
  chartContainer.innerHTML = "";  
  
  fetch(`${url}/api/average-daily-usage-by-unit-type`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      city_name: city,
      start_date: startDate,
      end_date: endDate
    })
  })
    .then(response => response.json())
    .then(data => {
      console.log("Data received for Tab 4:", data);
      renderChartTab4(data);
    })
    .catch(error => {
      console.error("Error fetching data for Tab 4:", error);
    })
    .finally(() => {
      // Hide loader after rendering
      loader.classList.add("hidden");
    });
}

// Event listener for Fetch Data button
document.getElementById("fetch-data-4").addEventListener("click", fetchDataTab4);

// Function to render the bar chart using D3.js
function renderChartTab4(data) {
  // Clear previous chart
  // d3.select("#chart-container-4").html("");

  // Prepare data
  const dates = data.map(d => d.date);
  const unitTypes = Array.from(new Set(data.flatMap(d => d.unit_type_averages.map(u => u.unit_type))));

  // Process data into a nested structure
  const plotData = data.map(d => {
    const obj = { date: d.date };
    d.unit_type_averages.forEach(u => {
      obj[u.unit_type] = u.average_usage;
    });
    return obj;
  });

  console.log("Processed data for chart in Tab 4:", plotData);

  // Set dimensions
  const margin = { top: 40, right: 50, bottom: 80, left: 60 },
        width = 900 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;

  // Create SVG element
  const svg = d3.select("#chart-container-4")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

  // X scale
  const x0 = d3.scaleBand()
    .domain(dates)
    .range([0, width])
    .padding(0.2);

  // X1 scale for unit types
  const x1 = d3.scaleBand()
    .domain(unitTypes)
    .range([0, x0.bandwidth()])
    .padding(0.05);

  // Y scale
  const y = d3.scaleLinear()
    .domain([0, d3.max(plotData, d => d3.max(unitTypes, key => d[key]))])
    .nice()
    .range([height, 0]);

  // Color scale
  const color = d3.scaleOrdinal()
    .domain(unitTypes)
    .range(d3.schemeSet2);

  // Add X axis
  svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x0))
    .selectAll("text")
    .attr("transform", "rotate(45)")
    .style("text-anchor", "start");

  // Add Y axis
  svg.append("g")
    .call(d3.axisLeft(y));

  // Add axis labels
  svg.append("text")
    .attr("x", width / 2)
    .attr("y", height + margin.bottom - 10)
    .style("text-anchor", "middle")
    .text("Dates");

  svg.append("text")
    .attr("x", -(height / 2))
    .attr("y", -margin.left + 10)
    .attr("transform", "rotate(-90)")
    .style("text-anchor", "middle")
    .text("Average Energy Usage (kWh)");

  // Draw bars
  const bars = svg.append("g")
    .selectAll("g")
    .data(plotData)
    .enter()
    .append("g")
    .attr("transform", d => `translate(${x0(d.date)},0)`);

  bars.selectAll("rect")
    .data(d => unitTypes.map(key => ({ key: key, value: d[key] })))
    .enter()
    .append("rect")
    .attr("x", d => x1(d.key))
    .attr("y", d => y(d.value))
    .attr("width", x1.bandwidth())
    .attr("height", d => height - y(d.value))
    .attr("fill", d => color(d.key))
    .on("mouseover", (event, d) => {
      tooltip.style("display", "block")
        .html(`Unit Type: ${d.key}<br>Energy Usage: ${d.value.toFixed(2)} kWh`);
    })
    .on("mousemove", event => {
      tooltip.style("left", `${event.pageX + 10}px`)
        .style("top", `${event.pageY - 20}px`);
    })
    .on("mouseout", () => {
      tooltip.style("display", "none");
    });

  // Add legend
  const legend = svg.selectAll(".legend")
    .data(unitTypes)
    .enter()
    .append("g")
    .attr("transform", (d, i) => `translate(${i * 100}, -10)`);

  legend.append("rect")
    .attr("x", 0)
    .attr("y", 0)
    .attr("width", 10)
    .attr("height", 10)
    .attr("fill", d => color(d));

  legend.append("text")
    .attr("x", 15)
    .attr("y", 10)
    .text(d => d);

  // Add tooltips
  const tooltip = d3.select("#chart-container-4")
    .append("div")
    .style("position", "absolute")
    .style("background-color", "white")
    .style("border", "1px solid #ccc")
    .style("padding", "5px")
    .style("border-radius", "5px")
    .style("display", "none")
    .style("pointer-events", "none");

  console.log("Chart rendered successfully for Tab 4");
}

// Function to fetch and render data for Tab 5
function fetchDataTab5() {
  const city = document.getElementById("city-select-5").value;
  console.log(`Fetching top units for city: ${city}`);
  
  fetch(`${url}/top-units/${encodeURIComponent(city)}`)
    .then(response => response.json())
    .then(data => {
      console.log("Data received for Tab 5:", data);
      renderTableTab5(data);
    })
    .catch(error => {
      console.error("Error fetching data for Tab 5:", error);
    });
}

// Event listener for Fetch Data button
document.getElementById("fetch-data-5").addEventListener("click", fetchDataTab5);

// Function to render the table
function renderTableTab5(data) {
  const table = document.getElementById("top-units-table");
  const tbody = document.querySelector("#top-units-table tbody");

  // Clear previous data
  tbody.innerHTML = ""; 

  // Show table headers
  table.classList.remove("hidden");

  // Populate table rows
  data.forEach(item => {
      const row = document.createElement("tr");

      row.innerHTML = `
          <td>${item.unit_id}</td>
          <td>${item.address}</td>
          <td>${item.total_energy_usage.toFixed(2)}</td>
      `;

      tbody.appendChild(row);
  });

  console.log("Top units table rendered successfully");
}

// Function to fetch and render data for Tab 6
function fetchDataTab6() {
  const city = document.getElementById("city-select-6").value;
  console.log(`Fetching data for city: ${city}`);

  const loader = document.getElementById("loader-6");
  const chartContainer = document.getElementById("chart-container-6");

  // Show loader and hide chart container
  loader.classList.remove("hidden");
  chartContainer.innerHTML = "";
  
  fetch(`${url}/average-energy-by-device-type/${encodeURIComponent(city)}`)
    .then(response => response.json())
    .then(data => {
      console.log("Data received for Tab 6:", data);
      renderChartTab6(data);
    })
    .catch(error => {
      console.error("Error fetching data for Tab 6:", error);
    })
    .finally(() => {
      // Hide loader after rendering
      loader.classList.add("hidden");
    });
}

// Event listener for Fetch Data button
document.getElementById("fetch-data-6").addEventListener("click", fetchDataTab6);

// Function to render the bar chart using D3.js
function renderChartTab6(data) {
  // Clear previous chart
  // d3.select("#chart-container-6").html("");

  console.log("Processed data for chart in Tab 6:", data);

  // Set dimensions
  const margin = { top: 40, right: 50, bottom: 80, left: 70 },
        width = 800 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;

  // Create SVG element
  const svg = d3.select("#chart-container-6")
      .append("svg")
      .attr("width", width + margin.left + margin.right)
      .attr("height", height + margin.top + margin.bottom)
      .append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

  // X scale
  const x = d3.scaleBand()
      .domain(data.map(d => d.device_type))
      .range([0, width])
      .padding(0.2);

  // Y scale
  const y = d3.scaleLinear()
      .domain([0, d3.max(data, d => d.average_energy_usage)])
      .nice()
      .range([height, 0]);

// Add X axis
svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x).tickFormat(d => d.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())))
    .selectAll("text")
    .attr("transform", "rotate(45)")
    .style("text-anchor", "start");

  // Add Y axis
  svg.append("g")
      .call(d3.axisLeft(y));

  // Add axis labels
  svg.append("text")
      .attr("x", width / 2)
      .attr("y", height + margin.bottom - 10)
      .style("text-anchor", "middle")
      .text("Device Types");

  svg.append("text")
      .attr("x", -(height / 2))
      .attr("y", -margin.left + 20)
      .attr("transform", "rotate(-90)")
      .style("text-anchor", "middle")
      .text("Average Energy Usage (kWh)");

  // Draw bars
  svg.selectAll(".bar")
      .data(data)
      .enter()
      .append("rect")
      .attr("x", d => x(d.device_type))
      .attr("y", d => y(d.average_energy_usage))
      .attr("width", x.bandwidth())
      .attr("height", d => height - y(d.average_energy_usage))
      .attr("fill", "steelblue")
      .on("mouseover", (event, d) => {
          tooltip.style("display", "block")
              .html(`Device Type: ${d.device_type}<br>Average Usage: ${d.average_energy_usage.toFixed(2)} kWh`);
      })
      .on("mousemove", event => {
          tooltip.style("left", `${event.pageX + 10}px`)
              .style("top", `${event.pageY - 20}px`);
      })
      .on("mouseout", () => {
          tooltip.style("display", "none");
      });

  // Add tooltips
  const tooltip = d3.select("#chart-container-6")
      .append("div")
      .style("position", "absolute")
      .style("background-color", "white")
      .style("border", "1px solid #ccc")
      .style("padding", "5px")
      .style("border-radius", "5px")
      .style("display", "none")
      .style("pointer-events", "none");

}











  
  



  