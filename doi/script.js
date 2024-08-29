document.getElementById('fileInput').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const content = e.target.result;
            const keys = extractBibTeXKeys(content);
            document.getElementById('keyOutput').value = keys.join('\n');
        };
        reader.readAsText(file);
    }
});

function extractBibTeXKeys(content) {
    const keyRegex = /@[a-zA-Z]+\{([^,]+),/g;
    let match;
    const keys = [];
    while ((match = keyRegex.exec(content)) !== null) {
        keys.push(match[1]);
    }
    return keys;
}

document.getElementById('copyButton').addEventListener('click', function() {
    const keyOutput = document.getElementById('keyOutput');
    keyOutput.select();
    document.execCommand('copy');
});
