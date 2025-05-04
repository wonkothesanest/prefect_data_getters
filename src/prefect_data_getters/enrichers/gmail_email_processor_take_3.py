"""
Multi-turn email extraction with one conversation:
  1) summary          2) categories   3) teams
  4) projects         5) systems      6) action_items / dates
  7) rationale        8) importance   9) urgency
 10) final JSON merge (parsed & auto-fixed)

Works with any chat-style model; defaults to Ollama’s mistral-nemo.
"""

from __future__ import annotations
import datetime as _dt, json, re
from typing import Dict, List, Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_ollama import ChatOllama          # local
# from langchain_openai import ChatOpenAI                       # cloud
from langchain.output_parsers import StructuredOutputParser, ResponseSchema, OutputFixingParser
from langchain.prompts import ChatPromptTemplate
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

# ────────────────────────────── JSON SCHEMA ──────────────────────────────── #

schemas = [
    ResponseSchema(name="summary",               description="≤2-sentence summary",           type="string"),
    ResponseSchema(name="categories",            description="array",                         type="array",  items={"type":"string"}),
    ResponseSchema(name="teams",                 description="array",                         type="array",  items={"type":"string"}),
    ResponseSchema(name="projects",              description="array",                         type="array",  items={"type":"string"}),
    ResponseSchema(name="systems",               description="array",                         type="array",  items={"type":"string"}),
    ResponseSchema(name="action_items",          description="array of strings",              type="array",  items={"type":"string"}),
    ResponseSchema(name="deadlines_or_dates",    description="array ISO-8601 strings",        type="array",  items={"type":"string"}),
    ResponseSchema(name="attachments_summary",   description="short string",                  type="string"),
    ResponseSchema(name="reason",                description="priority rationale",            type="string"),
    ResponseSchema(name="is_important",          description="boolean",                       type="boolean"),
    ResponseSchema(name="is_urgent",             description="boolean",                       type="boolean"),
    ResponseSchema(name="notes_for_memory",      description="array",                         type="array",  items={"type":"string"}),
]

_struct_parser = StructuredOutputParser.from_response_schemas(schemas)
_parser        = OutputFixingParser.from_llm(
                     llm    = ChatOllama(model="mistral-nemo:latest", temperature=0),
                     parser = _struct_parser,
                     max_retries = 2
                 )

FORMAT_INSTRUCTIONS = _struct_parser.get_format_instructions()

# ────────────────────────────── PROCESSOR ────────────────────────────────── #

def _clean_array(text: str) -> List[str]:
    """Returns [] for 'none/na', else parses JSON or comma-lists."""
    text   = text.strip()
    if text.lower() in ("none", "n/a", "na", ""):
        return []
    try:
        # if model already gave JSON array
        return json.loads(text)
    except Exception:
        # fallback: split by comma / newline, strip, dedup
        items = [re.sub(r'^[\-\*\d\.\s]+', '', t).strip()   # bullet/trailing chars
                 for t in re.split(r'[\n,]+', text)]
        return [t for t in dict.fromkeys(items) if t]       # dedup while preserving order


