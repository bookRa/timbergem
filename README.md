# TimberGem 💎

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/your-username/timbergem)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**TimberGem** is a full-stack MVP designed to transform static construction documents into an intelligent, queryable "digital twin." By combining a human-in-the-loop (HITL) annotation interface with modern OCR and Large Language Models (LLMs), TimberGem aims to de-risk and automate the complex process of construction scope analysis and estimation.

This project moves beyond simple document viewing by creating a structured, interconnected **Unified Context Model**, enabling a machine to understand the content of a blueprint in a way that was previously only possible for a human expert.

## ✨ Core Features (MVP)

* **PDF Ingestion:** Upload and process multi-page construction documents.
* **Human-in-the-Loop Annotation:** A web-based UI for users to visually segment documents, identifying key regions like title blocks, drawing areas, notes, and legends.
* **Intelligent OCR:** Run targeted OCR on human-annotated regions to ensure high-accuracy text extraction.
* **Structured Context Store:** Save the combination of visual (annotations) and semantic (text) data into a clean, queryable JSON format.
* **LLM-Powered Q&A:** An interface to ask questions about the document, with an LLM using the generated context store to provide accurate, context-aware answers.

## 🛠️ Tech Stack

* **Backend:** Python 3.10+ with **Flask** or **FastAPI**
* **PDF Processing:** **PyMuPDF**
* **OCR:** Any cloud-based OCR service (e.g., **Google Vision API**, **Amazon Textract**)
* **Frontend:** **React** (with Vite) or **Vue.js**
* **Annotation UI:**
    * **Branch `main`:** A custom UI built with **Fabric.js** or **Konva.js**.
    * **Branch `feature/label-studio`:** Integration with **Label Studio**.
* **Testing:** **Pytest** for backend testing.

## 🗺️ Project Roadmap

This project is broken down into four key phases, moving from foundational setup to a fully functional MVP.

### **Phase 1: Foundation & The Annotation UI**

*Goal: Set up the core application and enable users to upload and visually annotate a construction document.*

* **Milestone 1.1: Project Scaffolding & PDF Upload**
    * **User Story:** As a developer, I can set up a monorepo with a `backend` (Flask/FastAPI) and `frontend` (React) directory, with basic communication established.
    * **User Story:** As a user, I can visit the web app and use a file input to upload a PDF document to the backend.

* **Milestone 1.2: PDF Processing & Page Rendering**
    * **User Story:** As a user, after uploading a PDF, I want the backend to process it and render each page as a high-resolution image that can be requested by the frontend.
    * **User Story:** As a user, I can see the pages of my uploaded document displayed in the browser, ready for annotation.

* **Milestone 1.3: Annotation Interface & Data Persistence**
    * **User Story:** As a user, I can draw bounding boxes over key areas on a page image.
    * **User Story:** As a user, after drawing a box, I can assign a tag to it (e.g., `TitleBlock`, `NotesArea`, `Legend`, `DrawingArea`) from a predefined list.
    * **User Story:** As a user, I can press a "Save" button to send my annotation data (page number, coordinates, tags) to the backend, which saves it as a structured JSON file.

### **Phase 2: Guided Digitization & Context Generation**

*Goal: Use the human-provided annotations to perform intelligent OCR and build the initial structured JSON context file.*

* **Milestone 2.1: Intelligent OCR Pipeline**
    * **User Story:** As a developer, when annotations are saved, I want a backend process to trigger that uses the bounding box coordinates to crop the relevant image regions.
    * **User Story:** As a developer, I want to send these cropped, semantically-tagged image regions to an OCR service to get high-accuracy text.

* **Milestone 2.2: Building the Unified Context Model v1**
    * **User Story:** As a developer, I want to combine the annotation data (tags, coordinates) with the extracted OCR text into a single, well-structured JSON file representing the entire document. This file is our first "Unified Context Model".

### **Phase 3: Basic Q&A and LLM Integration**

*Goal: Create an interface for the LLM to use the context model to answer questions.*

* **Milestone 3.1: Context-Aware Backend API**
    * **User Story:** As a developer, I can create a new API endpoint (e.g., `/api/ask`) that accepts a user's question.

* **Milestone 3.2: Simple RAG Implementation**
    * **User Story:** As a developer, when a question is received, the backend should load the corresponding context JSON, find the most relevant sections (based on keywords or simple embeddings), and formulate a prompt for an LLM.
    * **User Story:** As a user, I can type a question into a text box in the UI and have the system provide an answer generated by an LLM that has been given the relevant context from my document.

