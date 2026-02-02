/**
 * SupportIQ - Query Resolution UI
 * Frontend JavaScript for API integration
 */

const API_BASE = '/api/v1';

// DOM Elements
const queryForm = document.getElementById('queryForm');
const submitBtn = document.getElementById('submitBtn');
const resultsContainer = document.getElementById('resultsContainer');

// Analysis Elements
const sentimentEmoji = document.getElementById('sentimentEmoji');
const sentimentLabel = document.getElementById('sentimentLabel');
const confidenceBar = document.getElementById('confidenceBar');
const confidenceText = document.getElementById('confidenceText');
const urgencyScore = document.getElementById('urgencyScore');
const urgencyLevel = document.getElementById('urgencyLevel');
const urgencyExplanation = document.getElementById('urgencyExplanation');
const tierBadge = document.getElementById('tierBadge');
const tierDesc = document.getElementById('tierDesc');
const ticketId = document.getElementById('ticketId');
const ticketStatus = document.getElementById('ticketStatus');
const solutionCount = document.getElementById('solutionCount');
const solutionsList = document.getElementById('solutionsList');
const noSolutions = document.getElementById('noSolutions');

// Sentiment emoji mapping
const sentimentEmojis = {
    'POSITIVE': '😊',
    'NEGATIVE': '😟',
    'NEUTRAL': '😐',
    'positive': '😊',
    'negative': '😟',
    'neutral': '😐'
};

// Tier descriptions
const tierDescriptions = {
    'L1': 'Self-Service / FAQ',
    'L2': 'Technical Support',
    'L3': 'Expert / Specialist'
};

// Tier icons
const tierIcons = {
    'L1': '👤',
    'L2': '👨‍💻',
    'L3': '🧑‍🔬'
};

// Form submission handler
queryForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = new FormData(queryForm);
    const data = {
        title: formData.get('title'),
        description: formData.get('description'),
        user_email: formData.get('email') || null,
        category: formData.get('category') || null
    };

    // Validate
    if (!data.title || data.title.length < 5) {
        showError('Title must be at least 5 characters');
        return;
    }
    if (!data.description || data.description.length < 10) {
        showError('Description must be at least 10 characters');
        return;
    }

    // Show loading state
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    try {
        // Create ticket via API
        const response = await fetch(`${API_BASE}/tickets`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to create ticket');
        }

        const result = await response.json();
        displayResults(result);

    } catch (error) {
        console.error('Error:', error);
        showError(error.message || 'An error occurred. Please try again.');
    } finally {
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
});

// Display results
function displayResults(result) {
    // Show results container
    resultsContainer.classList.remove('hidden');

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Update sentiment analysis
    const sentiment = result.sentiment_analysis;
    const label = sentiment.label.toUpperCase();
    sentimentEmoji.textContent = sentimentEmojis[label] || '😐';
    sentimentLabel.textContent = capitalize(sentiment.label);

    const confidence = Math.round(sentiment.confidence * 100);
    confidenceBar.style.width = `${confidence}%`;
    confidenceText.textContent = `${confidence}% confidence`;

    // Update urgency
    const urgency = result.urgency_analysis;
    animateNumber(urgencyScore, 0, urgency.score, 600);
    urgencyLevel.textContent = urgency.level.toUpperCase();
    urgencyLevel.className = `urgency-badge ${urgency.level.toLowerCase()}`;
    urgencyExplanation.textContent = urgency.explanation || '';

    // Update urgency score color
    urgencyScore.style.color = getUrgencyColor(urgency.score);

    // Update tier
    const tier = urgency.assigned_tier;
    tierBadge.className = `tier-badge ${tier}`;
    tierBadge.querySelector('.tier-icon').textContent = tierIcons[tier] || '👤';
    tierBadge.querySelector('.tier-name').textContent = tier;
    tierDesc.textContent = tierDescriptions[tier] || 'Support Tier';

    // Update ticket info
    ticketId.textContent = result.ticket.id;
    ticketStatus.textContent = result.ticket.status.toUpperCase();
    ticketStatus.className = `ticket-status ${result.ticket.status}`;

    // Update solutions
    displaySolutions(result.suggested_solutions);
}

