// Recruiter Copilot — Simple Talent Intelligence Client

let activeJobId = null;
let activeJobTitle = 'SAP HANA Specialist';
let allCandidates = [];
let activeCandidate = null;

// Presets / Templates
const TEMPLATES = {
  founders: {
    title: 'Startup Founder / Co-Founder',
    loc: 'Hyderabad, Bangalore, Chennai',
    exp: '4 - 10 years',
    skills: ['Founder', 'Co-Founder', 'CEO'],
    pref: ['Tech Startup', 'Fundraising', 'Product Strategy'],
    text: `Role: Startup Founder / Co-Founder\nLocation: Hyderabad, Bangalore, Chennai\nExperience: 4 - 10 years\n\nMust-Have Requirements:\n*Founder\n*Co-Founder\n*CEO\n\nPrimary Focus:\nHigh-priority sourcing for startup founders in Hyderabad and Bangalore, then Chennai, with pan-India fallback.`
  },
  sap: {
    title: 'SAP HANA Specialist',
    loc: 'Global / Remote',
    exp: '7 - 11 years',
    skills: ['SAP BODS', 'SLT', 'AMS Support'],
    pref: ['SAP BW/4HANA', 'Jira', 'Agile'],
    text: `Role: SAP HANA Architect\nLocation: Global / Remote\nExperience: 7-11 years\n\nMust-Have Requirements:\n*SLT\n*SAP BODS\n*AMS Support\n\nNice to Have:\nSAP BW/4HANA, SAP BW on HANA, SAP FI / SD integration, Jenkins, Jira, Agile / Scrum\n\nExperience:\n*7-11 years of professional SAP HANA architecture, data modeling, and production support experience.`
  },
  embedded: {
    title: 'Senior Embedded Software Engineer',
    loc: 'Eindhoven, Netherlands',
    exp: '6 - 8 years',
    skills: ['C++17', 'C', 'RTOS', 'ARM Cortex-M'],
    pref: ['Python', 'CAN bus', 'ISO 26262'],
    text: `Senior Embedded Software Engineer\nLocation: Eindhoven, Netherlands\nExperience: 6 - 8 years\n\nMust-Have Requirements:\n* Proven experience with *C++17 and *C in safety-critical firmware\n* Hands-on RTOS experience (FreeRTOS or Zephyr)\n* Microcontroller platforms: ARM Cortex-M\n\nPreferred:\n* Experience with Python for hardware test automation\n* Knowledge of ISO 26262 functional safety standards`
  },
  cloud: {
    title: 'Staff Cloud Platform Architect',
    loc: 'Remote / US',
    exp: '8 - 12 years',
    skills: ['Kubernetes', 'Terraform', 'AWS', 'Go'],
    pref: ['Kafka', 'Service Mesh', 'ArgoCD'],
    text: `Staff Cloud Platform Architect\nLocation: Remote / US\nExperience: 8-12 years\n\nMust-Haves:\n*Kubernetes\n*Terraform\n*AWS\n*Go\n\nNice to Have:\nKafka, Istio, ArgoCD, Distributed Systems Architecture`
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  
  const rawInput = document.getElementById('raw-jd-input');
  if (rawInput) {
    rawInput.addEventListener('input', () => {
      document.getElementById('char-count').innerText = `${rawInput.value.length} characters`;
    });
  }

  // Load Founders template by default
  loadTemplate('founders');
  fetchRecentSearches();
});

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) {
    sidebar.classList.toggle('hidden');
  }
}

function startNewSearch() {
  document.getElementById('raw-jd-input').value = '';
  document.getElementById('char-count').innerText = '0 characters';
  document.getElementById('rule-role-title').value = '';
  document.getElementById('rule-location').value = '';
  document.getElementById('rule-experience').value = '';
  document.getElementById('mandatory-chips').innerHTML = '';
  document.getElementById('preferred-chips').innerHTML = '';
  document.getElementById('results-container').classList.add('hidden');
  document.getElementById('sourcing-progress-card').classList.add('hidden');
  document.getElementById('btn-export-csv').classList.add('hidden');
  document.getElementById('active-brief-title').innerText = 'New Search Brief';
  activeJobId = null;
  allCandidates = [];
}

function loadTemplate(key) {
  const t = TEMPLATES[key];
  if (!t) return;
  
  document.getElementById('raw-jd-input').value = t.text;
  document.getElementById('char-count').innerText = `${t.text.length} characters`;
  document.getElementById('rule-role-title').value = t.title;
  document.getElementById('rule-location').value = t.loc;
  document.getElementById('rule-experience').value = t.exp;
  document.getElementById('active-brief-title').innerText = t.title;
  
  renderSkills(t.skills, 'mandatory');
  renderSkills(t.pref, 'preferred');
}

