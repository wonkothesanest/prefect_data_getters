OKR_SECTION_EXAMPLE = """
"""
class okr:
    def __init__(self, team, title, description):
        self.team = team
        self.title = title
        self.description = description
    def __str__(self):
        return f"OKR Summary:\n  Team: {self.team}\n  Title: {self.title}\n  Description: {self.description}"

okrs_2024_q4 = [
    # Data Acquisition Team (INGEST)
    okr(
        team="INGEST",
        title="Infrastructure KR 1.1: Sigma Visibility into Key Metrics",
        description="Provide the company with visibility into key metrics for onboarding, data acquisition, and client portal through Sigma or the appropriate analytics tool(s)."
    ),
    okr(
        team="INGEST",
        title="Residential KR (Carryover): Metadata Verification Extraction",
        description="Extract and verify metadata for photovoltaic (PV) assets to enhance data accuracy and quality."
    ),
    okr(
        team="INGEST",
        title="Infrastructure KR 1.8: Business Domain Definition",
        description="Define and document the business domain to provide clarity and understanding across teams."
    ),
    okr(
        team="INGEST",
        title="Residential KR 2.1: Ingesting Tesla API Data",
        description="Enhance support for Qcells, EverBright, and all TPO clients by ingesting PV, native alerts, and battery data from the Tesla API."
    ),
    okr(
        team="INGEST",
        title="Infrastructure KR 1.9: Data Quality Awareness Checks",
        description="Increase trust in company data by detecting discrepancies between our data and OEM sources."
    ),
    okr(
        team="INGEST",
        title="Infrastructure KR 1.10x: Establish Data Streams for Issue Detection",
        description="Quickly detect issues on commercial assets by establishing power, voltage, and current data streams from four OEMs."
    ),
    
    # Onboarding / Feature Team (ONBRD)
    okr(
        team="ONBRD",
        title="Communication BD Service I8.9",
        description="Implement the Communication Business Development (BD) Service."
    ),
    okr(
        team="ONBRD",
        title="Qcells Off of HoPo R6.3",
        description="Transition Qcells off of the Home Portal (HoPo) platform."
    ),
    okr(
        team="ONBRD",
        title="TPO Documents R6.5",
        description="Develop and update Third-Party Owner (TPO) documents."
    ),
    okr(
        team="ONBRD",
        title="EB Change in Emails R6.4",
        description="Implement changes in email communications for EverBright clients."
    ),
    okr(
        team="ONBRD",
        title="Residential KR 6.2: Market Assessment & Strategy",
        description="Document the market requirements and customer journey for a unified customer experience, potentially including data-informed FAQs, troubleshooting guides, and service tracking."
    ),
    okr(
        team="ONBRD",
        title="Residential KR 6.3: Transition Qcells/EnFin Welcome Experience",
        description="Shift the welcome experience for Qcells/EnFin customers to their own portal and remove access to the Omnidian Customer Portal."
    ),
    okr(
        team="ONBRD",
        title="Residential KR 1.1: View CT Issues in PVT Task List",
        description="Allow the Operations team to view Current Transformer (CT) issues identified during Post-Verification Testing (PVT) in their task list."
    ),
    okr(
        team="ONBRD",
        title="Residential KR 2.3: Enhance Issues Platform",
        description="Present all alerts requiring human diagnosis in a prioritized list to meet client Service Level Agreements."
    ),
    
    # Client Team (CLIENT)
    okr(
        team="CLIENT",
        title="Commercial Dispatch Approvals C4.1",
        description="Implement dispatch approvals for commercial clients within the client portal."
    ),
    okr(
        team="CLIENT",
        title="User Engagement Metrics I1.8",
        description="Gain a data-backed understanding of how the Operations Portal and Client Portal are being used by clients."
    ),
    okr(
        team="CLIENT",
        title="Improving Performance of Commercial Pages I4.3",
        description="Enhance the performance of commercial pages in the client portal to ensure a smooth and responsive user experience."
    ),
    okr(
        team="CLIENT",
        title="Client Portal Multi-Pod Deployment I5.11 (Tech Debt)",
        description="Deploy the client portal across multiple pods to improve scalability, reliability, and performance."
    ),
    okr(
        team="CLIENT",
        title="Residential KR 3.1: Enhance Client Portal for EverBright",
        description="Enable EverBright to view Cases and Work Orders instead of tickets in the client portal."
    ),
    okr(
        team="CLIENT",
        title="Residential KR 3.2: Automate NCSR Approvals",
        description="Allow EverBright to review and approve Non-Conformance Service Requests (NCSRs) directly in the client portal."
    ),
    okr(
        team="CLIENT",
        title="Residential KR 3.7: Launch Residential Client Portal for EverBright",
        description="Successfully deploy the Residential Client Portal, providing EverBright with real-time access to support cases and service activities."
    )
]

OKR_REPORT_DESCRIPTION = """
"""