class EmailExtractor:
    def __init__(self, model_name: str = "mistral-nemo:latest"):
        self.llm = ChatOllama(model=model_name, temperature=0)

        self.sys_rules = SystemMessage(content=
            "You are a meticulous e-mail analyst for Dusty Hagstrom. "
            "Never guess. If a value is missing, output an empty list [], "
            "empty string \"\", or false.\n"
            "Dates MUST be ISO-8601 (YYYY-MM-DD).")

    # ───────────────────── helpers ────────────────────── #
    def _ask(self, chat: List, ask: str) -> str:
        """Append a user question, call model, return assistant answer."""
        chat.append(HumanMessage(content=ask))
        answer = self.llm.invoke(chat)
        chat.append(answer)
        return answer.content.strip()

    # ─────────────────── main entry ───────────────────── #
    @time_it
    def parse_email(self, email: Dict[str,str]) -> Dict[str,Any]:
        """
        email keys: to, from, subject, date (ISO), text
        Returns: Dict matching schemas list above.
        """
        chat: List = [self.sys_rules]

        # ─ 1) SUMMARY ─
        self._ask(chat,
            f"Today is {_dt.date.today()}.\n\nHere is the raw e-mail:\n"
            f"---\n{email['text']}\n---\n\n"
            "Give ONLY a ≤2-sentence summary.")
        summary = chat[-1].content

        # ─ 2) CATEGORIES ─
        cat = self._ask(chat,
            f"Using that e-mail, list any *Categories* from this whitelist:\n"
            f"{CATEGORIES}\nReturn [] if none.")

        # ─ 3) TEAMS ─
        teams = self._ask(chat,
            f"List *Teams* explicitly mentioned from whitelist {TEAMS}. [] if none.")

        # ─ 4) PROJECTS ─
        projects = self._ask(chat,
            f"List *Projects* mentioned from whitelist {PROJECTS}. [] if none.")

        # ─ 5) SYSTEMS ─
        systems = self._ask(chat,
            f"List *Systems* mentioned from whitelist {SYSTEMS}. [] if none.")

        # ─ 6) ACTION ITEMS (with dates) ─
        actions = self._ask(chat,
            "Extract any action items or tasks (bullet points). "
            "Embed ISO dates when stated, else omit dates.")

        # ─ 7) DEADLINES / DATES ─
        deadlines = self._ask(chat,
            "List all explicit deadlines or calendar dates in the e-mail (ISO). "
            "[] if none.")

        # ─ 8) RATIONALE ─
        reason = self._ask(chat,
            "Why should Dusty prioritise or ignore this e-mail? "
            "Be concise (≤1 paragraph).")

        # ─ 9) IMPORTANCE / URGENCY ─
        important = self._ask(chat,
            "true or false – is this e-mail important to Dusty, does he need to take action or follow up?")
        urgent    = self._ask(chat,
            "true or false – does it require response < 24h?")

        # ─10) ATTACH / NOTES ─
        attach   = self._ask(chat, "Short description of attachments (\"\" if none).")
        memnotes = self._ask(chat, "Anything worth long-term memory? [] if none.")

        # ─11) FINAL JSON MERGE ─
        escaped = FORMAT_INSTRUCTIONS.replace("{", "{{").replace("}", "}}")
        # merge_prompt = ChatPromptTemplate.from_messages([
        #     ("system", f"Combine everything …\n{escaped}\n\nRemember …"),
        #     ("user",  "Provide the JSON object now.")
        # ])
        raw_json = self._ask(
            chat,
            "Now assemble everything you have produced so far into *exactly* "
            f"this JSON schema:\n{escaped}"
        )
        # raw_json = self.llm.invoke(merge_prompt.format_messages()).content
        parsed   = _parser.parse(raw_json)

        # the model may have left numeric/boolean strings – quick normalise
        # parsed["categories"]          = _clean_array(parsed["categories"])
        # parsed["teams"]               = _clean_array(parsed["teams"])
        # parsed["projects"]            = _clean_array(parsed["projects"])
        # parsed["systems"]             = _clean_array(parsed["systems"])
        # parsed["action_items"]        = _clean_array(parsed["action_items"])
        # parsed["deadlines_or_dates"]  = _clean_array(parsed["deadlines_or_dates"])
        # parsed["notes_for_memory"]    = _clean_array(parsed["notes_for_memory"])
        # parsed["is_important"]        = str(parsed["is_important"]).lower() == "true"
        # parsed["is_urgent"]           = str(parsed["is_urgent"]).lower()   == "true"

        return parsed


# ─────────────────────────────── Demo ─────────────────────────────── #

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

    extractor = EmailExtractor()
    result    = extractor.parse_email(sample)
    print(json.dumps(result, indent=2))
