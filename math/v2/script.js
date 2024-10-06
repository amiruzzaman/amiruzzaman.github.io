// Helper function to generate random integers with a specific number of digits
function generateRandomNumber(digits) {
    const min = Math.pow(10, digits - 1);
    const max = Math.pow(10, digits) - 1;
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

// Function to generate addition and subtraction problems
function generateProblems() {
    // Randomly generate number of digits (between 2 and 10)
    const digits1 = Math.floor(Math.random() * 9) + 2;
    const digits2 = Math.floor(Math.random() * 9) + 2;

    // Generate two random numbers for addition and subtraction
    const num1 = generateRandomNumber(digits1);
    const num2 = generateRandomNumber(digits2);
    const num3 = generateRandomNumber(digits1);
    const num4 = generateRandomNumber(digits2);

    // Set the numbers for addition and subtraction problems
    document.getElementById('problem1-top').innerText = num1;
    document.getElementById('problem1-bottom').innerText = `+ ${num2}`;
    document.getElementById('problem1-carry').innerText = '';

    document.getElementById('problem2-top').innerText = num3;
    document.getElementById('problem2-bottom').innerText = `- ${num4}`;
    document.getElementById('problem2-carry').innerText = '';

    // Clear previous answers
    document.getElementById('answer1').value = '';
    document.getElementById('answer2').value = '';

    // Clear previous result message
    document.getElementById('result').innerText = '';
}

// Function to calculate carry and display it
function calculateCarry(num1, num2, operation) {
    const strNum1 = num1.toString().split('').reverse();
    const strNum2 = num2.toString().split('').reverse();

    let carry = [];
    let carryValue = 0;

    for (let i = 0; i < Math.max(strNum1.length, strNum2.length); i++) {
        const digit1 = parseInt(strNum1[i] || '0');
        const digit2 = parseInt(strNum2[i] || '0');
        let result = 0;

        if (operation === 'add') {
            result = digit1 + digit2 + carryValue;
            carryValue = result >= 10 ? 1 : 0;
        } else if (operation === 'subtract') {
            result = digit1 - digit2 - carryValue;
            carryValue = result < 0 ? 1 : 0;
        }

        carry.unshift(carryValue);
    }

    return carry.join(' ').trim();
}

// Function to verify answers and calculate carry
function verifyAnswers() {
    const num1 = parseInt(document.getElementById('problem1-top').innerText);
    const num2 = parseInt(document.getElementById('problem1-bottom').innerText.split(' ')[1]);
    const num3 = parseInt(document.getElementById('problem2-top').innerText);
    const num4 = parseInt(document.getElementById('problem2-bottom').innerText.split(' ')[1]);

    const correctAnswer1 = num1 + num2;
    const correctAnswer2 = num3 - num4;

    const userAnswer1 = parseInt(document.getElementById('answer1').value);
    const userAnswer2 = parseInt(document.getElementById('answer2').value);

    // Calculate carry
    const carry1 = calculateCarry(num1, num2, 'add');
    const carry2 = calculateCarry(num3, num4, 'subtract');

    document.getElementById('problem1-carry').innerText = carry1 ? `Carry: ${carry1}` : '';
    document.getElementById('problem2-carry').innerText = carry2 ? `Carry: ${carry2}` : '';

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
