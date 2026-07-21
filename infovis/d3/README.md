# Data Visualization Portfolio

## Project Overview

This project presents interactive data visualizations for five different datasets using JavaScript and D3.js library. Each visualization employs a different technique to best represent the characteristics and insights of each dataset.

## Datasets and Visualizations

### 1. Cars Dataset - Scatter Plot Visualization
**File:** `cars.csv`
**Visualization Type:** Interactive Scatter Plot
**Description:** Displays the relationship between fuel efficiency (MPG) and engine power (Horsepower) for automobiles from 1970-1982, color-coded by country of origin (American, European, Japanese).

**Justification:** A scatter plot is ideal for showing the correlation between two continuous variables (MPG and Horsepower). The color coding by origin adds a categorical dimension that reveals regional manufacturing patterns and preferences.

### 2. Cereals Dataset - Grouped Bar Chart
**File:** `cereals.csv`
**Visualization Type:** Grouped Bar Chart
**Description:** Compares average nutritional content (calories, protein, fiber, sugar) across different cereal manufacturers.

**Justification:** A grouped bar chart effectively compares multiple metrics across categories, allowing easy visual comparison of nutritional profiles between manufacturers. This facilitates informed consumer decision-making by highlighting nutritional differences.

### 3. Film Dataset - Stacked Area Chart
**File:** `film.csv`
**Visualization Type:** Stacked Area Timeline
**Description:** Shows the distribution of movie releases across years and genres, revealing trends in film production over time.

**Justification:** A stacked area chart is perfect for showing how different categories (genres) contribute to a total over time. This visualization reveals both overall industry trends and shifting genre popularity across decades.

### 4. Grocery Store Survey Dataset - Bubble Chart
**File:** `grocerystoresurvey.csv`
**Visualization Type:** Bubble Chart
**Description:** Visualizes individual customers as bubbles, with age on the x-axis, purchase amount on the y-axis, bubble size representing family size, and color representing store chain.

**Justification:** A bubble chart allows for multi-dimensional analysis of individual customer behavior, revealing patterns in age, spending, family size, and store preference. This approach provides a more granular and insightful view than aggregated bar charts.

### 5. Mutual Funds Dataset - Pie Chart with Outside Labels and Color Legend
**File:** `mutualfunds.csv`
**Visualization Type:** Pie Chart with Outside Labels and Color Legend
**Description:** Displays asset allocation across mutual fund categories. All category labels are outside the pie, connected with leader lines, and a color legend is provided for clarity. Interactive tooltips show detailed performance metrics on hover.

**Justification:** The improved pie chart ensures all labels are readable and categories are clearly explained, making it ideal for showing proportional relationships. Leader lines and a color legend enhance clarity and accessibility.

## Technical Implementation

### Technologies Used
- **HTML5** - Page structure and semantic markup
- **CSS3** - Styling and responsive design
- **JavaScript (ES6+)** - Data processing and interactivity
- **D3.js v7** - Data visualization library

### Features
- **Interactive Tooltips** - Hover effects showing detailed information
- **Color-coded Legends** - Clear visual categorization
- **Responsive Design** - Adapts to different screen sizes
- **Data Preprocessing** - Automatic data cleaning and aggregation
- **Smooth Animations** - Enhanced user experience

## File Structure
```
├── index.html          # Main HTML file with embedded visualizations
├── cars.csv           # Automobile performance data
├── cereals.csv        # Cereal nutritional information
├── film.csv          # Movie industry data
├── grocerystoresurvey.csv  # Consumer spending survey data
├── mutualfunds.csv    # Investment fund performance data
└── README.md         # Project documentation
```

## How to Run

1. **Download all files** to the same directory
2. **Open index.html** in a modern web browser (Chrome, Firefox, Safari, Edge)
3. **Ensure internet connection** for D3.js CDN loading
4. **Interact with visualizations** by hovering over data elements

### Requirements
- Modern web browser with JavaScript enabled
- Internet connection (for D3.js library loading)
- All CSV files must be in the same directory as index.html

## Data Processing Notes

### Cars Dataset
- Filters out entries with missing MPG or Horsepower values
- Converts string values to numeric types
- Groups by origin country for color coding

### Cereals Dataset
- Aggregates nutritional data by manufacturer
- Calculates average values for multiple metrics
- Scales protein and fiber values for visual comparison

### Film Dataset
- Groups movies by year and genre
- Creates stacked data structure for area chart
- Handles sparse data years with zero values

### Grocery Store Survey Dataset
- Uses individual customer data points (not just aggregated groups)
- Plots age, purchase amount, family size, and store chain for each customer
- Filters out invalid numeric entries

### Mutual Funds Dataset
- Excludes the "Grand Total" summary row
- Processes performance metrics for multiple time periods
- Calculates percentage allocations for pie chart
- All labels are placed outside the pie with leader lines
- A color legend is provided for all categories

## Browser Compatibility
- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Author
This visualization portfolio demonstrates advanced data visualization techniques using modern web technologies and best practices in information design. 