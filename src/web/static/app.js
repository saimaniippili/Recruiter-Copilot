// Recruiter Copilot — Minimalist Talent Sourcing & Geographic Verification Client

let activeJobId = null;
let activeJobTitle = 'SAP HANA Cloud Consultant';
let allCandidates = [];
let activeCandidate = null;

const TEMPLATES = {
  sap: {
    title: 'SAP HANA Cloud Consultant',
    loc: 'Eindhoven, Netherlands',
    exp: '7 - 11 years',
    skills: ['SAP HANA Modeling', 'Calculation Views', 'SQLScript', 'CDS Views', 'SLT', 'SAP BODS'],
    prompt: `Job Title: SAP HANA Cloud Consultant\nLocation: Eindhoven, Netherlands\nExperience: 7-11 years\n\nMandatory Requirements:\n*SAP HANA Modeling\n*Calculation Views\n*CDS Views\n*SQLScript\n*SLT\n*SAP BODS\n*AMS Support`
  },
  embedded: {
    title: 'Senior Embedded Software Engineer',
    loc: 'Eindhoven, Netherlands',
    exp: '6 - 8 years',
    skills: ['C++17', 'C', 'RTOS', 'ARM Cortex-M'],
    prompt: 'Senior Embedded Software Engineer with C++17, RTOS, and ARM Cortex-M in Eindhoven, Netherlands'
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
      const panel = document.getElementById('advanced-options-panel');
      if (panel && panel.classList.contains('hidden')) {
        document.getElementById('rule-role-title').value = '';
        document.getElementById('rule-location').value = '';
        document.getElementById('rule-experience').value = '';
        document.getElementById('mandatory-chips').innerHTML = '';
      }
    });
  }

  // Load SAP HANA Eindhoven template by default
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
      btn.classList.remove('text-orange-400');
    } else {
      btn.classList.add('text-orange-400');
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
  (skills || []).forEach(s => {
    const chip = document.createElement('span');
    chip.className = 'inline-flex items-center gap-1 bg-[#18181B] border border-[#27272A] text-orange-400 text-[11px] px-2 py-0.5 rounded-full';
    chip.innerHTML = `<span>⭐ ${s}</span><button onclick="this.parentElement.remove()" class="text-[#71717A] hover:text-white ml-0.5">×</button>`;
    container.appendChild(chip);
  });
}

function addSkill() {
  const input = document.getElementById('new-skill-input');
  const val = input.value.trim();
  if (!val) return;
  
  const container = document.getElementById('mandatory-chips');
  const chip = document.createElement('span');
  chip.className = 'inline-flex items-center gap-1 bg-[#18181B] border border-[#27272A] text-orange-400 text-[11px] px-2 py-0.5 rounded-full';
  chip.innerHTML = `<span>⭐ ${val}</span><button onclick="this.parentElement.remove()" class="text-[#71717A] hover:text-white ml-0.5">×</button>`;
  container.appendChild(chip);
  input.value = '';
}

