# 36.-Capitaland-AI-Hackathon-2025
The **Knowledge Base Retrieval Assistant Chatbot** (we only managed to create a prototype), our submission for the Capitaland AI Hackathon 2025, aims to automate the process of searching and comparing internal 
domain knowledge of a company with external online sources (market), which can take a significant amount of time manually.

By solving this issue, it speeds up time efficiency, allowing employees to focus on more important parts of the project. At a business level, it allows more projects to be 
handled simulataneously, and allow for more latest and quality market research, boosting growth and keeping ahead in the market.

The nature of this 2-day hackathon is on GenAI.

Last but not least, much much thanks to my teammates! We did not win, but I thought we came up with something worth remembering.
- [Wenxuan](https://github.com/Wenxuan-Ang)
- [John-Henry Lim](https://github.com/Interpause)
- mentors and organising team from Capitaland

<br>

## Development Process
During the hackathon, we were given internal data (of which I cannot share unfortunately) consisting of various documents such as,
- Design guidelines
- Quality procedures
- Project records

as well as, 
- a query (input) and response (output) test conditions (which may/may not include the properly retrieved internal domain knowledge document, if queried by the user) database to check if the chatbot is working. For example:

| **Query** | **Expected Response** | **Retrieved Document** |
|:------:|:------:|:------:|
| `May I get XXX company's LOA form?` | `Sure, here is XXX company's LOA form` | `LOA_form.pdf` |
| `Is XXX company's floor plan abiding by the government's policies?` | `Yes it is, it is still 40m x 40m, which abides by the government's guidelines.` | `floor_plan.pdf` |
| `Is XXX company's revenue higher than YYY company's revenue this year?` | `Yes, XXX company earned $300 million, which YYY company earned $200 million.` | `revenue.pdf` | 
| `What is the time now?` | `It is 1pm.` | NIL |

With these data and test cases, we were asked to create,  
```text
3-layer AI bot​ that enhances capabilities and boost productivity​:
Layer 1 - AI chatbot of Domain Knowledge database for easy info extraction. ​
Layer 2 - Link chatbot to OpenWeb/external data for ease of market research and benchmarking e.g. compare, in a table, our standards of car parking lot
size/layout/demarcation lines to that of the latest workspace building in the market, good LOA template.​
Layer 3 - Leveraging AI-generated insights to augment the continuous enhancement of the design guidelines, quality procedures and records
```

<br>

## Knowledge Base Retrieval Assistant Chatbot architecture and Technology Stack
**Our technology stack**
<p align="center"> 
  <img width="700" alt="image" src="https://github.com/user-attachments/assets/9f280dab-fd81-4a0f-9a3b-785c00622bc1" />
</p> 

**Knowledge Base Retrieval Assistant Chatbot architecture**
<p align="center"> 
  <img width="700" alt="image" src="https://github.com/user-attachments/assets/1082dc81-2df8-409b-87bb-f19554856490" />
</p>

Most of the LLM configuration is done within [Azure AI Foundry](https://ai.azure.com/)'s UI playground, rather than in code. Unfortunately, we found this to be very restrictive, compared to coding from scratch, but we had no choice due to the limited time we had for the hackathon.

The Knowledge Base Retrieval Assistant Chatbot is made up of 3 LLMs (we used GPT 4o),
- a Local Files (Child) Agent that is used to retrieve documents from the internal domain knowledge using Retrieval Augmented Generation (RAG) (we used Azure AI Foundry's in-built Azure AI Search. However, the downside for this is that it only can read PDF files, and not other file types (e.g. .pptx, .xlsx, .jpeg, .png etc.). We thought that an improved version of this would be the Azure AI Foundry's in-built Multimodal RAG (but unfortunately we did not have access to this feature)
- a Web Search (Child) Agent that is used to search external online sources (we used the Azure AI Foundry's in-built Bing Search)
- a Coordinator (Parent) Agent that receives the query (input) and generates the output (response). It decides if to receive input from the Local Files (Child) Agent and/or the Web Search (Child) Agent based on the nature of the query (input). For example,
  - If it is a query about retrieving a particular document only (e.g. a LOA form) from the internal domain knowledge, the Coordinator (Parent) Agent should only call for input from the Local Files (Child) Agent
  - If it is a query about that cannot be found in the domain knowledge/specifically for an external online source (e.g. "What is the time today?"), the Coordinator (Parent) Agent should only call for input from the Web Search (Child) Agent
  - If it is a query about comparing a internal domain knowledge with an external online source (e.g. "Is our carpark guidelines still abiding by the government's guidelines?"), the Coordinator (Parent) Agent should call for input from both the Local Files (Child) Agent and the Web Search (Child) Agent

We used prompt engineering to tune the System Prompt of each of the LLMs based on the outputs (repsonse).

Source(s):
- https://www.youtube.com/playlist?list=PLyqwquIuSMZqpk8GWbSFMwtHWpopBBnR_ (LinoTV) (YouTube playlist by LinoTV, titled "Azure AI Foundry")
- https://www.youtube.com/watch?v=WSsA21xw-gY&t=9s (Gradio Guy) (YouTube video by Gradio Guy, titled "Gradio Tutorial for Beginners: Quick Start Guide")

<br>

## How to Run?
(DISCLAIMER: The code for this prototype no longer works as it requires access to the API keys from the provided [Azure AI Foundry](https://ai.azure.com/) accounts by the 
hackathon, which are already removed.)

If not using the Devcontainer, install Poetry here: <https://python-poetry.org/docs/#installation>

Afterwards, run the following to install dependencies and run the Gradio:
```sh
poetry install
poetry run gradio chat.py
```

<br>

## Future Improvements
- We understand LLMs always have the issue of hallucination. To reduce this, we had an idea to improve by adding a sort of "controller" layer between the Parent Agent and the Child Agents, which is used to fact check the outputs from the Child Agents. If the outputs is found to be untrue, the outputs will not be fed into the Parent Agent, and the Parent Agent should respond with something like, "We had an error retrieving the relevant documents. Please try again."

  However we weren't able to implement this in time.

- An alternative to using [Azure AI Foundry](https://ai.azure.com/)'s UI playground is to use [Pydantic AI](https://ai.pydantic.dev/#hello-world-example), which allows us to create AI workflows as well from scratch. We thought in the future this could be used instead.