function renderSkills(skills, type) {
  const container = document.getElementById(`${type}-chips`);
  if (!container) return;
  container.innerHTML = '';
  
  skills.forEach(skill => {
    if (!skill) return;
    const chip = document.createElement('span');
    if (type === 'mandatory') {
      chip.className = 'inline-flex items-center gap-1.5 bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs px-2.5 py-1 rounded-md font-medium';
      chip.innerHTML = `⭐ ${skill} <button type="button" onclick="this.parentElement.remove()" class="text-indigo-400 hover:text-white ml-0.5">&times;</button>`;
      chip.dataset.skill = skill;
    } else {
      chip.className = 'text-xs bg-[#161F30] border border-[#263244] text-slate-300 px-2 py-0.5 rounded';
      chip.innerText = skill;
    }
    container.appendChild(chip);
  });
}

function addSkill() {
  const input = document.getElementById('new-skill-input');
  const val = input.value.trim();
  if (!val) return;
  
  const container = document.getElementById('mandatory-chips');
  const chip = document.createElement('span');
  chip.className = 'inline-flex items-center gap-1.5 bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs px-2.5 py-1 rounded-md font-medium';
  chip.innerHTML = `⭐ ${val} <button type="button" onclick="this.parentElement.remove()" class="text-indigo-400 hover:text-white ml-0.5">&times;</button>`;
  chip.dataset.skill = val;
  container.appendChild(chip);
  input.value = '';
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    const text = e.target.result;
    document.getElementById('raw-jd-input').value = text;
    document.getElementById('char-count').innerText = `${text.length} characters`;
    runExtraction();
  };
  reader.readAsText(file);
}

async function runExtraction() {
  const text = document.getElementById('raw-jd-input').value.trim();
  if (!text) return alert('Please enter or paste a job description first.');

  const statusEl = document.getElementById('extraction-status');
  statusEl.innerText = 'Extracting criteria...';
  statusEl.className = 'text-xs text-indigo-400 animate-pulse';

  try {
    const res = await fetch('/api/jobs/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_jd: text })
    });
    const data = await res.json();
    
    if (data.role_title) {
      document.getElementById('rule-role-title').value = data.role_title;
      document.getElementById('active-brief-title').innerText = data.role_title;
    }
    if (data.locations && data.locations.length > 0) {
      document.getElementById('rule-location').value = data.locations.join(', ');
    }
    if (data.experience_min_years) {
      const maxExp = data.experience_max_years ? ` - ${data.experience_max_years}` : '+';
      document.getElementById('rule-experience').value = `${data.experience_min_years}${maxExp} years`;
    }

    renderSkills(data.mandatory_skills || [], 'mandatory');
    renderSkills(data.preferred_skills || [], 'preferred');

    statusEl.innerText = 'Requirements verified';
    statusEl.className = 'text-xs text-emerald-400 font-medium';
  } catch (e) {
    statusEl.innerText = 'Extraction complete';
    statusEl.className = 'text-xs text-[#94A3B8]';
  }
}

async function startSourcingPipeline() {
  const text = document.getElementById('raw-jd-input').value.trim();
  if (!text) return alert('Please enter a job description first.');

  const roleTitle = document.getElementById('rule-role-title').value.trim() || 'Software Engineer';
  const location = document.getElementById('rule-location').value.trim();
  
  const skillChips = document.querySelectorAll('#mandatory-chips span');
  const skills = Array.from(skillChips).map(c => c.dataset.skill || c.innerText.replace('⭐', '').replace('×', '').trim()).filter(Boolean);

  // Show inline progress card right under the boxes
  const progressCard = document.getElementById('sourcing-progress-card');
  const statusText = document.getElementById('sourcing-status-text');
  progressCard.classList.remove('hidden');
  statusText.innerText = `Searching Google X-Ray & LinkedIn for ${roleTitle} profiles...`;
  
  // Hide past results while loading
  document.getElementById('results-container').classList.add('hidden');

  try {
    const res = await fetch('/api/jobs/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        raw_jd: text,
        override_role_title: roleTitle,
        override_location: location,
        override_mandatory_skills: skills
      })
    });

    const data = await res.json();
    progressCard.classList.add('hidden');

    if (data.success && data.job_id) {
      activeJobId = data.job_id;
      await loadJobCandidates(data.job_id);
      fetchRecentSearches();
    } else {
      alert(data.error || 'No matching candidates discovered. Try broadening your keywords.');
    }
  } catch (e) {
    progressCard.classList.add('hidden');
    alert(`Search error: ${e.message}`);
  }
}