async function startSourcingPipeline() {
  const rawJd = document.getElementById('raw-jd-input').value.trim();
  if (!rawJd) {
    alert('Please enter or paste a job brief first.');
    return;
  }

  const btn = document.getElementById('btn-start-sourcing');
  btn.disabled = true;
  btn.innerHTML = `<div class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div><span>Searching...</span>`;

  const progressCard = document.getElementById('sourcing-progress-card');
  progressCard.classList.remove('hidden');

  let overrideTitle = null;
  let overrideLoc = null;
  let overrideSkills = [];

  const panel = document.getElementById('advanced-options-panel');
  if (panel && !panel.classList.contains('hidden')) {
    overrideTitle = document.getElementById('rule-role-title').value.trim() || null;
    overrideLoc = document.getElementById('rule-location').value.trim() || null;
    const chips = document.querySelectorAll('#mandatory-chips span span');
    overrideSkills = Array.from(chips).map(c => c.innerText.replace('⭐', '').trim()).filter(Boolean);
  }

  try {
    const res = await fetch('/api/jobs/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        raw_jd: rawJd,
        override_role_title: overrideTitle,
        override_location: overrideLoc,
        override_mandatory_skills: overrideSkills.length ? overrideSkills : null
      })
    });

    const data = await res.json();
    if (!data.success) {
      alert(`Sourcing failed: ${data.error || 'Unknown error'}`);
      return;
    }

    activeJobId = data.job_id;
    await loadJobCandidates(activeJobId);
    fetchRecentSearches();

  } catch (err) {
    alert(`Request error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="sparkles" class="w-3.5 h-3.5"></i><span>Find Candidates</span>`;
    progressCard.classList.add('hidden');
    if (window.lucide) lucide.createIcons();
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
    list.innerHTML = `<div class="p-8 text-center text-[#94A3B8] surface-card border border-[#1F2937]">No candidate profiles matched the active filter.</div>`;
    return;
  }

  candidates.forEach(c => {
    const item = document.createElement('div');
    item.className = 'surface-card p-4 border border-[#27272A] hover:border-orange-500/40 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 cursor-pointer';
    item.onclick = () => openDrawer(c);

    // Score badge style
    let scoreBadge = 'badge-strong';
    if (c.score < 40) scoreBadge = 'badge-error';
    else if (c.score < 75) scoreBadge = 'badge-review';

    // Geographic badge (Requirement M: ELIGIBLE, MISMATCH, UNKNOWN)
    const geoStatus = c.geographic_eligibility?.status || 'UNKNOWN';
    let geoBadge = '<span class="text-[10px] bg-amber-500/10 border border-amber-500/30 text-amber-300 px-2 py-0.5 rounded font-mono font-bold">? UNRESOLVED</span>';
    if (geoStatus === 'ELIGIBLE') {
      geoBadge = '<span class="text-[10px] bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 px-2 py-0.5 rounded font-mono font-bold">✓ ELIGIBLE</span>';
    } else if (geoStatus === 'MISMATCH') {
      geoBadge = '<span class="text-[10px] bg-rose-500/10 border border-rose-500/30 text-rose-300 px-2 py-0.5 rounded font-mono font-bold">✕ MISMATCH</span>';
    }

    // Match status label
    let matchBadge = `<span class="text-[10px] bg-[#18181B] border border-[#27272A] text-zinc-300 px-2 py-0.5 rounded font-mono">${c.match_status || 'EVALUATED'}</span>`;
    if (c.match_status === 'EXPLICIT_MATCH') {
      matchBadge = `<span class="text-[10px] bg-orange-500/10 border border-orange-500/30 text-orange-400 px-2 py-0.5 rounded font-mono font-bold">⭐ EXPLICIT MATCH</span>`;
    }

    const initials = (c.name || 'Candidate').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'CA';
    const locText = c.current_location?.value || c.location || 'Location unverified';
    
    // Skills tags
    const skillsList = (c.supporting_evidence || []).slice(0, 3).map(s => 
      `<span class="text-[10px] bg-[#18181B] border border-[#27272A] text-orange-300 px-2 py-0.5 rounded font-mono">${s.skill}</span>`
    ).join(' ');

    item.innerHTML = `
      <div class="flex items-center gap-3.5 min-w-0">
        <div class="w-9 h-9 rounded-full bg-orange-500/10 border border-orange-500/30 flex items-center justify-center font-bold text-xs text-orange-400 shrink-0">
          ${initials}
        </div>
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2">
            <h4 class="font-semibold text-xs text-white hover:text-orange-400 transition truncate">${c.name}</h4>
            <span class="${scoreBadge} text-[10px] font-mono font-bold px-1.5 py-0.2 rounded shrink-0">
              ${c.score ? c.score.toFixed(0) : '0'}%
            </span>
            ${geoBadge}
            ${matchBadge}
          </div>
          <p class="text-[11px] text-[#A1A1AA] truncate max-w-md">${c.headline || 'Technical Professional'}</p>
          <div class="flex items-center gap-2 text-[10px] text-[#71717A] mt-0.5">
            <span class="flex items-center gap-1">📍 ${locText}</span>
            <span>•</span>
            <span>${c.mandatory_skill_coverage ? Math.round(c.mandatory_skill_coverage * 100) : '0'}% skill coverage</span>
          </div>
          <div class="flex flex-wrap gap-1 mt-1">
            ${skillsList || '<span class="text-[10px] text-[#71717A]">Skills evaluated</span>'}
          </div>
        </div>
      </div>

      <div class="flex items-center gap-2 shrink-0 self-end sm:self-center" onclick="event.stopPropagation()">
        <a href="${c.profile_url}" target="_blank" class="flex items-center gap-1 bg-[#18181B] hover:bg-[#27272A] border border-[#27272A] text-[#E4E4E7] text-[11px] px-2.5 py-1 rounded transition">
          <span>Profile</span>
          <i data-lucide="external-link" class="w-3 h-3 text-[#A1A1AA]"></i>
        </a>
        <button onclick="openOutreach('${c.candidate_id}')" class="flex items-center gap-1 bg-orange-500 hover:bg-orange-600 text-white text-[11px] font-semibold px-3 py-1 rounded transition shadow-sm">
          <i data-lucide="sparkles" class="w-3 h-3"></i>
          <span>Evidence</span>
        </button>
      </div>
    `;

    list.appendChild(item);
  });

  if (window.lucide) lucide.createIcons();
}

