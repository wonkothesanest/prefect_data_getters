from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains.llm import LLMChain
from typing import Dict

from prefect_data_getters.utilities.timing import time_it

# ────────────────────────── CONSTANT LOOK-UP LISTS ───────────────────────── #

CATEGORIES = ["Account Issues","Team","Collaboration","Interview","Personal Info",
              "Job Opportunity","Project","Task","Request","Onboarding","Kickoff",
              "Meeting","Technical Issue","Engineering","System Alert",
              "System Update","Error Report","Announcement","Info Sharing",
              "Discussion","Reminder","Survey","Marketing","Event","LinkedIn",
              "Industry News","Security","IT Support","Spam","Unsolicited"]

TEAMS      = ["Client Team","OCI","Data Acquisition Team","Onboarding Team",
              "Accounts Payable","Backend Team","Capital Markets","Client Success",
              "Operations","Data Engineering","Data Science","Engineering",
              "Executive Team","HR","Legal","Product Team","QA","Sales",
              "Security","Software Engineering"]

PROJECTS   = ["2025 Roadmap","BUSA Onboarding","Client Engagement","Commercial Ops",
              "Company Initiatives","Data Acquisition","Engineering Roadmap",
              "Hyperion","Metadata Verification","Onboarding","PVT",
              "Ops Efficiency & TTR","Client Portal","Customer Portal","Reporting",
              "VEE Ledger","Residential Ops","Service Cloud Launch","SolCharged Event",
              "VEE Project","Q1","Q2","Q3","Q4"]

SYSTEMS    = ["APIs","Asana","Atlassian","Bitbucket","Confluence","Databricks",
              "Enphase","EverBright","Google Analytics","Green Power Monitor",
              "Jira","LastPass","Okta","Resolv","Salesforce","Service Cloud",
              "Sigma","Slack","Slab","Zendesk"]


