# AI-Based Timetable Generator

An intelligent, web-based academic timetable management system designed to simplify timetable preparation using optimization techniques and automated scheduling.

## About the Project

The **AI-Based Timetable Generator** is a web application developed to automate and simplify the academic timetable preparation process.

Traditional timetable preparation involves manually assigning teachers, subjects, classrooms and time slots. This can become complicated when dealing with multiple classes, teachers, subjects and laboratory sessions.

Our project aims to solve this problem by providing a centralized platform for academic data management and automated timetable generation using a Genetic Algorithm-based optimization approach.

The application is being developed using Python, Flask, MySQL and frontend technologies.

## Objectives

- Automate academic timetable preparation.
- Reduce manual scheduling effort.
- Manage teachers, classes, subjects and classrooms.
- Maintain academic information in a centralized database.
- Support Excel-based academic data import.
- Identify teacher, classroom and class scheduling conflicts.
- Handle laboratory sessions requiring consecutive periods.
- Generate organized academic timetables.

## Technologies Used

### Frontend
- HTML5
- CSS3
- JavaScript
- Jinja2

### Backend
- Python
- Flask
- Flask-Login

### Database
- MySQL

### Optimization
- Genetic Algorithm
- Constraint Handling
- Conflict Detection
- Timetable Validation

### Other Tools and Libraries
- OpenPyXL – Excel file processing
- Visual Studio Code – Development environment
- MySQL Workbench – Database management
- Git and GitHub – Version control

## Key Features

### 1. User Authentication
- Login functionality.
- Registration functionality.
- User session management.

### 2. Dashboard
- Centralized application interface.
- Navigation to academic management modules.

### 3. Teacher Management
- Add teacher information.
- View teacher records.
- Update and manage teacher details.

### 4. Class Management
- Manage academic classes and sections.
- Maintain class-related information.

### 5. Subject Management
- Maintain subject records.
- Store information required for timetable preparation.

### 6. Room Management
- Manage classrooms and laboratories.
- Maintain room-related information.

### 7. Excel Import
- Import academic information through Excel files.
- Process spreadsheet data using OpenPyXL.

### 8. Timetable Optimization
- Genetic Algorithm-based scheduling approach.
- Constraint-aware timetable generation.
- Candidate timetable evaluation.

### 9. Conflict Detection and Validation
- Teacher scheduling conflict checks.
- Classroom allocation conflict checks.
- Class scheduling conflict checks.
- Laboratory scheduling validation.

*Note: Timetable optimization, complete constraint validation and final integration are under development. Feature availability may vary as development progresses.*

## Project Architecture

The project follows a modular Flask-based architecture.

```text
timetable-ai/
│
├── app.py
├── config.py
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── optimizer/
│   ├── scheduler.py
│   ├── genetic_optimizer.py
│   ├── constraints.py
│   ├── conflict_checker.py
│   ├── validator.py
│   └── workload.py
│
├── routes/
│   ├── auth.py
│   ├── dashboard.py
│   ├── teachers.py
│   ├── classes.py
│   ├── subjects.py
│   ├── rooms.py
│   ├── constraints.py
│   ├── timetable.py
│   └── imports.py
│
├── utils/
│   ├── helpers.py
│   └── crud.py
│
├── templates/
│
├── static/
│
└── README.md
```

## Installation and Setup

Follow these steps to run the project locally.

### Prerequisites

Install the following software:

- Python 3.x
- MySQL Server
- MySQL Workbench (recommended)
- Git

### Step 1: Clone the Repository

```bash
git clone https://github.com/ZavedAkthar/timetable-ai-generator.git
```

### Step 2: Open the Project Directory

```bash
cd timetable-ai-generator
```

### Step 3: Create a Virtual Environment

```bash
python -m venv venv
```

### Step 4: Activate the Virtual Environment

For Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

If the requirements file is not available, install the required packages individually after checking the project's imports:

