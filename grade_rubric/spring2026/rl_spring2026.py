from flask import Flask, render_template_string, request, jsonify, send_file
import json
import os
from io import BytesIO
from datetime import datetime

app = Flask(__name__)

# Initial rubric data (same as from your assignment)
RUBRIC_DATA = {
    "A": {
        "title": "Requirements (10 points)",
        "problems": [[
            {"yes": "LaTeX and Overleaf: You provide your report in LaTeX with a link to Overleaf, as well as provide an accessible GitHub commit hash and clear run instructions in your REPRO document.", "no": "You must provide your report in LaTeX with a link to Overleaf, as well as provide an accessible GitHub commit hash and clear run instructions in your REPRO document.", "point": 10, "key": "A1"},
            {"yes": "Page Length: Your report adheres to the 8-page max length rule.", "no": "Your report must adhere to the 8-page max length rule.", "point": 10, "key": "A2"},
            {"yes": "Legibility: Your graphs, tables, figures and text are legible and properly captioned.", "no": "Your graphs, tables, figures and text must be legible and properly captioned.", "point": 10, "key": "A3"},
            {"yes": "References: You provide a references section and your references consistently adhere to one of three acceptable citation formats (APA, MLA, IEEE).", "no": "You must provide a references section and your references must consistently adhere to one of three acceptable citation formats (APA, MLA, IEEE).", "point": 10, "key": "A4"}
        ]]
    },
    "B": {
        "title": "Hypothesis (8 points)",
        "problems": [[
            {"yes": "Hypothesis Declaration: You provide at least one explicitly stated, coherent and well-reasoned hypothesis that paves the way to measured experiments to draw out conclusions about your algorithms and MDP environments.", "no": "You must provide at least one explicitly stated, coherent and well-reasoned hypothesis that paves the way to measured experiments to draw out conclusions about your algorithms and MDP environments.", "point": 2, "key": "B1"},
            {"yes": "Hypothesis Base Rationale: You provide suitable grounding of each hypothesis declared by citing theory such as drawing from lecture, official textbooks, the provided FAQ, a trusted publication or well-established RL theory.", "no": "You must provide suitable grounding of each hypothesis declared by citing theory such as drawing from lecture, official textbooks, the provided FAQ, a trusted publication or well-established RL theory.", "point": 2, "key": "B2"},
            {"yes": "Hypothesis Follow-Through: You follow-up through your experiments and in your conclusion on each hypothesis provided and provide evaluation of whether the results you find validate or invalidate each hypothesis.", "no": "You must provide follow-up through your experiments and in your conclusion on each hypothesis provided as well as evaluate whether the results you find validate or invalidate each hypothesis.", "point": 2, "key": "B3"},
            {"yes": "Hypothesis Conclusion Justification: Your conclusions regarding each hypothesis are well-defended; you appropriately cite plots, tables and other figures in your report to justify your conclusions.", "no": "Your conclusions regarding each hypothesis must be well-defended; you must appropriately cite plots, tables and other figures in your report to justify your conclusions.", "point": 2, "key": "B4"}
        ]]
    },
    "C": {
        "title": "MDP Overview and Discretization (24 points)",
        "problems": [[
            {"yes": "Blackjack MDP: You appropriately set the scene with MDP descriptive items like state, action and reward structure (including player sum, dealer up card, usable-ace flag for states, hit and stick for actions and +1, 0, -1 for win, draw and loss, respectively) and you describe the episodic nature of the MDP through Blackjack rules like the episode ending by bust or stick.", "no": "You must appropriately set the scene with MDP descriptive items like state, action and reward structure (including player sum, dealer up card, usable-ace flag for states, hit and stick for actions and +1, 0, -1 for win, draw and loss, respectively) and you need to describe the episodic nature of the MDP through Blackjack rules like the episode ending by bust or stick.", "point": 8, "key": "C1"},
            {"yes": "Cartpole MDP: You list each of the relevant state variables for Cartpole, including cart position and velocity and pole angle and angular velocity, and you aptly address the actions of left or right applied force and reward per time step sustained of +1. You appropriately outline the termination conditions such as out-of-bounds angle and position thresholds.", "no": "You should list each of the relevant state variables for Cartpole, including cart position and velocity and pole angle and angular velocity, as well as address the actions of left or right applied force and reward per time step sustained of +1. You also need to outline the termination conditions such as out-of-bounds angle and position thresholds.", "point": 8, "key": "C2"},
            {"yes": "Comparison and Discretization Strategy: You address the matter of Blackjack being a small/discrete problem and state space while Cartpole is continuous and varies in scale based on its discretization for application to VI/PI and tabular RL approaches. You address the implications of discrete vs. continuous problems and the need to discretize carefully on the ease of problem setup and ultimately performance. You clearly articulate how you went about discretization, calling upon mapping of continuous states to bins and number of bins per feature. You appropriately address the repercussions of binning choices on runtime fidelity and computation or memory tradeoffs to help the reader appreciate the differences in scale on discretizing.", "no": "You must address the matter of Blackjack being a small/discrete problem and state space while Cartpole is continuous and varies in scale based on its discretization for application to VI/PI and tabular RL approaches. You need also to address the implications of discrete vs. continuous problems and the need to discretize carefully on the ease of problem setup and ultimately performance. You should always clearly articulate how you went about discretization, calling upon mapping of continuous states to bins and number of bins per feature. You should have also addressed the repercussions of binning choices on runtime fidelity and computation or memory tradeoffs to help the reader appreciate the differences in scale on discretizing.", "point": 8, "key": "C3"}
        ]]
    },
    "D": {
        "title": "Value Iteration and Policy Iteration (30 points)",
        "problems": [[
            {"yes": "VI/PI Explanation: You appropriately make mention of Bellman optimality updates in the context of Value Iteration to the point of its convergence. You also describe the policy-evaluation (value at the current policy) and greedy policy improvement loop. You address convergence guarantees in finite MDPs whose transition dynamics are known, and you contrast VI with PI as it relates to their respective updates and computational tradeoffs therein.", "no": "You must make mention of Bellman optimality updates in the context of Value Iteration to the point of its convergence. You also must describe the policy-evaluation (value at the current policy) and greedy policy improvement loop. You should have addressed convergence guarantees in finite MDPs whose transition dynamics are known, and you needed to contrast VI with PI as it relates to their respective updates and computational tradeoffs therein.", "point": 6, "key": "D1"},
            {"yes": "Convergence Visualizations: You provide four distinct plots spanning both problems (Cartpole and Blackjack) and both DP MDP methods (VI and PI). Your VI-Blackjack change in value per iteration plot shows clear convergence at or above your threshold. Your PI-Blackjack plot demonstrates the number of policy changes over iterations, where a decrease in policy change is expected as you stabilize near the optimal policy. Your VI-Cartpole change in value per iteration plot demonstrates the same as with Blackjack with the addition of alluding to your discretization selections and how their results may vary. Your PI-Cartpole shows the same as Blackjack with the addition again of discretization coarseness-based stability and convergence.", "no": "You should have provided four distinct plots spanning both problems (Cartpole and Blackjack) and both DP MDP methods (VI and PI). You should have included a VI-Blackjack change in value per iteration plot showing clear convergence at or above your threshold. Your PI-Blackjack plot must also demonstrate the number of policy changes over iterations, where a decrease in policy change is expected as you stabilize near the optimal policy. You were expected to provide a VI-Cartpole change in value per iteration plot which demonstrates the same as with Blackjack with the addition of some alluding to your discretization selections and how their results varied. Your PI-Cartpole was expected to show the same as Blackjack with the addition again of discretization coarseness-based stability and convergence.", "point": 8, "key": "D2"},
            {"yes": "Convergence Analysis: You appropriately study convergence under different hyperparameter tuning regimes, including theta and gamma, where several values of each are tested. You address the convergence speed discrepancy (in terms of iteration count) between PI and VI, and situate this in the greedy policy improvement step of the PI loop. You note the iterations to convergence for both VI and PI and provide explicit (such as an equation that's cited) convergence formulation.", "no": "You must appropriately analyze convergence under different hyperparameter tuning regimes, including theta and gamma, where several values of each must be tested. You should address the convergence speed discrepancy (in terms of iteration count) between PI and VI, and situate this in the greedy policy improvement step of the PI loop. You should've noted the iterations to convergence for both VI and PI and provide explicit (such as an equation that's cited) convergence formulation.", "point": 6, "key": "D3"},
            {"yes": "Final Policy Comparison: Your address of the differing and similar results between VI and PI, such as whether they converge on the same best policy at time of convergence, is well done. You provide justification in either case and your visual for this section helps reinforce the underlying claim and observations.", "no": "You should have addressed the differing and similar results between VI and PI, such as whether they converge on the same best policy at time of convergence. Providing justification in either case, your visual for this section should help reinforce the underlying claim and observations.", "point": 5, "key": "D4"},
            {"yes": "State Space Impact on Cartpole: You explicitly acknowledge approximation error associated with discretization and discuss the tradeoffs between discretizations via quantitative or otherwise demonstrable means like demonstrating the effect of binning on state space size and ultimately on policy granularity and optimality, compute overhead and runtime.", "no": "You needed to acknowledge approximation error associated with discretization and discuss the tradeoffs between discretizations via quantitative or otherwise demonstrable means like demonstrating the effect of binning on state space size and ultimately on policy granularity and optimality, compute overhead and runtime.", "point": 5, "key": "D5"}
        ]]
    },
    "E": {
        "title": "Model-Free Control w/ SARSA and Q-Learning (28 points)",
        "problems": [[
            {"yes": "Algorithm Explanation and On/Off-Policy Nuance: You provide suitable explanation or explicitly provide the update equations for both SARSA and Q-Learning and address SARSA as on-policy (with interpretation) and Q-Learning as off-policy (with interpretation).", "no": "You must provide suitable explanation or explicitly provide the update equations for both SARSA and Q-Learning and address SARSA as on-policy (with interpretation) and Q-Learning as off-policy (with interpretation).", "point": 6, "key": "E1"},
            {"yes": "Learning and Convergence Diagnostics: You show both learning and convergence on both algorithms and both environments for a total of four plots. You provide performance trajectories by some means (reward or episode length vs episodes) and offer a signal of stability in the form of mean delta-Q or TD-error decay or variance/stdev of returns and offer follow-up discussion.", "no": "You should show both learning and convergence on both algorithms and both environments for a total of four plots. You also should have provided performance trajectories by some means (reward or episode length vs episodes) and offered a signal of stability in the form of mean delta-Q or TD-error decay or variance/stdev of returns with follow-up discussion.", "point": 8, "key": "E2"},
            {"yes": "Exploration Strategy Design and Impact: You describe one or more exploration scheme and delve into their parameter settings as well as provide justification for the schedule with respect to its suitability exploring both environments. In doing so, you provide clear quantitative evidence to compare behavior under the given schedule and you connect this back to the schedule's mechanics as well as those of the environment's state-action space.", "no": "You must describe one or more exploration scheme and delve into their parameter settings as well as provide justification for the schedule with respect to its suitability in exploring both environments. In doing so, you should have provided clear quantitative evidence to compare behavior under the given schedule while connecting this back to the schedule's mechanics as well as those of the environment's state-action space.", "point": 6, "key": "E3"},
            {"yes": "Policy and Behavioral Analysis: You offer comparison between SARSA and Q-Learning's policies and behaviors for both MDPs and illustrate the effects through your visuals, value tables, heatmaps, etc. You tie the observed behaviors back to the nature of the active method being on or off-policy as well as address the role of exploration schedule and the variations you find therein. You also draw comparison between your observations on one of the model-free methods and the model-based DP ones and invoke evidence to highlight any differences you call to attention.", "no": "You need to compare between SARSA and Q-Learning's policies and behaviors for both MDPs and to illustrate the effects through your visuals, value tables, heatmaps, etc. You must tie the observed behaviors back to the nature of the active method being on or off-policy as well as address the role of exploration schedule and the variations you find therein. You should also draw comparison between your observations on one of the model-free methods and the model-based DP ones and invoke evidence to highlight any differences called to attention.", "point": 8, "key": "E4"}
        ]]
    },
    "EC": {
        "title": "Extra Credit: Cartpole DQN (5 points)",
        "problems": [[
            {"yes": "Full DQN implementation: Your DQN implementation includes a replay buffer for learning on traceback AND target network for computation of training targets and you provide some substantive improvement such as one from Rainbow DQN or an independent ablation. Your entire architecture including parameters like buffer size, batch size, learning rate, gamma, epsilon schedule and target update are adequately described. Your output learning curves are clear and are compared with SARSA and Q-Learning, where you also address stability performance, issues and mitigation and quantitative comparison that you provide appropriate justification for.", "no": "Not applicable - insufficient DQN implementation", "point": 5, "key": "EC_FULL"},
            {"yes": "Partial DQN: Your DQN is set to learn on Cartpole with at least one of replay buffer OR target network. You provide partial but incomplete overview of your parameters tuned and the overall architecture. You allude to your tabular methods SARSA and Q-Learning and offer some comparison between these and DQN, however this is surface level and doesn't come with quantitative proof or interpretation of the underlying mechanisms. Rainbow modification, if at all provided, is deemed to be shallower than is expected in order to earn the full score.", "no": "Not applicable", "point": 3, "key": "EC_PARTIAL"},
            {"yes": "Incomplete attempt: You present an honest (and commendable), yet incomplete attempt at implementing DQN, where across the gamut of discussion points from architecture to hyperparameter settings and tuning as well as visiting failure modes, we felt you underdelivered in spite of your noble attempt. We felt for any extension to your tabular methods (SARSA and Q-Learning), your comparison skimmed the surface and was not up to par with our expectations for fuller credit here.", "no": "Not applicable", "point": 1, "key": "EC_MINIMAL"},
            {"yes": "No attempt or cursory attempt: You either did not attempt the Extra Credit portion, or any attempts seen in the report were slightly too cursory to be deserving of extra credit.", "no": "Not applicable", "point": 0, "key": "EC_NONE"}
        ]]
    }
}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rubric Editor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 0.9em;
        }
        
        .toolbar {
            padding: 20px 30px;
            background: #f7f9fc;
            border-bottom: 1px solid #e1e8ed;
            display: flex;
            gap: 15px;
            justify-content: flex-end;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-success {
            background: #10b981;
            color: white;
        }
        
        .btn-success:hover {
            background: #059669;
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        
        .btn-secondary:hover {
            background: #5a6268;
        }
        
        .status {
            padding: 10px 20px;
            margin: 0 30px 20px 30px;
            border-radius: 6px;
            font-size: 14px;
            display: none;
        }
        
        .status.success {
            background: #d1fae5;
            color: #065f46;
            border: 1px solid #a7f3d0;
            display: block;
        }
        
        .status.error {
            background: #fee2e2;
            color: #991b1b;
            border: 1px solid #fecaca;
            display: block;
        }
        
        .content {
            padding: 30px;
            max-height: 70vh;
            overflow-y: auto;
        }
        
        .rubric-section {
            margin-bottom: 30px;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .section-header {
            background: #f7f9fc;
            padding: 15px 20px;
            border-bottom: 1px solid #e1e8ed;
            cursor: pointer;
            user-select: none;
            transition: background 0.2s;
        }
        
        .section-header:hover {
            background: #eef2f7;
        }
        
        .section-header h2 {
            font-size: 1.3em;
            color: #2d3748;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .collapse-icon {
            font-size: 1.2em;
            transition: transform 0.3s;
        }
        
        .section-content {
            padding: 20px;
            display: block;
        }
        
        .section-content.collapsed {
            display: none;
        }
        
        .rubric-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        
        .rubric-table th {
            background: #f7f9fc;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #2d3748;
            border-bottom: 2px solid #e1e8ed;
        }
        
        .rubric-table td {
            padding: 15px 12px;
            border-bottom: 1px solid #e1e8ed;
            vertical-align: top;
        }
        
        .rubric-table tr:last-child td {
            border-bottom: none;
        }
        
        .criteria-key {
            font-weight: 600;
            color: #667eea;
            width: 60px;
        }
        
        .criteria-points {
            width: 80px;
            text-align: center;
        }
        
        .points-input {
            width: 70px;
            padding: 5px 8px;
            border: 1px solid #cbd5e0;
            border-radius: 4px;
            font-size: 14px;
            text-align: center;
        }
        
        .points-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .criteria-text {
            line-height: 1.5;
        }
        
        .criteria-text textarea {
            width: 100%;
            padding: 8px;
            border: 1px solid #cbd5e0;
            border-radius: 4px;
            font-family: inherit;
            font-size: 14px;
            resize: vertical;
        }
        
        .criteria-text textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
            margin-right: 8px;
        }
        
        .badge-yes {
            background: #d1fae5;
            color: #065f46;
        }
        
        .badge-no {
            background: #fee2e2;
            color: #991b1b;
        }
        
        .auto-save-indicator {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #2d3748;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            opacity: 0;
            transition: opacity 0.3s;
            pointer-events: none;
        }
        
        .auto-save-indicator.show {
            opacity: 0.8;
        }
        
        @media (max-width: 768px) {
            .content {
                padding: 15px;
            }
            
            .rubric-table th,
            .rubric-table td {
                padding: 10px 8px;
            }
            
            .criteria-key {
                width: 50px;
                font-size: 12px;
            }
            
            .toolbar {
                padding: 15px;
            }
        }
        
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📋 Rubric Editor</h1>
            <p>Edit rubric criteria, points, and descriptions - changes auto-save to JSON</p>
        </div>
        
        <div class="toolbar">
            <button class="btn btn-secondary" onclick="expandAll()">📂 Expand All</button>
            <button class="btn btn-secondary" onclick="collapseAll()">📁 Collapse All</button>
            <button class="btn btn-success" onclick="downloadRubric()">💾 Download JSON</button>
        </div>
        
        <div id="status" class="status"></div>
        
        <div class="content" id="rubric-content">
            <!-- Dynamic content will be loaded here -->
            <div style="text-align: center; padding: 40px;">Loading rubric...</div>
        </div>
    </div>
    
    <div id="autoSaveIndicator" class="auto-save-indicator">Auto-saved ✓</div>
    
    <script>
        let rubricData = {};
        let saveTimeout = null;
        
        // Load rubric data from server
        async function loadRubric() {
            try {
                const response = await fetch('/api/rubric');
                rubricData = await response.json();
                renderRubric();
            } catch (error) {
                showStatus('Error loading rubric: ' + error.message, 'error');
            }
        }
        
        // Render the rubric as HTML tables
        function renderRubric() {
            const container = document.getElementById('rubric-content');
            let html = '';
            
            for (const [sectionKey, section] of Object.entries(rubricData)) {
                const sectionId = `section-${sectionKey}`;
                html += `
                    <div class="rubric-section">
                        <div class="section-header" onclick="toggleSection('${sectionId}')">
                            <h2>
                                <span>${section.title}</span>
                                <span class="collapse-icon" id="${sectionId}-icon">▼</span>
                            </h2>
                        </div>
                        <div class="section-content" id="${sectionId}">
                `;
                
                // Handle different problem structures
                if (section.problems && Array.isArray(section.problems)) {
                    for (const problemGroup of section.problems) {
                        if (Array.isArray(problemGroup)) {
                            html += `
                                <table class="rubric-table">
                                    <thead>
                                        <tr><th style="width: 60px;">Criteria</th><th>Description</th><th style="width: 100px;">Points</th></tr>
                                    </thead>
                                    <tbody>
                            `;
                            
                            for (const item of problemGroup) {
                                html += `
                                    <tr>
                                        <td class="criteria-key">${item.key}</td>
                                        <td class="criteria-text">
                                            <div>
                                                <span class="badge badge-yes">Yes</span>
                                                <textarea rows="2" data-section="${sectionKey}" data-key="${item.key}" data-field="yes" onchange="scheduleAutoSave()">${escapeHtml(item.yes)}</textarea>
                                            </div>
                                            <div style="margin-top: 10px;">
                                                <span class="badge badge-no">No</span>
                                                <textarea rows="2" data-section="${sectionKey}" data-key="${item.key}" data-field="no" onchange="scheduleAutoSave()">${escapeHtml(item.no)}</textarea>
                                            </div>
                                        </td>
                                        <td class="criteria-points">
                                            <input type="number" class="points-input" data-section="${sectionKey}" data-key="${item.key}" value="${item.point}" step="any" onchange="scheduleAutoSave()">
                                        </td>
                                    </tr>
                                `;
                            }
                            
                            html += `
                                    </tbody>
                                </table>
                            `;
                        }
                    }
                }
                
                html += `
                        </div>
                    </div>
                `;
            }
            
            container.innerHTML = html;
        }
        
        // Helper function to escape HTML
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        // Toggle section collapse/expand
        function toggleSection(sectionId) {
            const content = document.getElementById(sectionId);
            const icon = document.getElementById(`${sectionId}-icon`);
            
            if (content.classList.contains('collapsed')) {
                content.classList.remove('collapsed');
                icon.textContent = '▼';
            } else {
                content.classList.add('collapsed');
                icon.textContent = '▶';
            }
        }
        
        // Expand all sections
        function expandAll() {
            const sections = document.querySelectorAll('.section-content');
            const icons = document.querySelectorAll('.collapse-icon');
            
            sections.forEach(section => section.classList.remove('collapsed'));
            icons.forEach(icon => icon.textContent = '▼');
        }
        
        // Collapse all sections
        function collapseAll() {
            const sections = document.querySelectorAll('.section-content');
            const icons = document.querySelectorAll('.collapse-icon');
            
            sections.forEach(section => section.classList.add('collapsed'));
            icons.forEach(icon => icon.textContent = '▶');
        }
        
        // Schedule auto-save after user stops typing
        function scheduleAutoSave() {
            if (saveTimeout) clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => saveRubric(), 1000);
            showAutoSaveIndicator();
        }
        
        // Save rubric data to server
        async function saveRubric() {
            try {
                // Collect all changes from the DOM
                const textareas = document.querySelectorAll('textarea[data-section][data-key]');
                const inputs = document.querySelectorAll('input.points-input');
                
                for (const textarea of textareas) {
                    const section = textarea.dataset.section;
                    const key = textarea.dataset.key;
                    const field = textarea.dataset.field;
                    const value = textarea.value;
                    
                    // Find the item in rubricData
                    for (const problemGroup of rubricData[section].problems) {
                        for (const item of problemGroup) {
                            if (item.key === key) {
                                item[field] = value;
                                break;
                            }
                        }
                    }
                }
                
                for (const input of inputs) {
                    const section = input.dataset.section;
                    const key = input.dataset.key;
                    let value = parseFloat(input.value);
                    
                    // Find the item in rubricData
                    for (const problemGroup of rubricData[section].problems) {
                        for (const item of problemGroup) {
                            if (item.key === key) {
                                item.point = isNaN(value) ? 0 : value;
                                break;
                            }
                        }
                    }
                }
                
                // Send to server
                const response = await fetch('/api/rubric', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(rubricData)
                });
                
                if (response.ok) {
                    showStatus('Changes saved successfully', 'success');
                } else {
                    throw new Error('Failed to save');
                }
            } catch (error) {
                showStatus('Error saving changes: ' + error.message, 'error');
            }
        }
        
        // Download rubric as JSON file
        async function downloadRubric() {
            try {
                // First ensure latest data is saved
                await saveRubric();
                
                const response = await fetch('/api/rubric/download');
                const blob = await response.blob();
                
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `rubric_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
                
                showStatus('Rubric downloaded successfully', 'success');
            } catch (error) {
                showStatus('Error downloading rubric: ' + error.message, 'error');
            }
        }
        
        // Show status message
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = `status ${type}`;
            
            setTimeout(() => {
                statusDiv.className = 'status';
            }, 3000);
        }
        
        // Show auto-save indicator
        function showAutoSaveIndicator() {
            const indicator = document.getElementById('autoSaveIndicator');
            indicator.classList.add('show');
            
            setTimeout(() => {
                indicator.classList.remove('show');
            }, 1500);
        }
        
        // Add keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Ctrl+S to save manually
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveRubric();
            }
            // Ctrl+E to expand all
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                expandAll();
            }
        });
        
        // Initialize
        loadRubric();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/rubric', methods=['GET'])
def get_rubric():
    return jsonify(RUBRIC_DATA)

@app.route('/api/rubric', methods=['POST'])
def update_rubric():
    global RUBRIC_DATA
    try:
        RUBRIC_DATA = request.json
        return jsonify({'status': 'success', 'message': 'Rubric saved successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/rubric/download', methods=['GET'])
def download_rubric():
    try:
        json_str = json.dumps(RUBRIC_DATA, indent=2, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        return send_file(
            BytesIO(json_bytes),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'rubric_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)