class EmailExtractor:
    def __init__(self, model_name: str = "mistral-nemo:latest", temperature: float = 0.7):
        self.llm = ChatOllama(model=model_name, temperature=temperature)
        
        # Build LangChain chains
        self.summarization_chain = self._build_summary_chain()
        self.extraction_chain = self._build_extraction_chain()

    def _build_summary_chain(self) -> LLMChain:
        sys_msg = """
You are an AI assistant responsible for reviewing incoming emails for me, Dusty Hagstrom, an Engineering Manager. \
The intent of this categorization and summary
is to help me prioritize my tasks and manage my time effectively. I need to be able to quickly filter out emails that
come in as unprompted requests, spam and other irrelevant emails. I need to know about emails that are important to me, my team and my company. 
Direct emails and ones where I have a specific ask by a client or someone in the company are the most important.

For each email, please provide structured information in the following format. When given a list of options only pick from that list. If any options are None or not applicable, just leave them blank.

Categories: Pick only from this list: {CATEGORIES}
Mentioned Teams: Pick only from this list: {TEAMS}
Mentioned Projects: Pick only from this list: {PROJECTS}
Mentioned Systems: Pick only from this list: {SYSTEMS}
Summary: [Concise 1-2 sentence summary of the email topic]
Action Items or Requests: [Bullet points describing what is being asked, tasks required, or follow-ups needed, be specific so that it is understandable without the full email]
Deadlines or Dates: [List explicit deadlines or scheduled dates mentioned]
Attachments Summary: [If any; e.g. “Excel with monthly metrics”]
Reason for Importance (or Not): [1 paragraph explaining why Dusty should prioritize or de-prioritize]
Is Important: [true or false - whether it needs attention by Dusty and is considered important]
Next Steps: [If any - e.g. respond, delegate, set up meeting, etc.]
Notes for Memory: [Any relevant context or reference to older threads, status updates, or new metrics that are valuable to remember, be specific so that it is understandable without the full email context]

Example output 
Categories: Collaboration, Project
Mentioned Teams: [Data Engineering,Onboarding Team,Product Team]
Mentioned Projects: [Commercial Ops, VEE Project] 
Mentioned Systems: [Asana, Jira]
Summary: John is proposing a planning meeting to finalize the Phase 2 rollout timeline.
Action Items or Requests:
 - Dusty to confirm availability for Thursday afternoon for the phase 2 rollout timeline.
 - Provide input on the new data ingestion metrics for the phase 2 project by next week.
Deadlines or Dates:
 - Next Thursday (proposed meeting time)
 - Next week (feedback due)
Attachments Summary: []
Reason for Importance:
 This email directly impacts the Phase 2 rollout schedule for the Client Portal, which falls under Dusty’s responsibilities for ensuring data accuracy and timely deployment. Without Dusty’s input, the team risks missing critical integration milestones and stakeholder expectations.
Is Important: true
Next Steps:
 - Dusty should respond with availability.
 - Review the data ingestion metrics John provided in the previous email thread.
Notes for Memory:
 - This meeting is a follow-up to the March 30 conversation regarding Phase 2 of project Orca scope expansion.
 """
        sys_prompt = SystemMessagePromptTemplate.from_template(sys_msg)
        prompt = HumanMessagePromptTemplate.from_template("""
Below is the Email content you need to review and process.

To: {to}
From: {from_}
Subject: {subject}
Email Content:
{text}


""")
        return LLMChain(llm=self.llm, prompt=ChatPromptTemplate.from_messages([sys_prompt, prompt]))
    

    def _build_output_parser(self) -> StructuredOutputParser:
        response_schemas = [
            ResponseSchema(name="summary", description="Summarize the email in two sentences or less. Be concise."),
            ResponseSchema(name="categories", description="List of relevant labels (e.g., Project Updates, Client Communication).", type="array", items={"type": "string"}),
            ResponseSchema(name="is_important", description="Whether the email is important to Dusty.", type="boolean"),
            ResponseSchema(name="is_urgent", description="Whether it needs a timely response.", type="boolean"),
            ResponseSchema(name="action_items", description="List of explicit or implicit action items required.", type="array", items={"type": "string"}),
            ResponseSchema(name="deadlines_or_dates", description="Mentioned dates or time-sensitive references.", type="array", items={"type": "string"}),
            ResponseSchema(name="attachments_summary", description="Short description of any attachments."),
            ResponseSchema(name="reason", description="Why Dusty should or should not prioritize this."),
            ResponseSchema(name="notes_for_memory", description="Context or references for memory.", type="array", items={"type": "string"})
        ]
        return StructuredOutputParser.from_response_schemas(response_schemas)
    


    def _build_extraction_chain(self) -> LLMChain:
        prompt = ChatPromptTemplate.from_template("""
You are an expert data extraction algorithm.
Remember that the following are the only acceptable values for categories, teams, projects and systems:
Categories: Pick only from this list: [Account Issues,Team,Collaboration,Interview,Personal Info,Job Opportunity,Project,Task,Request,Onboarding,Kickoff,Meeting,Technical Issue,Engineering,System Alert,System Update,Error Report,Announcement,Info Sharing,Discussion,Reminder,Survey,Marketing,Event,LinkedIn,Industry News,Security,IT Support,Spam,Unsolicited]
Teams: Pick only from this list: [Client Team, OCI, Data Acquisition Team, Onboarding Team, AI Team,Accounts Payable,Asset Management,Backend Team,Capital Markets,Client Success,Customer Support,Data Engineering,Data Science,Engineering,Executive Team,Finance,Frontend Team,HR,Legal,Manufacturing,Onboarding Team,Product Team,QA,Sales,Security,Software Engineering,Support Team]
Projects: Pick only from this list: [2025 Roadmap, BUSA Onboarding, Client Engagement, Clean Power Research, Commercial Ops, Company Initiatives, Data Acquisition, Engineering Roadmap, Hyperion, Metadata Verification, Onboarding, Ops Efficiency & TTR, Residential Ops, Service Cloud Launch, SolCharged Event, VEE Project] 
Systems: Pick only from this list: [API Integration, Asana, Atlassian, Bitbucket, Confluence, Databricks, Enphase, EverBright, Google Analytics, Green Power Monitor, Jira, LastPass, Okta, Resolv, Salesforce, Service Cloud, Sigma, Slack, Slab, Solar Monitoring System, VEE Ledger, Zendesk]

Extract the following fields strictly in JSON format:
(summary, categories, reason, is_important, is_urgent, action_items, deadlines_or_dates, attachments_summary, notes_for_memory, next_steps, teams, projects, systems, )

Text to extract from:
{llm_output}
""")
        return LLMChain(llm=self.llm, prompt=prompt, output_parser= self._build_output_parser())
    @time_it
    def parse_email(self, email: Dict) -> Dict:
        """Run summarization + extraction on a single email."""
        summarized = self.summarization_chain.run(
            to=email["to"],
            from_=email["from"],
            subject=email["subject"],
            text=email["text"],
            CATEGORIES=CATEGORIES,
            TEAMS=TEAMS,        
            PROJECTS=PROJECTS,
            SYSTEMS=SYSTEMS,

        )
        
        extracted_info = self.extraction_chain.run(llm_output=summarized)
        
        return {
            "llm_output": {"text": summarized},
            "analysis": extracted_info
        }



# # ──────────────────────────────── TESTING ──────────────────────────────── #

