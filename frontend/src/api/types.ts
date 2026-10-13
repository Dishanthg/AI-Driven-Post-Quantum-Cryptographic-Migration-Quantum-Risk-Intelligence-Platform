// Mirrors backend/app/api/schemas.py exactly. Do not add fields the backend
// doesn't send - every value rendered by this app must trace to a real
// response field, never a client-invented one.

export interface Algorithm {
  id: string
  name: string
  family: string
  role: string
  classification: string
  security_basis: string
  quantum_vulnerability: string
  standard_ref: string
  library_source: string
  typical_key_size_bits: number
}

export interface ThreatEntry {
  algorithm_family: string
  attack_model: string
  classical_security_assumption: string
  theoretical_quantum_complexity: string
  practical_constraint: string
  current_limitation: string
  plain_language_explanation: string
}

export interface Application {
  id: string
  name: string
  business_unit: string
  business_importance: string
  description: string
}

export interface Certificate {
  id: string
  subject: string
  issuer: string
  not_before: string
  not_after: string
  signature_algorithm_id: string
}

export interface Asset {
  id: string
  application_id: string
  hostname: string
  environment: string
  usage_type: string
  protocol: string
  algorithm_id: string
  key_size_bits: number
  data_sensitivity: string
  data_lifetime_years: number
  asset_criticality: string
  internet_exposure: boolean
  migration_complexity: string
  current_status: string
  discovery_source: string
  last_seen: string
}

export interface AssetDetail extends Asset {
  application: Application
  certificates: Certificate[]
}

export interface ScanResult {
  source_dir: string
  files_scanned: number
  applications_seen: number
  assets_created: number
  assets_updated: number
  errors: string[]
}

export interface RiskFactor {
  feature_name: string
  contribution: number
}

export interface RiskAssessment {
  id: string
  asset_id: string
  method: string
  model_version_id: string | null
  risk_score: number
  priority: string
  confidence: number
  created_at: string
  factors: RiskFactor[]
}

export interface PQCRecommendation {
  id: string
  asset_id: string
  risk_assessment_id: string
  strategy: string
  target_algorithm_id: string | null
  rationale: string
  assumptions: string
  tradeoffs: string
}

export interface MigrationStep {
  id: string
  sequence: number
  stage: string
  description: string
  status: string
  simulated_result_json: Record<string, unknown>
}

export interface MigrationPlan {
  id: string
  asset_id: string
  recommendation_id: string
  current_algorithm_id: string
  target_algorithm_id: string
  priority: string
  estimated_effort_hours: number
  performance_impact_json: Record<string, unknown>
  compatibility_risk: string
  rollback_strategy: string
  verification_criteria: string
  owner: string
  status: string
  steps: MigrationStep[]
}

export interface BenchmarkSummary {
  operation: string
  provider_key: string
  iterations: number
  mean_ms: number
  median_ms: number
  stdev_ms: number
  p95_ms: number
  p99_ms: number
  ci95_low_ms: number
  ci95_high_ms: number
  public_key_bytes: number | null
  ciphertext_or_signature_bytes: number | null
  environment: Record<string, unknown>
}

export interface GroverRunResult {
  n_qubits: number
  search_space_size: number
  marked_states: string[]
  iterations_used: number
  iterations_theoretical_optimal: number
  shots: number
  circuit_depth: number
  counts: Record<string, number>
  success_probability: number
  classical_expected_queries: number
  quantum_expected_queries: number
  runtime_seconds: number
  backend: string
  data_label: string
  hardware_type: string
  caveat: string
}

export interface ShorRunResult {
  N: number
  a: number
  target_qubits: number
  counting_qubits: number
  total_qubits: number
  circuit_depth: number
  shots: number
  measured_phase_bitstrings: Record<string, number>
  period_found: number | null
  factors: [number, number] | null
  success: boolean
  runtime_seconds: number
  classical_shortcut_used: boolean
  backend: string
  data_label: string
  hardware_type: string
  caveat: string
}

export interface QuantumRunSummary {
  id: string
  backend: string
  qubits: number
  circuit_depth: number
  shots: number
  runtime_seconds: number
  success_probability: number
  is_real_hardware: boolean
  created_at: string
}

export interface ModelVersion {
  id: string
  version: string
  algorithm: string
  dataset_ref: string
  random_seed: number
  metrics_json: Record<string, unknown>
  artifact_path: string
  is_active: boolean
}

export interface AuditLog {
  id: string
  timestamp: string
  actor: string
  action: string
  target_type: string
  target_id: string
  before_json: Record<string, unknown>
  after_json: Record<string, unknown>
}

export interface InventoryOverview {
  total_assets: number
  legacy_public_key_assets: number
  high_risk_assets: number
  critical_risk_assets: number
  pqc_migrated_assets: number
  hybrid_assets: number
  algorithm_distribution: Record<string, number>
  priority_distribution: Record<string, number>
  migration_status_distribution: Record<string, number>
}

export interface HealthStatus {
  status: string
  database: string
  risk_model_artifacts: string
  app_name: string
  environment: string
}

export interface ExperimentSummary {
  experiment_id: string
  hypothesis: string
  description: string
  run_count: number
}
