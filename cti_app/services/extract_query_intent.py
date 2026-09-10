from typing import Dict, List, Optional
from langchain_classic.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.agents import create_agent

from dotenv import load_dotenv
load_dotenv()

from cti_app.llm_constants import llm

# Labels that are present in docs metadata
ENTITY_TYPES = [
    "technique",
    "group",
    "software",
    "mitigation",
    "detection",
    "asset",
    "tactic",
    "campaign"
]

RELATIONSHIP_TYPES = [
    "employs",
    "attributed-to",
    "uses",
    "mitigates",
    "detects",
    "subtechnique-of",
    "procedure-of",
    "belongs-to-tactic"
]

schemas = [
    ResponseSchema(
        name="entities",
        description=f"List of MITRE ATT&CK entity types relevant to the query. Must be one of: {ENTITY_TYPES}"
    ),
    ResponseSchema(
        name="relationships",
        description=f"List of MITRE ATT&CK relationship types relevant to the query. Must be one of: {RELATIONSHIP_TYPES}"
    )
]

output_parser = StructuredOutputParser.from_response_schemas(schemas)


SYSTEM_PROMPT_INTENT_EXTRACTION = """
You are an assistant that analyzes user queries about cyber security questions and extracts the intent behind the questions (e.g. what the user wants to know, not what the query is about).
Your goal is to determine what kind of MITRE ATT&CK entities and relationships the user is asking about, based on **their intention**, not just the literal words in the query. 
Focus on what the user wants to find out, especially if they are asking how to detect, mitigate, or investigate attacks.

For example:
- Query: "How do I find if attackers are using PowerShell in our environment?"
  Entities: ["detection"]
  Relationships: ["detects"]
  
Your PRIMARY focus is to identify whether the user is asking about:
- detection (how to identify attacks)
- mitigation (how to prevent or reduce attacks)

Always prioritize detection and mitigation when the query implies:
- identifying malicious activity
- monitoring systems
- finding indicators of compromise
- defending against attacks
- reducing risk

FOR defensive queries:
You MUST return ONLY:
- detection
- mitigation
- detects
- mitigates
  
Never use "employs" or "uses" in combination with mitigation or detection!

Do NOT classify software unless the question explicitly asks:
- what malware was used
- what tools attackers used
  
You must return a JSON object with exactly the fields specified in the schema.
Only include allowed labels. Do not include any explanations or extra text outside of the JSON object.

Use the following definitions to better understand the query:
Entities:
- technique: How threat actors achieve a tactical goal. Example: dumping credentials (refers to **only** malicious and adversary-used technique)
- sub-technique: More specific behavior of a technique that was executed by threat actors. Example: dumping credentials via LSA Secrets 
- procedure: A real-world implementation of a technique/sub-technique by threat actors. Example: using PowerShell to scrape LSASS memory. (refers to **only** malicious and adversary-used procedure)
- group: Threat actor group responsible for campaigns or attacks (refers to **only** malicious groups)
- software: Malware or tools used by threat actors to carry out attacks (refers to **only** malicious and adversary-used software)
- mitigation: Countermeasures to reduce or prevent attacks.
- detection: Methods to detect techniques or attacks.
- asset: Systems, devices, or resources targeted by attacks.

Relationships:
- employs: Technique or sub-technique employed in a campaign or by a group.
- uses: Software used in a campaign or by a group.
- mitigates: Mitigations that counter specific techniques or attacks.
- detects: Detections that identify a technique, campaign, or attack activity.
- subtechnique-of: A technique is a sub-technique of a parent technique.
- procedure-of: How a technique or sub-technique is executed in real scenarios.
- attributed-to: Links campaigns or attacks to specific groups.

    The schema of the data:
    (:Campaign)-[:USES]->(:Technique)
    (:Campaign)-[:USES]->(:SubTechnique)
    (:Campaign)-[:USES]->(:Software)
    (:Campaign)-[:ATTRIBUTED_TO]->(:Group)
    (:Technique)-[:SUBTECHNIQUE_OF]->(:Technique)
    (:Procedure)-[:PROCEDURE_OF]->(:Technique)
    (:Procedure)-[:PROCEDURE_OF]->(:SubTechnique)
    (:Mitigation)-[:MITIGATES]->(:Technique)
    (:Mitigation)-[:MITIGATES]->(:SubTechnique)
    (:Detection)-[:DETECTS]->(:Technique)
    (:Detection)-[:DETECTS]->(:SubTechnique)
    (:Tactic)-[:INCLUDES_TECHNIQUE]->(:Technique)
    (:Tactic)-[:INCLUDES_TECHNIQUE]->(:SubTechnique)
    (:Group)-[:USES]->(:Technique)
    (:Group)-[:USES]->(:SubTechnique)
    (:Group)-[:USES]->(:Software)
    (:Asset)-[:TARGETS]->(:Technique)
    (:SubTechnique)-[:SUBTECHNIQUE_OF]->(:Technique)
"""

agent = create_agent(
    model=llm,
    tools=[],
    system_prompt=SYSTEM_PROMPT_INTENT_EXTRACTION
)

def extract_intent(query: str) -> Dict[str, List[str]]:
    """
    Uses the agent with structured output parser to return intent.
    Only includes allowed labels.
    """
    prompt = f"""
    Query: "{query}"
    
    Return a JSON object with the following keys:
    {output_parser.get_format_instructions()}
    
    - The "entities" value must be a JSON array, even if it has only one item.
    - The "relationships" value must be a JSON array, even if it has only one item.
    """

    response = llm.invoke(input=prompt)
    parsed = output_parser.parse(response.text)

    # Normalize: always lists
    for key in ["entities", "relationships"]:
        if key not in parsed or parsed[key] is None:
            parsed[key] = []
        elif isinstance(parsed[key], str):
            parsed[key] = [parsed[key]]

    # Filter only allowed labels
    parsed["entities"] = [e for e in parsed["entities"] if e in ENTITY_TYPES]
    parsed["relationships"] = [r for r in parsed["relationships"] if r in RELATIONSHIP_TYPES]

    return parsed

def build_filter_from_intent(query: str, campaign_id: Optional[str] = None) -> Dict:
    """
    Builds a Chroma metadata filter using the intent extracted by the LLM.
    https://skrath.medium.com/optimizing-vector-search-unleashing-the-power-of-metadata-in-vector-databases-a558449455f7
    """
    intent = extract_intent(query)

    clauses = []

    if intent["entities"]:
        clauses.append({"type": {"$in": intent["entities"]}})

    if intent["relationships"]:
        clauses.append({"relationship_type": {"$in": intent["relationships"]}})



    if not clauses:
        return {}

    if len(clauses) == 1:
        return clauses[0]

    return {"$or": clauses}


if __name__ == "__main__":

    query = "What are detections for PowerShell execution?"
    query = "Ways to identify malicious PowerShell activity."
    #  query = "Ways to monitor and detect PowerShell exploitation?"
    #  query = "How do I find if attackers are using PowerShell in our environment?"
    #  query = "Approaches to identifying malicious PowerShell execution"
    campaign_id = "C0029"

    chroma_filter = build_filter_from_intent(query, campaign_id)
    print("Chroma filter generated:\n", chroma_filter)

