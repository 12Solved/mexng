import pytz
import tzlocal

from .base_step import Step


class HelloStep(Step):
    """
    Prints a summary of the email to stdout.
    """

    category = "debug"
    node_type = "default"
    args_in = {"email": "Email"}
    args_out = []
    config_schema = {}
    def execute(self, context):
        email = context.get("email")

        local_tz = tzlocal.get_localzone()

        if email.date:
            if email.date.tzinfo is None:
                utc = pytz.utc
                email_date = utc.localize(email.date)
            else:
                email_date = email.date

            local_date = email_date.astimezone(local_tz)

            print(f"Subject: {email.subject}")
            print(f"Received (Local Time): {local_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            print("-" * 50)
