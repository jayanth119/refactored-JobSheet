# 📋 refactored-JobSheet

A **Streamlit-based Job Sheet Management System** designed for mobile/computer repair shops. The system streamlines job tracking, customer and product management, PDF generation, and automated communication via email and WhatsApp.

---

## 🚀 Project Description

`refactored-JobSheet` is a lightweight, modular, and database-driven application that helps small to mid-size repair businesses handle everyday operations efficiently. Built using **Python, Streamlit, and SQLite**, the app provides an intuitive interface for technicians and administrators to manage repair jobs, customer records, and inventory — all in one place.

Whether it's printing a job receipt, managing device repairs, or tracking customer history, this app does it all with minimal setup and no server dependencies.

---

## 🔑 Key Features

| Feature                  | Description                                                                 |
|--------------------------|-----------------------------------------------------------------------------|
| 📦 SQLite Integration    | Local, structured data storage for persistent state                         |
| 🧾 PDF Job Sheets        | Automatically generate professional-looking job reports                     |
| 📤 Email/WhatsApp Share | Send job sheets directly to customers via email or WhatsApp (Twilio-ready) |
| 🔐 User Authentication   | Role-based login (Admin, Staff)                                             |
| 🛠️ Job Management       | Add, edit, track and close repair jobs with real-time updates               |
| 👥 Customer Management   | Manage customer profiles (add/edit/delete/search)                           |
| 📦 Product Inventory     | Track spare parts and accessories                                           |
| 🔍 Smart Search          | Instantly search through jobs and customers                                 |
| 📈 Reporting & Analytics | Generate job completion reports, revenue stats, etc.                        |

---

<!-- ## 📁 Project Structure

```plaintext
refactored-JobSheet/
│
├── main.py                         # Entry point for the Streamlit app
├── requirements.txt                # Python dependencies
│
├── database/
│   └── repair_shop.db              # SQLite database file
│
├── ui/
│   ├── main_window.py              # Routing and layout logic
│   ├── login_page.py               # Login and authentication logic
│   ├── home_page.py                # Dashboard with navigation
│   ├── add_job_page.py             # Add new jobs & generate job sheets
│   ├── job_management_page.py      # Manage/edit/export jobs
│   ├── customer_management_page.py # CRUD for customers
│   ├── product_management_page.py  # Manage products & pricing
│   ├── reporting_page.py           # Analytics and reporting
│   └── navigation_bar.py           # Sidebar/topbar navigation
│
├── utils/
│   ├── database_manager.py         # DB operations (CRUD)
│   ├── pdf_generator.py            # Job sheet PDF builder
│   └── email_sender.py             # Email sender utility
│
└── assets/
    └── logo.png                    # App branding/logo
```` -->
<!-- 
--- -->

## 🧠 Mermaid Diagrams

### 📂 Folder Structure

```mermaid
graph TD
A[main.py] --> B[ui/]
A --> C[utils/]
A --> D[database/]
A --> E[assets/]

B --> B1[main_window.py]
B --> B2[login_page.py]
B --> B3[home_page.py]
B --> B4[add_job_page.py]
B --> B5[job_management_page.py]
B --> B6[customer_management_page.py]
B --> B7[product_management_page.py]
B --> B8[reporting_page.py]
B --> B9[navigation_bar.py]

C --> C1[database_manager.py]
C --> C2[pdf_generator.py]
C --> C3[email_sender.py]
```

---

### 🔐 Authentication Flow

```mermaid
flowchart TD
LoginForm --> DB[Check users table]
DB -->|Valid| Dashboard
DB -->|Invalid| ErrorMessage
```

---

### 🔄 Job Lifecycle Flow

```mermaid
flowchart LR
NewJob --> Ongoing
Ongoing --> Finished
Finished -->|Export| PDFJobSheet
PDFJobSheet -->|Send| EmailClient
```

---

### 📈 Reporting Flow

```mermaid
graph TD
Customer --> AddCustomer --> Jobs
Jobs --> AddJob --> StatusUpdate
StatusUpdate --> ReportGen
ReportGen --> PDFExport --> EmailOrWhatsApp
```

---

## 📊 Software Design Diagrams

---

### 1. ✅ **Use Case Diagram** – Job Sheet System

```mermaid
graph TD
  User((User)) -->|Login| AuthSystem
  User -->|Add Job| JobSystem
  User -->|Manage Customers| CustomerSystem
  User -->|Manage Products| ProductSystem
  User -->|Generate PDF| PDFGenerator
  User -->|Send Email| EmailSender
  User -->|Send WhatsApp| WhatsAppAPI
  Admin((Admin)) -->|View Reports| ReportSystem
  Admin -->|Manage Users| UserManagement
