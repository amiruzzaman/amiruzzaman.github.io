document.getElementById('entry-type').addEventListener('change', generateForm);
document.getElementById('generate-button').addEventListener('click', generateBibTeX);
document.getElementById('copy-button').addEventListener('click', copyToClipboard);

function generateForm() {
    const entryType = document.getElementById('entry-type').value;
    const formContainer = document.getElementById('form-container');
    formContainer.innerHTML = ''; // Clear previous form

    let formFields = '';

    switch (entryType) {
        case 'journal':
            formFields = `
                <label>Author:</label><input type="text" id="author">
                <label>Title:</label><input type="text" id="title">
                <label>Journal:</label><input type="text" id="journal">
                <label>Year:</label><input type="text" id="year">
                <label>Volume:</label><input type="text" id="volume">
                <label>Pages:</label><input type="text" id="pages">
            `;
            break;
        case 'conference':
            formFields = `
                <label>Author:</label><input type="text" id="author">
                <label>Title:</label><input type="text" id="title">
                <label>Conference:</label><input type="text" id="conference">
                <label>Year:</label><input type="text" id="year">
                <label>Location:</label><input type="text" id="location">
            `;
            break;
        case 'book':
            formFields = `
                <label>Author:</label><input type="text" id="author">
                <label>Title:</label><input type="text" id="title">
                <label>Publisher:</label><input type="text" id="publisher">
                <label>Year:</label><input type="text" id="year">
            `;
            break;
        case 'chapter':
            formFields = `
                <label>Author:</label><input type="text" id="author">
                <label>Title:</label><input type="text" id="title">
                <label>Book Title:</label><input type="text" id="booktitle">
                <label>Pages:</label><input type="text" id="pages">
                <label>Year:</label><input type="text" id="year">
            `;
            break;
        case 'thesis':
            formFields = `
                <label>Author:</label><input type="text" id="author">
                <label>Title:</label><input type="text" id="title">
                <label>University:</label><input type="text" id="university">
                <label>Year:</label><input type="text" id="year">
            `;
            break;
        case 'misc':
            formFields = `
                <label>Author:</label><input type="text" id="author">
                <label>Title:</label><input type="text" id="title">
                <label>Note:</label><input type="text" id="note">
            `;
            break;
    }

    formContainer.innerHTML = formFields;
}

function generateBibTeX() {
    const entryType = document.getElementById('entry-type').value;
    if (!entryType) return alert('Please select an entry type.');

    let bibtex = `@${entryType}{example,\n`;
    const inputs = document.querySelectorAll('#form-container input');
    inputs.forEach(input => {
        const key = input.id;
        const value = input.value.trim();
        if (value) bibtex += `  ${key} = {${value}},\n`;
    });
    bibtex += '}';

    document.getElementById('bibtex-output').textContent = bibtex;
    document.getElementById('output').style.display = 'block';
}

function copyToClipboard() {
    const bibtexOutput = document.getElementById('bibtex-output');
    navigator.clipboard.writeText(bibtexOutput.textContent).then(() => {
        alert('BibTeX copied to clipboard!');
    });
}
