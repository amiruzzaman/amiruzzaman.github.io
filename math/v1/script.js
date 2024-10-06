// Function to generate random addition and subtraction problems
function generateProblems() {
    // Generate two random problems
    const num1 = Math.floor(Math.random() * 20) + 1;
    const num2 = Math.floor(Math.random() * 20) + 1;
    const num3 = Math.floor(Math.random() * 20) + 1;
    const num4 = Math.floor(Math.random() * 20) + 1;

    // Set addition and subtraction problems
    document.getElementById('problem1').innerText = `${num1} + ${num2} = `;
    document.getElementById('problem2').innerText = `${num3} - ${num4} = `;

    // Clear previous answers
    document.getElementById('answer1').value = '';
    document.getElementById('answer2').value = '';

    // Clear previous result message
    document.getElementById('result').innerText = '';
}

// Function to verify answers
function verifyAnswers() {
    const num1 = parseInt(document.getElementById('problem1').innerText.split(' ')[0]);
    const num2 = parseInt(document.getElementById('problem1').innerText.split(' ')[2]);
    const num3 = parseInt(document.getElementById('problem2').innerText.split(' ')[0]);
    const num4 = parseInt(document.getElementById('problem2').innerText.split(' ')[2]);

    const correctAnswer1 = num1 + num2;
    const correctAnswer2 = num3 - num4;

    const userAnswer1 = parseInt(document.getElementById('answer1').value);
    const userAnswer2 = parseInt(document.getElementById('answer2').value);

    let resultMessage = '';

    if (userAnswer1 === correctAnswer1 && userAnswer2 === correctAnswer2) {
        resultMessage = 'Great job! Both answers are correct!';
    } else {
        resultMessage = 'Try again! ';
        if (userAnswer1 !== correctAnswer1) {
            resultMessage += `The correct answer for ${num1} + ${num2} is ${correctAnswer1}. `;
        }
        if (userAnswer2 !== correctAnswer2) {
            resultMessage += `The correct answer for ${num3} - ${num4} is ${correctAnswer2}.`;
        }
    }

    document.getElementById('result').innerText = resultMessage;
}

// Generate problems on page load
window.onload = generateProblems;
