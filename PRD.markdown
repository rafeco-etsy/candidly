# Candidly: Peer Feedback Collection Tool with Conversational Follow-Ups

## 1. Overview

Candidly is a web-based tool for collecting richer, more candid peer feedback. It supports a mix of:

* **Rating questions** (e.g., 1–5 scale or N/A)
* **Discussion questions**, which are answered through a chatbot-driven conversation rather than a simple text box

The chatbot dynamically asks follow-up questions to encourage elaboration, detects when the user is finished, and generates a clean, summarized response.

Once all questions are answered, **Candidly shows the feedback giver a compiled draft of their responses for review and optional edits before final submission.** Only after the feedback giver confirms will the final answers be stored and shared with the requestor.

---

## 2. Goals

* **Make open-ended feedback easier and more actionable** by prompting deeper reflections through conversation
* **Encourage specificity and honesty** with gentle chatbot-led follow-ups
* **Reduce friction for feedback givers** by guiding them step by step
* **Ensure control and transparency** by letting feedback givers review and edit before submission
* **Provide well-structured, easy-to-read feedback** for requestors

---

## 3. User Roles

* **Feedback Requestor**

  * Sets up a feedback request for a person (target)
  * Receives completed feedback once submitted

* **Feedback Giver**

  * Completes the survey (ratings + chatbot discussions)
  * Reviews and confirms final responses before submission

* **System / Chatbot**

  * Guides feedback givers with dynamic probing questions
  * Detects completion and summarizes the discussion

---

## 4. User Flow

1. **Feedback Requestor creates a request**

   * Specifies the person being reviewed
   * Defines the survey questions (mix of ratings + discussion prompts)
   * Sends an invite link to feedback givers

2. **Feedback Giver completes the survey**

   * Sees an introduction explaining purpose and confidentiality
   * Answers **rating questions** quickly with a 1–5 scale or N/A
   * For **discussion questions**, enters a conversational flow with the chatbot, which asks follow-up questions

3. **Chatbot engagement for discussion questions**

   * Asks the main question (e.g., “What are their greatest strengths?”)
   * Responds to initial answers with probing prompts like:

     * “Can you share a specific example?”
     * “How has this impacted the team?”
   * Stops when the user indicates they’re done
   * Summarizes the entire chat into a concise, professional feedback statement

4. **Draft review page**

   * Once all questions are complete, the system compiles:

     * All rating responses
     * All discussion summaries
   * Feedback giver can:

     * Review the compiled answers
     * Edit any of the summaries directly (if needed)
     * Go back to a question if they want to add more context

5. **Final submission**

   * After reviewing and editing, the feedback giver clicks “Submit”
   * Finalized feedback is stored and made available to the requestor

6. **Feedback Requestor views compiled report**

   * Receives a structured, clean report of ratings + discussion summaries

---

## 5. Example Interaction

**Discussion Question:** *“What are this person’s greatest strengths?”*

* User: *“They’re a strong communicator and very supportive.”*
* Chatbot: *“Can you share a time when their communication made a big difference?”*
* User: *“During a crisis last quarter, they kept the team calm and aligned.”*
* Chatbot: *“Anything else you’d highlight about how they help the team succeed?”*
* User: *“No, that’s it.”*

**Summarized Draft:**
*They are a strong communicator who supports the team, especially during high-stress situations, keeping everyone calm and aligned.*

At the end of the survey, the feedback giver sees:

* Communication: 5
* Teamwork: N/A
* Greatest strengths: *They are a strong communicator who supports the team, especially during high-stress situations, keeping everyone calm and aligned.*
* Areas for growth: *They could improve in delegating responsibilities earlier in a project.*

The user can edit any summary before submission.

---

## 6. Key Product Requirements

1. **Survey composition**

   * Supports both rating and discussion questions
   * Flexible ordering of questions

2. **Chatbot-driven discussion**

   * Uses dynamic follow-up prompts
   * Can detect when the user is finished
   * Generates a clean, concise summary of the conversation

3. **Review and edit step**

   * Feedback giver sees a compiled draft of all answers
   * Can edit summaries before final submission
   * Can navigate back to questions if needed

4. **Finalized feedback storage**

   * Only stores feedback after confirmation
   * Provides a structured, readable report for the requestor

5. **Privacy & trust**

   * Clear messaging about who sees the feedback
   * Option to remain anonymous (if configured by requestor)

---

## 7. Non-Functional Requirements

* **Simplicity:** Minimal cognitive load; clean, intuitive UI
* **Performance:** Low-latency chatbot responses
* **Data security:** Keep feedback private and accessible only to the intended requestor
* **Clarity:** Avoid overly long chat interactions; limit probing to 2–3 follow-ups

---

## 8. Out of Scope for MVP

* Authentication & user accounts
* Email notifications or reminders
* Complex analytics or dashboards
* Integrations with HR or performance systems

---

## 9. Deliverables for MVP

* Single-page survey flow with ratings + chatbot questions
* Chatbot follow-ups and summarization
* Draft review page for confirmation
* Basic compiled report for requestors

---

## 10. Tagline

**Candidly: Honest feedback, reviewed and confirmed before it’s shared.**

