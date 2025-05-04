class okr:
    def __init__(self, team, title, description, search_queries: list = []):
        self.team = team
        self.title = title
        self.description = description
        self.search_queries = search_queries
    def __str__(self):
        return f"OKR Summary:\n  Team: {self.team}\n  Title: {self.title}\n  Description: {self.description}"
    
okrs_2025_q2 = [
    okr(
        team="ONBRD",
        title="6.10 - 100% of our key services have SLAs and SLA adherence measurement",
        description="This project focuses on improving the reliability of metadata verification (MDV) by ensuring full metric coverage for all possible failure scenarios, supporting better SLA tracking and adherence across key services.",
        search_queries=["MDV Hardening SLA coverage"]
    ),
    okr(
        team="INGEST",
        title="14.20 - Support 5x number of data streams at 5 minute intervals while meeting SLAs",
        description="Upgrade systems to handle the current asset load and 5x the number of data streams at 5-minute intervals, ensuring system scalability and SLA adherence under increased data throughput.",
        search_queries=["System upgrade data stream SLA"]
    ),
    okr(
        team="ONBRD",
        title="18.10 - Move Resi Reporting maturity from a 2 to a 3 on Initiative scorecard by end of Q1 2026",
        description="Engineering work on VEE backend services to elevate Resi Reporting maturity, aligning with Client Data & Visibility initiative goals.",
        search_queries=["Resi Reporting VEE backend"]
    ),
    okr(
        team="CLIENT",
        title="20.30 - Increase Resi & CML Reporting maturity by 0.5 points by EOQ2",
        description="Centralize and standardize the delivery of field reporting to improve the maturity of Resi and CML reporting by 0.5 points.",
        search_queries=["Field reporting standardization"]
    ),
    okr(
        team="CLIENT",
        title="20.60 - Client & Customer Engagement takes over all reporting responsibilities",
        description="Transition all reporting responsibilities to the Client & Customer Engagement team, improving accountability and streamlining processes.",
        search_queries=["Client Engagement reporting transition"]
    ),
    okr(
        team="INGEST",
        title="25.20 - Maintain labor cost associated with MV, PVT, and proactive monitoring (telemetry transition)",
        description="Transition to using telemetry and production_meter to manage proactive monitoring labor cost for Enphase systems.",
        search_queries=["Enphase telemetry labor cost"]
    ),
    okr(
        team="INGEST",
        title="25.30 - Maintain labor cost: Tesla and Q-Cells alerts independent of PV detectors",
        description="Surface Tesla and Q-Cells battery alerts independent of PV detectors to sustain monitoring labor costs; follow-on to native alerts project.",
        search_queries=["Tesla Q-Cells battery alert"]
    ),
    okr(
        team="INGEST",
        title="25.12 - QCells Universal API Upgrade",
        description="Upgrade QCells to a Universal API, ensuring continued compatibility and cost-effective monitoring; delays could impact client relationships.",
        search_queries=["QCells API upgrade"]
    ),
    okr(
        team="CLIENT",
        title="27.20 - Clear customer communication on noncom email outreach",
        description="Ensure customer communication clearly articulates required actions and expectations during noncompliant email outreach campaigns.",
        search_queries=["Customer outreach noncom email"]
    ),
    okr(
        team="INGEST",
        title="31.60 - Improve pipeline coverage ratio from 1.9 to 2.3 via GPM integration",
        description="Integrate Green Power Monitor to expand commercial opportunities and improve pipeline coverage ratio from 1.9 to 2.3.",
        search_queries=["GPM integration pipeline ratio"]
    ),
    okr(
        team="CLIENT",
        title="35.30 - Turn off Home Owner Portal Access",
        description="Shut down the Home Owner Portal to streamline operations and enhance data security, supporting operational excellence goals.",
        search_queries=["Home Owner Portal shutdown"]
    ),


]
okrs_2025_q1 = [

    okr(
        team="ONBRD",
        title="Sigma Visibility into Key Metrics",
        description="Provide the company with visibility into key metrics for onboarding, data acquisition, and client portal through Sigma or the appropriate analytics tool(s)."
    ),
    okr(
        team="ONBRD",
        title="KR 62: Residential Operations is launched on SalesForce Service Cloud",
        description="""
The Onboarding team's responsibility for this project is to ensure that during onboarding the assets are properly synced to service cloud
without error.  We need to make sure that the Contacts are also synced when onboarding so that Salesforce has a representation of the 
asset's key contacts. some key phrases that might be linked to this project are "Asset Sync", "Salesforce Service", 
"contact Sync", "Channel Partner assets", "Hybrid Clients" and "Ticket Service". There has to be special consideration paid to Channel Partner assets and Hybrid Clients
"""
    ),
    okr(
        team="CLIENT",
        title="KR 11: Clients Can see Cases and work order data and customer communication in the client portal",
        description="""
Our clients used to have access to Zendesk but as we transition to Salesforce Service Cloud we want them to start 
logging into our client portal to see the on going work and the communications on each ticket (Cases and Workorders).
The Client Portal is a user interface for our clients to log into and review their Solar data. 

        """
    ),
    okr(
        team="CLIENT",
        title="KR 4: User Engagement metrics for Client Portal",
        description="""
- We have a centralized system for reviewing user engagement metrics. 
- They will achieve the desires to understand customer engagement
- Review of User Engagement Analytic Tool Capabilities
- Same Metrics system across Resolv & Client Portal
- Grading Criteria: Dashboard viewable by product that gives insight into at least 1 aspect of customer engagement through the portals
"""
    ),
    okr(
        team="INGEST",
        title="KR 29: Ingest power, voltage, and current (PVC) for Greenbyte and Also Energy assets",
        description="""1. Also Energy and GreenByte PVC is available as accessable data in Timeseries Database
2. No greater than 1 hour delay from ingestion to availability
3. Data is in a normalized format across all providers"""
    ),
    okr(
        team="INGEST",
        title="Ingest battery heuristic data for Enphase DAS",
        description="""1. At least 3 streams of site-level battery data (charge, discharge, and SOC) are landed in Databricks and ready for analysis for Enphase
2. Data delay is < 1 hour
3. Data is aggregated to hourly and daily data."""
    ),
]
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
