document.getElementById('convert-button').addEventListener('click', function() {
    // Get the input UTC date and time
    const utcInput = document.getElementById('utc-time').value;

    try {
        // Parse the input into a Date object
        const utcDate = new Date(utcInput);

        // Convert UTC to EST using toLocaleString
        const estDateStr = utcDate.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            timeZoneName: 'short'
        });

        // Display the converted EST time
        document.getElementById('est-time').textContent = `Due: EST Time: ${estDateStr}`;
    } catch (error) {
        document.getElementById('est-time').textContent = 'Invalid date format. Please enter a valid UTC date and time.';
    }
});
