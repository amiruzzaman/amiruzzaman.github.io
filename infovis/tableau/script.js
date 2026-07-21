//Vis 1

//Config
const margin = { top: 20, right: 120, bottom: 60, left: 60 };
const width = 900 - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

//color mapping for origins
const countryColors = {
  European: "#2ca02c",
  American: "#1f77b4",
  Japanese: "#d62728"
};
const colorScale = (country) => {
  return countryColors[country] || "#7f7f7f";
};

const svg = d3
  .select("#chart")
  .attr("width", width + margin.left + margin.right)
  .attr("height", height + margin.top + margin.bottom);

const g = svg
  .append("g")
  .attr("transform", `translate(${margin.left},${margin.top})`);

const tooltip = d3.select("#tooltip");

let currentData = [];

async function loadData() {
  try {
    const csvUrl =
      "https://raw.githubusercontent.com/wgmckeon/HW2-csv-files/refs/heads/main/cars.csv";
    const data = await d3.csv(csvUrl);
    const processedData = data
      .map((d) => {
        const acceleration =
          +d.acceleration ||
          +d.Acceleration ||
          +d["0-60"] ||
          +d["0-60 mph"] ||
          +d.accel;

        const origin =
          d.origin ||
          d.Origin ||
          d.country ||
          d.Country ||
          d.nationality ||
          d.Nationality;

        const name = d.name || d.Name || d.car || d.Car || d.model || d.Model;

        return {
          acceleration: acceleration,
          origin: origin,
          name: name,

          mpg: +d.mpg || +d.MPG || null,
          horsepower: +d.horsepower || +d.Horsepower || +d.hp || +d.HP || null,
          weight: +d.weight || +d.Weight || null,
          year: +d.year || +d.Year || null
        };

        //remove unused data
      })
      .filter((d) => !isNaN(d.acceleration) && d.origin);

    if (processedData.length === 0) {
      throw new Error("Data invalid.");
    }
    currentData = processedData;
    document.getElementById("loading").style.display = "none";

    createScatterPlot();
    console.log(`Loaded ${currentData.length} records`);
  } catch (error) {
    document.getElementById("loading").style.display = "none";
    document.getElementById("error").style.display = "block";
    document.getElementById(
      "error"
    ).innerHTML = `Error loading data: ${error.message}<br><small>Please check that the CSV file is accessible.</small>`;
    console.error("Data loading error:", error);
  }
}

//scatter plot visualization
function createScatterPlot() {
  g.selectAll("*").remove();

  const data = currentData;

  const countries = [...new Set(data.map((d) => d.origin))];

  const xScale = d3
    .scaleLinear()
    .domain(d3.extent(data, (d) => d.acceleration))
    .range([0, width])
    .nice();

  const yScale = d3
    .scaleBand()
    .domain(countries)
    .range([height, 0])
    .padding(0.2);

  const jitter = () => (Math.random() - 0.5) * yScale.bandwidth() * 0.8;

  g.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(xScale));

  g.append("g").attr("class", "axis").call(d3.axisLeft(yScale));

  g.append("text")
    .attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin.left)
    .attr("x", 0 - height / 2)
    .attr("dy", "1em")
    .style("text-anchor", "middle");

  g.append("text")
    .attr("class", "axis-label")
    .attr(
      "transform",
      `translate(${width / 2}, ${height + margin.bottom - 10})`
    )
    .style("text-anchor", "middle")
    .text("Acceleration (seconds 0-60 mph)");

  g.selectAll(".dot")
    .data(data)
    .enter()
    .append("circle")
    .attr("class", "dot")
    .attr("r", 4)
    .attr("cx", (d) => xScale(d.acceleration))
    .attr("cy", (d) => yScale(d.origin) + yScale.bandwidth() / 2 + jitter())
    .style("fill", (d) => colorScale(d.origin))
    .style("opacity", 0.7)
    .style("stroke", "white")
    .style("stroke-width", 1)
    .on("mouseover", function (event, d) {
      d3.select(this)
        .transition()
        .duration(200)
        .attr("r", 6)
        .style("opacity", 1);

      tooltip.transition().duration(200).style("opacity", 1);

      tooltip
        .html(
          `<strong>${d.name || "Unknown Car"}</strong><br/>Origin: ${
            d.origin
          }<br/>Acceleration: ${d.acceleration}s<br/>${
            d.horsepower ? `Horsepower: ${d.horsepower}<br/>` : ""
          }${d.year ? `Year: ${d.year}` : ""}`
        )
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 10 + "px");
    })
    .on("mouseout", function (d) {
      d3.select(this)
        .transition()
        .duration(200)
        .attr("r", 4)
        .style("opacity", 0.7);

      tooltip.transition().duration(200).style("opacity", 0);
    });

  createLegend(countries);
}