```bash
pip install flask flask-login mysql-connector-python openpyxl
```

### Step 6: Configure the Database

1. Open MySQL Workbench.
2. Create the database named `timetable_ai`.
3. Configure your database credentials in the application configuration.
4. Execute the database schema script if setting up a fresh database.

**Important:** The schema script may contain table deletion statements. Do not execute it against an existing database without checking its contents and backing up your data.

### Step 7: Run the Application

```bash
python app.py
```

### Step 8: Open in Browser

```text
http://127.0.0.1:5000/
```

The application should now be accessible locally if the database and application configuration are correct.

## Database Structure

The project uses a MySQL relational database named:

` timetable_ai `

Major database tables include:

| Table | Description |
|---|---|
| users | User account information |
| teachers | Teacher details |
| classes | Academic class information |
| rooms | Classroom and laboratory details |
| subjects | Subject information |
| time_slots | Available timetable periods |
| teacher_availability | Teacher availability |
| constraints | Scheduling constraints |
| timetable | Timetable allocations |
| notifications | Notification records |

## Genetic Algorithm Approach

The project uses a Genetic Algorithm-based approach for timetable optimization.

The general optimization workflow is:

1. Initialize a population of candidate timetables.
2. Evaluate each candidate using a fitness function.
3. Select suitable candidate solutions.
4. Perform crossover operations.
5. Apply mutation operations.
6. Evaluate the new timetable arrangements.
7. Repeat the process until a stopping condition is reached.

The objective is to find timetable arrangements that satisfy mandatory academic constraints while improving scheduling quality.

## Scheduling Constraints

The optimization process is designed to consider the following constraints:

### Hard Constraints
- A teacher cannot be assigned to multiple classes simultaneously.
- A class cannot attend multiple subjects simultaneously.
- A room cannot be allocated to multiple sessions simultaneously.
- Teacher availability must be respected.
- Required subject hours must be maintained.
- Laboratory sessions must occupy the required consecutive periods.

### Soft Constraints
- Balanced teacher workload.
- Better distribution of subjects.
- Reduced unnecessary gaps.
- Improved timetable organization.

The exact implementation and validation of these constraints are part of the ongoing development process.

## Current Development Status

| Module | Status |
|---|---|
| Requirement Analysis | Completed |
| Project Structure | Created |
| Database Design | Developed |
| Flask Application Setup | Developed |
| Frontend Development | Initial implementation |
| User Authentication | Initial implementation |
| Teacher Management | Initial implementation |
| Class Management | Initial implementation |
| Subject Management | Initial implementation |
| Room Management | Initial implementation |
| Excel Import | Developed and initially tested |
| Genetic Algorithm | Under development |
| Constraint Validation | Under development |
| Complete Timetable Generation | Pending completion |
| Final Integration | Pending |
| Comprehensive Testing | Pending |

## Future Enhancements

- Complete Genetic Algorithm integration.
- Improve timetable optimization.
- Implement complete constraint validation.
- Improve laboratory scheduling.
- Add timetable export functionality.
- Improve dashboard visualization.
- Add advanced reporting.
- Improve deployment and application security.

## Team Members

This project is developed by a team of four students.

| Name | University ID |
|---|---|
| Madduri Karthik Yadav | 24STUCHH010615 |
| Mohammad Zaved Akthar | 24STUCHH010427 |
| Amrute Sahoo | 24STUCHH010231 |
| Shivanolla Aavani | 24STUCHH010012 |

**Institution:**  
ICFAI Foundation for Higher Education, Hyderabad

**Faculty:**  
Faculty of Science & Technology

**Academic Year:** 2026–2027

## Project Repository

GitHub:  
https://github.com/ZavedAkthar/timetable-ai-generator

## License

This project is developed for academic purposes as part of the Bachelor of Technology programme.

---

**AI-Based Timetable Generator**  
*Making Academic Scheduling Smarter and More Efficient.*
