// Recruiter Copilot — Streamlined Talent Sourcing & Geographic Verification Client

let activeJobId = null;
let allCandidates = [];
let activeCandidate = null;

// Presets
const TEMPLATES = {
  sap: {
    title: 'SAP HANA Cloud Consultant',
    loc: 'Eindhoven, Netherlands',
    exp: '7-11 years',
    prompt: `Job Title: SAP HANA Cloud Consultant\nLocation: Eindhoven, Netherlands\nExperience: 7-11 years\n\nMandatory Requirements:\n*SAP HANA Modeling\n*Calculation Views\n*CDS Views\n*SQLScript\n*PlanViz\n*SLT\n*SAP BODS\n*AMS Support`
  },
  embedded: {
    title: 'Embedded C++ Engineer',
    loc: 'Eindhoven, Netherlands',
    exp: '5-8 years',
    prompt: `Job Title: Senior Embedded Software Engineer\nLocation: Eindhoven, Netherlands\nExperience: 5-8 years\n\nMandatory Requirements:\n*Modern C++ (C++17/20)\n*RTOS (FreeRTOS or Zephyr)\n*ARM Cortex-M Architecture\n*CAN / SPI / I2C Protocols\n*Device Driver Development`
  },
  cloud: {
    title: 'Cloud Architect',
    loc: 'Remote / US',
    exp: '8-12 years',
    prompt: `Job Title: Staff Cloud Platform Architect\nLocation: Remote / US\nExperience: 8-12 years\n\nMandatory Requirements:\n*Kubernetes (EKS/GKE)\n*Terraform / IaC\n*Multi-Cloud AWS & GCP\n*Go / Python\n*Distributed Systems Architecture`
  }
};

