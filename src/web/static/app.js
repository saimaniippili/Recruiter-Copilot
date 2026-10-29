// Recruiter Copilot — Minimalist Talent Sourcing Client

let activeJobId = null;
let activeJobTitle = 'SAP HANA Specialist';
let allCandidates = [];
let activeCandidate = null;

const TEMPLATES = {
  sap: {
    title: 'SAP HANA Cloud Consultant',
    loc: 'Eindhoven, Netherlands',
    exp: '7 - 11 years',
    skills: ['SAP HANA Cloud', 'SLT', 'SAP BODS', 'Native SAP HANA Modeling'],
    prompt: `Job Title: SAP HANA Cloud Consultant\nLocation: Eindhoven, Netherlands\nExperience: 7-11 years\n\nMandatory Requirements:\n*SAP HANA Cloud\n*Native SAP HANA Modeling\n*Calculation Views\n*CDS Views\n*SQLScript\n*PlanViz\n*SLT\n*SAP BODS\n*AMS Support`
  },
  embedded: {
    title: 'Senior Embedded Software Engineer',
    loc: 'Netherlands / Europe',
    exp: '6 - 8 years',
    skills: ['C++17', 'C', 'RTOS', 'ARM Cortex-M'],
    prompt: 'Senior Embedded Software Engineer with C++17, RTOS, and ARM Cortex-M in Netherlands or Europe'
  },
  cloud: {
    title: 'Staff Cloud Platform Architect',
    loc: 'US / Remote',
    exp: '8 - 12 years',
    skills: ['Kubernetes', 'Terraform', 'AWS', 'Go'],
    prompt: 'Staff Cloud Platform Architect with Kubernetes, Terraform, AWS, and Go, Remote'
  }
};

document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  
  const rawInput = document.getElementById('raw-jd-input');
  if (rawInput) {
    rawInput.addEventListener('input', () => {
      // If the advanced panel is closed, clear stale overrides so the AI extracts location directly from pasted text
      const panel = document.getElementById('advanced-options-panel');
      if (panel && panel.classList.contains('hidden')) {
        document.getElementById('rule-role-title').value = '';
        document.getElementById('rule-location').value = '';
        document.getElementById('rule-experience').value = '';
        document.getElementById('mandatory-chips').innerHTML = '';
      }
    });
  }

  // Load SAP template by default
  loadTemplate('sap');
  fetchRecentSearches();
});

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('hidden');
}

function toggleAdvancedOptions() {
  const panel = document.getElementById('advanced-options-panel');
  if (panel) {
    panel.classList.toggle('hidden');
    const btn = document.getElementById('btn-toggle-advanced');
    if (panel.classList.contains('hidden')) {
      btn.classList.remove('text-indigo-400');
    } else {
      btn.classList.add('text-indigo-400');
    }
  }
}

function startNewSearch() {
  document.getElementById('raw-jd-input').value = '';
  document.getElementById('rule-role-title').value = '';
  document.getElementById('rule-location').value = '';
  document.getElementById('rule-experience').value = '';
  document.getElementById('mandatory-chips').innerHTML = '';
  document.getElementById('results-container').classList.add('hidden');
  document.getElementById('sourcing-progress-card').classList.add('hidden');
  document.getElementById('btn-export-csv').classList.add('hidden');
  document.getElementById('active-brief-title').innerText = 'Ready to source';
  activeJobId = null;
  allCandidates = [];
}

function loadTemplate(key) {
  const t = TEMPLATES[key];
  if (!t) return;
  
  document.getElementById('raw-jd-input').value = t.prompt;
  document.getElementById('rule-role-title').value = t.title;
  document.getElementById('rule-location').value = t.loc;
  document.getElementById('rule-experience').value = t.exp;
  document.getElementById('active-brief-title').innerText = t.title;
  
  renderSkills(t.skills);
}

