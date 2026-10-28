# Digital Twin for Yield Calculation and Blank Optimisation

A Streamlit-based engineering prototype for automated sheet-metal blank nesting, material-yield calculation, priority-part identification, external yield comparison, and controlled blank-optimisation studies.

> **Current version:** Streamlit 3.5.1  
> **Status:** Demonstration / engineering prototype  
> **PLM connection:** Simulated. No live PLM system is contacted.

## Purpose

The tool supports early evaluation of BIW and other sheet-metal blank layouts to:

- calculate blank material yield;
- compare multiple nesting methods;
- evaluate standard, manually entered, and DXF geometries;
- identify parts below the project yield target;
- compare internal results with Cost Engineering and supplier yield values;
- simulate publishing results to PLM; and
- study manual blank-geometry optimisation such as convex-corner chamfering.

## Main Workflow

1. Project Setup
2. Fetch Parts from Mock PLM
3. Geometry Input and Validation
4. Part Type, Method, and Nesting Parameters
5. Nesting Analysis and Graphical Results
6. Priority Parts and External Yield Validation
7. Blank Optimisation

## Key Features

### Project Setup

- Project code validation beginning with `5465`
- Gateway selection from `DR0` to `DR5`
- Group selection: Upperbody or Underbody
- Module selection
- Editable project yield target, default `65%`

### Mock PLM Part Fetch

- Part-number validation beginning with `5465`
- Editable PLM description
- Editable material and thickness
- Part-selection checkboxes
- Simulated DXF availability status

Demo part numbers:

```text
54650001
54650002
54650003
54650004
```

Other part numbers beginning with `5465` create an assumed demonstration record.

### Geometry Input

- Manual DXF upload
- Manual coordinate entry
- Standard geometry library:
  - Rectangle
  - Right triangle
  - General triangle
  - Trapezoid
  - L-shape
  - T-shape
  - Circle
  - Ellipse
  - Regular polygon
  - Custom coordinate geometry
- Straight and curved DXF processing
- Polygon validity and blank-area calculation

### Nesting Methods

Manual mode supports:

- Bounding Box
- Rotated Close-Stack
- Alternate 0°/180° Interlocking
- Mirror Pair

Auto mode evaluates the applicable methods and ranks valid layouts using:

- 10° coarse-angle search;
- 2° fine-angle search around the best coarse candidates;
- overlap validation;
- quantity, pitch, strip-width, strip-length, and yield calculation; and
- top-four result ranking.

### Yield and Priority Analysis

The tool displays:

- current yield;
- calculated best yield;
- project target;
- yield shortfall;
- target status;
- priority classification;
- best method and angle; and
- graphical nesting layouts.

### Mock PLM Publication

The Nesting Analysis page includes a demonstration action to publish selected results to Mock PLM and display a publication status message.

No live PLM record is updated.

### Cost Engineering and Supplier Comparison

For priority parts, the user can independently provide:

- Cost Engineering blank layout;
- Cost Engineering yield;
- supplier blank layout; and
- supplier yield.

The application compares both external yields with the internal Digital Twin calculation.

### Blank Optimisation

The user can select:

- Manual Optimisation; or
- AI-Based Optimisation.

Manual Optimisation currently supports chamfering eligible convex exterior corners using a user-entered setback value. The tool then validates the revised polygon, reruns Auto Nesting, and compares:

- original and revised blank area;
- original and revised best yield;
- best method and angle;
- pitch and quantity; and
- existing and revised graphical layouts.

Concave or re-entrant corners are preserved. The applied chamfer is limited to 45% of the shorter adjacent edge to reduce the risk of crossing adjacent chamfers.

AI-Based Optimisation is currently a structured workflow placeholder for a later development phase.

## Project Files

```text
app_streamlit_v351.py
nesting_backend_v351.py
requirements.txt
README.md
.gitignore
```

For GitHub deployment, rename:

```text
requirements_v351.txt
```

to:

```text
requirements.txt
```

Keep the Python filenames unchanged because the application imports:

```python
from nesting_backend_v351 import *
```

## Local Installation

### 1. Install Python

Use a supported Python version. Python 3.11 or 3.12 is recommended for testing.

### 2. Create a virtual environment

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Run the application

```bat
streamlit run app_streamlit_v351.py
```

The application should open in the default browser. The sidebar should display:

```text
Digital Twin for Yield Calculation and Blank Optimisation
App version: Streamlit 3.5.1
```

## Recommended Test Sequence

1. Enter a project code beginning with `5465`.
2. Set gateway, group, module, and project yield target.
3. Fetch `54650001` from Mock PLM.
4. Select the part and continue.
5. Choose Standard Shapes and validate a rectangle.
6. Select common nesting parameters.
7. Run Auto Nesting.
8. Review the best and top-four layouts.
9. Publish the result to Mock PLM.
10. Review the priority-parts page.
11. Enter Cost Engineering and supplier yields.
12. Proceed to Blank Optimisation.
13. Apply a manual chamfer and compare existing versus revised yield.

## Streamlit Community Cloud Deployment

1. Create a GitHub repository.
2. Upload the application files to the repository root.
3. Ensure the dependency file is named `requirements.txt`.
4. Sign in to Streamlit Community Cloud.
5. Create a new app from the GitHub repository.
6. Select:

```text
Branch: main
Main file path: app_streamlit_v351.py
```

7. Select an appropriate supported Python version in Advanced Settings.
8. Deploy and review the build log.

## Data and Security Warning

Do not upload confidential, proprietary, supplier-controlled, cost-sensitive, or released vehicle data to a public deployment.

For public demonstrations, use only:

- synthetic geometry;
- approved sample DXFs;
- demonstration part numbers; and
- non-confidential yield values.

For real engineering data, use an approved internal deployment environment with authentication, access control, secure storage, audit logging, and enterprise cybersecurity approval.

## Current Limitations

- No live PLM connector
- Mock PLM publication is session-based
- Uploaded files are not permanently stored
- Session data may be lost after browser or server restart
- No user authentication
- No role-based access control
- No permanent database
- No actual email-sending service
- AI-Based Optimisation is not yet implemented
- Manual chamfer evaluates geometric nesting only

## Engineering Disclaimer

The calculated results support engineering evaluation but do not constitute automatic design approval.

Blank-geometry modifications require review for:

- forming feasibility;
- structural performance;
- crashworthiness;
- durability;
- joining and sealing;
- tooling feasibility;
- dimensional requirements;
- supplier constraints; and
- company standards.

## Planned Enhancements

- Persistent project and result database
- Secure user authentication
- Real PLM input/output adapter
- Permanent uploaded-file storage
- Publication reports and traceability IDs
- Outlook-ready email notification
- Additional manual geometry operations
- Configurable engineering-rule checks
- AI-assisted blank-optimisation suggestions
- Calculation regression tests
- Internal enterprise deployment