function createLegend(countries) {
  const legend = g
    .append("g")
    .attr("class", "legend")
    .attr("transform", `translate(${width + 20}, 20)`);

  const legendItems = legend
    .selectAll(".legend-item")
    .data(countries)
    .enter()
    .append("g")
    .attr("class", "legend-item")
    .attr("transform", (d, i) => `translate(0, ${i * 20})`);

  legendItems
    .append("rect")
    .attr("width", 12)
    .attr("height", 12)
    .style("fill", (d) => colorScale(d));

  legendItems
    .append("text")
    .attr("x", 18)
    .attr("y", 9)
    .attr("dy", ".35em")
    .text((d) => d);
}

//vis 2

//config 2
const margin2 = { top: 20, right: 40, bottom: 60, left: 80 };
const width2 = 900 - margin2.left - margin2.right;
const height2 = 400 - margin2.top - margin2.bottom;

const manufacturerColors = {
  G: "#1f77b4",
  K: "#ff7f0e",
  N: "#2ca02c",
  P: "#d62728",
  Q: "#9467bd",
  R: "#8c564b",
  A: "#e377c2"
};

const manufacturerNames = {
  G: "General Mills",
  K: "Kellogg's",
  N: "Nabisco",
  P: "Post",
  Q: "Quaker",
  R: "Ralston",
  A: "American"
};

const svg2 = d3
  .select("#chart2")
  .attr("width", width2 + margin2.left + margin2.right)
  .attr("height", height2 + margin2.top + margin2.bottom);

const g2 = svg2
  .append("g")
  .attr("transform", `translate(${margin2.left},${margin2.top})`);

let cerealData = [];

async function loadCerealData() {
  try {
    const csvUrl =
      "https://raw.githubusercontent.com/wgmckeon/HW2-csv-files/refs/heads/main/cereals.csv";
    const data = await d3.csv(csvUrl);

    const processedData = data
      .map((d) => ({
        cereal: d.Cereal,
        manufacturer: d.Manufacturer,
        calories: +d.Calories,
        protein: +d.Protein,
        fat: +d.Fat,
        sodium: +d.Sodium,
        fiber: +d.Fiber,
        carbs: +d.Carbohydrates,
        sugars: +d.Sugars,
        potassium: +d.Potassium,
        vitamins: +d.Vitamins
      }))
      .filter((d) => !isNaN(d.calories) && d.manufacturer);

    cerealData = processedData;

    createCalorieBarChart();

    console.log(`Loaded ${cerealData.length} cereal records`);
  } catch (error) {
    console.error("Error loading data:", error);
    d3.select("#chart2")
      .append("text")
      .attr("x", width2 / 2)
      .attr("y", height2 / 2)
      .attr("text-anchor", "middle")
      .style("fill", "red")
      .text("Error loading cereal data");
  }
}