function renderSkills(skills) {
  const container = document.getElementById('mandatory-chips');
  if (!container) return;
  container.innerHTML = '';
  
  skills.forEach(skill => {
    if (!skill) return;
    const chip = document.createElement('span');
    chip.className = 'inline-flex items-center gap-1.5 bg-[#161F30] border border-[#1F2937] text-indigo-300 text-xs px-2.5 py-1 rounded-md';
    chip.innerHTML = `${skill} <button type="button" onclick="this.parentElement.remove()" class="text-[#64748B] hover:text-white">&times;</button>`;
    chip.dataset.skill = skill;
    container.appendChild(chip);
  });
}

function addSkill() {
  const input = document.getElementById('new-skill-input');
  const val = input.value.trim();
  if (!val) return;
  
  const container = document.getElementById('mandatory-chips');
  const chip = document.createElement('span');
  chip.className = 'inline-flex items-center gap-1.5 bg-[#161F30] border border-[#1F2937] text-indigo-300 text-xs px-2.5 py-1 rounded-md';
  chip.innerHTML = `${val} <button type="button" onclick="this.parentElement.remove()" class="text-[#64748B] hover:text-white">&times;</button>`;
  chip.dataset.skill = val;
  container.appendChild(chip);
  input.value = '';
}

async function startSourcingPipeline() {
  const text = document.getElementById('raw-jd-input').value.trim();
  if (!text) return alert('Please describe the role or candidate requirements first.');

  // Only pass explicit overrides if the advanced options panel is currently open
  const advancedOpen = !document.getElementById('advanced-options-panel').classList.contains('hidden');
  const roleTitle = advancedOpen ? document.getElementById('rule-role-title').value.trim() : null;
  const location = advancedOpen ? document.getElementById('rule-location').value.trim() : null;
  
  let skills = undefined;
  if (advancedOpen) {
    const skillChips = document.querySelectorAll('#mandatory-chips span');
    const extractedSkills = Array.from(skillChips).map(c => c.dataset.skill || c.innerText.replace('×', '').trim()).filter(Boolean);
    if (extractedSkills.length > 0) skills = extractedSkills;
  }

  const progressCard = document.getElementById('sourcing-progress-card');
  const statusText = document.getElementById('sourcing-status-text');
  progressCard.classList.remove('hidden');
  statusText.innerText = 'Searching verified LinkedIn profiles and technical platforms...';
  
  document.getElementById('results-container').classList.add('hidden');

  try {
    const res = await fetch('/api/jobs/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        raw_jd: text,
        override_role_title: roleTitle || undefined,
        override_location: location || undefined,
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
    document.getElementById('results-count-badge').innerText = `${allCandidates.length} Found`;
    document.getElementById('btn-export-csv').classList.remove('hidden');
    
    renderCandidates(allCandidates);
    document.getElementById('results-container').classList.remove('hidden');
    
    document.getElementById('results-container').scrollIntoView({ behavior: 'smooth' });
  } catch (e) {
    console.error('Failed to load candidates', e);
  }
}

function renderCandidates(candidates) {
  const list = document.getElementById('candidates-grid');
  list.innerHTML = '';

  if (candidates.length === 0) {
    list.innerHTML = `<div class="p-8 text-center text-[#94A3B8] surface-card border border-[#1F2937]">No candidate profiles matched the filter.</div>`;
    return;
  }

  candidates.forEach(c => {
    const item = document.createElement('div');
    item.className = 'surface-card p-4 border border-[#1F2937] hover:border-indigo-500/40 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer';
    item.onclick = () => openDrawer(c);

    let scoreBadge = 'badge-strong';
    if (c.score < 50) scoreBadge = 'badge-error';
    else if (c.score < 75) scoreBadge = 'badge-review';

    const initials = c.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'CA';
    
    // Skills tags
    const skillsList = (c.mandatory_matches || []).slice(0, 3).map(s => 
      `<span class="text-[10px] bg-[#161F30] border border-[#1F2937] text-indigo-300 px-2 py-0.5 rounded font-mono">${s}</span>`
    ).join(' ');

    item.innerHTML = `
      <div class="flex items-center gap-3.5 min-w-0">
        <div class="w-9 h-9 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-xs text-indigo-300 shrink-0">
          ${initials}
        </div>
        <div class="min-w-0">
          <div class="flex items-center gap-2">
            <h4 class="font-semibold text-xs text-white hover:text-indigo-400 transition truncate">${c.name}</h4>
            <span class="${scoreBadge} text-[10px] font-mono font-bold px-1.5 py-0.2 rounded shrink-0">
              ${c.score.toFixed(0)}%
            </span>
          </div>
          <p class="text-[11px] text-[#94A3B8] truncate max-w-md">${c.headline || 'Technical Professional'}</p>
          <div class="flex flex-wrap gap-1 mt-1">
            ${skillsList || '<span class="text-[10px] text-[#64748B]">Skills evaluated</span>'}
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0 self-end sm:self-center" onclick="event.stopPropagation()">
        <a href="${c.profile_url}" target="_blank" class="flex items-center gap-1 bg-[#161F30] hover:bg-[#1E293B] border border-[#1F2937] text-[#CBD5E1] text-[11px] px-2.5 py-1 rounded transition">
          <span>LinkedIn</span>
          <i data-lucide="external-link" class="w-3 h-3 text-[#94A3B8]"></i>
        </a>
        <button onclick="openOutreach('${c.candidate_id}')" class="flex items-center gap-1 bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] font-medium px-3 py-1 rounded transition">
          <i data-lucide="sparkles" class="w-3 h-3"></i>
          <span>Outreach</span>
        </button>
      </div>
    `;

    list.appendChild(item);
  });

  if (window.lucide) lucide.createIcons();
}

function filterResults(query) {
  const kw = (query || '').toLowerCase().trim();

  const filtered = allCandidates.filter(c => {
    const matchesKw = !kw || c.name.toLowerCase().includes(kw) || (c.headline && c.headline.toLowerCase().includes(kw));
    return matchesKw;
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
  badge.innerText = `${candidate.score.toFixed(0)}% Fit`;
  badge.className = candidate.score >= 75 ? 'badge-strong text-xs font-mono font-bold px-2 py-0.5 rounded-full' : 'badge-review text-xs font-mono font-bold px-2 py-0.5 rounded-full';
  
  document.getElementById('drawer-profile-link').href = candidate.profile_url;

  const skillsListEl = document.getElementById('drawer-skills-list');
  skillsListEl.innerHTML = '';
  (candidate.mandatory_matches || []).forEach(skill => {
    const chip = document.createElement('span');
    chip.className = 'text-[11px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded';
    chip.innerText = `✓ ${skill}`;
    skillsListEl.appendChild(chip);
  });

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
  if (candidate) openDrawer(candidate);
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
    textarea.value = data.draft || `Hi ${candidate.name.split(' ')[0]},\n\nI noticed your strong background in ${candidate.mandatory_matches?.join(', ') || 'your technical domain'} and wanted to connect regarding a ${activeJobTitle} role with our team.\n\nWould you be open to a brief chat this week?`;
  } catch (e) {
    textarea.value = `Hi ${candidate.name.split(' ')[0]},\n\nI came across your profile and noticed your background in ${activeJobTitle}. We have an open role where your expertise would be a tremendous fit.\n\nBest regards,\nTechnical Talent Team`;
  }
}

function regenerateOutreach() {
  if (activeCandidate) generateOutreachForCandidate(activeCandidate);
}

function copyOutreachText() {
  const text = document.getElementById('drawer-outreach-text').value;
  navigator.clipboard.writeText(text).then(() => {
    const label = document.getElementById('copy-text-label');
    label.innerText = 'Copied!';
    setTimeout(() => {
      label.innerText = 'Copy Message';
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
      listEl.innerHTML = `<div class="text-xs text-[#64748B] px-2 py-3 text-center">No recent searches</div>`;
      return;
    }

    jobs.slice(0, 10).forEach(j => {
      const btn = document.createElement('button');
      btn.className = 'w-full text-left px-2 py-1.5 rounded-md text-xs text-[#CBD5E1] hover:bg-[#161F30] hover:text-white transition flex items-center justify-between group';
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
