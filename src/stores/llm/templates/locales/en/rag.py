from string import Template

###RAG PROMPTS###

##System ##

system_prompt =Template(
    "\n".join([
        "You are an assistant to generate a response for the user.",
        "You will be provided with a set of documents assosciated with the user's query.",
        "You have to generate a response based on the provided documents.",
        "Ignore the documents that are not relevant to the user's query.",
        "You can apologize if you don't have enough information to answer the user's query.",
        "You have to generate a response in the same language as the user's query.",
        "Be polite and concise in your response.",
        "Be precise and to the point in your response.Avoid unnecessary details.",
    ])
)

### Document###

document_prompt = Template(
    "\n".join([
        "## Document No: $doc_no ",
        "### Content: $chunk_text"
        
    ])
)

### Footer ###

footer_prompt = Template(
    "\n".join([
    "Based only on the above documents, generate a response for the following user query:",
    "## Question:",
    "$query",
    "## Answer:"
    ])
)