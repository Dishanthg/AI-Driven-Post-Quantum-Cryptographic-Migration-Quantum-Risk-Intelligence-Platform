import { Card } from '../components/common'

export function AgilityDemoPage() {
  return (
    <div className="page">
      <h1>Cryptographic Agility Demo</h1>
      <div className="state-box state-info">
        This demo is a CLI artifact (<code>backend/agility_demo/</code>), not an API-exposed service, so this page
        documents what it actually does rather than fabricating a live control here.
      </div>

      <Card title="What it demonstrates">
        <p>
          <code>agility_demo/secure_api.py</code> is a minimal service (issue an identity, sign a request, verify a
          request) whose business logic depends only on <code>app.crypto.providers.CryptoProvider</code> — never a
          named algorithm library directly. <code>config.yaml</code> names the active algorithm via a single{' '}
          <code>provider_key</code> field.
        </p>
        <p>Run the same file through three algorithm generations with zero business-logic changes:</p>
        <pre className="json-block">{`python -m agility_demo.secure_api                 # ECDSA-P256 (config.yaml default)
python -c "from agility_demo.secure_api import set_active_provider; set_active_provider('ml_dsa_65')"
python -m agility_demo.secure_api                 # ML-DSA-65 — same file, zero code changes
python -c "from agility_demo.secure_api import set_active_provider; set_active_provider('slh_dsa_sha2_128f')"
python -m agility_demo.secure_api                 # SLH-DSA-SHA2-128f — still zero code changes`}</pre>
      </Card>

      <Card title="Comparison artifact">
        <p>
          <code>agility_demo/tightly_coupled_baseline.py</code> is a comparison-only file (never imported by the real
          service) showing what this logic looks like without the <code>CryptoProvider</code> abstraction — four
          separate hard-wired algorithm references that would each need editing to migrate.
        </p>
        <p>
          Experiment 6 (<code>research/experiments/exp6_crypto_agility.py</code>) runs both versions through the same
          swap sequence and records the measured comparison (files touched, lines changed, diff size) — see{' '}
          <code>research/tables/exp6_crypto_agility.md</code> once that experiment has been run.
        </p>
      </Card>
    </div>
  )
}