if __name__ == "__main__":
    sample = {
        "to":      "dusty@omnidian.com",
        "from":    "john@example.com",
        "subject": "Phase-2 Roll-out timeline",
        "date":    "2025-04-22",
        "text": (
            "Hey Dusty,\n\n"
            "Could you meet next Thursday (2025-04-24) at 14:00 to lock the "
            "Phase-2 roll-out? I’ll also need your feedback on the new "
            "ingestion metrics by 2025-05-01.\n\n– John"
        )
    }
    long_sample = {
        "to":      "dusty@omnidian.com",
        "from":    "john@example.com",
        "subject": "Phase-2 Roll-out timeline",
        "date":    "2025-04-22",
        "text": (
            """
We should be able to run some tests this week. All supply timestamps once
we have them.

Thanks,

Burt

On Wed, Apr 23, 2025 at 4:32 AM Liska, John <John.Liska@goeverbright.com>
wrote:

> Thanks Purna.
>
>
>
> Burt: is this something you can help out with this week? Please let me
> know, thanks.
>
>
>
> JPL
>
>
>
>
>
> *From: *Talasila, Purna chand <purnachand.talasila@goeverbright.com>
> *Date: *Tuesday, April 22, 2025 at 11:22 AM
> *To: *Liska, John <John.Liska@goeverbright.com>, Burt Bielicki <
> bbielicki@omnidian.com>, Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com>, Rodriguez, Amauris <
> Amauris.Rodriguez@goeverbright.com>
> *Cc: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Colleen Mooney <cmooney@omnidian.com>, Mike Beenen <mbeenen@omnidian.com>,
> David Kenny <dkenny@omnidian.com>, Karen Schlesinger <
> kschlesinger@omnidian.com>, Dusty Hagstrom <dhagstrom@omnidian.com>
> *Subject: *Re: EverBright <> Omnidian: SFTP testing
>
> Hi John,
>
>
> Sure. We are just waiting for time stamp of testing so we can check if
> traffic coming to our n/w or not. @Rodriguez, Amauris
> <Amauris.Rodriguez@goeverbright.com> can also check on his end.
>
> Thanks
> Purna
>
>
>
> *From: *Liska, John <John.Liska@goeverbright.com>
> *Date: *Tuesday, April 22, 2025 at 6:05 AM
> *To: *Burt Bielicki <bbielicki@omnidian.com>, Talasila, Purna chand <
> purnachand.talasila@goeverbright.com>, Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com>
> *Cc: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Colleen Mooney <cmooney@omnidian.com>, Mike Beenen <mbeenen@omnidian.com>,
> David Kenny <dkenny@omnidian.com>, Karen Schlesinger <
> kschlesinger@omnidian.com>, Dusty Hagstrom <dhagstrom@omnidian.com>,
> Rodriguez, Amauris <Amauris.Rodriguez@goeverbright.com>
> *Subject: *Re: EverBright <> Omnidian: SFTP testing
>
> Good morning. @Talasila, Purna chand
> <purnachand.talasila@goeverbright.com> @Devanapally, Sai pruthvi
> <saipruthvi.devanapally@goeverbright.com> can we resume testing now that
> the Omnidian resource is back from PTO? It would be great if we can resolve
> any outstanding issues this week. Thanks.
>
>
>
> JPL
>
>
> ------------------------------
>
> *From:* Burt Bielicki <bbielicki@omnidian.com>
> *Sent:* Friday, April 11, 2025 6:52:52 PM
> *To:* Talasila, Purna chand <purnachand.talasila@goeverbright.com>
> *Cc:* Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>;
> Colleen Mooney <cmooney@omnidian.com>; Liska, John <
> John.Liska@goeverbright.com>; Mike Beenen <mbeenen@omnidian.com>; David
> Kenny <dkenny@omnidian.com>; Karen Schlesinger <kschlesinger@omnidian.com>;
> Dusty Hagstrom <dhagstrom@omnidian.com>; Rodriguez, Amauris <
> Amauris.Rodriguez@goeverbright.com>
> *Subject:* Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
>
>
> Thank you. The engineer working on this project is out of office until
> April 21.
>
>
>
> On Thu, Apr 10, 2025 at 7:20 AM Talasila, Purna chand <
> purnachand.talasila@goeverbright.com> wrote:
>
> Hello Burt,
>
>
>
> Please find the public key attached. Whenever you finish connecting test,
> please send us the timestamp so we will check if something hits on our end.
>
> Thanks
> Purna
>
> *From: *Burt Bielicki <bbielicki@omnidian.com>
> *Date: *Monday, April 7, 2025 at 6:46 PM
> *To: *Talasila, Purna chand <purnachand.talasila@goeverbright.com>
> *Cc: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Colleen Mooney <cmooney@omnidian.com>, Liska, John <
> John.Liska@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Dusty Hagstrom <dhagstrom@omnidian.com>, Rodriguez, Amauris <
> Amauris.Rodriguez@goeverbright.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Hello,
>
>
>
> We were unable to reach server * eb-hub-ftp.goeverbright.com
> <http://eb-hub-ftp.goeverbright.com/> *from 54.158.141.64. Is it possible
> to send the public key for your host via email?
>
>
>
> Thanks,
>
>
>
> Burt
>
>
>
> On Fri, Apr 4, 2025 at 9:09 AM Talasila, Purna chand <
> purnachand.talasila@goeverbright.com> wrote:
>
> Hello Burt,
>
>
>
> Could you please run following command on the server(we whitelisted) you
> are connected to?
>
>
>
> *telnet eb-hub-ftp.goeverbright.com <http://eb-hub-ftp.goeverbright.com/>
> 22*
>
>
>
> Thanks
> Purna
>
>
>
>
>
>
>
> *From: *Burt Bielicki <bbielicki@omnidian.com>
> *Date: *Thursday, April 3, 2025 at 6:01 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
> *Cc: *Talasila, Purna chand <purnachand.talasila@goeverbright.com>,
> Colleen Mooney <cmooney@omnidian.com>, Liska, John <
> John.Liska@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Dusty Hagstrom <dhagstrom@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> We're unable to get the public key because of connection timeout using:
>
>           ssh-keyscan eb-hub-ftp.goeverbright.com
>
>
>
> Is it possible to allow keyscan publicly, or could you send us the public
> key value for the host?
>
>
>
> Thank you,
>
>
>
> Burt
>
>
>
> On Wed, Mar 26, 2025 at 11:31 AM Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com> wrote:
>
> Thanks for the call, Burt and Colleen. Let us know after testing it from
> your services and please use these SFTP paths
>
>
>
> PROD – FromOmnidian/
>
> Other environments – QA/
>
>
>
> Thanks,
>
> Sai
>
>
>
> *From: *Liska, John <John.Liska@goeverbright.com>
> *Date: *Monday, March 24, 2025 at 12:46 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Dusty Hagstrom <dhagstrom@omnidian.com>, Talasila, Purna chand <
> purnachand.talasila@goeverbright.com>
> *Cc: *bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris
> <Amauris.Rodriguez@goeverbright.com>, Patel, Nishit <
> Nishit.Patel@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Colleen Mooney <cmooney@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> Hi everyone,
>
>
>
> I wanted to circle back on this topic. Is there some time we could meet
> (ideally this week) to talk through / resolve any issues Omnidian is having
> accessing the new SFTP server. Please let me know some dates/times that
> would work on the Omnidian side and I can coordinate the EverBright folks.
> Thanks.
>
>
>
> JPL
>
>
>
> *From: *Liska, John <John.Liska@goeverbright.com>
> *Date: *Thursday, January 30, 2025 at 1:18 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Dusty Hagstrom <dhagstrom@omnidian.com>, Talasila, Purna chand <
> purnachand.talasila@goeverbright.com>
> *Cc: *bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris
> <Amauris.Rodriguez@goeverbright.com>, Patel, Nishit <
> Nishit.Patel@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Colleen Mooney <cmooney@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> Hi Dusty / Burt,
>
>
>
> How about sometime the week of Feb 10th? We would like to have Purna on
> the call and he’s out until Feb 10 unfortunately. Please let me know,
> thanks.
>
>
>
> JPL
>
>
>
> *From: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
> *Date: *Thursday, January 30, 2025 at 11:28 AM
> *To: *Liska, John <John.Liska@goeverbright.com>, Dusty Hagstrom <
> dhagstrom@omnidian.com>, Talasila, Purna chand <
> purnachand.talasila@goeverbright.com>
> *Cc: *bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris
> <Amauris.Rodriguez@goeverbright.com>, Patel, Nishit <
> Nishit.Patel@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Colleen Mooney <cmooney@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> Works for me. We need Purna on the call for this.
>
>
>
> *From: *Liska, John <John.Liska@goeverbright.com>
> *Date: *Thursday, January 30, 2025 at 8:28 AM
> *To: *Dusty Hagstrom <dhagstrom@omnidian.com>, Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com>, Talasila, Purna chand <
> purnachand.talasila@goeverbright.com>
> *Cc: *bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris
> <Amauris.Rodriguez@goeverbright.com>, Patel, Nishit <
> Nishit.Patel@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Colleen Mooney <cmooney@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> Hey Dusty,
>
>
>
> That time works fine for me (I’m CST, in Austin). @Devanapally, Sai
> pruthvi <saipruthvi.devanapally@goeverbright.com> / @Talasila, Purna chand
> <purnachand.talasila@goeverbright.com> does 2:30pm Pacific / 4:30pm
> Central on Friday work for both of you?
>
>
>
> JPL
>
>
>
> *From: *Dusty Hagstrom <dhagstrom@omnidian.com>
> *Date: *Thursday, January 30, 2025 at 10:00 AM
> *To: *Liska, John <John.Liska@goeverbright.com>
> *Cc: *Talasila, Purna chand <purnachand.talasila@goeverbright.com>,
> Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris <
> Amauris.Rodriguez@goeverbright.com>, Patel, Nishit <
> Nishit.Patel@goeverbright.com>, Mike Beenen <mbeenen@omnidian.com>, David
> Kenny <dkenny@omnidian.com>, Karen Schlesinger <kschlesinger@omnidian.com>,
> Colleen Mooney <cmooney@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Burt was sick yesterday and is not feeling well today either. Lets set up
> some time for Friday, does 2:30pm pacific on friday the 31st work for you?
>
> *Dusty Hagstrom*
>
> ENGINEERING MANAGER
>
> *Protecting Clean Energy Investments*
>
> Pronouns: He/Him *What's this?*
> <https://urldefense.com/v3/__https:/www.mypronouns.org/what-and-why__;!!CdlIDb5c!VAxpmW3alxVFVrQW0c7TDtBgCF8kCeT9iMThTB_Hc7zwLwnMaIA-FmNAeo5hvZFC6Z_Qgswzpd8saVguTU5VRCPQ5g$>
>
> *M.* 808.936.6061
> LinkedIn
> <https://urldefense.com/v3/__https:/www.linkedin.com/in/dusty-hagstrom/__;!!CdlIDb5c!VAxpmW3alxVFVrQW0c7TDtBgCF8kCeT9iMThTB_Hc7zwLwnMaIA-FmNAeo5hvZFC6Z_Qgswzpd8saVguTU5qRWYrDw$>
>
> *Error! Filename not specified.*
> <https://urldefense.com/v3/__https:/www.omnidian.com/__;!!CdlIDb5c!VAxpmW3alxVFVrQW0c7TDtBgCF8kCeT9iMThTB_Hc7zwLwnMaIA-FmNAeo5hvZFC6Z_Qgswzpd8saVguTU5PEP_lAQ$>
>
>
>
>
>
> On Wed, Jan 29, 2025 at 3:04 PM Liska, John <John.Liska@goeverbright.com>
> wrote:
>
> Hi Burt,
>
>
>
> Would you have any slots open Thu/Fri/early next week? I’d like to get
> some folks together from both teams to see if we can get this sorted out.
> Please let me know, thanks.
>
>
>
> JPL
>
> [image: signature_3655907067]
>
> *John P. Liska*
> Product Manager - Data | *Ever**Bright*
>
> *m:* (512) 992-7484
>
> www.goeverbright.com
>
> [book time with me]
> <https://urldefense.com/v3/__https:/outlook.office.com/bookwithme/user/c381e8de49ed43f8afa3853db46ba0d5@goeverbright.com?anonymous&ep=pcard__;!!CdlIDb5c!VAxpmW3alxVFVrQW0c7TDtBgCF8kCeT9iMThTB_Hc7zwLwnMaIA-FmNAeo5hvZFC6Z_Qgswzpd8saVguTU6TadS9Hw$>
>
>
>
>
>
>
>
>
>
> *From: *Talasila, Purna chand <purnachand.talasila@goeverbright.com>
> *Date: *Tuesday, January 14, 2025 at 10:57 AM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris <
> Amauris.Rodriguez@goeverbright.com>, Patel, Nishit <
> Nishit.Patel@goeverbright.com>
> *Cc: *'Dusty Hagstrom' <dhagstrom@omnidian.com>, 'Mike Beenen' <
> mbeenen@omnidian.com>, 'David Kenny' <dkenny@omnidian.com>, 'Karen
> Schlesinger' <kschlesinger@omnidian.com>, 'Colleen Mooney' <
> cmooney@omnidian.com>, Liska, John <John.Liska@goeverbright.com>, Patel,
> Nishit <Nishit.Patel@goeverbright.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> + @Patel, Nishit <Nishit.Patel@goeverbright.com>
>
>
>
> *From: *Talasila, Purna chand <purnachand.talasila@goeverbright.com>
> *Date: *Thursday, January 9, 2025 at 2:17 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> bbielicki@omnidian.com <bbielicki@omnidian.com>, Rodriguez, Amauris <
> Amauris.Rodriguez@goeverbright.com>
> *Cc: *'Dusty Hagstrom' <dhagstrom@omnidian.com>, 'Mike Beenen' <
> mbeenen@omnidian.com>, 'David Kenny' <dkenny@omnidian.com>, 'Karen
> Schlesinger' <kschlesinger@omnidian.com>, 'Colleen Mooney' <
> cmooney@omnidian.com>, Liska, John <John.Liska@goeverbright.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> Hello Sai,
>
> We got following from John. Adding  @Rodriguez, Amauris
> <Amauris.Rodriguez@goeverbright.com> from cyber team as they completed
> the change on firewall.
>
>
>
> *From: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
> *Date: *Thursday, January 9, 2025 at 1:45 PM
> *To: *bbielicki@omnidian.com <bbielicki@omnidian.com>, Talasila, Purna
> chand <purnachand.talasila@goeverbright.com>
> *Cc: *'Dusty Hagstrom' <dhagstrom@omnidian.com>, 'Mike Beenen' <
> mbeenen@omnidian.com>, 'David Kenny' <dkenny@omnidian.com>, 'Karen
> Schlesinger' <kschlesinger@omnidian.com>, 'Colleen Mooney' <
> cmooney@omnidian.com>, Liska, John <John.Liska@goeverbright.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
> Burt, that looks correct and works for me.
>
>
>
> @Talasila, Purna chand <purnachand.talasila@goeverbright.com>, can you
> please assist? What IPs did we whitelist for Omnidian?
>
>
>
> Thanks,
>
> Sai
>
>
>
> *From: *bbielicki@omnidian.com <bbielicki@omnidian.com>
> *Date: *Wednesday, January 8, 2025 at 5:02 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Talasila, Purna chand <purnachand.talasila@goeverbright.com>
> *Cc: *'Dusty Hagstrom' <dhagstrom@omnidian.com>, 'Mike Beenen' <
> mbeenen@omnidian.com>, 'David Kenny' <dkenny@omnidian.com>, 'Karen
> Schlesinger' <kschlesinger@omnidian.com>, 'Colleen Mooney' <
> cmooney@omnidian.com>, Liska, John <John.Liska@goeverbright.com>
> *Subject: *RE: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Hi Sai,
>
>
>
> When I try to connect, I get a server timeout:
>
>
>
>
>
> (“None” is replaced with the PEM key attached previously in the thread)
>
>
>
> Does this look correct?
>
>
>
> Thanks,
>
>
>
> Burt
>
>
>
> *From:* Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
>
> *Sent:* Tuesday, December 31, 2024 10:53 AM
> *To:* bbielicki@omnidian.com; Talasila, Purna chand <
> purnachand.talasila@goeverbright.com>
> *Cc:* 'Dusty Hagstrom' <dhagstrom@omnidian.com>; 'Mike Beenen' <
> mbeenen@omnidian.com>; 'David Kenny' <dkenny@omnidian.com>; 'Karen
> Schlesinger' <kschlesinger@omnidian.com>; 'Colleen Mooney' <
> cmooney@omnidian.com>; Liska, John <John.Liska@goeverbright.com>
> *Subject:* Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Hello Burt,
>
>
>
> Those are credentials for the prod environment. Can we have a call set up
> next week to troubleshoot SFTP access?
>
>
>
> Thanks,
>
> Sai
>
>
>
> *From: *bbielicki@omnidian.com <bbielicki@omnidian.com>
> *Date: *Thursday, December 19, 2024 at 4:36 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
> *Cc: *'Dusty Hagstrom' <dhagstrom@omnidian.com>, 'Mike Beenen' <
> mbeenen@omnidian.com>, 'David Kenny' <dkenny@omnidian.com>, 'Karen
> Schlesinger' <kschlesinger@omnidian.com>, 'Colleen Mooney' <
> cmooney@omnidian.com>, Liska, John <John.Liska@goeverbright.com>
> *Subject: *RE: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Thanks Sai. In our initial tests, we aren't weren’t able to reach the
> server below.
>
>
>
> Are those credentials for your test or production environment?
>
>
>
> Thanks,
>
>
>
> Burt
>
>
>
> *From:* Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
>
> *Sent:* Friday, December 13, 2024 7:12 AM
> *To:* bbielicki@omnidian.com
> *Cc:* 'Dusty Hagstrom' <dhagstrom@omnidian.com>; 'Mike Beenen' <
> mbeenen@omnidian.com>; 'David Kenny' <dkenny@omnidian.com>; 'Karen
> Schlesinger' <kschlesinger@omnidian.com>; 'Colleen Mooney' <
> cmooney@omnidian.com>; Liska, John <John.Liska@goeverbright.com>
> *Subject:* Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Hello Burt,
>
>
>
> I ran into some issues trying to attach the key file but here you go.
>
>
>
> *Server*: eb-hub-ftp.goeverbright.com
>
> *Username: *omnidian-user
>
> * Key file: *<attached>
>
>
>
> *Example command from cli client: *sftp -i <path/to/eb-omnidian-ssh>
> omnidian-user@eb-hub-ftp.goeverbright.com
>
>
>
> You will find two folders FromOmnidian and   ToOmnidian and we would like
> to have files uploaded to FromOmnidian folder when we are ready to switch
> sftp.
>
>
>
> Thanks,
>
> Sai
>
>
>
> *From: *bbielicki@omnidian.com <bbielicki@omnidian.com>
> *Date: *Wednesday, December 11, 2024 at 12:20 PM
> *To: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Liska, John <John.Liska@goeverbright.com>
> *Cc: *'Dusty Hagstrom' <dhagstrom@omnidian.com>, 'Mike Beenen' <
> mbeenen@omnidian.com>, 'David Kenny' <dkenny@omnidian.com>, 'Karen
> Schlesinger' <kschlesinger@omnidian.com>, 'Colleen Mooney' <
> cmooney@omnidian.com>
> *Subject: *RE: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Hi John and Sai,
>
> Could you please send us the new SFTP information if it is ready? That
> will allow us to prime some of our work for January.
>
>
>
> Thanks,
>
>
>
> Burt
>
>
>
>
>
> *From:* Burt Bielicki <bbielicki@omnidian.com>
> *Sent:* Tuesday, November 26, 2024 3:19 PM
> *To:* Colleen Mooney <cmooney@omnidian.com>
> *Cc:* Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>;
> Dusty Hagstrom <dhagstrom@omnidian.com>; Liska, John <
> John.Liska@goeverbright.com>; Mike Beenen <mbeenen@omnidian.com>; David
> Kenny <dkenny@omnidian.com>; Karen Schlesinger <kschlesinger@omnidian.com>
> *Subject:* Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Correct, the files are in CSV format.
>
>
>
> On Tue, Nov 26, 2024 at 7:48 AM Colleen Mooney <cmooney@omnidian.com>
> wrote:
>
> Thanks for understanding. I believe they are csv but I'd like @Burt
> Bielicki <bbielicki@omnidian.com> or @Dusty Hagstrom
> <dhagstrom@omnidian.com> to confirm.
>
>
>
> Colleen
>
>
>
> On Tue, Nov 26, 2024 at 7:35 AM Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com> wrote:
>
> Hi Collen,
>
>
>
> That’s ok. We can start this work in January.
>
>
>
> One question - Can you please confirm whether your team is sending us CSV
> files or PGP encrypted files?
>
>
>
> Thanks,
>
> Sai
>
>
>
> *From: *Colleen Mooney <cmooney@omnidian.com>
> *Date: *Monday, November 25, 2024 at 2:44 PM
> *To: *bbielicki@omnidian.com <bbielicki@omnidian.com>, Liska, John <
> John.Liska@goeverbright.com>
> *Cc: *Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>,
> Mike Beenen <mbeenen@omnidian.com>, David Kenny <dkenny@omnidian.com>,
> Karen Schlesinger <kschlesinger@omnidian.com>
> *Subject: *Re: FW: EverBright <> Omnidian: SFTP testing
>
>
>
> Hi John and Sai,
>
>
>
> Our teams are pretty booked up through the end of the year. Would it be ok
> to start this work in January when people are back from the holidays?
>
>
>
> Thanks,
>
> Colleen
>
>
>
>
>
> On Fri, Nov 22, 2024 at 1:35 PM <bbielicki@omnidian.com> wrote:
>
>
>
>
>
> *From:* Devanapally, Sai pruthvi <saipruthvi.devanapally@goeverbright.com>
>
> *Sent:* Friday, November 8, 2024 2:30 PM
> *To:* Liska, John <John.Liska@goeverbright.com>; Mike Beenen <
> mbeenen@omnidian.com>
> *Cc:* David K. <davidk@omnidian.com>; Karen Schlesinger <
> kschlesinger@omnidian.com>; Dusty Hagstrom <dhagstrom@omnidian.com>; Burt
> Bielicki <bbielicki@omnidian.com>
> *Subject:* Re: EverBright <> Omnidian: SFTP testing
>
>
>
> Hello everyone,
>
>
>
> Good to meet the Omnidian team. We need to do some internal testing first
> before involving the Omnidian team, but we wanted to check on your team's
> availability during the holiday/PTO period.
>
>
>
>    1. What sorts of tests are you expecting to run, and have us
>    participate in? – Once we are ready to start testing with your team, we’ll
>    just need some files uploaded to the new SFTP.
>    2. What changes/impacts will there be with the new SFTP setup:
>    a. Is the host name changing? - yes
>    b. Do we need to generate new SSH keys, or are there any sorts of
>    permissions changes? – no. we will share the new keys required for new SFTP
>
>         c. Any other functional changes? – like John mentioned, changing
> the file naming convention may be required but that can be done after
> testing the new SFTP.
>
>
>
>
>
> Thanks,
>
> Sai
>
>
>
>
>
>
>
>
>
> *From: *Liska, John <John.Liska@goeverbright.com>
> *Date: *Friday, November 8, 2024 at 11:02 AM
> *To: *Mike Beenen <mbeenen@omnidian.com>, Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com>
> *Cc: *David K. <davidk@omnidian.com>, Karen Schlesinger <
> kschlesinger@omnidian.com>, Dusty Hagstrom <dhagstrom@omnidian.com>, Burt
> Bielicki <bbielicki@omnidian.com>
> *Subject: *Re: EverBright <> Omnidian: SFTP testing
>
> Thanks Mike. (And good to meet you both Dusty and Burt.) As the Product
> Manager on our side I likely don’t provide a lot of value for the technical
> discussions, so that will primarily be Sai (with Support from DevOps where
> needed). @Devanapally, Sai pruthvi
> <saipruthvi.devanapally@goeverbright.com> what do you think makes sense:
> continue this thread or try to get folks together on a call to work out the
> details?
>
>
>
> I can quickly answer a couple of your questions:
>
>    - 2b) yes, the destination / hostname will be changing.
>    - 2c) in addition to what you listed we will be requesting a change to
>    the file naming convention. Basically moving the date suffix to a prefix.
>    (Currently your filenames look like “Everbright_Asset03052023.csv”.)
>
>
>
> I’ll continue to help out where I can with documentation and anything else
> so please continue to keep me in the loop, but I’ll let Sai walk through
> next steps / answer questions. Thanks.
>
>
>
> JPL
>
>
>
>
>
> *From: *Mike Beenen <mbeenen@omnidian.com>
> *Date: *Friday, November 8, 2024 at 10:51 AM
> *To: *Liska, John <John.Liska@goeverbright.com>
> *Cc: *David K. <davidk@omnidian.com>, Devanapally, Sai pruthvi <
> saipruthvi.devanapally@goeverbright.com>, Karen Schlesinger <
> kschlesinger@omnidian.com>, Dusty Hagstrom <dhagstrom@omnidian.com>, Burt
> Bielicki <bbielicki@omnidian.com>
> *Subject: *Re: EverBright <> Omnidian: SFTP testing
>
>
>
> Hi John,
>
>
>
> I've added Dusty and Burt from our side. I'll let them carry this
> conversation forward. Some questions that do pop up to me to understand the
> scope of the testing/migration effort:
>
>    1. What sorts of tests are you expecting to run, and have us
>    participate in?
>    2. What changes/impacts will there be with the new SFTP setup:
>    a. Is the host name changing?
>    b. Do we need to generate new SSH keys, or are there any sorts of
>    permissions changes?
>    c. Any other functional changes?
>
> Thanks!
>
>
>
> *Mike Beenen*
>
> SENIOR SOFTWARE ENGINEER
>
> *Protecting Clean Energy Investments*
>
> Pronouns: He/Him *What's this?*
> <https://urldefense.com/v3/__https:/www.mypronouns.org/what-and-why__;!!CdlIDb5c!Uz1v9WKY0K14yV3rhFxtC-hEsLkCKnEnbbPQhuXRNAyXABTdEJyoomlciZNet2LuCWdJk9xVcsdjpABp-GA69R8$>
>
> *P.* 800.597.9127 ext. 538   |  *M.* 516.233.9854
> LinkedIn
> <https://urldefense.com/v3/__https:/www.linkedin.com/in/mike-beenen-97536b1b/__;!!CdlIDb5c!Uz1v9WKY0K14yV3rhFxtC-hEsLkCKnEnbbPQhuXRNAyXABTdEJyoomlciZNet2LuCWdJk9xVcsdjpABpnCkQeXw$>
>
>
>
>
>
> On Wed, Nov 6, 2024 at 1:22 PM Liska, John <John.Liska@goeverbright.com>
> wrote:
>
> Hi Mike,
>
>
>
> Wanted to let you know that our DevOps team has completed the setup of our
> new SFTP server. Sai (cc’ed here) is one of the developers on our Data
> Platform team here and will be working on migrating the data pipeline on
> our side for Omnidian data.
>
>
>
> What kind of availability would your team have to help us with testing?
> I’m assuming your team is as busy as we are and all of us have holidays/PTO
> coming up. But wanted to start the conversation around how we think about
> getting through some testing first, and then after that what the production
> cutover would look like. Let me know what you think, or if you’d prefer a
> call I’ll put a meeting on the calendar. Thanks!
>
>
>
> JPL
>
> [image: signature_120732083]
>
> *John P. Liska*
> Product Manager - Data | *Ever**Bright*
>
> *m:* (512) 992-7484
>
> www.goeverbright.com
>
> [book time with me]
> <https://urldefense.com/v3/__https:/outlook.office.com/bookwithme/user/c381e8de49ed43f8afa3853db46ba0d5@goeverbright.com?anonymous&ep=pcard__;!!CdlIDb5c!Uz1v9WKY0K14yV3rhFxtC-hEsLkCKnEnbbPQhuXRNAyXABTdEJyoomlciZNet2LuCWdJk9xVcsdjpABpdiY02PY$>
>
>
>
>
>
>
>
> *Colleen Mooney*
>
> CLIENT SUCCESS MANAGER
>
>
> *P.* 650.576.0967
>
> *cmooney@omnidian.com* <cmooney@omnidian.com>
>
>
>
>
>
> *Colleen Mooney*
>
> CLIENT SUCCESS MANAGER
>
>
> *P.* 650.576.0967
>
> *cmooney@omnidian.com* <cmooney@omnidian.com>
>
> *Error! Filename not specified.*
>
>
>
>


            """
        )
        }
    

    sample = {
        "to":      "dusty@omnidian.com",
        "from":    "john@example.com",
        "subject": "Phase-2 Roll-out timeline",
        "date":    "2025-04-22",
        "text": (
            "Hey Dusty,\n\n"
            "Could you meet next Thursday (2025-04-24) at 14:00 to lock the "
            "Phase-2 roll-out? I’ll also need your feedback on the new "
            "ingestion metrics by 2025-05-01.\n\n– John"
        )
    }
    import json
    extractor = EmailExtractor()
    result    = extractor.parse_email(sample)
    print(json.dumps(result, indent=2))