function filterResults() {
  const kw = (document.getElementById('results-filter')?.value || '').toLowerCase().trim();
  const geoVal = document.getElementById('filter-geo')?.value || 'ALL';
  const matchVal = document.getElementById('filter-match')?.value || 'ALL';

  const filtered = allCandidates.filter(c => {
    const matchesKw = !kw || c.name.toLowerCase().includes(kw) || (c.headline && c.headline.toLowerCase().includes(kw));
    const candGeo = c.geographic_eligibility?.status || 'UNKNOWN';
    const matchesGeo = (geoVal === 'ALL') || (candGeo === geoVal);
    const candMatch = c.match_status || 'INSUFFICIENT_EVIDENCE';
    const matchesMatch = (matchVal === 'ALL') || (candMatch === matchVal);
    return matchesKw && matchesGeo && matchesMatch;
  });

  renderCandidates(filtered);
}

function openDrawer(candidate) {
  activeCandidate = candidate;
  const drawer = document.getElementById('candidate-drawer');
  const backdrop = document.getElementById('drawer-backdrop');
  
  const initials = (candidate.name || 'Candidate').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'CA';
  document.getElementById('drawer-avatar').innerText = initials;
  document.getElementById('drawer-name').innerText = candidate.name;
  document.getElementById('drawer-headline').innerText = candidate.headline || 'Technical Candidate';
  
  // Score badge
  const badge = document.getElementById('drawer-score-badge');
  badge.innerText = `${candidate.score.toFixed(0)}% Fit`;
  badge.className = candidate.score >= 75 ? 'badge-strong text-xs font-mono font-bold px-2 py-0.5 rounded-full' : 'badge-review text-xs font-mono font-bold px-2 py-0.5 rounded-full';
  
  // Geographic badge & explanation
  const geoBadge = document.getElementById('drawer-geo-badge');
  const geoStatus = candidate.geographic_eligibility?.status || 'UNKNOWN';
  geoBadge.innerText = geoStatus;
  if (geoStatus === 'ELIGIBLE') {
    geoBadge.className = 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-bold px-2 py-0.5 rounded-full inline-block';
  } else if (geoStatus === 'MISMATCH') {
    geoBadge.className = 'bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-bold px-2 py-0.5 rounded-full inline-block';
  } else {
    geoBadge.className = 'bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-bold px-2 py-0.5 rounded-full inline-block';
  }
  document.getElementById('drawer-geo-reason').innerText = candidate.geographic_eligibility?.reason || 'Location not verifiable from public snippet.';

  // Component breakdown
  document.getElementById('drawer-score-skills').innerText = Math.round(candidate.skill_score || 0);
  document.getElementById('drawer-score-seniority').innerText = Math.round(candidate.seniority_score || 0);
  document.getElementById('drawer-score-role').innerText = Math.round(candidate.role_alignment_score || 0);
  document.getElementById('drawer-score-evidence').innerText = Math.round(candidate.evidence_quality_score || 0);

  // Supporting quotations
  const quotList = document.getElementById('drawer-quotations-list');
  quotList.innerHTML = '';
  const evidenceList = candidate.supporting_evidence || [];
  if (evidenceList.length === 0) {
    quotList.innerHTML = `<span class="text-xs text-[#64748B]">No explicit text quotations parsed.</span>`;
  } else {
    evidenceList.forEach(item => {
      const el = document.createElement('div');
      el.className = 'p-2 rounded bg-[#09090B] border border-[#27272A] text-xs space-y-1';
      el.innerHTML = `
        <div class="flex items-center justify-between font-mono text-[10px]">
          <span class="text-orange-400 font-bold">✓ ${item.skill}</span>
          <span class="text-emerald-400">${item.state} (${(item.evidence_level*100).toFixed(0)}%)</span>
        </div>
        <p class="text-[11px] text-[#E4E4E7] italic">"${item.quotation}"</p>
      `;
      quotList.appendChild(el);
    });
  }

  document.getElementById('drawer-profile-link').href = candidate.profile_url;

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
  textarea.value = `Drafting evidence-grounded outreach for ${candidate.name}...`;

  try {
    const res = await fetch('/api/outreach/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate: {
          name: candidate.name,
          headline: candidate.headline,
          matched_skills: (candidate.supporting_evidence || []).map(s => s.skill)
        },
        role_title: activeJobTitle || 'Specialist'
      })
    });
    const data = await res.json();
    textarea.value = data.draft || `Hi ${candidate.name.split(' ')[0]},\n\nI noticed your strong background in SAP HANA data solutions and wanted to connect regarding our open ${activeJobTitle} role in Eindhoven.\n\nWould you be open to connecting?`;
  } catch (e) {
    textarea.value = `Hi ${candidate.name.split(' ')[0]},\n\nI noticed your technical expertise in SAP solutions. We have an Eindhoven-based role that strongly aligns with your experience.\n\nBest regards,\nTalent Acquisition`;
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
    const container = document.getElementById('recent-searches-list');
    if (!container) return;
    
    if (!jobs || jobs.length === 0) {
      container.innerHTML = '<div class="text-[11px] text-[#64748B] px-2 py-1">No prior campaigns</div>';
      return;
    }

    container.innerHTML = '';
    jobs.slice(0, 8).forEach(j => {
      const btn = document.createElement('button');
      btn.className = 'w-full text-left text-[11px] text-[#94A3B8] hover:text-white hover:bg-[#161F30] px-2 py-1.5 rounded truncate flex items-center justify-between transition';
      btn.onclick = () => loadJobCandidates(j.job_id);
      btn.innerHTML = `<span class="truncate">${j.role_title || 'Untitled Role'}</span><span class="font-mono text-[9px] text-[#64748B] shrink-0">${j.candidate_count || 0}</span>`;
      container.appendChild(btn);
    });
  } catch (e) {
    console.error('Failed to fetch recent searches', e);
  }
}

