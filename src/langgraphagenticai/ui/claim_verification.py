"""Read-only verification over original saved reports; no paid/provider actions."""
import json
import streamlit as st
from langgraphagenticai.analysis.claim_verification import audit_report
from langgraphagenticai.analysis.investment_brief import _safe_packet


def render_claim_audit(saved, *, credentials=(), reference_time=None):
    try:
        audit = _safe_packet(audit_report(saved, reference_time=reference_time), credentials)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        st.warning("Numerical claim audit unavailable for malformed saved evidence. Original report and downloads remain available; no claims are certified.")
        return
    coverage = audit["coverage"]; reconciliation = audit["reconciliation"]; freshness = audit["freshness"]
    st.markdown("#### Numerical claim checks")
    st.caption(f"Coverage: {coverage['checked_numeric_statements']} of {coverage['extracted_statements']} extracted numeric lines matched. "
               f"Freshness: {freshness['available_observations']} eligible / {freshness['stale_observations']} stale / {freshness['unavailable_observations']} unavailable observations. "
               f"Reconciliation: {reconciliation['contradictions']} contradictions / {reconciliation['unverifiable']} unverifiable lines.")
    st.caption("Interpretation: unassessed. Source facts, calculated amounts, assumptions and future targets are distinct. No overall confidence score or thesis certification.")
    if reconciliation["contradictions"]:
        st.warning("Unresolved numerical contradictions in the saved report. Review the findings and supporting inputs; original text is retained.")
    if not coverage["extracted_statements"]:
        st.info("No supported numeric lines extracted; this does not establish that the report is verified.")
    if coverage["text_truncated"] or coverage["omitted_numeric_lines"]:
        st.warning("Claim extraction reached its bounded limit. Omitted text is not verified; review the full original report.")
    with st.expander("Claim findings, evidence and verification limits"):
        st.caption("Local checks against saved evidence only. Ambiguous prose and unsupported metrics remain unverified. Original citations and reports are unchanged.")
        if audit["findings"]:
            st.dataframe([{"Claim":f["claim"]["text"],"Status":f["label"],"Severity":f["severity"],
                           "Finding":f["code"],"Expected amount":f["expected"],"Remediation":f["remediation"]}
                          for f in audit["findings"]], hide_index=True, width="stretch")
        for note in audit["limitations"]+audit["source_gaps"]:
            st.caption(note)
        st.caption("Evaluated: "+audit["reference_time"]+". Retrieval and fiscal/quote dates remain separate in the source records.")
        st.json(audit)
        st.download_button("Claim verification JSON", json.dumps(audit,allow_nan=False,ensure_ascii=False).encode(),
                           "claim_verification.json", "application/json", key="claim_audit_"+audit["report_sha256"][:20]+str(audit["run_id"]))
