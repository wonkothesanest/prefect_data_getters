# This file makes the flows directory a proper Python package
from src.management_ai.flows.okr_report_flow import okr_report_flow
from src.management_ai.flows.people_report_flow import people_report_flow
from src.management_ai.flows.rag_report_flow import rag_report_flow
from src.management_ai.flows.secretary_report_flow import secretary_report_flow

__all__ = [
    'okr_report_flow',
    'people_report_flow',
    'rag_report_flow',
    'secretary_report_flow',
]