// Display solutions
function displaySolutions(solutions) {
    solutionsList.innerHTML = '';

    if (!solutions || solutions.length === 0) {
        noSolutions.classList.remove('hidden');
        solutionCount.textContent = '0 found';
        return;
    }

    noSolutions.classList.add('hidden');
    solutionCount.textContent = `${solutions.length} found`;

    solutions.forEach((solution, index) => {
        const card = createSolutionCard(solution, index + 1);
        solutionsList.appendChild(card);
    });
}

// Create solution card
function createSolutionCard(solution, rank) {
    const card = document.createElement('div');
    card.className = 'solution-card';

    const score = Math.round((solution.hybrid_score || solution.semantic_score || 0) * 100);
    const keywords = solution.keywords || [];

    card.innerHTML = `
        <div class="solution-header">
            <div class="solution-title-group">
                <span class="solution-rank">${rank}</span>
                <span class="solution-title">${escapeHtml(solution.title)}</span>
            </div>
            <div class="solution-meta">
                <span class="solution-tier ${solution.tier}">${solution.tier}</span>
                <div class="solution-score">
                    <span>${score}%</span>
                    <div class="solution-score-bar">
                        <div class="solution-score-fill" style="width: ${score}%"></div>
                    </div>
                </div>
                <span class="solution-expand">▼</span>
            </div>
        </div>
        <div class="solution-content">
            <p class="solution-text">${escapeHtml(solution.content)}</p>
            ${keywords.length > 0 ? `
                <div class="solution-keywords">
                    ${keywords.map(kw => `<span class="keyword-tag">${escapeHtml(kw)}</span>`).join('')}
                </div>
            ` : ''}
            <div class="solution-actions">
                <button class="solution-btn primary" onclick="applySolution(${solution.id}, '${escapeHtml(solution.title)}')">
                    ✓ Apply Solution
                </button>
                <button class="solution-btn" onclick="copySolution('${escapeHtml(solution.content.replace(/'/g, "\\'"))}')">
                    📋 Copy
                </button>
            </div>
        </div>
    `;

    // Toggle expand on header click
    const header = card.querySelector('.solution-header');
    header.addEventListener('click', () => {
        card.classList.toggle('expanded');
    });

    // Auto-expand first result
    if (rank === 1) {
        card.classList.add('expanded');
    }

    return card;
}

// Apply solution (mark as helpful)
function applySolution(solutionId, title) {
    showSuccess(`Solution "${title}" has been applied to your ticket!`);
}

// Copy solution to clipboard
async function copySolution(content) {
    try {
        await navigator.clipboard.writeText(content);
        showSuccess('Solution copied to clipboard!');
    } catch (err) {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = content;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showSuccess('Solution copied to clipboard!');
    }
}

// Utility functions
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getUrgencyColor(score) {
    if (score <= 3) return '#10b981';
    if (score <= 5) return '#f59e0b';
    if (score <= 7) return '#f97316';
    return '#ef4444';
}

function animateNumber(element, start, end, duration) {
    const startTime = performance.now();
    const diff = end - start;

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(start + diff * easeOut);

        element.textContent = current;

        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }

    requestAnimationFrame(update);
}

// Toast notifications
function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showToast(message, type = 'info') {
    // Remove existing toasts
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-icon">${type === 'error' ? '⚠️' : type === 'success' ? '✅' : 'ℹ️'}</span>
        <span class="toast-message">${message}</span>
    `;

    // Add toast styles if not present
    if (!document.querySelector('#toast-styles')) {
        const styles = document.createElement('style');
        styles.id = 'toast-styles';
        styles.textContent = `
            .toast {
                position: fixed;
                bottom: 2rem;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 1rem 1.5rem;
                background: rgba(20, 20, 30, 0.95);
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
                z-index: 1000;
                animation: toastIn 0.3s ease-out;
            }
            .toast-error { border-color: rgba(239, 68, 68, 0.5); }
            .toast-success { border-color: rgba(16, 185, 129, 0.5); }
            .toast-icon { font-size: 1.25rem; }
            .toast-message { color: #fff; font-size: 0.9375rem; }
            @keyframes toastIn {
                from { opacity: 0; transform: translate(-50%, 20px); }
                to { opacity: 1; transform: translate(-50%, 0); }
            }
            @keyframes toastOut {
                from { opacity: 1; transform: translate(-50%, 0); }
                to { opacity: 0; transform: translate(-50%, -20px); }
            }
        `;
        document.head.appendChild(styles);
    }

    document.body.appendChild(toast);

    // Remove after delay
    setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease-out forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 SupportIQ UI initialized');
});
