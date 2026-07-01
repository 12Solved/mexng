import os
import sys
import glob
from email import policy
from email.parser import BytesParser

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mailextractor.app.config import config
from mailextractor.models import Attachment, Base, Email

engine = create_engine(config.DATABASE_URL)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

email_paths = []
for pattern in sys.argv[1:]:
    matched = glob.glob(pattern)
    if matched:
        email_paths.extend(matched)
    else:
        email_paths.append(pattern) # Add the original pattern if no matches found

if not email_paths:
    print("No email files found.")
    sys.exit(1)

success_count = 0
failure_count = 0

for email_path in email_paths:
    session = Session()
    
    try:
        if not os.path.exists(email_path):
            print(f"{email_path}: File not found")
            failure_count += 1
            continue

        print(f"Processing: {email_path}")
        
        with open(email_path, "rb") as f:
            msg = BytesParser(policy=policy.default).parse(f)

        body = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = part.get_content_disposition()
                content_type = part.get_content_type()

                if content_type == "text/plain" and content_disposition is None:
                    body = part.get_content()

                elif content_disposition == "attachment":

                    file_content = part.get_payload(decode=True)

                    filename = part.get_filename()

                    attachment = Attachment(
                    filename=filename,
                    content_type=content_type,
                    size=len(file_content),
                    content=file_content
                    )

                    attachments.append(attachment)
        else:
            body = msg.get_content()

        email_entry = Email(
            message_id=msg["Message-ID"],
            subject=msg["Subject"],
            sender=msg["From"],
            recipient=msg["To"],
            date=msg["Date"],
            body=body,
            raw_headers=dict(msg.items())
        )

        email_entry.attachments = attachments

        session.add(email_entry)
        session.commit()
        print(f"Inserted email with ID: {email_entry.id} ({len(attachments)} attachments)")
        success_count += 1
        
    except FileNotFoundError as e:
        print(f"{email_path}: File not found - {e}")
        session.rollback()
        failure_count += 1
    except Exception as e:
        print(f"{email_path}: Error - {e}")
        session.rollback()
        failure_count += 1
    finally:
        session.close()

print(f"\nCompleted: {success_count} succeeded, {failure_count} failed out of {len(email_paths)} total")