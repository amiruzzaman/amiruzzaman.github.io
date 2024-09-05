// Get references to DOM elements
const list1Input = document.getElementById("list1");
const list2Input = document.getElementById("list2");
const generateButton = document.getElementById("generate");
const chartDiv = document.getElementById("chart");

// Set dimensions for the scatter plot
const margin = {top: 20, right: 30, bottom: 40, left: 50},
    width = 800 - margin.left - margin.right,
    height = 400 - margin.top - margin.bottom;

// Create SVG container
const svg = d3.select("#chart")
    .append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);

// Generate scatter plot on button click
generateButton.addEventListener("click", () => {
    // Clear previous chart content
    svg.selectAll("*").remove();

    // Get the user input as arrays of numbers
    const list1 = list1Input.value.split(",").map(Number);
    const list2 = list2Input.value.split(",").map(Number);

    // Check if both lists have the same length
    if (list1.length !== list2.length || list1.some(isNaN) || list2.some(isNaN)) {
        alert("Both lists must contain the same number of valid numbers.");
        return;
    }

    // Create scales for x and y axes
    const xScale = d3.scaleLinear()
        .domain([d3.min(list1), d3.max(list1)])
        .range([0, width]);

    const yScale = d3.scaleLinear()
        .domain([d3.min(list2), d3.max(list2)])
        .range([height, 0]);

    // Add X axis
    svg.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(xScale));

    // Add Y axis
    svg.append("g")
        .call(d3.axisLeft(yScale));

    // Add points to scatter plot
    svg.selectAll("circle")
        .data(list1)
        .enter()
        .append("circle")
        .attr("cx", (d, i) => xScale(d))
        .attr("cy", (d, i) => yScale(list2[i]))
        .attr("r", 5)
        .style("fill", "#69b3a2");

    // Add X axis label
    svg.append("text")
        .attr("text-anchor", "end")
        .attr("x", width / 2 + margin.left)
        .attr("y", height + margin.top + 20)
        .text("List 1 (e.g., Midterm)");

    // Add Y axis label
    svg.append("text")
        .attr("text-anchor", "end")
        .attr("x", -height / 2)
        .attr("y", -margin.left + 20)
        .attr("transform", "rotate(-90)")
        .text("List 2 (e.g., Final)");
});