function exportCurrentCSV() {
  if (activeJobId) {
    window.location.href = `/api/jobs/${activeJobId}/export/csv`;
  }
}

// ========================================================
// UNSTRUCTURED PORTAL JD INTAKE & SKILLS ARCHITECT
// ========================================================

let currentIntakeSkills = [
  'SAP HANA Modeling',
  'Calculation Views',
  'CDS Views',
  'SQLScript',
  'SLT',
  'SAP BODS',
  'AMS Support'
];

function switchSourcingTab(tab) {
  const directTabBtn = document.getElementById('tab-btn-direct');
  const intakeTabBtn = document.getElementById('tab-btn-intake');
  const directContent = document.getElementById('tab-direct-content');
  const intakeContent = document.getElementById('tab-intake-content');

  if (tab === 'direct') {
    directTabBtn.className = 'text-xs font-semibold px-3 py-1.5 rounded-lg bg-orange-500 text-white transition flex items-center gap-1.5 shadow-sm';
    intakeTabBtn.className = 'text-xs font-medium px-3 py-1.5 rounded-lg bg-[#18181B] hover:bg-[#27272A] text-[#A1A1AA] hover:text-white border border-[#27272A] transition flex items-center gap-1.5';
    directContent.classList.remove('hidden');
    intakeContent.classList.add('hidden');
  } else {
    intakeTabBtn.className = 'text-xs font-semibold px-3 py-1.5 rounded-lg bg-orange-500 text-white transition flex items-center gap-1.5 shadow-sm';
    directTabBtn.className = 'text-xs font-medium px-3 py-1.5 rounded-lg bg-[#18181B] hover:bg-[#27272A] text-[#A1A1AA] hover:text-white border border-[#27272A] transition flex items-center gap-1.5';
    directContent.classList.add('hidden');
    intakeContent.classList.remove('hidden');
    
    // Initialize preview if first visit
    if (!document.getElementById('intake-role-title').value) {
      document.getElementById('intake-role-title').value = 'SAP HANA Cloud Consultant';
      document.getElementById('intake-location').value = 'Eindhoven, Netherlands';
      document.getElementById('intake-experience').value = '7-11 years';
      renderIntakeSkills(currentIntakeSkills);
      updateFormattedBriefPreview();
    }
  }
  if (window.lucide) lucide.createIcons();
}

