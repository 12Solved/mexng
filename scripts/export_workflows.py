import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mailextractor.app.config import config
from mailextractor.models import WorkflowModel

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

def sanitize_filename(name):
    """Sanitize workflow name for use in filename"""
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = sanitized.strip('. ')
    sanitized = re.sub(r'[_\s]+', '_', sanitized)
    return sanitized[:100] if sanitized else 'unnamed'

output_dir = ""
if len(sys.argv) > 1:
    output_dir = sys.argv[1]
else: 
    print("No output path provided.")
    sys.exit(1)

# Create output directory if it doesn't exist
try:
    os.makedirs(output_dir, exist_ok=True)
    print(f"Exporting workflows to: {output_dir}")
except OSError as e:
    print(f"Error creating directory '{output_dir}': {e}")
    sys.exit(1)


session = Session()
try:
    # Get all workflows from database
    workflows = session.query(WorkflowModel).all()
    
    if not workflows:
        print("No workflows found in database")
        session.close()
        sys.exit(0)
    
    print(f"Found {len(workflows)} workflow(s) to export")
    
    success_count = 0
    failure_count = 0
    
    for workflow in workflows:
        try:
            # Generate filename: {id}_{sanitized_name}.json
            sanitized_name = sanitize_filename(workflow.name)
            filename = f"{workflow.id}_{sanitized_name}.json"
            filepath = os.path.join(output_dir, filename)
            
            # Write workflow JSON to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(workflow.workflow_json, f, indent=2, ensure_ascii=False)
            
            print(f"  ✓ Exported: {filename}")
            success_count += 1
            
        except IOError as e:
            print(f"  ✗ Failed to write {workflow.id}_{workflow.name}: {e}")
            failure_count += 1
        except Exception as e:
            print(f"  ✗ Error exporting workflow {workflow.id}: {e}")
            failure_count += 1
    
    print(f"\nCompleted: {success_count} succeeded, {failure_count} failed out of {len(workflows)} total")

except Exception as e:
    print(f"Error accessing database: {e}")
    sys.exit(1)
finally:
    session.close()