//create bar chart
function createCalorieBarChart() {
  g2.selectAll("*").remove();

  //find average calories
  const avgCaloriesByMfg = d3.rollup(
    cerealData,
    (v) => d3.mean(v, (d) => d.calories),
    (d) => d.manufacturer
  );

  const barData = Array.from(
    avgCaloriesByMfg,
    ([manufacturer, avgCalories]) => ({
      manufacturer: manufacturer,
      manufacturerName: manufacturerNames[manufacturer] || manufacturer,
      avgCalories: avgCalories
    })
  ).sort((a, b) => b.avgCalories - a.avgCalories);

  const xScale = d3
    .scaleLinear()
    .domain([0, d3.max(barData, (d) => d.avgCalories)])
    .range([0, width2])
    .nice();

  const yScale = d3
    .scaleBand()
    .domain(barData.map((d) => d.manufacturerName))
    .range([0, height2])
    .padding(0.2);

  const bars = g2
    .selectAll(".bar")
    .data(barData)
    .enter()
    .append("rect")
    .attr("class", "bar")
    .attr("x", 0)
    .attr("y", (d) => yScale(d.manufacturerName))
    .attr("width", 0)
    .attr("height", yScale.bandwidth())
    .style("fill", (d) => manufacturerColors[d.manufacturer] || "#999")
    .style("opacity", 0.8);

  //animation
  bars
    .transition()
    .duration(1000)
    .attr("width", (d) => xScale(d.avgCalories));

  g2.selectAll(".bar-label")
    .data(barData)
    .enter()
    .append("text")
    .attr("class", "bar-label")
    .attr("x", (d) => xScale(d.avgCalories) + 5)
    .attr("y", (d) => yScale(d.manufacturerName) + yScale.bandwidth() / 2)
    .attr("dy", "0.35em")
    .style("font-size", "12px")
    .style("fill", "#333")
    .style("opacity", 0)
    .text((d) => Math.round(d.avgCalories))
    .transition()
    .delay(1000)
    .duration(500)
    .style("opacity", 1);

  g2.append("g")
    .attr("class", "axis")
    .attr("transform", `translate(0,${height2})`)
    .call(d3.axisBottom(xScale));

  g2.append("g").attr("class", "axis").call(d3.axisLeft(yScale));

  g2.append("text")
    .attr("class", "axis-label")
    .attr(
      "transform",
      `translate(${width2 / 2}, ${height2 + margin2.bottom - 10})`
    )
    .style("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "500")
    .text("Average Calories");

  g2.append("text")
    .attr("class", "axis-label")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin2.left)
    .attr("x", 0 - height2 / 2)
    .attr("dy", "1em")
    .style("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "500");

  bars
    .on("mouseover", function (event, d) {
      d3.select(this)
        .style("opacity", 1)
        .style("stroke", "#333")
        .style("stroke-width", 2);

      const tooltip = d3.select("#tooltip");
      tooltip.transition().duration(200).style("opacity", 1);

      const cerealCount = cerealData.filter(
        (c) => c.manufacturer === d.manufacturer
      ).length;

      tooltip
        .html(
          `<strong>${
            d.manufacturerName
          }</strong><br/>Average Calories: ${Math.round(
            d.avgCalories
          )}<br/>Number of Cereals: ${cerealCount}`
        )
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 10 + "px");
    })
    .on("mouseout", function (d) {
      d3.select(this).style("opacity", 0.8).style("stroke", "none");

      d3.select("#tooltip").transition().duration(200).style("opacity", 0);
    });
}

//vis 3

const margin3 = { top: 20, right: 20, bottom: 20, left: 20 };
const width3 = 500;
const height3 = 500;
const radius = Math.min(width3, height3) / 2 - 40;

const subjectColors = d3
  .scaleOrdinal()
  .range([
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf"
  ]);

const svg3 = d3
  .select("#chart3")
  .attr("width", width3 + margin3.left + margin3.right)
  .attr("height", height3 + margin3.top + margin3.bottom);

const g3 = svg3
  .append("g")
  .attr(
    "transform",
    `translate(${(width3 + margin3.left + margin3.right) / 2}, ${
      (height3 + margin3.top + margin3.bottom) / 2
    })`
  );

let filmData = [];

async function loadFilmData() {
  try {
    const csvUrl =
      "https://raw.githubusercontent.com/wgmckeon/HW2-csv-files/refs/heads/main/film.csv";
    const data = await d3.csv(csvUrl);

    const processedData = data
      .map((d) => ({
        title: d.Title,
        subject: d.Subject,
        year: +d.Year,
        length: +d.Length,
        actor: d.Actor,
        actress: d.Actress,
        director: d.Director,
        popularity: +d.Popularity,
        awards: d.Awards
      }))
      .filter((d) => d.awards === "Yes" && d.subject);

    filmData = processedData;

    createAwardsPieChart();

    console.log(`Loaded ${filmData.length} award-winning film records`);
  } catch (error) {
    console.error("Error loading data:", error);
    d3.select("#chart3")
      .append("text")
      .attr("x", width3 / 2)
      .attr("y", height3 / 2)
      .attr("text-anchor", "middle")
      .style("fill", "red")
      .text("Error loading film data");
  }
}