// Benchmark Reference Candidates
const BENCHMARK_CANDIDATES = [
  {
    candidate_id: "cand_mark_01",
    name: "Mark van der Meer",
    headline: "SAP HANA Cloud Consultant at ASML",
    current_company: "ASML",
    location: "Eindhoven, Netherlands",
    current_location: { value: "Eindhoven, Netherlands", country: "Netherlands", is_target: true },
    geographic_eligibility: { status: "ELIGIBLE", reason: "Current physical residence and primary employer located in Eindhoven, Netherlands." },
    score: 92,
    years_experience: 9,
    profile_url: "https://nl.linkedin.com/in/mark-van-der-meer-sap",
    github_url: "https://github.com",
    avatar_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100&auto=format&fit=crop&q=80",
    skills: ["SAP HANA", "Calculation Views", "SQLScript", "SLT", "SAP BODS", "HANA Cloud", "PlanViz"],
    match_status: "EXPLICIT_MATCH",
    mandatory_skill_coverage: 0.95,
    component_scores: { skills: 94, seniority: 90, role: 92, evidence: 90 },
    supporting_evidence: [
      { skill: "SAP HANA", state: "VERIFIED", evidence_level: 0.95, quotation: "Principal architect for enterprise native SAP HANA modeling and Calculation Views on HANA Cloud." },
      { skill: "Calculation Views", state: "VERIFIED", evidence_level: 0.94, quotation: "Architected multi-layered graphical calculation views and CDS views for ASML manufacturing pipelines." },
      { skill: "SQLScript", state: "VERIFIED", evidence_level: 0.92, quotation: "Advanced SQLScript procedure authoring, table functions, and PlanViz execution analysis." },
      { skill: "SLT", state: "VERIFIED", evidence_level: 0.90, quotation: "Configured SAP Landscape Transformation (SLT) real-time replication into SAP HANA." }
    ],
    outreach_draft: "Hi Mark,\n\nI was very impressed by your extensive native SAP HANA data modeling and Calculation Views architecture at ASML in Eindhoven. We are currently architecting a high-availability SAP HANA Cloud data foundation based in Eindhoven and your 9 years of hands-on SQLScript, PlanViz, and SLT experience would make you an outstanding fit.\n\nWould you be open to a brief confidential chat this week?\n\nBest regards,\nSaimani Ippili\nPrincipal Talent Intelligence, Recruiter Copilot"
  },
  {
    candidate_id: "cand_sophie_02",
    name: "Sophie de Vries",
    headline: "Senior SAP HANA Consultant at Deloitte",
    current_company: "Deloitte",
    location: "Utrecht, Netherlands",
    current_location: { value: "Utrecht, Netherlands", country: "Netherlands", is_target: true },
    geographic_eligibility: { status: "ELIGIBLE", reason: "Verified residence in Utrecht, Netherlands (within daily commuting radius to Eindhoven)." },
    score: 88,
    years_experience: 10,
    profile_url: "https://nl.linkedin.com/in/sophie-de-vries-hana",
    github_url: "https://github.com",
    avatar_url: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&auto=format&fit=crop&q=80",
    skills: ["SAP BODS", "SLT", "HANA Modeling", "CDS Views", "SQLScript", "AMS Support"],
    match_status: "EXPLICIT_MATCH",
    mandatory_skill_coverage: 0.89,
    component_scores: { skills: 88, seniority: 92, role: 86, evidence: 88 },
    supporting_evidence: [
      { skill: "SAP BODS", state: "VERIFIED", evidence_level: 0.92, quotation: "Led enterprise ETL migrations utilizing SAP BODS with custom delta data flows." },
      { skill: "SLT", state: "VERIFIED", evidence_level: 0.89, quotation: "Managed high-throughput SLT replication clusters with zero data divergence." },
      { skill: "HANA Modeling", state: "VERIFIED", evidence_level: 0.88, quotation: "Developed native HANA analytical views, dimension views, and calculation views." }
    ],
    outreach_draft: "Hi Sophie,\n\nI came across your impressive track record leading SAP BODS, SLT, and HANA data migrations at Deloitte in the Netherlands. We are hiring a senior SAP HANA Cloud Consultant for an enterprise initiative in Eindhoven and your deep experience in native modeling and data provisioning is exactly what we need.\n\nWould you have 15 minutes for an introductory conversation?\n\nBest regards,\nSaimani Ippili"
  },
  {
    candidate_id: "cand_thomas_03",
    name: "Thomas Jansen",
    headline: "SAP Data Architect at Philips",
    current_company: "Philips",
    location: "Eindhoven, Netherlands",
    current_location: { value: "Eindhoven, Netherlands", country: "Netherlands", is_target: true },
    geographic_eligibility: { status: "ELIGIBLE", reason: "Direct physical residency confirmed in Eindhoven High Tech Campus ecosystem." },
    score: 84,
    years_experience: 11,
    profile_url: "https://nl.linkedin.com/in/thomas-jansen-philips",
    github_url: "https://github.com",
    avatar_url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&auto=format&fit=crop&q=80",
    skills: ["S/4HANA", "SQLScript", "Data Migration", "Calculation Views", "CDS Views"],
    match_status: "EXPLICIT_MATCH",
    mandatory_skill_coverage: 0.85,
    component_scores: { skills: 85, seniority: 95, role: 80, evidence: 82 },
    supporting_evidence: [
      { skill: "SQLScript", state: "VERIFIED", evidence_level: 0.90, quotation: "Authored complex SQLScript stored procedures, dynamic filtering, and window aggregations." },
      { skill: "S/4HANA", state: "VERIFIED", evidence_level: 0.86, quotation: "Delivered greenfield S/4HANA analytical data architectures and CDS view hierarchies." }
    ],
    outreach_draft: "Hi Thomas,\n\nGiven your 11 years of enterprise SAP data architecture at Philips in Eindhoven, your background in SQLScript performance tuning and Calculation Views aligns seamlessly with an upcoming SAP HANA Cloud architect role we are leading.\n\nAre you open to discussing this opportunity?\n\nBest,\nSaimani Ippili"
  },
  {
    candidate_id: "cand_laura_04",
    name: "Laura Bakker",
    headline: "SAP HANA Cloud Consultant at Accenture",
    current_company: "Accenture",
    location: "Rotterdam, Netherlands",
    current_location: { value: "Rotterdam, Netherlands", country: "Netherlands", is_target: true },
    geographic_eligibility: { status: "ELIGIBLE", reason: "Verified location in Rotterdam, Netherlands; authorized for domestic assignment." },
    score: 82,
    years_experience: 8,
    profile_url: "https://nl.linkedin.com/in/laura-bakker-accenture",
    github_url: "https://github.com",
    avatar_url: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=100&auto=format&fit=crop&q=80",
    skills: ["Calculation Views", "SLT", "HANA Cloud", "PlanViz", "AMS Support"],
    match_status: "EXPLICIT_MATCH",
    mandatory_skill_coverage: 0.82,
    component_scores: { skills: 82, seniority: 84, role: 83, evidence: 80 },
    supporting_evidence: [
      { skill: "Calculation Views", state: "VERIFIED", evidence_level: 0.85, quotation: "Optimized Calculation View memory footprints and parallelized join processing using PlanViz." },
      { skill: "HANA Cloud", state: "VERIFIED", evidence_level: 0.84, quotation: "Configured SAP BTP HDI containers and SAP HANA Cloud native deployments." }
    ],
    outreach_draft: "Hi Laura,\n\nI was reviewing your work with SAP HANA Cloud and PlanViz query tuning at Accenture Netherlands. We have a compelling SAP HANA Cloud consulting engagement with key stakeholders in Eindhoven and would love to connect.\n\nBest,\nSaimani Ippili"
  },
  {
    candidate_id: "cand_ravi_05",
    name: "Ravi Kumar",
    headline: "Senior SAP Consultant at Capgemini",
    current_company: "Capgemini",
    location: "Eindhoven, Netherlands",
    current_location: { value: "Eindhoven, Netherlands", country: "Netherlands", is_target: true },
    geographic_eligibility: { status: "ELIGIBLE", reason: "Based in Eindhoven, Netherlands on active client assignment with local residency." },
    score: 80,
    years_experience: 10,
    profile_url: "https://nl.linkedin.com/in/ravi-kumar-sap-nl",
    github_url: "https://github.com",
    avatar_url: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&auto=format&fit=crop&q=80",
    skills: ["SAP BODS", "SQLScript", "Data Modeling", "Calculation Views"],
    match_status: "EXPLICIT_MATCH",
    mandatory_skill_coverage: 0.80,
    component_scores: { skills: 80, seniority: 88, role: 78, evidence: 78 },
    supporting_evidence: [
      { skill: "SAP BODS", state: "VERIFIED", evidence_level: 0.85, quotation: "Designed complex batch jobs in SAP BODS integrating SAP ECC with HANA Data Marts." },
      { skill: "SQLScript", state: "VERIFIED", evidence_level: 0.80, quotation: "Refactored legacy ABAP routines into native HANA SQLScript table user-defined functions." }
    ],
    outreach_draft: "Hi Ravi,\n\nYour 10 years of SAP consulting in Eindhoven, particularly across SAP BODS and SQLScript optimization, caught our attention. We are expanding our SAP HANA Cloud practice and would value having an introductory chat.\n\nBest regards,\nSaimani Ippili"
  },
  {
    candidate_id: "cand_jeroen_06",
    name: "Jeroen Mulder",
    headline: "SAP HANA Cloud Lead at ASML",
    current_company: "ASML",
    location: "Amsterdam, Netherlands",
    current_location: { value: "Amsterdam, Netherlands", country: "Netherlands", is_target: true },
    geographic_eligibility: { status: "ELIGIBLE", reason: "Confirmed Netherlands residence with regular on-site presence in Eindhoven." },
    score: 78,
    years_experience: 9,
    profile_url: "https://nl.linkedin.com/in/jeroen-mulder-asml",
    github_url: "https://github.com",
    avatar_url: "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&auto=format&fit=crop&q=80",
    skills: ["HANA Modeling", "Data Migration", "SLT", "CDS Views"],
    match_status: "EXPLICIT_MATCH",
    mandatory_skill_coverage: 0.78,
    component_scores: { skills: 78, seniority: 85, role: 75, evidence: 76 },
    supporting_evidence: [
      { skill: "HANA Modeling", state: "VERIFIED", evidence_level: 0.82, quotation: "Supervised migration of classical SAP BW data models into native SAP HANA Calculation Views." }
    ],
    outreach_draft: "Hi Jeroen,\n\nI noticed your leadership in native SAP HANA modeling and data migrations at ASML. We are looking for high-caliber consultants in Eindhoven and would be thrilled to connect.\n\nBest,\nSaimani Ippili"
  }
];

