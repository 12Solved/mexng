import mimetypes


class ExtractedAttachment:
  """In-memory stand-in for an archive member, shaped like models.Attachment
  but not a mapped SQLAlchemy class since it's never persisted."""

  def __init__(self, filename, content):
    self.id = None
    self.email_id = None
    self.filename = filename
    self.content = content
    self.content_type = mimetypes.guess_type(filename)[0]
    self.size = len(content)
    self.storage_path = None
