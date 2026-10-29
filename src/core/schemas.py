from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class RoleFamily(str, Enum):
    SOFTWARE_ENGINEERING = "software_engineering"
    EMBEDDED_FIRMWARE = "embedded_firmware"
    HARDWARE_ELECTRONICS = "hardware_electronics"
    DATA_SCIENCE_ML = "data_science_ml"
    DATA_ENGINEERING = "data_engineering"
    DEVOPS_SRE_CLOUD = "devops_sre_cloud"
    CYBERSECURITY = "cybersecurity"
    UX_UI_DESIGN = "ux_ui_design"
    PRODUCT_MANAGEMENT = "product_management"
    QA_TEST_ENGINEERING = "qa_test_engineering"
    SAP_TECHNICAL_CONSULTING = "sap_technical_consulting"
    GENERIC_OTHER = "generic_other"


class RequirementType(str, Enum):
    TECHNICAL_SKILL = "technical_skill"
    DOMAIN_KNOWLEDGE = "domain_knowledge"
    EXPERIENCE_YEARS = "experience_years"
    LANGUAGE = "language"
    METHODOLOGY = "methodology"
    EDUCATION = "education"
    SOFT_SKILL = "soft_skill"
    OTHER = "other"


class RequirementImportance(str, Enum):
    MANDATORY = "mandatory"
    PREFERRED = "preferred"


class EvidenceClassification(str, Enum):
    EXPLICIT_MATCH = "explicit_match"
    PARTIAL_MATCH = "partial_match"
    EXPLICIT_MISMATCH = "explicit_mismatch"
    UNKNOWN = "unknown"
    CONTRADICTORY = "contradictory"


class EligibilityStatus(str, Enum):
    MEETS_VERIFIED_REQUIREMENTS = "meets_verified_requirements"
    DOES_NOT_MEET_VERIFIED_REQUIREMENT = "does_not_meet_verified_requirement"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