function loadSamplePortalJD() {
  const sample = `Job Title: SAP HANA Cloud Consultant
Location: Eindhoven, Netherlands (Hybrid - 3 days per week)
Experience: 7-11 years of professional experience

About the Role:
We are seeking an experienced SAP HANA Cloud Consultant based in Eindhoven to architect, optimize, and support enterprise data solutions. You will be responsible for native HANA data modeling, SQLScript performance optimization, and high-availability AMS L2/L3 production support.

Key Requirements & Responsibilities:
- Native SAP HANA Modeling and Calculation Views design.
- Core Data Services (CDS Views) and ABAP on HANA integration.
- SQLScript procedure authoring and PlanViz query performance tuning.
- Real-time data provisioning with SLT (SAP Landscape Transformation).
- Enterprise ETL and integration with SAP BODS (BusinessObjects Data Services).
- Production incident management and AMS Support.

Nice to have:
SAP BW/4HANA, SAP BTP, Jira, Agile/Scrum.`;

  document.getElementById('portal-raw-jd').value = sample;
  parseUnstructuredJD();
}

async function parseUnstructuredJD() {
  const rawText = document.getElementById('portal-raw-jd').value.trim();
  if (!rawText) {
    alert('Please paste an unstructured Job Description first.');
    return;
  }

  const btn = document.getElementById('btn-parse-portal-jd');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<div class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div><span>Extracting & Formatting...</span>`;

  try {
    const res = await fetch('/api/jobs/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ raw_jd: rawText })
    });

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data = await res.json();

    document.getElementById('intake-role-title').value = data.role_title || '';
    document.getElementById('intake-location').value = data.location_str || (data.locations && data.locations[0]) || '';
    document.getElementById('intake-experience').value = data.experience_str || '7-11 years';

    currentIntakeSkills = (data.mandatory_skills && data.mandatory_skills.length > 0)
      ? data.mandatory_skills
      : ['SAP HANA Modeling', 'Calculation Views', 'CDS Views', 'SQLScript', 'SLT', 'SAP BODS', 'AMS Support'];

    renderIntakeSkills(currentIntakeSkills);

    // Suggestions from preferred skills
    const suggContainer = document.getElementById('intake-suggestions-container');
    const suggChips = document.getElementById('intake-suggestions-chips');
    suggChips.innerHTML = '';
    if (data.preferred_skills && data.preferred_skills.length > 0) {
      data.preferred_skills.forEach(skill => {
        const btnSugg = document.createElement('button');
        btnSugg.className = 'text-[10px] bg-[#18181B] hover:bg-[#27272A] text-orange-300 border border-orange-500/20 px-2 py-0.5 rounded transition flex items-center gap-1';
        btnSugg.innerHTML = `<span>+ ${skill}</span>`;
        btnSugg.onclick = () => {
          if (!currentIntakeSkills.includes(skill)) {
            currentIntakeSkills.push(skill);
            renderIntakeSkills(currentIntakeSkills);
            updateFormattedBriefPreview();
          }
          btnSugg.remove();
        };
        suggChips.appendChild(btnSugg);
      });
      suggContainer.classList.remove('hidden');
    } else {
      suggContainer.classList.add('hidden');
    }

    const badge = document.getElementById('parsing-badge');
    if (badge) badge.classList.remove('hidden');

    updateFormattedBriefPreview();

  } catch (err) {
    console.error('Extraction error:', err);
    alert('Extraction notice: loaded rule-based parser. You can review and edit all skills.');
    
    // Fallback extraction
    document.getElementById('intake-role-title').value = 'SAP HANA Cloud Consultant';
    document.getElementById('intake-location').value = 'Eindhoven, Netherlands';
    document.getElementById('intake-experience').value = '7-11 years';
    currentIntakeSkills = ['SAP HANA Modeling', 'Calculation Views', 'CDS Views', 'SQLScript', 'SLT', 'SAP BODS', 'AMS Support'];
    renderIntakeSkills(currentIntakeSkills);
    updateFormattedBriefPreview();
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    if (window.lucide) lucide.createIcons();
  }
}

function renderIntakeSkills(skills) {
  const container = document.getElementById('intake-skills-chips');
  const countSpan = document.getElementById('intake-skills-count');
  if (!container) return;

  container.innerHTML = '';
  if (!skills || skills.length === 0) {
    container.innerHTML = `<span class="text-[11px] text-[#64748B] italic">No skills added yet. Add one below.</span>`;
    if (countSpan) countSpan.innerText = '0 skills';
    return;
  }

  if (countSpan) countSpan.innerText = `${skills.length} skills`;

  skills.forEach((s, idx) => {
    const chip = document.createElement('span');
    chip.className = 'inline-flex items-center gap-1.5 bg-[#18181B] border border-orange-500/30 text-orange-300 text-[11px] px-2.5 py-1 rounded-md shadow-sm';
    chip.innerHTML = `<span>⭐ ${s}</span><button onclick="removeIntakeSkill(${idx})" class="text-[#64748B] hover:text-rose-400 ml-1 font-bold text-xs transition">×</button>`;
    container.appendChild(chip);
  });
}

function addIntakeSkill() {
  const input = document.getElementById('intake-new-skill');
  const val = input.value.trim();
  if (!val) return;

  const clean = val.replace(/^\*+/, '').trim();
  if (clean && !currentIntakeSkills.includes(clean)) {
    currentIntakeSkills.push(clean);
    renderIntakeSkills(currentIntakeSkills);
    updateFormattedBriefPreview();
  }
  input.value = '';
}

function removeIntakeSkill(index) {
  if (index >= 0 && index < currentIntakeSkills.length) {
    currentIntakeSkills.splice(index, 1);
    renderIntakeSkills(currentIntakeSkills);
    updateFormattedBriefPreview();
  }
}

function updateFormattedBriefPreview() {
  const title = document.getElementById('intake-role-title').value.trim() || 'Job Title';
  const loc = document.getElementById('intake-location').value.trim() || 'Location';
  const exp = document.getElementById('intake-experience').value.trim() || 'Experience Target';

  let skillsText = '';
  if (currentIntakeSkills.length > 0) {
    skillsText = currentIntakeSkills.map(s => `*${s}`).join('\n');
  } else {
    skillsText = '*Core Technical Competencies';
  }

  const formatted = `Job Title: ${title}\nLocation: ${loc}\nExperience: ${exp}\n\nMandatory Requirements:\n${skillsText}`;
  const pre = document.getElementById('intake-formatted-preview');
  if (pre) pre.innerText = formatted;
}

function copyFormattedBrief() {
  const pre = document.getElementById('intake-formatted-preview');
  if (!pre) return;
  navigator.clipboard.writeText(pre.innerText).then(() => {
    const label = document.getElementById('copy-brief-label');
    if (label) {
      const orig = label.innerText;
      label.innerText = 'Copied!';
      setTimeout(() => { label.innerText = orig; }, 1800);
    }
  });
}

function sourceFromIntake() {
  const pre = document.getElementById('intake-formatted-preview');
  const formattedText = pre ? pre.innerText : '';
  const title = document.getElementById('intake-role-title').value.trim();
  const loc = document.getElementById('intake-location').value.trim();
  const exp = document.getElementById('intake-experience').value.trim();

  // Populate direct prompt and advanced fields
  document.getElementById('raw-jd-input').value = formattedText;
  document.getElementById('rule-role-title').value = title;
  document.getElementById('rule-location').value = loc;
  document.getElementById('rule-experience').value = exp;
  document.getElementById('active-brief-title').innerText = title || 'Custom Intake Brief';

  renderSkills(currentIntakeSkills);

  // Switch to direct tab to show the active sourcing progress
  switchSourcingTab('direct');

  // Trigger sourcing
  startSourcingPipeline();
}
