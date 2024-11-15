# ScholarSearch

### Overview
Preparing for institutional accreditation often involves manually collecting and summarizing research publications. This process can be tedious, error-prone, and time-consuming, especially when information is scattered across platforms like Google Scholar, DBLP, and individual records. 

ScholarSearch solves this by:
1. Automating the search for research publications.
2. Summarizing data using customizable queries and methods.
3. Providing outputs in flexible formats like Excel, Word, or BibTeX.

---

## Features
- **Author-wise Summary Generation**: Includes citation metrics like h-index and i10-index.
- **RAG Pipeline**: Offers paper recommendations, author publication summaries, and semantic search capabilities.
- **Custom Queries and Filtering**: Filter data by years, topics, authors, affiliations, publication types, and locations.
- **Flexible Integration**: Available as a website, API, or Excel extension.
- **Comprehensive Dashboards**: Showcasing research contributions and collaborations.

---

## Tech Stack
- **Backend**: Aggregates data from multiple academic databases.
- **Frontend**: Provides user-friendly interfaces for queries and dashboards.
- **Database**: Stores queried results and author information for faster and more efficient access.
- **Programming Paradigm**: Utilizes asynchronous programming for parallel processing and reduced computation time.

---

## Benefits
- **Time-Efficient**: Automates the otherwise manual process of collecting and summarizing publications.
- **Error Reduction**: Cross-references data to ensure accuracy.
- **Sustainability**: Minimizes redundant queries, saving energy and computational resources.
- **Enhanced Collaboration**: Identifies potential collaborators or mentors by analyzing publication data.

---

## Usage
ScholarSearch offers three ways to integrate into existing workflows:
1. **Website**: Access a user-friendly platform to manage publications and generate summaries.
2. **Public APIs**: Integrate directly into institutional systems.
3. **Excel Extension**: Use Excel to input data and retrieve summaries effortlessly.

---

## Installation and Setup

### Prerequisites
Ensure the following tools are installed:
- Node.js and npm
- Python 3.x and pip

### Steps
1. **Clone the repository**:
   ```bash
   git clone https://github.com/omkar-334/ScholarSearch.git
   cd mindscape
   ```

2. **Install dependencies**:
   - For the frontend:
     ```bash
     npm install
     ```
   - For the backend:
     ```bash
     pip install -r requirements.txt
     ```

3. **Run the backend server**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Run the frontend server**:
   ```bash
   npm start
   ```

5. Open the app in your browser at `http://localhost:5173` (frontend) and `http://localhost:8000` (backend).

---

## Contribution

ScholarSearch is an open-source project. Contributions are welcome to enhance features or address issues. 

### How to Contribute
1. Fork the repository.
2. Create a new branch:
   ```bash
   git checkout -b feature-name
   ```
3. Make your changes and commit them:
   ```bash
   git commit -m "Description of changes"
   ```
4. Push the branch and submit a pull request.


---

## Future Scope
- Regularly updating author summaries.
- Integration with established databases like Google Scholar and Scopus for improved accuracy.
- Enhanced author disambiguation using advanced matching algorithms.

---

## References
- [Semantic Scholar](https://www.semanticscholar.org/)
- [Google Scholar](https://scholar.google.com/)
- [Scopus](https://www.scopus.com/home)
- Scholarly references from *Journal of King Saud University* and *PeerJ*.

