class WorkflowContext:
  def __init__(self, initial_data=None):
    self.data = dict(initial_data or {})

  def set(self, key, value):
    self.data[key] = value

  def get(self, key, default=None):
    return self.data.get(key, default)

  def has(self, key):
    return key in self.data