function createAwardsPieChart() {
  g3.selectAll("*").remove();

  const awardsBySubject = d3.rollup(
    filmData,
    (v) => v.length,
    (d) => d.subject
  );

  const pieData = Array.from(awardsBySubject, ([subject, count]) => ({
    subject: subject,
    count: count
  }));

  const pie = d3
    .pie()
    .value((d) => d.count)
    .sort(null);

  const arc = d3.arc().innerRadius(0).outerRadius(radius);

  const labelArc = d3
    .arc()
    .innerRadius(radius + 10)
    .outerRadius(radius + 10);

  const arcs = g3
    .selectAll(".arc")
    .data(pie(pieData))
    .enter()
    .append("g")
    .attr("class", "arc");

  arcs
    .append("path")
    .attr("d", arc)
    .style("fill", (d) => subjectColors(d.data.subject))
    .style("stroke", "white")
    .style("stroke-width", 2)
    .style("opacity", 0.8)
    .on("mouseover", function (event, d) {
      d3.select(this).style("opacity", 1).style("stroke-width", 3);

      const tooltip = d3.select("#tooltip");
      tooltip.transition().duration(200).style("opacity", 1);

      const percentage = ((d.data.count / filmData.length) * 100).toFixed(1);

      tooltip
        .html(
          `<strong>${d.data.subject}</strong><br/>Awards: ${d.data.count}<br/>Percentage: ${percentage}%`
        )
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 10 + "px");
    })
    .on("mouseout", function (d) {
      d3.select(this).style("opacity", 0.8).style("stroke-width", 2);

      d3.select("#tooltip").transition().duration(200).style("opacity", 0);
    });

  arcs
    .append("text")
    .attr("transform", (d) => `translate(${labelArc.centroid(d)})`)
    .attr("text-anchor", "middle")
    .style("font-size", "12px")
    .style("font-weight", "500")
    .text((d) => {
      const percentage = (d.data.count / filmData.length) * 100;
      return percentage > 5 ? d.data.subject : "";
    });

  arcs
    .append("text")
    .attr("transform", (d) => `translate(${arc.centroid(d)})`)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .style("fill", "white")
    .text((d) => {
      const percentage = (d.data.count / filmData.length) * 100;
      return percentage > 3 ? d.data.count : "";
    });

  g3.append("text")
    .attr("text-anchor", "middle")
    .attr("y", -radius - 20)
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .style("fill", "#333")
    .text("Award-Winning Films by Subject");
}

//vis 4
const margin4 = { top: 40, right: 150, bottom: 100, left: 80 };
const width4 = 800;
const height4 = 500;

const svg4 = d3
  .select("#chart4")
  .attr("width", width4 + margin4.left + margin4.right)
  .attr("height", height4 + margin4.top + margin4.bottom);

const g4 = svg4
  .append("g")
  .attr("transform", `translate(${margin4.left}, ${margin4.top})`);

let groceryData = [];

const incomeColorScale = d3
  .scaleOrdinal()
  .range(["#8B0000", "#FF4500", "#FFD700", "#32CD32", "#4169E1"]);

function categorizeIncome(income) {
  if (income === 0) return "No Income";
  if (income <= 25000) return "Low ($1-25K)";
  if (income <= 50000) return "Medium ($25-50K)";
  if (income <= 75000) return "High ($50-75K)";
  return "Very High ($75K+)";
}

async function loadGroceryData() {
  try {
    const csvUrl =
      "https://raw.githubusercontent.com/wgmckeon/HW2-csv-files/refs/heads/main/grocerystoresurvey.csv";
    const data = await d3.csv(csvUrl);

    const processedData = data
      .map((d) => ({
        age: +d.Age,
        gender: d.Gender,
        income: +d.Income,
        purchaseAmount: +d.PurchaseAmount,
        chain: d.Chain,
        paymentMethod: d.PaymentMethod,
        occupation: d.Occupation,
        familySize: +d.FamilySize,
        incomeCategory: categorizeIncome(+d.Income)
      }))
      .filter((d) => d.chain && d.purchaseAmount && !isNaN(d.purchaseAmount));

    groceryData = processedData;

    createStackedBarChart();

    console.log(`Loaded ${groceryData.length} grocery store survey records`);
  } catch (error) {
    console.error("Error loading grocery data:", error);
    d3.select("#chart4")
      .append("text")
      .attr("x", width4 / 2)
      .attr("y", height4 / 2)
      .attr("text-anchor", "middle")
      .style("fill", "red")
      .text("Error loading grocery store data");
  }
}