class JobStateEnum(str, Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    SEARCHING = "searching"
    EVALUATING = "evaluating"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


# --- Requirement E & F: Geographic Verification Models ---
class LocationEvidenceCategory(str, Enum):
    CURRENT_RESIDENCE = "CURRENT_RESIDENCE"
    CURRENT_WORK_LOCATION = "CURRENT_WORK_LOCATION"
    SELF_REPORTED_LOCATION = "SELF_REPORTED_LOCATION"
    VERIFIED_CURRENT_LOCATION = "VERIFIED_CURRENT_LOCATION"
    CLIENT_PROJECT_LOCATION = "CLIENT_PROJECT_LOCATION"
    HISTORICAL_RESIDENCE = "HISTORICAL_RESIDENCE"
    HISTORICAL_EMPLOYMENT_LOCATION = "HISTORICAL_EMPLOYMENT_LOCATION"
    EMPLOYER_OFFICE_LOCATION = "EMPLOYER_OFFICE_LOCATION"
    RELOCATION_REPORTED = "RELOCATION_REPORTED"
    WORK_AUTHORIZATION_REPORTED = "WORK_AUTHORIZATION_REPORTED"
    WORK_AUTHORIZATION_VERIFIED = "WORK_AUTHORIZATION_VERIFIED"
    AMBIGUOUS_LOCATION = "AMBIGUOUS_LOCATION"
    NO_LOCATION_EVIDENCE = "NO_LOCATION_EVIDENCE"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    SELF_REPORTED = "SELF_REPORTED"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"
    CONFLICTING = "CONFLICTING"
    UNKNOWN = "UNKNOWN"


class GeographicEligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    MISMATCH = "MISMATCH"
    UNKNOWN = "UNKNOWN"


class MatchStatus(str, Enum):
    EXPLICIT_MATCH = "EXPLICIT_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    LOCATION_MISMATCH = "LOCATION_MISMATCH"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class SkillEvidenceState(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    MENTIONED = "MENTIONED"
    SUPPORTED_BY_PROJECT_EVIDENCE = "SUPPORTED_BY_PROJECT_EVIDENCE"
    STRONGLY_SUPPORTED = "STRONGLY_SUPPORTED"
    VERIFIED_ABSENT = "VERIFIED_ABSENT"
    UNKNOWN = "UNKNOWN"


class LocationRequirementSchema(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    work_mode: str = "HYBRID"  # ON_SITE, HYBRID, REMOTE
    relocation_allowed: bool = False
    commuting_radius_km: Optional[int] = None


class CandidateLocationModel(BaseModel):
    value: Optional[str] = None
    evidence_type: LocationEvidenceCategory = LocationEvidenceCategory.NO_LOCATION_EVIDENCE
    verification_status: VerificationStatus = VerificationStatus.UNKNOWN
    source_url: Optional[str] = None
    observed_at: Optional[str] = None
    supporting_quotation: Optional[str] = None
    explanation: Optional[str] = None


class GeographicEligibilityModel(BaseModel):
    status: GeographicEligibilityStatus = GeographicEligibilityStatus.UNKNOWN
    reason: Optional[str] = None
    supporting_evidence: List[str] = Field(default_factory=list)


class RequirementSchema(BaseModel):
    requirement_id: str
    normalized_name: str
    raw_text: str = ""
    requirement_type: RequirementType = RequirementType.TECHNICAL_SKILL
    importance: RequirementImportance = RequirementImportance.MANDATORY
    evidence_needed: str = ""
    acceptable_equivalents: List[str] = Field(default_factory=list)
    weight: float = 1.0


class JobDescriptionSchema(BaseModel):
    role_title: str
    alternative_titles: List[str] = Field(default_factory=list)
    role_family: RoleFamily = RoleFamily.GENERIC_OTHER
    seniority: Optional[str] = None
    locations: List[str] = Field(default_factory=list)
    location_spec: Optional[LocationRequirementSchema] = None
    work_arrangement: Optional[str] = None  # Remote, Hybrid, On-site
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    mandatory_requirements: List[RequirementSchema] = Field(default_factory=list)
    preferred_requirements: List[RequirementSchema] = Field(default_factory=list)
    explicit_exclusions: List[str] = Field(default_factory=list)
    ambiguous_requirements: List[str] = Field(default_factory=list)
    clarification_questions: List[str] = Field(default_factory=list)
    search_languages: List[str] = Field(default_factory=lambda: ["en", "nl"])
    raw_jd_text: str = ""


class SearchResultSchema(BaseModel):
    title: str
    url: str
    snippet: str = ""
    provider: str = "serpapi"
    query_used: str = ""
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateEvidence(BaseModel):
    requirement_id: str
    classification: EvidenceClassification = EvidenceClassification.UNKNOWN
    supporting_text: str = ""
    is_direct_statement: bool = True
    confidence: float = 1.0
    evidence_state: SkillEvidenceState = SkillEvidenceState.UNKNOWN
    quotation: Optional[str] = None


class CandidateSchema(BaseModel):
    candidate_id: str
    name: Optional[str] = None
    profile_url: str
    canonical_profile_url: Optional[str] = None
    headline: Optional[str] = None
    current_role: Optional[str] = None
    location: Optional[str] = None
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    source_snippets: List[str] = Field(default_factory=list)
    source_provider: str = "serpapi"
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Geographic Verification (Requirements E, F, K)
    current_location: CandidateLocationModel = Field(default_factory=CandidateLocationModel)
    geographic_eligibility: GeographicEligibilityModel = Field(default_factory=GeographicEligibilityModel)
    
    # ATS Technical Scoring Components (Requirements G, H, I, J)
    evidence_by_requirement: Dict[str, CandidateEvidence] = Field(default_factory=dict)
    experience_years_stated: Optional[float] = None
    experience_years_estimated: Optional[float] = None
    experience_basis: str = "unknown"
    experience_years: Optional[float] = None
    
    skill_score: Optional[float] = None
    seniority_score: Optional[float] = None
    role_alignment_score: Optional[float] = None
    evidence_quality_score: Optional[float] = None
    overall_score: Optional[float] = None
    mandatory_skill_coverage: Optional[float] = None
    
    # Backwards compatibility and match states
    preliminary_match_score: float = 0.0
    eligibility: EligibilityStatus = EligibilityStatus.INSUFFICIENT_EVIDENCE
    match_status: MatchStatus = MatchStatus.INSUFFICIENT_EVIDENCE
    evidence_completeness: float = 0.0  # 0.0 to 1.0
    fit_summary: str = ""
    
    # Audit and Provenance
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    missing_requirements: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    conflicting_evidence: List[str] = Field(default_factory=list)
    review_flags: List[str] = Field(default_factory=list)
    last_observed_at: Optional[str] = None
    review_status: str = "PENDING"
