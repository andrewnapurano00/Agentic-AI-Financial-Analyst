"""Opt-in preparation only: production activation remains unavailable."""
import streamlit as st
from langgraphagenticai.monitoring import ACTIVATION_GATES
from langgraphagenticai.monitoring.models import snapshot_model


def render_monitoring_plan(result,credentials=()):
    with st.expander("Monitoring plan · activation unavailable"):
        st.caption("Prepare a disabled plan only for this explicitly saved model portfolio. No background collection, model spending, alerts, trades or portfolio changes are enabled.")
        saved=st.session_state.get('architect_saved',{}).get(result.id)
        consent=st.checkbox("Prepare a disabled plan for this saved portfolio",key='monitor_consent_'+result.id)
        if not saved: st.info("Use Save session snapshot first; unsaved browsing cannot become a monitoring plan.")
        if st.button("Prepare monitoring plan",key='monitor_prepare_'+result.id,disabled=not bool(saved and consent)):
            try:
                model=snapshot_model(saved,credentials=credentials)
                plans=st.session_state.setdefault('monitoring_disabled_plans',{})
                if len(plans)>=6 and model.fingerprint not in plans:
                    st.warning("Six disabled plans are already retained in this session.")
                else:
                    plans[model.fingerprint]=model
                    st.session_state['monitor_plan_active_'+result.id]=model.fingerprint
                    st.success("Disabled plan prepared. No monitoring has started.")
            except (ValueError,TypeError,KeyError,StopIteration):
                st.warning("This saved portfolio cannot form a consistent monitoring baseline. Original results remain available.")
        plans=st.session_state.get('monitoring_disabled_plans',{})
        candidates={key:plan for key,plan in plans.items() if plan.result_id==result.id}
        plan=None
        if candidates:
            selected=st.selectbox('Disabled monitoring plan',list(candidates),key='monitor_plan_active_'+result.id,
                                  format_func=lambda key:candidates[key].created_at+' · '+key[:12])
            plan=candidates[selected]
        if plan:
            st.json({'status':'disabled','fingerprint':plan.fingerprint,'baseline':plan.model_dump(),
                     'supported_rehearsal':'price-driven top-level concentration drift with verified same-share-basis evidence',
                     'unavailable_events':['earnings','estimate revisions','ETF constituent exposures'],
                     'model_budget_usd':0,'execution':'unavailable'},expanded=False)
        st.button("Enable monitoring",key='monitor_enable_'+result.id,disabled=True)
        for gate in ACTIVATION_GATES: st.caption(gate)
        st.caption("The durable queue is an offline rehearsal foundation, not an authenticated job service. Approval records do not apply simulated changes; brokerage execution is unavailable.")