---

## 🎨 UI Development Strategy: A/B Branching

To accelerate development while ensuring a powerful end-product, we will pursue two UI strategies in parallel branches.

### Branch: `main` (or `develop`)
**Strategy: Roll Your Own UI**
This branch will contain a simple, fast, and tightly integrated annotation UI using a canvas library. This is the quickest path to a demonstrable MVP.

* **Pros:** No external dependencies, full control over the UX, fast to get started.
* **Cons:** Becomes difficult to manage for complex annotation schemas or multi-user setups.

### Branch: `feature/label-studio-integration`
**Strategy: Integrate with Label Studio**
This branch will focus on offloading the complex annotation work to Label Studio, a powerful open-source data labeling tool.

* **Pros:** Extremely powerful, handles complex schemas, built-in user management, highly extensible.
* **Cons:** Higher initial setup complexity, requires running a separate service, learning curve for its API.
* **Integration Steps:**
    1.  Set up Label Studio via Docker.
    2.  Use the Label Studio API to create a new project and upload the PDF pages as tasks.
    3.  Build a simple "dashboard" UI in TimberGem that links out to the relevant Label Studio project.
    4.  Use Label Studio webhooks or its API to export the completed annotations back into the TimberGem backend for processing.

---

## 📂 Directory Structure

```

timbergem/
├── backend/
│   ├── app/
│   │   ├── **init**.py
│   │   ├── main.py         \# Flask/FastAPI app definition
│   │   ├── models.py       \# Pydantic models for API
│   │   └── routes.py       \# API endpoints
│   ├── tests/              \# Pytest tests
│   ├── venv/
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/     \# React components
│   │   │   └── AnnotationCanvas.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── data/                   \# Output directory for processed PDFs
│   └── processed/
│       └── [document\_id]/
│           ├── page\_1.png
│           ├── page\_2.png
│           └── context.json
├── .gitignore
└── README.md

```

## 🚀 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/timbergem.git](https://github.com/your-username/timbergem.git)
    cd timbergem
    ```

2.  **Setup Backend:**
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
    *Create a `.env` file and add your API keys (e.g., for Google Vision AI).*

3.  **Setup Frontend:**
    ```bash
    cd frontend
    npm install
    ```

4.  **Run the Application:**
    * In terminal 1 (from `backend` directory): `flask run` or `uvicorn app.main:app --reload`
    * In terminal 2 (from `frontend` directory): `npm run dev`

5.  Open your browser to `http://localhost:5173` (or as specified by Vite).

---

## ✅ Roadmap Checklist

### Phase 1: Foundation & Annotation UI
-   [x] **M1.1:** Setup backend and frontend project structure.
-   [x] **M1.1:** Create `/api/upload` endpoint on the backend.
-   [x] **M1.1:** Create a file upload component in the frontend.
-   [x] **M1.2:** Implement PDF-to-image conversion logic using PyMuPDF.
-   [x] **M1.2:** Create a paginated view in the frontend to display document images.
-   [x] **M1.3:** **(`main` branch)** Integrate Fabric.js/Konva.js into a React component.
-   [x] **M1.3:** **(`main` branch)** Implement bounding box drawing and tagging functionality.
-   [ ] **M1.3:** **(`feature/label-studio` branch)** Setup Label Studio and create a project template.
-   [ ] **M1.3:** **(`feature/label-studio` branch)** Implement API calls to push tasks to Label Studio.
-   [x] **M1.3:** Create `/api/save_annotations` endpoint.
-   [x] **M1.3:** Implement frontend logic to post annotation data to the backend.

### Phase 2: Guided Digitization
-   [ ] **M2.1:** Write a Python script to process saved annotation JSON.
-   [ ] **M2.1:** Implement image cropping based on bounding box data using Pillow.
-   [ ] **M2.1:** Integrate with a cloud OCR service API.
-   [ ] **M2.2:** Define the final `context.json` schema.
-   [ ] **M2.2:** Implement the logic to merge annotations and OCR text into the final context file.

### Phase 3: LLM Integration
-   [ ] **M3.1:** Create a `/api/ask` endpoint in the backend.
-   [ ] **M3.1:** Create a simple chat interface in the frontend.
-   [ ] **M3.2:** Implement a basic keyword-based context retrieval function.
-   [ ] **M3.2:** Integrate with an LLM API (e.g., OpenAI, Google AI).
-   [ ] **M3.2:** Implement prompt engineering to combine the user's question with the retrieved context.
-   [ ] **M3.2:** Stream the LLM response back to the frontend.
