from langchain_community.chat_models import ChatOllama
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains.llm import LLMChain
from typing import Dict

class EmailProcessor:
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

For each email, please provide structured information in the following format. 

Category: [List any relevant categories: e.g. Project Updates, Meeting Requests, Client Communication, etc.]
Mentioned Teams/Projects/Systems: [List references, e.g. Data Acquisition, Salesforce, etc.]
Summary: [Concise 1-2 sentence summary of the email topic]
Action Items or Requests: [Bullet points describing what is being asked, tasks required, or follow-ups needed, be specific so that it is understandable without the full email]
Deadlines or Dates: [List explicit deadlines or scheduled dates mentioned]
Attachments Summary: [If any; e.g. “Excel with monthly metrics”]
Reason for Importance (or Not): [1 paragraph explaining why Dusty should prioritize or de-prioritize]
Is Important: [true or false - whether it needs immediate/later attention]
Next Steps: [If any - e.g. respond, delegate, set up meeting, etc.]
Notes for Memory: [Any relevant context or reference to older threads, status updates, or new metrics that are valuable to remember, be specific so that it is understandable without the full email context]

Example output 
Category: Meeting Requests, Project Updates
Mentioned Teams/Projects/Systems: Client Portal, Data Ingestion Pipeline
Summary: John is proposing a planning meeting to finalize the Phase 2 rollout timeline.
Action Items or Requests:
 - Dusty to confirm availability for Thursday afternoon.
 - Provide input on the new data ingestion metrics by next week.
Deadlines or Dates:
 - Next Thursday (proposed meeting time)
 - Next week (feedback due)
Attachments Summary: [None]
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
You are an expert data extraction algorithm. Extract the following fields strictly in JSON format:
(summary, categories, reson, is_important, is_urgent, action_items, deadlines_or_dates, attachments_summary, notes_for_memory, next_steps, mentioned_teams_projects_systems, )

Text to extract from:
{llm_output}
""")
        return LLMChain(llm=self.llm, prompt=prompt, output_parser= self._build_output_parser())

    def process_email(self, email: Dict) -> Dict:
        """Run summarization + extraction on a single email."""
        summarized = self.summarization_chain.run(
            to=email["to"],
            from_=email["from"],
            subject=email["subject"],
            text=email["text"]
        )
        
        extracted_info = self.extraction_chain.run(llm_output=summarized)
        
        return {
            "llm_output": {"text": summarized},
            "analysis": extracted_info
        }