function createStackedBarChart() {
  g4.selectAll("*").remove();

  const groupedData = d3.rollup(
    groceryData,
    (v) => d3.sum(v, (d) => d.purchaseAmount),
    (d) => d.chain,
    (d) => d.incomeCategory
  );

  const chains = Array.from(groupedData.keys()).sort();
  const incomeCategories = [
    "No Income",
    "Low ($1-25K)",
    "Medium ($25-50K)",
    "High ($50-75K)",
    "Very High ($75K+)"
  ];

  const stackData = chains.map((chain) => {
    const chainData = { chain: chain };
    incomeCategories.forEach((category) => {
      chainData[category] = groupedData.get(chain)?.get(category) || 0;
    });
    return chainData;
  });

  const xScale = d3.scaleBand().domain(chains).range([0, width4]).padding(0.1);

  const maxTotal = d3.max(stackData, (d) =>
    incomeCategories.reduce((sum, cat) => sum + d[cat], 0)
  );

  const yScale = d3.scaleLinear().domain([0, maxTotal]).range([height4, 0]);

  const stack = d3.stack().keys(incomeCategories);

  const stackedData = stack(stackData);

  incomeColorScale.domain(incomeCategories);

  const bars = g4
    .selectAll(".income-group")
    .data(stackedData)
    .enter()
    .append("g")
    .attr("class", "income-group")
    .style("fill", (d) => incomeColorScale(d.key));

  bars
    .selectAll("rect")
    .data((d) => d)
    .enter()
    .append("rect")
    .attr("x", (d) => xScale(d.data.chain))
    .attr("y", (d) => yScale(d[1]))
    .attr("height", (d) => yScale(d[0]) - yScale(d[1]))
    .attr("width", xScale.bandwidth())
    .style("stroke", "white")
    .style("stroke-width", 1)
    .on("mouseover", function (event, d) {
      d3.select(this).style("opacity", 0.8).style("stroke-width", 2);

      const tooltip = d3.select("#tooltip");
      tooltip.transition().duration(200).style("opacity", 1);

      const incomeCategory = d3.select(this.parentNode).datum().key;
      const amount = d[1] - d[0];

      tooltip
        .html(
          `
                <strong>Chain:</strong> ${d.data.chain}<br/>
                <strong>Income Level:</strong> ${incomeCategory}<br/>
                <strong>Total Spending:</strong> $${amount.toLocaleString()}
            `
        )
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 10 + "px");
    })
    .on("mouseout", function (d) {
      d3.select(this).style("opacity", 1).style("stroke-width", 1);

      d3.select("#tooltip").transition().duration(200).style("opacity", 0);
    });

  g4.append("g")
    .attr("transform", `translate(0, ${height4})`)
    .call(d3.axisBottom(xScale))
    .selectAll("text")
    .style("text-anchor", "end")
    .attr("dx", "-.8em")
    .attr("dy", ".15em")
    .attr("transform", "rotate(-45)")
    .style("font-size", "12px");

  g4.append("g")
    .call(d3.axisLeft(yScale).tickFormat((d) => `$${d / 1000}K`))
    .style("font-size", "12px");

  g4.append("text")
    .attr("x", width4 / 2)
    .attr("y", height4 + margin4.bottom - 10)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text("Grocery Store Chain");

  g4.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin4.left + 20)
    .attr("x", 0 - height4 / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text("Total Amount Spent ($)");

  g4.append("text")
    .attr("x", width4 / 2)
    .attr("y", -20)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Total Spending by Grocery Chain and Income Level");

  createGroceryLegend(incomeCategories);
}

function createGroceryLegend(incomeCategories) {
  const legend = svg4
    .append("g")
    .attr("class", "legend")
    .attr(
      "transform",
      `translate(${width4 + margin4.left + 20}, ${margin4.top + 50})`
    );

  const legendItems = legend
    .selectAll(".legend-item")
    .data(incomeCategories)
    .enter()
    .append("g")
    .attr("class", "legend-item")
    .attr("transform", (d, i) => `translate(0, ${i * 25})`);

  legendItems
    .append("rect")
    .attr("width", 18)
    .attr("height", 18)
    .style("fill", (d) => incomeColorScale(d))
    .style("stroke", "#333")
    .style("stroke-width", 1);

  legendItems
    .append("text")
    .attr("x", 25)
    .attr("y", 9)
    .attr("dy", "0.35em")
    .style("font-size", "12px")
    .style("fill", "#333")
    .text((d) => d);

  legend
    .append("text")
    .attr("x", 0)
    .attr("y", -10)
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .style("fill", "#333")
    .text("Income Levels");
}