```

---

### 2. 🔄 **Sequence Diagram** – Job Creation & Notification Flow

```mermaid
sequenceDiagram
    participant User
    participant StreamlitUI
    participant DatabaseManager
    participant PDFGenerator
    participant EmailSender
    participant WhatsAppAPI

    User->>StreamlitUI: Fill job + customer form
    StreamlitUI->>DatabaseManager: Insert customer & job
    DatabaseManager-->>StreamlitUI: Confirmation
    StreamlitUI->>PDFGenerator: Generate job sheet
    PDFGenerator-->>StreamlitUI: PDF file path
    StreamlitUI->>EmailSender: Send PDF to user
    EmailSender-->>StreamlitUI: Email sent
    StreamlitUI->>WhatsAppAPI: Send PDF on WhatsApp
    WhatsAppAPI-->>StreamlitUI: WhatsApp sent
```


### 3 🧩 Component Diagram – Application Architecture (Fixed ✅)

```mermaid
graph LR
  A[Streamlit UI] --> B[UI Pages: Login, Home, Jobs, Reports]
  A --> C[Navigation Component]
  B --> D[Database Manager]
  B --> E[PDF Generator]
  B --> F[Email Sender]
  D --> G[SQLite Database]
  F --> H[SMTP or Email API]
```

---


### 4. 🏗️ **Class Diagram** – Major Python Modules

```mermaid
classDiagram
    class DatabaseManager {
        +connect()
        +execute_query()
        +fetch_data()
    }

    class PDFGenerator {
        +generate_job_sheet()
        +export_pdf()
    }

    class EmailSender {
        +send_email(to, pdf_path)
    }

    class LoginPage {
        +authenticate_user()
    }

    class AddJobPage {
        +submit_job()
        +capture_customer()
    }

    class Job {
        +id
        +customer
        +device_type
        +status
        +created_date
    }

    AddJobPage --> Job
    AddJobPage --> DatabaseManager
    PDFGenerator --> Job
    EmailSender --> PDFGenerator
```

---

### 5. 🔁 **Activity Diagram** – Job Submission

```mermaid
graph TD
  Start --> FillForm
  FillForm --> ValidateData
  ValidateData -- Valid --> SaveToDB
  ValidateData -- Invalid --> ShowError
  SaveToDB --> GeneratePDF
  GeneratePDF --> SendEmail
  SendEmail --> SendWhatsApp
  SendWhatsApp --> End
  ShowError --> End
```

---

### 6. 🧪 **Data Flow Diagram (Level 1)**

```mermaid
graph LR
  UserInput -->|Form Data| UI
  UI -->|Process| Controller
  Controller -->|Query| Database
  Controller -->|Call| PDFGenerator
  Controller -->|Call| EmailSender
  Controller -->|Call| WhatsAppSender
  Database -->|Response| Controller
  PDFGenerator -->|Job Sheet PDF| Controller
  EmailSender -->|Email Sent| Controller
  WhatsAppSender -->|Message Sent| Controller
```

---

## 🧾 Summary

These diagrams provide full architectural and functional insight into how your `# refactored-JobSheet` app operates:

| Diagram Type      | Purpose                                                       |
| ----------------- | ------------------------------------------------------------- |
| Use Case Diagram  | Shows system functionality from the user's perspective        |
| Sequence Diagram  | Explains interaction between components during job submission |
| Component Diagram | Shows how modules interact within the system                  |
| Class Diagram     | Illustrates Python module and class structures                |
| Activity Diagram  | Captures the logic behind submitting a repair job             |
| Data Flow Diagram | Visualizes the movement of data across system layers          |

---

## 🛠️ Installation

### 1. Clone the repo

```bash
git clone https://github.com/jayanth119/refactored-JobSheet.git
cd refactored-JobSheet
```

### 2. Setup environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
streamlit run main.py
```

---

## 📌 Example Users (for demo)

| Username | Password | Role  |
| -------- | -------- | ----- |
| admin    | admin123 | Admin |
| staff1   | pass123  | Staff |

---

## 📧 Contact

Built with ❤️ by [Jayanth ](mailto:chjayanth119@gmail.com)
GitHub: [github.com/jayanth119](https://github.com/jayanth119)
```