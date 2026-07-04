# Kaggle Capstone Project: Submission Checklist

To ensure your submission meets all criteria for the **Intensive Vibe Coding Capstone Project (Freestyle Track)** by the **July 6, 2026** deadline, follow this checklist.

---

## 1. Codebase Preparation (GitHub)
- [ ] **Create a Public Git Repository**:
  - Push the code in `capstone-rpg` to a public repository (GitHub or GitLab).
  - Ensure the repository is publicly accessible so judges can inspect the code.
- [ ] **Document the README.md**:
  - Summarize the RPG game concept.
  - Explain the multi-agent design (GM and Companion NPC).
  - Include quickstart instructions for installing dependencies (`agents-cli install`) and running the CLI (`uv run python app/main.py`).
  - Explain how to execute BDD tests (`uv run behave`) and evaluations (`agents-cli eval run`).
- [ ] **Verify Code Cleanup**:
  - Run `agents-cli lint` to check code format and quality constraints.
  - Double check that there are no hardcoded API keys or personal credentials in `.env` files.

---

## 2. Video Demonstration (2–3 Minutes)
- [ ] **Record a Screenshare Video**:
  - Showcase the command-line game loop in action using `uv run python app/main.py`.
  - Record yourself choosing a class (Wizard or Fighter).
  - Show the Game Master agent generating routes and narrating rooms.
  - Show at least one combat encounter with the ASCII art rendering.
  - Demonstrate a turn where the NPC Companion takes a cooperative tactical action.
- [ ] **Provide a Quick Technical Walkthrough**:
  - Briefly open the code structure in your IDE.
  - Show the Gherkin feature files in `features/` to highlight your BDD spec-driven architecture.
  - Mention your use of the Google ADK and `agents-cli eval` for agent quality metrics.
- [ ] **Upload and Host the Video**:
  - Upload the video to YouTube (as public or unlisted), Loom, or Google Drive (ensure public viewing access is enabled).

---

## 3. Evaluation & Testing Validation
- [ ] **Run all BDD scenarios**:
  - Execute `uv run behave` and screenshot or copy the terminal output showing `9 scenarios passed, 52 steps passed`.
- [ ] **Execute the Agent Evaluator**:
  - Run `agents-cli eval run` to regenerate the traces and check scores.
  - Locate the generated HTML results file (`artifacts/grade_results/results_*.html`) and open it in a browser to inspect the detailed LLM-as-a-judge feedback.
- [ ] **Add test outputs to documentation**:
  - Include the test and evaluation results in your Kaggle Writeup to demonstrate technical quality.

---

## 4. Deployment (Optional but Recommended)
- [ ] **Decide on Deployment**:
  - While live deployment is not strictly mandatory for the capstone, presenting a deployed agent adds major points to the **Implementation Quality** and **Solution Design** criteria.
- [ ] **Deploy to Agent Runtime**:
  - Run `agents-cli deploy` inside `capstone-rpg` to package the GM agent and deploy it to the Google Cloud Gemini Enterprise platform.
  - Ensure your GCP project permissions (`kaggle-ai-agents-478322`) are active and your gcloud CLI is authenticated.

---

## 5. Submit to Kaggle
- [ ] **Format the Kaggle Writeup**:
  - Copy the drafted content from your `kaggle_writeup.md` artifact.
  - Publish the writeup on the Kaggle competition discussion panel or form as requested by the competition organizers.
- [ ] **Fill the Submission Form**:
  - Provide the URL of your public GitHub repository.
  - Provide the link to your video demonstration.
  - Include the deployed agent link or registration endpoint (if deployed).
  - Submit before the deadline: **July 6, 2026, at 11:59 PM PT**.
