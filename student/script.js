// script.js
document.getElementById('compareBtn').addEventListener('click', function() {
    const file1 = document.getElementById('file1').files[0];
    const file2 = document.getElementById('file2').files[0];

    if (file1 && file2) {
        parseCSV(file1, function(data1) {
            parseCSV(file2, function(data2) {
                const differences = findDifferences(data1, data2);
                displayResults(differences);
            });
        });
    } else {
        alert('Please select both files.');
    }
});

function parseCSV(file, callback) {
    Papa.parse(file, {
        complete: function(results) {
            callback(results.data);
        },
        header: true
    });
}

function findDifferences(data1, data2) {
    const set1 = new Set(data1.map(row => JSON.stringify(row)));
    const set2 = new Set(data2.map(row => JSON.stringify(row)));

    const differences = [];

    set1.forEach(item => {
        if (!set2.has(item)) {
            differences.push(JSON.parse(item));
        }
    });

    set2.forEach(item => {
        if (!set1.has(item)) {
            differences.push(JSON.parse(item));
        }
    });

    return differences;
}

function displayResults(differences) {
    const resultsElement = document.getElementById('results');
    resultsElement.innerHTML = '';

    if (differences.length > 0) {
        differences.forEach(diff => {
            const li = document.createElement('li');
            li.textContent = JSON.stringify(diff);
            resultsElement.appendChild(li);
        });
    } else {
        const li = document.createElement('li');
        li.textContent = 'No differences found.';
        resultsElement.appendChild(li);
    }
}