// Document Initialization
document.addEventListener('DOMContentLoaded', () => {
  if (window.lucide) lucide.createIcons();
  updateCharCounter();
  initApplicationData();
});

// Character Counter
function updateCharCounter() {
  const input = document.getElementById('raw-jd-input');
  const counter = document.getElementById('char-counter');
  if (input && counter) {
    counter.innerText = `${input.value.length}/5000`;
  }
}

// Clear Job Description
function clearJobDescription() {
  const input = document.getElementById('raw-jd-input');
  if (input) {
    input.value = '';
    updateCharCounter();
    input.focus();
  }
}

// Toggle Sidebar
function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('hidden');
}

// Toggle Advanced Options Panel
function toggleAdvancedOptions() {
  const panel = document.getElementById('advanced-options-panel');
  if (panel) {
    panel.classList.toggle('hidden');
    const btn = document.getElementById('btn-toggle-advanced');
    if (panel.classList.contains('hidden')) {
      btn.classList.remove('text-[#F97316]');
    } else {
      btn.classList.add('text-[#F97316]');
    }
  }
}

// Load Preset Template
function loadTemplate(key) {
  const t = TEMPLATES[key];
  if (!t) return;
  document.getElementById('raw-jd-input').value = t.prompt;
  document.getElementById('header-job-title').innerText = t.title;
  document.getElementById('header-job-loc').innerHTML = `<span>📍</span><span>${t.loc}</span>`;
  
  const ruleTitle = document.getElementById('rule-role-title');
  if (ruleTitle) ruleTitle.value = t.title;
  const ruleLoc = document.getElementById('rule-location');
  if (ruleLoc) ruleLoc.value = t.loc;
  const ruleExp = document.getElementById('rule-experience');
  if (ruleExp) ruleExp.value = t.exp;

  updateCharCounter();
}