//vis 5

const margin5 = { top: 40, right: 150, bottom: 80, left: 80 };
const width5 = 800;
const height5 = 500;

const svg5 = d3
  .select("#chart5")
  .attr("width", width5 + margin5.left + margin5.right)
  .attr("height", height5 + margin5.top + margin5.bottom);

const g5 = svg5
  .append("g")
  .attr("transform", `translate(${margin5.left}, ${margin5.top})`);

let fundsData = [];

const categoryColorScale = d3
  .scaleOrdinal()
  .range(["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"]);

async function loadFundsData() {
  try {
    const csvUrl =
      "https://raw.githubusercontent.com/wgmckeon/HW2-csv-files/refs/heads/main/mutualfunds.csv";
    const data = await d3.csv(csvUrl);

    console.log("Raw CSV data:", data);

    const processedData = data
      .filter(
        (d) =>
          d.Category &&
          d.Category.trim() !== "Grand Total" &&
          d.Category.trim() !== ""
      )
      .map((d) => {
        const netAssets = +(
          d["Net assets"] ||
          d["Net assets,"] ||
          d["Net assets, YTD"] ||
          0
        );
        const ytd = +(d["YTD"] || d[" YTD"] || 0);
        const tenYear = +(d["10YR"] || d[" 10YR"] || 0);
        const fiveYear = +(d["5YR"] || d[" 5YR"] || 0);

        return {
          category: d.Category.trim(),
          netAssets: netAssets,
          ytd: ytd,
          tenYear: tenYear,
          fiveYear: fiveYear
        };
      })
      .filter(
        (d) =>
          !isNaN(d.netAssets) &&
          !isNaN(d.ytd) &&
          !isNaN(d.tenYear) &&
          d.netAssets > 0 &&
          d.category !== ""
      );

    console.log("Processed data:", processedData);

    fundsData = processedData;

    if (fundsData.length === 0) {
      console.error("No valid data found");
      g5.append("text")
        .attr("x", width5 / 2)
        .attr("y", height5 / 2)
        .attr("text-anchor", "middle")
        .style("fill", "red")
        .text("No valid data found");
      return;
    }

    createBubbleChart();

    console.log(`Loaded ${fundsData.length} mutual fund categories`);
  } catch (error) {
    console.error("Error loading funds data:", error);

    g5.append("text")
      .attr("x", width5 / 2)
      .attr("y", height5 / 2)
      .attr("text-anchor", "middle")
      .style("fill", "red")
      .text("Error loading mutual funds data: " + error.message);
  }
}

