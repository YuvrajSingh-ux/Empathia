from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnableParallel,RunnableLambda
from langchain_groq import ChatGroq
from typing import List,Tuple
from dotenv import load_dotenv


load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.4
    # device='cuda' if torch.cuda.is_available() else 'cpu'
)

fast_llm = ChatGroq(
    model="llama-3.1-8b-instant",  # ⚡ faster
    temperature=0.0
)

conversation_history=[]

summary_prompt=PromptTemplate(template="""
    Recent Conversations are: {conversation_history}.
    User query is: {query}
    Agent's response is: {response}
    Generate a short summary based on this history and query.""",
    input_variables=['conversation_history','query','response'])

parser1=StrOutputParser()

summary_chain=summary_prompt|llm|parser1

prompt=PromptTemplate(
    template="""
    The recent conversation:{conversation_history}.
    The emotions detected via speech are: {speech_emotions}.
    The emotions detected via text are: {text_emotions}.
    The emotions detected can be contradicting too, so go with the emotions which makes sense in reference to the query: {query}
    You are a therapist.
    Generate an empathetic response to the query: {query}.
    Make sure the response is relevant and is equivalent to what a therapist would say.
    Don't mention the emotions explicitly, generate a human-like response and keep it short.
    """,
    input_variables=["speech_emotions","text_emotions","query"]
)


response_chain = prompt | llm | parser1

def generate_response(emotions):
    global conversation_history


    inputs = {
        "conversation_history": conversation_history,
        "speech_emotions": emotions['speech_emotions'],
        "text_emotions": emotions['text_emotions'],
        "query": emotions["query"]
    }
    response = response_chain.invoke(inputs)

    return response

response_generation=RunnableLambda(generate_response)


prompt3 = PromptTemplate(
    template="""
Given this query: {query}, text emotion: {text_emotions}, speech emotions: {speech_emotions},
determine if the user is expressing suicidal thoughts. Suicidal thoughts include, but are not limited to:
- Thinking about ending one's life.
- Wanting to die.
- Thinking about committing suicide.
- Feeling like there is no reason to live.

Respond only with "Yes" or "No", do not include anything else.
If you are not sure, respond with "No".
""",
    input_variables=["query", "text_emotions", "speech_emotions"]
)


suicide_check=prompt3|llm|parser1


# prompt2=PromptTemplate(
#     template="""Given this response: {response}, convert it into a response whithout any harmful, rude or insensitive language. Return the filtered out response only,
#     don't mention anything about the content moderation.
#     If {suicide_check} is Yes, then suggest the following helplines in bold:
#     Say '\nYou can contact the following helplines for further help:
#     India Suicide Helpline Directory | AASRA: 91-9820466726
#     Emergency number: 112.'
#     If {suicide_check} is No, don't mention the helpline or anything related to suicide.""",
#     input_variables=["response","suicide_check"]
# )

prompt2 = PromptTemplate(
    template="""
You are a content moderator ensuring responses are safe and supportive.

Given this response: {response}
The suicide risk check result: {suicide_check}

If the suicide risk check result is "Yes":
- Add the following helpline message **verbatim** at the end of your response:
  "You can contact the following helplines for further help:
  India Suicide Helpline Directory | AASRA: 91-9820466726
  Emergency number: 112."
- Do NOT remove the original response.

If the suicide risk check result is "No":
- Return the response as it is, just ensure no harmful or insensitive language.

Return only the final, safe message.
""",
    input_variables=["response", "suicide_check"]
)



response_moderation=prompt2|fast_llm|parser1



# def build_chain():
#     first_phase = RunnableParallel(
#         response=response_generation,
#         suicide_check=suicide_check
#     )

#     def unpack_and_moderate(d):
#         print("Suicide check output:", d["suicide_check"])
#         return response_moderation.invoke({
#             "response": d["response"],
#             "suicide_check": d["suicide_check"].strip().capitalize() 
#         })

#     chain = first_phase | RunnableLambda(unpack_and_moderate)
#     return chain


def build_chain():
    first_phase = RunnableParallel(
        response=response_generation,
        suicide_check=suicide_check
    )

    def unpack_and_moderate(d):
        print("Suicide check output:", d["suicide_check"])
        moderated = response_moderation.invoke({
            "response": d["response"],
            "suicide_check": d["suicide_check"].strip().capitalize()
        })
        # Return both
        return {
            "final_response": moderated,
            "suicide_check": d["suicide_check"].strip().capitalize()
        }

    chain = first_phase | RunnableLambda(unpack_and_moderate)
    return chain


cached_chain = build_chain() 

# def voice_agent_reply(emotions):
#     result = cached_chain.invoke({
#         "speech_emotions": emotions['speech_emotions'],
#         "text_emotions": emotions['text_emotions'],
#         "query": emotions['query']
#     })

#     if isinstance(result, dict):
#         return result.get("response") or str(result)
#     return str(result)



def voice_agent_reply(emotions):
    result = cached_chain.invoke({
        "speech_emotions": emotions['speech_emotions'],
        "text_emotions": emotions['text_emotions'],
        "query": emotions['query']
    })

    # result is now a dict with both fields
    if isinstance(result, dict):
        return {
            "response": result.get("final_response"),
            "suicide_check": result.get("suicide_check")
        }
    else:
        return {
            "response": str(result),
            "suicide_check": "No"
        }



# prompt=PromptTemplate(
#     template="""
#     The recent conversation:{conversation_history}.
#     The emotions detected via speech are: {speech_emotions}.
#     The emotions detected via text are: {text_emotions}.
#     The emotions detected can be contradicting too, so go with the emotions which makes sense in reference to the query: {query}
#     You are a therapist.
#     Generate an empathetic response to the query: {query}.
#     Make sure the response is relevant and is equivalent to what a therapist would say.
#     Don't mention the emotions explicitly, generate a human-like response and keep it short.

#     Determine internally if the user is expressing suicidal thoughts. Suicidal thoughts include, but are not limited to:
#     - Thinking about ending one's life.
#     - Wanting to die.
#     - Thinking about suicide.
#     - Feeling like there is no reason to live.

#     If yes,then suggest the following helplines in bold:
#         Say '\nYou can contact the following helplines for further help:
#         India Suicide Helpline Directory | AASRA: 91-9820466726
#         Emergency number: 112.'
#     If no, never mention the helpline or anything related to suicide,don't let the user know that suicide check is being done on their query.

#     Your response should not contain any harmful, rude or insensitive language.

#     """,
#     input_variables=["speech_emotions","text_emotions","query"]
# )

# cached_chain=prompt|llm|parser1

# def voice_agent_reply(emotions):
#     global conversation_history
#     result = cached_chain.invoke({
#         "conversation_history":conversation_history,
#         "speech_emotions": emotions['speech_emotions'],
#         "text_emotions": emotions['text_emotions'],
#         "query": emotions['query']
#     })

#     if isinstance(result, dict):
#         return result.get("response") or str(result)
#     return str(result)


def update_history(query,response):
    global conversation_history
    summary=summary_chain.invoke({'conversation_history':conversation_history,'query':query,'response':response})
    conversation_history.clear()
    conversation_history.append(summary)