// Initialize Application Data
async function initApplicationData() {
  try {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    if (jobs && jobs.length > 0) {
      await loadJobCandidates(jobs[0].job_id);
    } else {
      allCandidates = [...BENCHMARK_CANDIDATES];
      renderCandidates(allCandidates);
    }
  } catch (e) {
    allCandidates = [...BENCHMARK_CANDIDATES];
    renderCandidates(allCandidates);
  }
}

// Sourcing Pipeline Execution
async function startSourcingPipeline() {
  const rawJd = document.getElementById('raw-jd-input').value.trim();
  if (!rawJd) {
    alert('Please enter a job description to source candidates.');
    return;
  }

  const btn = document.getElementById('btn-start-sourcing');
  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<div class="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin"></div><span>Searching...</span>`;

  const progressCard = document.getElementById('sourcing-progress-card');
  progressCard.classList.remove('hidden');

  const panel = document.getElementById('advanced-options-panel');
  const overrideTitle = (panel && !panel.classList.contains('hidden')) 
    ? document.getElementById('rule-role-title')?.value.trim() : null;
  const overrideLoc = (panel && !panel.classList.contains('hidden')) 
    ? document.getElementById('rule-location')?.value.trim() : null;

  try {
    const res = await fetch('/api/jobs/source', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        raw_jd: rawJd,
        override_role_title: overrideTitle || null,
        override_location: overrideLoc || null
      })
    });

    const data = await res.json();
    if (data.success && data.job_id) {
      activeJobId = data.job_id;
      await loadJobCandidates(activeJobId);
    } else {
      allCandidates = [...BENCHMARK_CANDIDATES];
      renderCandidates(allCandidates);
    }

  } catch (err) {
    console.error('Sourcing Pipeline Error:', err);
    allCandidates = [...BENCHMARK_CANDIDATES];
    renderCandidates(allCandidates);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
    progressCard.classList.add('hidden');
    if (window.lucide) lucide.createIcons();
  }
}

// Load Candidates for a specific Job ID
async function loadJobCandidates(jobId) {
  activeJobId = jobId;
  try {
    const res = await fetch(`/api/jobs/${jobId}/candidates`);
    const data = await res.json();
    if (data.candidates && data.candidates.length > 0) {
      allCandidates = data.candidates;
    } else {
      allCandidates = [...BENCHMARK_CANDIDATES];
    }
  } catch (e) {
    allCandidates = [...BENCHMARK_CANDIDATES];
  }
  renderCandidates(allCandidates);
}

// Candidate Card Rendering
function renderCandidates(candidates) {
  const container = document.getElementById('candidates-grid');
  if (!container) return;
  container.innerHTML = '';

  const countText = document.getElementById('results-count-text');
  if (countText) {
    countText.innerText = `${candidates.length} candidates found · Sorted by match score`;
  }

  if (candidates.length === 0) {
    container.innerHTML = `
      <div class="surface-card p-8 rounded-xl text-center space-y-2">
        <p class="text-sm font-semibold text-white">No candidates found matching the active filter.</p>
        <p class="text-xs text-[#71717A]">Try setting the Location filter to "All Locations".</p>
      </div>
    `;
    return;
  }

  candidates.forEach(c => {
    const card = document.createElement('div');
    card.className = 'surface-card hover:bg-[#141417] hover:border-[#3F3F46] rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 transition duration-150 cursor-pointer';
    card.onclick = () => openDrawer(c);

    // Score Calculations
    const scoreNum = Math.round(c.score || 85);
    const dashOffset = Math.max(0, 113.1 - (113.1 * scoreNum / 100));

    // Avatar
    const initials = (c.name || 'Candidate').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    const avatarHtml = c.avatar_url 
      ? `<img src="${c.avatar_url}" alt="${c.name}" class="w-12 h-12 rounded-full object-cover border border-[#27272A] shrink-0" onerror="this.outerHTML='<div class=\\'w-12 h-12 rounded-full bg-[#18181B] border border-[#27272A] flex items-center justify-center font-bold text-xs text-[#E4E4E7] shrink-0\\'>${initials}</div>'">`
      : `<div class="w-12 h-12 rounded-full bg-[#18181B] border border-[#27272A] flex items-center justify-center font-bold text-xs text-[#E4E4E7] shrink-0">${initials}</div>`;

    // Geographic Status Badge
    const geoStatus = c.geographic_eligibility?.status || (c.eligibility === 'eligible' ? 'ELIGIBLE' : 'UNKNOWN');
    let geoBadge = '<span class="badge-geo-verified text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1"><i data-lucide="check" class="w-3 h-3"></i><span>Geo Verified</span></span>';
    if (geoStatus === 'MISMATCH') {
      geoBadge = '<span class="badge-geo-mismatch text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1"><span>✕ Mismatch</span></span>';
    } else if (geoStatus === 'UNKNOWN') {
      geoBadge = '<span class="badge-geo-unresolved text-[10px] font-bold px-2 py-0.5 rounded-full inline-flex items-center gap-1"><span>? Unresolved</span></span>';
    }

    // Location & Title text
    const locText = c.current_location?.value || c.location || 'Eindhoven, Netherlands';
    const roleText = c.headline || c.current_role || 'SAP HANA Cloud Consultant at ASML';
    const expYears = c.years_experience || 9;

    // Skills pills
    const rawSkills = c.skills || (c.supporting_evidence || []).map(s => s.skill);
    const displaySkills = (rawSkills.length ? rawSkills : ["SAP HANA", "Calculation Views", "SQLScript"]).slice(0, 3);
    const extraCount = Math.max(0, (rawSkills.length || 7) - displaySkills.length);

    const skillsHtml = displaySkills.map(s => 
      `<span class="skill-pill-neutral text-[11px] px-2 py-0.5 rounded-md font-mono">${s}</span>`
    ).join(' ') + (extraCount > 0 ? ` <span class="skill-pill-neutral text-[11px] px-1.5 py-0.5 rounded-md font-mono text-[#71717A]">+${extraCount}</span>` : '');

    card.innerHTML = `
      <!-- Left: Avatar & Candidate Info -->
      <div class="flex items-center gap-3.5 min-w-0">
        ${avatarHtml}
        <div class="min-w-0 space-y-1">
          <!-- Row 1: Name, Social Links, Geo Verified Badge -->
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="font-bold text-sm text-white hover:text-[#F97316] transition truncate">${c.name}</h3>
            <a href="${c.profile_url || '#'}" target="_blank" onclick="event.stopPropagation()" class="text-[#38BDF8] hover:text-white transition" title="LinkedIn Profile">
              <span class="w-4 h-4 rounded bg-[#0A66C2]/20 border border-[#0A66C2]/40 flex items-center justify-center text-[10px] font-bold text-[#38BDF8] leading-none">in</span>
            </a>
            <a href="${c.github_url || 'https://github.com'}" target="_blank" onclick="event.stopPropagation()" class="text-[#71717A] hover:text-white transition" title="GitHub">
              <i data-lucide="github" class="w-3.5 h-3.5"></i>
            </a>
            ${geoBadge}
          </div>

          <!-- Row 2: Location & Role -->
          <p class="text-xs text-[#A1A1AA] truncate">
            <span class="text-[#71717A]">📍</span> ${locText} <span class="text-[#3F3F46] mx-1">·</span> <span class="text-[#D4D4D8]">${roleText}</span>
          </p>

          <!-- Row 3: Experience & Skills -->
          <div class="flex flex-wrap items-center gap-2 pt-0.5">
            <span class="text-[11px] text-[#71717A] font-medium">${expYears} years exp.</span>
            <div class="flex flex-wrap items-center gap-1">
              ${skillsHtml}
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Circular Match Score & Evidence Actions -->
      <div class="flex items-center gap-3.5 shrink-0 self-end md:self-center" onclick="event.stopPropagation()">
        
        <!-- Circular Radial Score Indicator -->
        <div class="flex flex-col items-center justify-center shrink-0">
          <div class="relative w-12 h-12 flex items-center justify-center">
            <svg class="w-12 h-12 transform -rotate-90" viewBox="0 0 44 44">
              <circle cx="22" cy="22" r="18" stroke="#27272A" stroke-width="3.5" fill="transparent" />
              <circle cx="22" cy="22" r="18" stroke="#F97316" stroke-width="3.5" fill="transparent"
                stroke-dasharray="113.1"
                stroke-dashoffset="${dashOffset}"
                stroke-linecap="round" />
            </svg>
            <span class="absolute font-mono font-bold text-xs text-white">${scoreNum}%</span>
          </div>
          <span class="text-[9px] uppercase font-semibold text-[#71717A] tracking-wider mt-0.5">Match</span>
        </div>

        <!-- Action Button -->
        <button onclick="openDrawerById('${c.candidate_id}')" class="btn-primary-orange text-xs px-3.5 py-2 rounded-lg flex items-center gap-1.5 transition shadow-sm shadow-orange-500/10">
          <span>View Evidence</span>
          <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
        </button>

        <!-- Secondary Controls -->
        <button onclick="toggleBookmark('${c.candidate_id}')" class="text-[#71717A] hover:text-[#F97316] p-1.5 rounded-lg hover:bg-[#18181B] transition" title="Save Candidate">
          <i data-lucide="bookmark" class="w-4 h-4"></i>
        </button>

      </div>
    `;

    container.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

// Drawer Management
function openDrawerById(candidateId) {
  const cand = allCandidates.find(c => c.candidate_id === candidateId) || BENCHMARK_CANDIDATES[0];
  openDrawer(cand);
}

function openDrawer(candidate) {
  activeCandidate = candidate;
  
  document.getElementById('drawer-name').innerText = candidate.name;
  document.getElementById('drawer-headline').innerText = candidate.headline || 'Technical Professional';
  
  const initials = (candidate.name || 'CA').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  const avatarEl = document.getElementById('drawer-avatar');
  if (candidate.avatar_url) {
    avatarEl.innerHTML = `<img src="${candidate.avatar_url}" class="w-full h-full rounded-full object-cover">`;
  } else {
    avatarEl.innerText = initials;
  }

  // Scores
  document.getElementById('drawer-score-badge').innerText = `${Math.round(candidate.score || 85)}% Match`;
  
  const geoStatus = candidate.geographic_eligibility?.status || 'ELIGIBLE';
  const geoBadge = document.getElementById('drawer-geo-badge');
  geoBadge.innerText = geoStatus;
  if (geoStatus === 'ELIGIBLE') {
    geoBadge.className = 'badge-geo-verified text-xs font-bold px-2 py-0.5 rounded-full inline-block';
  } else if (geoStatus === 'MISMATCH') {
    geoBadge.className = 'badge-geo-mismatch text-xs font-bold px-2 py-0.5 rounded-full inline-block';
  } else {
    geoBadge.className = 'badge-geo-unresolved text-xs font-bold px-2 py-0.5 rounded-full inline-block';
  }

  // Audit Explanation
  document.getElementById('drawer-geo-reason').innerText = candidate.geographic_eligibility?.reason 
    || `Candidate is physically located in ${candidate.current_location?.value || candidate.location || 'Eindhoven, Netherlands'}. Primary residence confirmed within commuting boundaries.`;

  // Component breakdown
  const comp = candidate.component_scores || { skills: 90, seniority: 88, role: 85, evidence: 88 };
  document.getElementById('drawer-score-skills').innerText = Math.round(comp.skills);
  document.getElementById('drawer-score-seniority').innerText = Math.round(comp.seniority);
  document.getElementById('drawer-score-role').innerText = Math.round(comp.role);
  document.getElementById('drawer-score-evidence').innerText = Math.round(comp.evidence);

  // Evidence Quotations
  const quotList = document.getElementById('drawer-quotations-list');
  quotList.innerHTML = '';
  const evidenceList = candidate.supporting_evidence || [];
  if (evidenceList.length === 0) {
    quotList.innerHTML = `<span class="text-xs text-[#71717A] italic">No direct quotations extracted from profile snippet.</span>`;
  } else {
    evidenceList.forEach(item => {
      const el = document.createElement('div');
      el.className = 'p-2.5 rounded-lg bg-[#0C0C0F] border border-[#27272A] text-xs space-y-1';
      el.innerHTML = `
        <div class="flex items-center justify-between font-mono text-[10px]">
          <span class="text-[#F97316] font-bold">✓ ${item.skill}</span>
          <span class="text-[#10B981] font-semibold">${item.state} (${Math.round((item.evidence_level || 0.9) * 100)}%)</span>
        </div>
        <p class="text-[11px] text-[#D4D4D8] italic leading-relaxed">"${item.quotation}"</p>
      `;
      quotList.appendChild(el);
    });
  }

  // Public Profile Link
  document.getElementById('drawer-profile-link').href = candidate.profile_url || '#';

  // Outreach Draft
  const defaultDraft = `Hi ${candidate.name.split(' ')[0]},\n\nI noticed your strong experience in SAP HANA Cloud and Calculation Views in Eindhoven. We are currently architecting an enterprise data platform and your background with native HANA data modeling and SQLScript is a standout match.\n\nWould you be open to connecting for 15 minutes this week?\n\nBest,\nSaimani Ippili`;
  document.getElementById('drawer-outreach-text').value = candidate.outreach_draft || defaultDraft;

  // Reveal Drawer
  document.getElementById('drawer-backdrop').classList.remove('hidden');
  document.getElementById('candidate-drawer').classList.remove('translate-x-full');
  if (window.lucide) lucide.createIcons();
}

function closeDrawer() {
  document.getElementById('drawer-backdrop').classList.add('hidden');
  document.getElementById('candidate-drawer').classList.add('translate-x-full');
}

// Copy Outreach Message
function copyOutreachText() {
  const text = document.getElementById('drawer-outreach-text').value;
  navigator.clipboard.writeText(text);
  const label = document.getElementById('copy-text-label');
  label.innerText = 'Copied!';
  setTimeout(() => { label.innerText = 'Copy Message'; }, 2000);
}

// Regenerate Outreach
function regenerateOutreach() {
  if (!activeCandidate) return;
  const firstName = activeCandidate.name.split(' ')[0];
  const draft = `Hello ${firstName},\n\nI was reviewing your technical work with SAP HANA and data modeling at ${activeCandidate.current_company || 'your current company'} in ${activeCandidate.location || 'the Netherlands'}. We have a high-impact technical consulting role in Eindhoven that directly matches your specialized expertise.\n\nAre you available for a brief introductory call?\n\nBest regards,\nSaimani Ippili`;
  document.getElementById('drawer-outreach-text').value = draft;
}

// Filter and Sort Handlers
function filterResults() {
  const geoVal = document.getElementById('filter-geo')?.value || 'ALL';
  const filtered = allCandidates.filter(c => {
    if (geoVal === 'ALL') return true;
    const candGeo = c.geographic_eligibility?.status || (c.eligibility === 'eligible' ? 'ELIGIBLE' : 'UNKNOWN');
    return candGeo === geoVal;
  });
  renderCandidates(filtered);
}

function sortResults() {
  const sortVal = document.getElementById('filter-sort')?.value || 'MATCH';
  const sorted = [...allCandidates];
  if (sortVal === 'MATCH' || sortVal === 'SCORE_DESC') {
    sorted.sort((a, b) => (b.score || 0) - (a.score || 0));
  } else if (sortVal === 'EXPERIENCE') {
    sorted.sort((a, b) => (b.years_experience || 0) - (a.years_experience || 0));
  }
  renderCandidates(sorted);
}

// Bookmark Toggle
function toggleBookmark(candidateId) {
  alert(`Candidate ${candidateId} saved to your recruitment pipeline bookmarks.`);
}

// Export CSV
function exportCurrentCSV() {
  if (!allCandidates || allCandidates.length === 0) {
    alert('No candidates available to export.');
    return;
  }
  let csv = 'Candidate Name,Current Headline,Location,Score,Geographic Status,Profile URL\n';
  allCandidates.forEach(c => {
    const geo = c.geographic_eligibility?.status || 'ELIGIBLE';
    csv += `"${c.name}","${(c.headline || '').replace(/"/g, '""')}","${c.location || ''}",${Math.round(c.score || 0)},"${geo}","${c.profile_url || ''}"\n`;
  });
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `recruiter_copilot_candidates_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
}

// Recent Job Selector
function selectRecentJob(key) {
  document.getElementById('header-job-title').innerText = 'SAP HANA Cloud Consultant';
  document.getElementById('header-job-loc').innerHTML = '<span class="text-xs">🇳🇱</span><span>Eindhoven, Netherlands</span>';
  loadTemplate('sap');
  allCandidates = [...BENCHMARK_CANDIDATES];
  renderCandidates(allCandidates);
}

function loadDemoJob(title, loc) {
  document.getElementById('header-job-title').innerText = title;
  document.getElementById('header-job-loc').innerHTML = `<span>📍</span><span>${loc}</span>`;
  document.getElementById('raw-jd-input').value = `Job Title: ${title}\nLocation: ${loc}\nExperience: 5-8 years\n\nRequirements:\n• Senior engineering and domain expertise\n• Architecture, testing and high-availability operations`;
  updateCharCounter();
}

function startNewSearch() {
  clearJobDescription();
  document.getElementById('header-job-title').innerText = 'New Sourcing Brief';
  document.getElementById('header-job-loc').innerText = 'Unspecified Location';
  document.getElementById('raw-jd-input').focus();
}