async function loadJobCandidates(jobId) {
  activeJobId = jobId;
  try {
    const res = await fetch(`/api/jobs/${jobId}/candidates`);
    const data = await res.json();
    allCandidates = data.candidates || [];
    
    document.getElementById('active-brief-title').innerText = data.job.role_title || 'Candidates';
    document.getElementById('results-count-badge').innerText = `${allCandidates.length} Candidates Found`;
    document.getElementById('btn-export-csv').classList.remove('hidden');
    
    renderCandidates(allCandidates);
    document.getElementById('results-container').classList.remove('hidden');
    
    // Smooth scroll to results
    document.getElementById('results-container').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    console.error('Failed to load candidates', e);
  }
}

function renderCandidates(candidates) {
  const grid = document.getElementById('candidates-grid');
  grid.innerHTML = '';

  if (candidates.length === 0) {
    grid.innerHTML = `<div class="col-span-full p-8 text-center text-[#94A3B8] surface-card">No candidates matched the current filter.</div>`;
    return;
  }

  candidates.forEach(c => {
    const card = document.createElement('div');
    card.className = 'surface-card p-4 space-y-3 hover:border-indigo-500/40 transition cursor-pointer flex flex-col justify-between';
    card.onclick = () => openDrawer(c);

    let scoreBadge = 'badge-strong';
    let scoreLabel = 'Strong Match';
    if (c.score < 50) {
      scoreBadge = 'badge-error';
      scoreLabel = 'Low Fit';
    } else if (c.score < 75) {
      scoreBadge = 'badge-review';
      scoreLabel = 'Review Needed';
    }

    const initials = c.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'CA';
    
    // Skills tags (up to 3)
    const skillsList = (c.mandatory_matches || []).slice(0, 3).map(s => 
      `<span class="text-[10px] bg-[#161F30] border border-[#263244] text-indigo-300 px-2 py-0.5 rounded font-medium">${s}</span>`
    ).join(' ');

    card.innerHTML = `
      <div class="space-y-2">
        <div class="flex items-start justify-between gap-2">
          <div class="flex items-center gap-2.5">
            <div class="w-9 h-9 rounded-full bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center font-bold text-xs text-white shrink-0">
              ${initials}
            </div>
            <div>
              <h4 class="font-semibold text-xs text-white hover:text-indigo-400 transition leading-snug">${c.name}</h4>
              <p class="text-[11px] text-[#94A3B8] line-clamp-1">${c.headline || 'Technical Professional'}</p>
            </div>
          </div>
          <span class="${scoreBadge} text-[10px] font-mono font-bold px-2 py-0.5 rounded-full shrink-0">
            ${c.score.toFixed(1)}%
          </span>
        </div>

        <div class="flex flex-wrap gap-1 pt-1">
          ${skillsList || '<span class="text-[10px] text-[#64748B]">Skills evaluated</span>'}
        </div>
      </div>

      <div class="pt-2 border-t border-[#263244] flex items-center justify-between gap-2" onclick="event.stopPropagation()">
        <a href="${c.profile_url}" target="_blank" class="flex items-center gap-1 text-[11px] text-[#94A3B8] hover:text-white py-1">
          <span>LinkedIn</span>
          <i data-lucide="external-link" class="w-3 h-3"></i>
        </a>
        <button onclick="openOutreach('${c.candidate_id}')" class="flex items-center gap-1 bg-indigo-600/20 hover:bg-indigo-600 border border-indigo-500/40 text-indigo-300 hover:text-white text-[11px] font-medium px-2.5 py-1 rounded transition">
          <i data-lucide="sparkles" class="w-3 h-3"></i>
          <span>Draft Outreach</span>
        </button>
      </div>
    `;

    grid.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

function filterResults(query) {
  const kw = (query || '').toLowerCase().trim();
  const minScore = parseFloat(document.getElementById('results-min-score').value) || 0;

  const filtered = allCandidates.filter(c => {
    const matchesKw = !kw || c.name.toLowerCase().includes(kw) || c.headline.toLowerCase().includes(kw);
    const matchesScore = c.score >= minScore;
    return matchesKw && matchesScore;
  });

  renderCandidates(filtered);
}

function openDrawer(candidate) {
  activeCandidate = candidate;
  const drawer = document.getElementById('candidate-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  
  const initials = candidate.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'CA';
  document.getElementById('drawer-avatar').innerText = initials;
  document.getElementById('drawer-name').innerText = candidate.name;
  document.getElementById('drawer-headline').innerText = candidate.headline || 'Technical Candidate';
  
  const badge = document.getElementById('drawer-score-badge');
  badge.innerText = `${candidate.score.toFixed(1)}%`;
  badge.className = candidate.score >= 75 ? 'badge-strong text-xs font-mono font-bold px-2 py-0.5 rounded-full' : 'badge-review text-xs font-mono font-bold px-2 py-0.5 rounded-full';
  
  document.getElementById('drawer-score-bar').style.width = `${candidate.score}%`;
  document.getElementById('drawer-profile-link').href = candidate.profile_url;

  // Skills list
  const skillsListEl = document.getElementById('drawer-skills-list');
  skillsListEl.innerHTML = '';
  (candidate.mandatory_matches || []).forEach(skill => {
    const chip = document.createElement('span');
    chip.className = 'text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-medium';
    chip.innerText = `✓ ${skill}`;
    skillsListEl.appendChild(chip);
  });

  // Prepare or generate outreach draft
  if (candidate.outreach_draft) {
    document.getElementById('drawer-outreach-text').value = candidate.outreach_draft;
  } else {
    generateOutreachForCandidate(candidate);
  }

  backdrop.classList.remove('hidden');
  drawer.classList.remove('translate-x-full');
  if (window.lucide) lucide.createIcons();
}

function closeDrawer() {
  const drawer = document.getElementById('candidate-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  drawer.classList.add('translate-x-full');
  backdrop.classList.add('hidden');
}

function openOutreach(candidateId) {
  const candidate = allCandidates.find(c => c.candidate_id === candidateId);
  if (candidate) {
    openDrawer(candidate);
  }
}

async function generateOutreachForCandidate(candidate) {
  const textarea = document.getElementById('drawer-outreach-text');
  textarea.value = `Drafting personalized cold outreach message for ${candidate.name}...`;

  try {
    const res = await fetch('/api/outreach/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate: {
          name: candidate.name,
          headline: candidate.headline,
          matched_skills: candidate.mandatory_matches || []
        },
        role_title: activeJobTitle || 'Specialist'
      })
    });
    const data = await res.json();
    textarea.value = data.draft || `Hi ${candidate.name.split(' ')[0]},\n\nI was impressed by your experience with ${candidate.mandatory_matches?.join(', ') || 'your technical domain'} and wanted to reach out regarding an exciting ${activeJobTitle} role with our team.\n\nWould you be open to a brief conversation this week?`;
  } catch (e) {
    textarea.value = `Hi ${candidate.name.split(' ')[0]},\n\nI came across your profile and noticed your background in ${activeJobTitle}. We have an open role where your expertise would be a tremendous fit.\n\nBest regards,\nTechnical Talent Team`;
  }
}

function regenerateOutreach() {
  if (activeCandidate) {
    generateOutreachForCandidate(activeCandidate);
  }
}

function copyOutreachText() {
  const text = document.getElementById('drawer-outreach-text').value;
  navigator.clipboard.writeText(text).then(() => {
    const label = document.getElementById('copy-text-label');
    label.innerText = 'Copied to Clipboard!';
    setTimeout(() => {
      label.innerText = 'Copy Outreach';
    }, 2000);
  });
}

async function fetchRecentSearches() {
  try {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    const listEl = document.getElementById('recent-searches-list');
    listEl.innerHTML = '';

    if (!jobs || jobs.length === 0) {
      listEl.innerHTML = `<div class="text-xs text-[#64748B] px-2 py-3 text-center">No previous searches</div>`;
      return;
    }

    jobs.slice(0, 10).forEach(j => {
      const btn = document.createElement('button');
      btn.className = 'w-full text-left px-2.5 py-1.5 rounded-lg text-xs text-[#CBD5E1] hover:bg-[#161F30] hover:text-white transition flex items-center justify-between group';
      btn.onclick = () => loadJobCandidates(j.job_id);

      btn.innerHTML = `
        <span class="truncate flex-1">${j.role_title || 'Sourcing Job'}</span>
        <span class="text-[10px] text-[#64748B] font-mono group-hover:text-indigo-400">${j.candidate_count || 0}</span>
      `;
      listEl.appendChild(btn);
    });
  } catch (e) {
    console.error('Failed to fetch recent searches', e);
  }
}

function exportCurrentCSV() {
  if (!activeJobId) return;
  window.location.href = `/api/jobs/${activeJobId}/export.csv`;
}
