# Collection of Resources and Findings During Our Time at ICTP
## Before starting
* Download and install pylon library, give sudo permit to install USB rules, in case of doubt, follow `Install.txt` instructions.

[Install link, click here:](https://www.baslerweb.com/en/downloads/software/3032421996/?downloadCategory.values.label.data=pylon)

* Setup a .venv in the Top-level of the local repository.

```Bash
cd <git_address>
python3 -m venv .venv
```
or create it using vscode environemnts.

Activate the .venv and install the requirements library
```Bash
source .venv/bin/activate
pip install -r venv_requirements/requirements.txt
```

*To run the software

```Bash
chmod +x Run.sh #Only the first time
source Run.sh
```

## Done so far:
  * Made adjustments to the main DHM code:
  * Organized the program to follow a logical sequence of operations
  * Added functionality to perform all operations with a single click
  * Resolved issues with negative/positive cells in phase computation
  * Enabled batch processing of multiple images
  * Fixed ROI selection – now works correctly from the first click
  * Corrected the thickness functions – each function now opens in a separate, * independent window

## To do:
  * Improve the noise reduction functionality using Artificial Intelligence
  * Train a machine learning model for remote, label-free, automated point-of-care disease diagnosis.
  * Use features extracted from DHM to train ML algorithms for detecting diseases * such as malaria and sickle cell anemia.

