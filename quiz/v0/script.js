const questionsData = [
  {
    question: "Question 1: Is HTML a programming language?",
    feedback: {
      correct: "Correct! HTML is a markup language.",
      incorrect: "Incorrect! HTML is not a programming language."
    },
    points: 0
  },
  {
    question: "Question 2: Is CSS used for styling?",
    feedback: {
      correct: "Correct! CSS is used to style web pages.",
      incorrect: "Incorrect! CSS is a styling language."
    },
    points: 0
  },
  {
    question: "Question 3: Is JavaScript a server-side language?",
    feedback: {
      correct: "Correct! JavaScript can be used server-side with Node.js.",
      incorrect: "Incorrect! JavaScript is often used for client-side."
    },
    points: 0
  },
  {
    question: "Question 4: Is Python used for web development?",
    feedback: {
      correct: "Correct! Python can be used with frameworks like Django and Flask.",
      incorrect: "Incorrect! Python can indeed be used for web development."
    },
    points: 0
  },
  {
    question: "Question 5: Is React a library for building UIs?",
    feedback: {
      correct: "Correct! React is a UI library by Facebook.",
      incorrect: "Incorrect! React is a library for building user interfaces."
    },
    points: 0
  }
];

function loadQuestions(questions) {
  const container = document.getElementById('questions-container');
  container.innerHTML = '';
  
  questions.forEach((questionData, index) => {
    const questionDiv = document.createElement('div');
    questionDiv.className = 'question-item';

    questionDiv.innerHTML = `
      <label class="question-label">${questionData.question}</label>
      <input type="radio" name="question-${index}" value="correct"> Correct
      <input type="radio" name="question-${index}" value="incorrect"> Incorrect
    `;
    
    container.appendChild(questionDiv);
  });
}

function calculatePoints() {
  let totalPoints = 0;
  const feedbackSelections = [];

  questionsData.forEach((questionData, index) => {
    const selectedOption = document.querySelector(`input[name="question-${index}"]:checked`);
    
    if (selectedOption) {
      const isCorrect = selectedOption.value === 'correct';
      questionData.points = isCorrect ? 1 : 0.5;
      feedbackSelections.push({
        //question: questionData.question,
		question: questionData.question.match(/^Question \d+:/),
        feedback: isCorrect ? questionData.feedback.correct : questionData.feedback.incorrect,
        //points: questionData.points
      });
      totalPoints += questionData.points;
    }
  });

  document.getElementById('total-points').innerText = `Total Points: ${totalPoints}`;
  return feedbackSelections;
}

function downloadFeedback(format) {
  const feedbackSelections = calculatePoints();

  if (format === 'txt') {
    //const txtContent = feedbackSelections.map(item => `${item.question}\nFeedback: ${item.feedback}\nPoints: ${item.points}\n`).join('\n');
	const txtContent = feedbackSelections.map(item => `${item.question}${item.feedback}`).join('\n');
    downloadFile(txtContent, 'feedback.txt', 'text/plain');
  } else if (format === 'json') {
    const jsonContent = JSON.stringify(feedbackSelections, null, 2);
    downloadFile(jsonContent, 'selections.json', 'application/json');
  }
}

function downloadFile(content, fileName, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = fileName;
  link.click();
}

function uploadJsonFile() {
  const fileInput = document.getElementById('file-input');
  const file = fileInput.files[0];

  if (file) {
    const reader = new FileReader();
    reader.onload = function(event) {
      const questionsFromFile = JSON.parse(event.target.result);
      loadQuestions(questionsFromFile);
    };
    reader.readAsText(file);
  }
}

function extractQuestionNumbers(questions) {
  return questions.map(questionObj => {
    // Use regex to match "Question X:" part of the question string
    const match = questionObj.question.match(/^Question \d+:/);
    return match ? match[0] : null;
  });
}

// Example usage:
const questionNumbers = extractQuestionNumbers(questionsData);
console.log(questionNumbers);


// Load default questions on page load
document.addEventListener('DOMContentLoaded', () => {
  loadQuestions(questionsData);
});


