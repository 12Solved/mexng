import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mailextractor.app.config import config
from mailextractor.models import WorkflowModel

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

workflow_paths = []
for pattern in sys.argv[1:]:
    matched = glob.glob(pattern)
    if matched:
        workflow_paths.extend(matched)
    else:
        workflow_paths.append(pattern) # Add the original pattern if no matches found

if not workflow_paths:
    print("No workflow files found.")
    sys.exit(1)

success_count = 0
failure_count = 0

for workflow_path in workflow_paths:
    session = Session()
    
    try:
        if not os.path.exists(workflow_path):
            print(f"{workflow_path}: File not found")
            failure_count += 1
            continue

        print(f"Processing: {workflow_path}")

        with open(workflow_path, "r") as f:
            workflow_json = json.load(f)

        # Extract name from JSON or use filename as fallback
        workflow_name = workflow_json.get("name", os.path.splitext(os.path.basename(workflow_path))[0])
        
        workflow = WorkflowModel(
            name=workflow_name,
            description=workflow_json.get("description"),
            workflow_json=workflow_json,
            enabled=True
        )
        
        session.add(workflow)
        session.commit()
        print(f"Inserted workflow '{workflow_name}' with ID: {workflow.id}")
        success_count += 1
        
    except json.JSONDecodeError as e:
        print(f"{workflow_path}: Invalid JSON - {e}")
        session.rollback()
        failure_count += 1
    except FileNotFoundError as e:
        print(f"{workflow_path}: File not found - {e}")
        session.rollback()
        failure_count += 1
    except Exception as e:
        print(f"{workflow_path}: Error - {e}")
        session.rollback()
        failure_count += 1
    finally:
        session.close()

print(f"\nCompleted: {success_count} succeeded, {failure_count} failed out of {len(workflow_paths)} total")