function createBubbleChart() {
  g5.selectAll("*").remove();

  console.log("Creating bubble chart with data:", fundsData);

  const xExtent = d3.extent(fundsData, (d) => d.tenYear);
  const yExtent = d3.extent(fundsData, (d) => d.ytd);
  const assetExtent = d3.extent(fundsData, (d) => d.netAssets);

  console.log("Extents - X:", xExtent, "Y:", yExtent, "Assets:", assetExtent);

  const xPadding = (xExtent[1] - xExtent[0]) * 0.1;
  const yPadding = (yExtent[1] - yExtent[0]) * 0.1;

  const xScale = d3
    .scaleLinear()
    .domain([xExtent[0] - xPadding, xExtent[1] + xPadding])
    .range([0, width5]);

  const yScale = d3
    .scaleLinear()
    .domain([yExtent[0] - yPadding, yExtent[1] + yPadding])
    .range([height5, 0]);

  const radiusScale = d3.scaleSqrt().domain(assetExtent).range([15, 60]);

  categoryColorScale.domain(fundsData.map((d) => d.category));

  const bubbles = g5
    .selectAll(".bubble")
    .data(fundsData)
    .enter()
    .append("circle")
    .attr("class", "bubble")
    .attr("cx", (d) => xScale(d.tenYear))
    .attr("cy", (d) => yScale(d.ytd))
    .attr("r", (d) => radiusScale(d.netAssets))
    .style("fill", (d) => categoryColorScale(d.category))
    .style("stroke", "#333")
    .style("stroke-width", 2)
    .style("opacity", 0.7)
    .on("mouseover", function (event, d) {
      d3.select(this).style("opacity", 1).style("stroke-width", 3);

      const tooltip = d3.select("#tooltip");
      tooltip.transition().duration(200).style("opacity", 1);

      tooltip
        .html(
          `
                <strong>${d.category}</strong><br/>
                <strong>Net Assets:</strong> $${(d.netAssets / 1000000).toFixed(
                  1
                )}M<br/>
                <strong>YTD Return:</strong> ${d.ytd.toFixed(2)}%<br/>
                <strong>10-Year Return:</strong> ${d.tenYear.toFixed(2)}%<br/>
                <strong>5-Year Return:</strong> ${d.fiveYear.toFixed(2)}%
            `
        )
        .style("left", event.pageX + 10 + "px")
        .style("top", event.pageY - 10 + "px");
    })
    .on("mouseout", function (d) {
      d3.select(this).style("opacity", 0.7).style("stroke-width", 2);

      d3.select("#tooltip").transition().duration(200).style("opacity", 0);
    });

  g5.selectAll(".bubble-label")
    .data(fundsData)
    .enter()
    .append("text")
    .attr("class", "bubble-label")
    .attr("x", (d) => xScale(d.tenYear) + radiusScale(d.netAssets) + 8)
    .attr("y", (d) => yScale(d.ytd))
    .attr("dy", "0.35em")
    .style("font-size", "12px")
    .style("font-weight", "600")
    .style("fill", "#333")
    .style("pointer-events", "none")
    .text((d) => d.category);

  g5.append("g")
    .attr("transform", `translate(0, ${height5})`)
    .call(d3.axisBottom(xScale).tickFormat((d) => d.toFixed(1) + "%"))
    .style("font-size", "12px");

  g5.append("g")
    .call(d3.axisLeft(yScale).tickFormat((d) => d.toFixed(1) + "%"))
    .style("font-size", "12px");

  if (xScale.domain()[0] < 0 && xScale.domain()[1] > 0) {
    g5.append("line")
      .attr("x1", xScale(0))
      .attr("x2", xScale(0))
      .attr("y1", 0)
      .attr("y2", height5)
      .style("stroke", "#999")
      .style("stroke-dasharray", "3,3")
      .style("opacity", 0.5);
  }

  if (yScale.domain()[0] < 0 && yScale.domain()[1] > 0) {
    g5.append("line")
      .attr("x1", 0)
      .attr("x2", width5)
      .attr("y1", yScale(0))
      .attr("y2", yScale(0))
      .style("stroke", "#999")
      .style("stroke-dasharray", "3,3")
      .style("opacity", 0.5);
  }

  g5.append("text")
    .attr("x", width5 / 2)
    .attr("y", height5 + margin5.bottom - 20)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text("10-Year Return (%)");

  g5.append("text")
    .attr("transform", "rotate(-90)")
    .attr("y", 0 - margin5.left + 20)
    .attr("x", 0 - height5 / 2)
    .attr("text-anchor", "middle")
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .text("Year-to-Date Return (%)");

  g5.append("text")
    .attr("x", width5 / 2)
    .attr("y", -20)
    .attr("text-anchor", "middle")
    .style("font-size", "16px")
    .style("font-weight", "bold")
    .text("Mutual Fund Performance: YTD vs 10-Year Returns");

  createFundsLegend();
}

function createFundsLegend() {
  const legend = svg5
    .append("g")
    .attr("class", "legend")
    .attr(
      "transform",
      `translate(${width5 + margin5.left + 20}, ${margin5.top + 50})`
    );

  legend
    .append("text")
    .attr("x", 0)
    .attr("y", -20)
    .style("font-size", "14px")
    .style("font-weight", "bold")
    .style("fill", "#333")
    .text("Fund Categories");

  const legendItems = legend
    .selectAll(".legend-item")
    .data(fundsData)
    .enter()
    .append("g")
    .attr("class", "legend-item")
    .attr("transform", (d, i) => `translate(0, ${i * 25})`);

  legendItems
    .append("circle")
    .attr("cx", 9)
    .attr("cy", 9)
    .attr("r", 8)
    .style("fill", (d) => categoryColorScale(d.category))
    .style("stroke", "#333")
    .style("stroke-width", 1);

  legendItems
    .append("text")
    .attr("x", 25)
    .attr("y", 9)
    .attr("dy", "0.35em")
    .style("font-size", "12px")
    .style("fill", "#333")
    .text((d) => d.category);
}

//intialize visualizations
loadData();

loadCerealData();

loadFilmData();

loadGroceryData();

loadFundsData();