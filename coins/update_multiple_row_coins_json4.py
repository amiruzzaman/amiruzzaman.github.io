#!/usr/bin/env python3
"""
Numismatic Vault - Professional Coin Management System
Features: Bulk editing, inline editing, div-based table, CSS notifications, auto-open browser
NO EMOJIS - All icons are pure CSS/SVG
UPDATED: Removed "Apply Bulk" button, unified save workflow
"""

from flask import Flask, render_template_string, request, jsonify
import json
import os
import webbrowser
import threading

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(BASE_DIR, 'images', 'coins.json')

# Ensure the images directory exists
os.makedirs(os.path.dirname(FILE_NAME), exist_ok=True)

# Create sample data if file doesn't exist
if not os.path.exists(FILE_NAME):
    sample_data = [
        {"image": "coin_001", "box": "A1", "country": "USA", "currency_type": "Morgan Dollar", "note": "Silver dollar", "year": "1881", "donor_name": "Smith Collection"},
        {"image": "coin_002", "box": "A2", "country": "Great Britain", "currency_type": "Sovereign", "note": "Gold coin", "year": "1902", "donor_name": "Royal Mint"},
        {"image": "coin_003", "box": "B1", "country": "Canada", "currency_type": "Maple Leaf", "note": "Proof silver", "year": "1976", "donor_name": "Johnson Estate"},
        {"image": "coin_004", "box": "B2", "country": "Germany", "currency_type": "Mark", "note": "Weimar Republic", "year": "1923", "donor_name": "Schmidt Donation"}
    ]
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>Numismatic Vault | Professional Coin Manager</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
            background: #f0f2f8;
            padding: 28px 32px;
            color: #1a2634;
        }

        .vault-container {
            max-width: 1600px;
            margin: 0 auto;
        }

        /* Header with CSS icon */
        .header {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            flex-wrap: wrap;
            margin-bottom: 24px;
            gap: 16px;
        }

        .title-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .vault-icon {
            width: 40px;
            height: 40px;
            background: #1e3a5f;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }

        .vault-icon svg {
            width: 24px;
            height: 24px;
            stroke: white;
            stroke-width: 1.7;
            fill: none;
        }

        h1 {
            font-size: 1.9rem;
            font-weight: 600;
            letter-spacing: -0.3px;
            background: linear-gradient(135deg, #1e3a5f, #2c5282);
            background-clip: text;
            -webkit-background-clip: text;
            color: transparent;
        }

        .badge {
            background: #e9eef3;
            padding: 6px 12px;
            border-radius: 40px;
            font-size: 0.8rem;
            font-weight: 500;
            color: #2c3e66;
        }

        /* Instruction card with CSS icons */
        .instruction-card {
            background: white;
            border-radius: 24px;
            padding: 20px 26px;
            margin-bottom: 28px;
            box-shadow: 0 6px 14px rgba(0, 0, 0, 0.02), 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid #e2e8f0;
        }

        .instruction-title {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 18px;
            font-weight: 600;
            font-size: 1.2rem;
            color: #0f2b3d;
        }

        .book-icon {
            width: 28px;
            height: 28px;
            background: #eef2ff;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .steps-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 18px;
            margin-bottom: 16px;
        }

        .step-item {
            flex: 1;
            min-width: 170px;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }

        .step-marker {
            width: 28px;
            height: 28px;
            background: #1e3a5f;
            color: white;
            font-weight: bold;
            border-radius: 30px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.85rem;
            flex-shrink: 0;
        }

        .step-text strong {
            display: block;
            font-size: 0.9rem;
        }
        .step-text p {
            font-size: 0.8rem;
            color: #4b5565;
            margin-top: 4px;
        }

        .note-warning {
            background: #fffbeb;
            border-left: 4px solid #e6b02e;
            padding: 12px 16px;
            border-radius: 14px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 12px;
            margin-top: 12px;
        }
        .warning-icon {
            width: 20px;
            height: 20px;
            background: #f59e0b;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='currentColor'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z'%3E%3C/path%3E%3C/svg%3E") no-repeat center;
            mask-size: contain;
            background-color: #b45309;
        }
        .note-warning span:last-child {
            color: #92400e;
        }

        /* Toolbar */
        .toolbar {
            background: white;
            border-radius: 20px;
            padding: 16px 20px;
            margin-bottom: 24px;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 16px;
            justify-content: space-between;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.05);
            border: 1px solid #e9edf2;
        }
        .search-area {
            flex: 2;
            min-width: 220px;
            position: relative;
        }
        .search-area::before {
            content: "";
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            background: #94a3b8;
            mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='currentColor'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'%3E%3C/path%3E%3C/svg%3E") no-repeat center;
            mask-size: contain;
            background-color: #94a3b8;
            pointer-events: none;
        }
        .search-area input {
            width: 100%;
            padding: 10px 16px 10px 36px;
            border-radius: 40px;
            border: 1px solid #cbd5e1;
            background: #fefefe;
            font-size: 0.9rem;
            transition: 0.2s;
        }
        .search-area input:focus {
            outline: none;
            border-color: #1e3a5f;
            box-shadow: 0 0 0 2px rgba(30,58,95,0.2);
        }
        .bulk-panel {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            align-items: center;
            background: #f8fafc;
            padding: 6px 14px;
            border-radius: 48px;
        }
        .bulk-panel select, .bulk-panel input {
            padding: 8px 12px;
            border-radius: 32px;
            border: 1px solid #cbd5e1;
            background: white;
            font-size: 0.85rem;
        }
        button {
            background: #1e3a5f;
            border: none;
            padding: 8px 24px;
            border-radius: 40px;
            font-weight: 500;
            color: white;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            transition: 0.2s;
            font-size: 0.85rem;
            box-shadow: 0 1px 1px rgba(0,0,0,0.05);
        }
        button:hover {
            background: #143049;
            transform: translateY(-1px);
        }
        .save-btn {
            background: #2b6e3c;
        }
        .save-btn:hover {
            background: #1f5730;
        }
        .button-icon {
            width: 16px;
            height: 16px;
            display: inline-block;
        }
        .selected-info {
            font-weight: 500;
            background: #eef2ff;
            padding: 6px 14px;
            border-radius: 32px;
            font-size: 0.85rem;
        }

        /* DIV-based table (CSS Grid) */
        .coins-grid {
            background: white;
            border-radius: 24px;
            border: 1px solid #eef2f6;
            overflow-x: auto;
            box-shadow: 0 8px 20px rgba(0,0,0,0.02);
        }
        .grid-header {
            display: grid;
            grid-template-columns: 48px 90px 140px 130px 1fr 100px 150px;
            background: #f9fbfd;
            border-bottom: 1px solid #e2e8f0;
            padding: 14px 16px;
            font-weight: 600;
            font-size: 0.85rem;
            color: #334155;
            letter-spacing: 0.3px;
        }
        .grid-row {
            display: grid;
            grid-template-columns: 48px 90px 140px 130px 1fr 100px 150px;
            padding: 12px 16px;
            border-bottom: 1px solid #edf2f7;
            align-items: center;
            transition: background 0.1s ease;
        }
        .grid-row:hover {
            background: #fafcff;
        }
        .selected-row {
            background: #e6f0ff !important;
            border-left: 3px solid #1e3a5f;
        }
        .cell-checkbox {
            display: flex;
            justify-content: center;
        }
        .cell-checkbox input {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        .cell-data {
            font-size: 0.9rem;
            color: #1e293b;
            word-break: break-word;
            cursor: pointer;
            padding: 4px 6px;
            border-radius: 10px;
            transition: background 0.1s;
        }
        .cell-data:hover {
            background: #eef2ff;
        }
        .inline-input {
            width: 95%;
            padding: 6px 10px;
            border-radius: 12px;
            border: 1px solid #1e3a5f;
            font-size: 0.85rem;
            background: white;
        }

        /* CSS Notifications */
        .toast-notification {
            position: fixed;
            bottom: 28px;
            right: 28px;
            z-index: 2000;
            min-width: 280px;
            max-width: 380px;
            background: white;
            border-radius: 20px;
            padding: 14px 20px;
            box-shadow: 0 20px 35px -12px rgba(0,0,0,0.2);
            display: flex;
            align-items: center;
            gap: 14px;
            transform: translateX(400px);
            transition: transform 0.25s cubic-bezier(0.2, 0.9, 0.4, 1.1);
            pointer-events: none;
            border-left: 6px solid;
        }
        .toast-notification.show {
            transform: translateX(0);
        }
        .toast-icon {
            width: 24px;
            height: 24px;
            flex-shrink: 0;
        }
        .toast-message {
            font-weight: 500;
            font-size: 0.9rem;
        }
        .toast-success {
            background: #f0fdf4;
            border-left-color: #2b9348;
            color: #14532d;
        }
        .toast-error {
            background: #fef2f2;
            border-left-color: #dc2626;
            color: #991b1b;
        }
        .toast-info {
            background: #eff6ff;
            border-left-color: #2563eb;
        }

        @media (max-width: 1000px) {
            body { padding: 18px; }
            .grid-header, .grid-row {
                grid-template-columns: 48px 80px 120px 110px 1fr 90px 130px;
                gap: 6px;
            }
        }
        @media (max-width: 780px) {
            .grid-header, .grid-row {
                grid-template-columns: 40px 70px 100px 90px 1fr 80px 110px;
                font-size: 0.75rem;
            }
        }
        
        .empty-placeholder {
            text-align: center;
            padding: 48px;
            color: #6c757d;
        }
    </style>
</head>
<body>
<div class="vault-container">
    <div class="header">
        <div class="title-section">
            <div class="vault-icon">
                <svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8" fill="none">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="white"/>
                    <circle cx="12" cy="12" r="3" stroke="white"/>
                </svg>
            </div>
            <h1>Numismatic Vault</h1>
            <div class="badge">unified save · bulk ready</div>
        </div>
    </div>

    <div class="instruction-card">
        <div class="instruction-title">
            <div class="book-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1e3a5f" stroke-width="2">
                    <path d="M4 6h16M4 12h16M4 18h16" stroke="currentColor"/>
                    <rect x="2" y="3" width="20" height="18" rx="2" stroke="currentColor"/>
                </svg>
            </div>
            <span>How to use this tool</span>
        </div>
        <div class="steps-grid">
            <div class="step-item"><div class="step-marker">1</div><div class="step-text"><strong>Search & Select</strong><p>Filter by any field, check boxes for bulk update</p></div></div>
            <div class="step-item"><div class="step-marker">2</div><div class="step-text"><strong>Set Bulk Value</strong><p>Choose field and enter new value for selected rows</p></div></div>
            <div class="step-item"><div class="step-marker">3</div><div class="step-text"><strong>Single Edit</strong><p>Click any cell to edit individually</p></div></div>
            <div class="step-item"><div class="step-marker">4</div><div class="step-text"><strong>Save All Changes</strong><p>Click SAVE button to persist everything to file</p></div></div>
        </div>
        <div class="note-warning">
            <div class="warning-icon"></div>
            <span><strong>Unified workflow:</strong> Edit single cells OR select rows → apply bulk changes → all changes stay in memory. Then click <strong>Save to File</strong> once to persist everything.</span>
        </div>
    </div>

    <div class="toolbar">
        <div class="search-area">
            <input type="text" id="searchInput" placeholder="Search by country, donor, year, note...">
        </div>
        <div class="bulk-panel">
            <select id="bulkField">
                <option value="note">Note</option>
                <option value="donor_name">Donor</option>
                <option value="year">Year</option>
                <option value="country">Country</option>
                <option value="currency_type">Currency Type</option>
                <option value="box">Box</option>
            </select>
            <input id="bulkValue" placeholder="New value for selected rows" style="min-width:140px;">
            <button id="applyBulkInlineBtn" style="background:#2c5282;">
                <svg class="button-icon" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                    <path d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    <path d="M12 12h4v4M16 12l-4 4" />
                </svg>
                Apply to Selected
            </button>
        </div>
        <button id="saveBtn" class="save-btn">
            <svg class="button-icon" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
                <path d="M17 21v-8H7v8M12 3v5"/>
            </svg>
            Save to File (Persist All)
        </button>
        <div class="selected-info" id="selectedCountDisplay">0 selected</div>
    </div>

    <div class="coins-grid">
        <div class="grid-header">
            <div></div>
            <div>Box</div>
            <div>Country</div>
            <div>Type</div>
            <div>Note</div>
            <div>Year</div>
            <div>Donor</div>
        </div>
        <div id="gridBody"></div>
    </div>
</div>

<div id="toastRoot"></div>

<script>
    let masterData = [];
    let selectedSet = new Set();
    let searchTerm = "";

    const gridBody = document.getElementById("gridBody");
    const searchInput = document.getElementById("searchInput");
    const bulkField = document.getElementById("bulkField");
    const bulkValue = document.getElementById("bulkValue");
    const applyBulkInlineBtn = document.getElementById("applyBulkInlineBtn");
    const saveBtn = document.getElementById("saveBtn");
    const selectedCountSpan = document.getElementById("selectedCountDisplay");

    function showNotification(message, type = "success") {
        const toastContainer = document.getElementById("toastRoot");
        const toast = document.createElement("div");
        toast.className = `toast-notification toast-${type === 'success' ? 'success' : (type === 'error' ? 'error' : 'info')}`;
        
        const iconSpan = document.createElement("div");
        iconSpan.className = "toast-icon";
        if (type === "success") {
            iconSpan.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#15803d" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>`;
        } else if (type === "error") {
            iconSpan.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#b91c1c" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v4M12 16h.01"/></svg>`;
        } else {
            iconSpan.innerHTML = `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="#1e40af" stroke-width="2"><path d="M12 8v4M12 16h.01"/><circle cx="12" cy="12" r="10"/></svg>`;
        }
        
        const msgSpan = document.createElement("div");
        msgSpan.className = "toast-message";
        msgSpan.innerText = message;
        
        toast.appendChild(iconSpan);
        toast.appendChild(msgSpan);
        toastContainer.appendChild(toast);
        
        setTimeout(() => toast.classList.add("show"), 10);
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    function escapeHtml(str) {
        if (str === undefined || str === null) return "";
        return String(str).replace(/[&<>]/g, function(m) {
            if (m === '&') return '&amp;';
            if (m === '<') return '&lt;';
            if (m === '>') return '&gt;';
            return m;
        });
    }

    function getFilteredData() {
        if (!searchTerm.trim()) return masterData;
        const term = searchTerm.toLowerCase();
        return masterData.filter(item => {
            return Object.values(item).some(val => 
                String(val ?? "").toLowerCase().includes(term)
            );
        });
    }

    function pruneSelectedSet() {
        const existingIds = new Set(masterData.map(c => c.image));
        for (let id of selectedSet) {
            if (!existingIds.has(id)) selectedSet.delete(id);
        }
    }

    function renderGrid() {
        pruneSelectedSet();
        const filtered = getFilteredData();
        
        if (!filtered.length) {
            gridBody.innerHTML = `<div class="empty-placeholder" style="grid-column:1/-1; text-align:center;">No coins match your search</div>`;
            selectedCountSpan.innerText = `${selectedSet.size} selected`;
            return;
        }
        
        let html = "";
        for (let item of filtered) {
            const id = item.image;
            const isSelected = selectedSet.has(id);
            const rowClass = isSelected ? "grid-row selected-row" : "grid-row";
            
            html += `
                <div class="${rowClass}" data-row-id="${id}">
                    <div class="cell-checkbox"><input type="checkbox" class="row-selector" data-id="${id}" ${isSelected ? "checked" : ""}></div>
                    <div class="cell-data editable-cell" data-id="${id}" data-field="box">${escapeHtml(item.box ?? "") || "—"}</div>
                    <div class="cell-data editable-cell" data-id="${id}" data-field="country">${escapeHtml(item.country ?? "") || "—"}</div>
                    <div class="cell-data editable-cell" data-id="${id}" data-field="currency_type">${escapeHtml(item.currency_type ?? "") || "—"}</div>
                    <div class="cell-data editable-cell" data-id="${id}" data-field="note">${escapeHtml(item.note ?? "") || "—"}</div>
                    <div class="cell-data editable-cell" data-id="${id}" data-field="year">${escapeHtml(item.year ?? "") || "—"}</div>
                    <div class="cell-data editable-cell" data-id="${id}" data-field="donor_name">${escapeHtml(item.donor_name ?? "") || "—"}</div>
                </div>
            `;
        }
        gridBody.innerHTML = html;
        selectedCountSpan.innerText = `${selectedSet.size} selected`;
        
        document.querySelectorAll('.row-selector').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const cid = cb.getAttribute('data-id');
                if (cb.checked) selectedSet.add(cid);
                else selectedSet.delete(cid);
                renderGrid();
            });
        });
        
        attachInlineEditEvents();
    }
    
    function attachInlineEditEvents() {
        document.querySelectorAll('.editable-cell').forEach(cell => {
            cell.removeEventListener('click', inlineEditHandler);
            cell.addEventListener('click', inlineEditHandler);
        });
    }
    
    function inlineEditHandler(e) {
        const cell = e.currentTarget;
        const id = cell.getAttribute('data-id');
        const field = cell.getAttribute('data-field');
        if (!id || !field) return;
        
        const item = masterData.find(i => i.image === id);
        if (!item) return;
        const oldVal = item[field] ?? "";
        
        const input = document.createElement('input');
        input.value = oldVal;
        input.className = "inline-input";
        cell.innerHTML = "";
        cell.appendChild(input);
        input.focus();
        
        const saveEdit = () => {
            const newVal = input.value.trim();
            const targetItem = masterData.find(i => i.image === id);
            if (targetItem) {
                targetItem[field] = newVal;
            }
            renderGrid();
            showNotification(`Updated ${field} → "${newVal || 'empty'}" (click Save to persist)`, "info");
        };
        
        input.addEventListener('blur', saveEdit);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                input.blur();
            }
        });
    }
    
    function applyBulkToSelected() {
        const field = bulkField.value;
        const newValue = bulkValue.value;
        if (selectedSet.size === 0) {
            showNotification("No rows selected. Please select at least one coin.", "error");
            return;
        }
        if (!field) return;
        
        let countUpdated = 0;
        for (let i = 0; i < masterData.length; i++) {
            if (selectedSet.has(masterData[i].image)) {
                masterData[i][field] = newValue;
                countUpdated++;
            }
        }
        showNotification(`Bulk update applied to ${countUpdated} coin(s). Field "${field}" set to "${newValue || '(empty)'}". Click Save to persist.`, "success");
        renderGrid();
    }
    
    async function saveToBackend() {
        try {
            const response = await fetch('/api/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(masterData)
            });
            if (response.ok) {
                const result = await response.json();
                showNotification(`✓ All changes saved! ${result.count || masterData.length} coins written to coins.json`, "success");
            } else {
                const errData = await response.json();
                showNotification(`Save failed: ${errData.error || "server error"}`, "error");
            }
        } catch (err) {
            showNotification("Network error while saving. Make sure Flask server is running.", "error");
        }
    }
    
    async function loadData() {
        try {
            const res = await fetch('/api/coins');
            if (!res.ok) throw new Error("HTTP error");
            const data = await res.json();
            if (Array.isArray(data)) {
                masterData = data;
                selectedSet.clear();
                renderGrid();
                showNotification(`Loaded ${masterData.length} coins from vault.`, "info");
            } else {
                masterData = [];
                renderGrid();
            }
        } catch (err) {
            showNotification("Could not load coins.json. Ensure Flask backend is running.", "error");
            masterData = [];
            renderGrid();
        }
    }
    
    searchInput.addEventListener('input', (e) => {
        searchTerm = e.target.value;
        renderGrid();
    });
    
    applyBulkInlineBtn.addEventListener('click', applyBulkToSelected);
    saveBtn.addEventListener('click', saveToBackend);
    
    bulkValue.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            applyBulkToSelected();
        }
    });
    
    loadData();
</script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/coins')
def get_coins():
    try:
        with open(FILE_NAME, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        print("ERROR loading coins:", e)
        return jsonify([])

@app.route('/api/save', methods=['POST'])
def save_coins():
    try:
        data = request.json
        with open(FILE_NAME, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Saved {len(data)} coins to {FILE_NAME}")
        return jsonify({'status': 'ok', 'count': len(data)})
    except Exception as e:
        print("SAVE ERROR:", e)
        return jsonify({'error': str(e)}), 500

def open_browser():
    """Automatically open browser when server starts"""
    webbrowser.open('http://127.0.0.1:5000')

if __name__ == '__main__':
    # Open browser automatically after a short delay
    threading.Timer(1.5, open_browser).start()
    app.run(debug=True, use_reloader=False, host='127.0.0.1', port=5000)