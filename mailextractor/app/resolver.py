import re


class Resolver:

    pattern = re.compile(r"\$\{([^}]+)\}")

    def resolve(self, value, context):
      if not isinstance(value, str):
        return value

      def replace(match):
        key = match.group(1)
        return str(context.get(key, "${"+key+"}"))

      return self.pattern.sub(replace, value)

    def resolve_config(self, value, context):
      if isinstance(value, dict):
        return {
          k: self.resolve_config(v, context)
          for k, v in value.items()
        }

      return self.resolve(value, context)
