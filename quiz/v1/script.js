const questionsData = [
  {
    question: "Question 1: Much like Rule 6 in Ten simple rules for structuring papers by Konrad Kording and Brett Mensh, what is the gap the authors provide?",
    feedback: {
      correct: "You have good job capturing some of the gaps from the article.",
      incorrect: "Incorrect! HTML is not a programming language."
    },
    points: 0
  },
  {
    question: "Question 2: What is the hypothesis of the article? Please provide 100 words or less.",
    feedback: {
      correct: "Good work on hypothesis.",
      incorrect: "Incorrect! CSS is a styling language."
    },
    points: 0
  },
  {
    question: "Question 3: What specifics from article do you personally need to look up for understanding of claims? How will this information provide context to the claims? This can include background, notation, and citations. Please provide 400 words or less.",
    feedback: {
      correct: "Good work on this. You have captured important points that would be helpful to understand the article in depth.",
      incorrect: "Incorrect! JavaScript is often used for client-side."
    },
    points: 0
  },
  {
    question: "Question 4: After reviewing and re-reviewing the article, what limitations did do discern? These can be simple or more complex observations. Please provide reasoning in 400 words or less. ",
    feedback: {
      correct: "You have listed some limitations, good work!",
      incorrect: "Incorrect! Python can indeed be used for web development."
    },
    points: 0
  },
  {
    question: "Question 5: What might be next steps to further this research? There is no correct answer here, however your answer must be grounded in reasoning. Please then provide a hypothesis on what you'd like to investigate based on the knowledge gained in this exercise. Be concise with detail.Limit full response to 400 words. ",
    feedback: {
      correct: "Good work presenting some justification and guided your hypothesis using those.",
      incorrect: "Your opinion needed to be guided by reasoning."
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
      <input type="radio" name="question-${index}" value="incorrect" onchange="showFeedbackField(${index})"> Incorrect
      <input type="text" id="custom-feedback-${index}" class="custom-feedback" placeholder="Enter custom feedback" style="display:none;">
    `;
    
    container.appendChild(questionDiv);
  });
}

function showFeedbackField(index) {
  const feedbackField = document.getElementById(`custom-feedback-${index}`);
  feedbackField.style.display = 'block';
}

function calculatePoints() {
  let totalPoints = 0;
  const feedbackSelections = [];

  questionsData.forEach((questionData, index) => {
    const selectedOption = document.querySelector(`input[name="question-${index}"]:checked`);
    
    if (selectedOption) {
      const isCorrect = selectedOption.value === 'correct';
      const customFeedback = document.getElementById(`custom-feedback-${index}`).value;
      
      questionData.points = isCorrect ? 1 : 0.5;
      feedbackSelections.push({
        //question: questionData.question,
		question: questionData.question.match(/^Question \d+:/),
        feedback: isCorrect
          ? questionData.feedback.correct
          : (customFeedback || questionData.feedback.incorrect), // Use custom feedback if provided
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

// Load default questions on page load
document.addEventListener('DOMContentLoaded', () => {
  loadQuestions(questionsData);
});
